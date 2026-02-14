"""
============================================
API/VIEWS.PY — Endpoints REST Toprix
============================================
Endpoints :
  GET  /api/v1/produits/           → recherche + liste
  GET  /api/v1/produits/<slug>/    → détail produit (comparatif)
  GET  /api/v1/categories/         → liste catégories
  GET  /api/v1/categories/<slug>/  → produits d'une catégorie
  GET  /api/v1/marques/            → liste marques
  GET  /api/v1/marques/<nom>/      → produits d'une marque
  GET  /api/v1/blog/               → liste articles
  GET  /api/v1/blog/<slug>/        → détail article
  GET  /api/v1/boutiques/          → liste boutiques
  POST /api/v1/demandes/           → soumettre une demande
"""
import logging
import re
from bson import ObjectId

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from db.mongo import get_comparatif, get_all_stores
from .models import BlogPost, BlogSummary, BlogSpecifications, BlogSection, StoreRequest
from .helpers.search import (
    clean_search_query,
    is_reference_query,
    build_reference_pipeline,
    build_text_search_pipeline,
    filter_by_relevance,
    filter_exact_matches,
)
from .serializers import (
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    StoreRequestSerializer,
)

logger = logging.getLogger('api')

# ============================================
# CONSTANTES
# ============================================
PAGE_SIZE = 12
MAX_PAGE = 100

# Champs à projeter dans les per-store collections
PRODUIT_PROJECTION = {
    '_id': 1,
    'title': 1,
    'price': 1,
    'old_price': 1,
    'brand': 1,
    'category': 1,
    'category_path': 1,
    'product_image': 1,
    'reference': 1,
    'etat_stock': 1,
    'discount': 1,
    'url': 1,
}

# Mapping des champs comparatif
COMPARATIF_KEYS = {
    'reference':        'Réf Mytek',
    'mytek_nom':        'Produit Mytek',
    'mytek_prix':       'Prix Mytek',
    'mytek_stock':      'Stock Mytek',
    'mytek_url':        'URL Mytek',
    'mytek_image':      'Image Mytek',
    'tunisianet_nom':   'Produit Tunisianet',
    'tunisianet_prix':  'Prix Tunisianet',
    'tunisianet_stock': 'Stock Tunisianet',
    'tunisianet_url':   'URL Tunisianet',
    'tunisianet_image': 'Image Tunisianet',
    'spacenet_nom':     'Produit Spacenet',
    'spacenet_prix':    'Prix Spacenet',
    'spacenet_stock':   'Stock Spacenet',
    'spacenet_url':     'URL Spacenet',
    'spacenet_image':   'Image Spacenet',
}

# Boutiques fixes
BOUTIQUES = [
    {'id': 'mytek',       'nom': 'Mytek',       'site_web': 'https://www.mytek.tn'},
    {'id': 'tunisianet',  'nom': 'Tunisianet',  'site_web': 'https://www.tunisianet.com.tn'},
    {'id': 'spacenet',    'nom': 'Spacenet',    'site_web': 'https://spacenet.tn'},
]


# ============================================
# HELPERS
# ============================================

def safe_price(val):
    """Convertit une valeur en float > 0, sinon None."""
    try:
        p = float(val)
        return p if p > 0 else None
    except (ValueError, TypeError):
        return None


def format_produit_from_store(doc, store_name: str) -> dict:
    """
    Transforme un document per-store en format API Produit.
    Champs MongoDB : price, brand, category, product_image, etat_stock, discount, old_price
    """
    return {
        'id': str(doc['_id']),
        'slug': None,                              # pas de slug dans per-store
        'nom': doc.get('title', ''),
        'marque': (doc.get('brand') or '').title(),
        'categorie': doc.get('category', ''),
        'categorie_nom': doc.get('category_path', ''),
        'prix_min': safe_price(doc.get('price')),
        'prix_max': safe_price(doc.get('old_price')),
        'image': doc.get('product_image') or doc.get('image', ''),
        'en_stock': doc.get('etat_stock') == 'En stock',
        'discount': doc.get('discount', 0),
        'reference': doc.get('reference', ''),
        'boutique': store_name,
        'url_boutique': doc.get('url', ''),
    }


def format_produit_from_comparatif(doc) -> dict:
    """
    Transforme un document comparatif en format API Produit (résumé).
    Utilisé pour la recherche dans le comparatif.
    """
    d = {key: doc.get(val) for key, val in COMPARATIF_KEYS.items()}

    nom = d['mytek_nom'] or d['tunisianet_nom'] or d['spacenet_nom'] or ''
    image = d['mytek_image'] or d['tunisianet_image'] or d['spacenet_image'] or ''

    prix = [safe_price(d[k]) for k in ('mytek_prix', 'tunisianet_prix', 'spacenet_prix') if safe_price(d[k])]
    prix_min = min(prix) if prix else None
    prix_max = max(prix) if prix else None

    # Extraire marque depuis le nom (premier mot)
    marque = nom.split()[0].title() if nom else ''

    return {
        'id': str(doc.get('_id', '')),
        'slug': doc.get('Slug', ''),
        'nom': nom,
        'marque': marque,
        'categorie': '',
        'prix_min': prix_min,
        'prix_max': prix_max,
        'image': image,
        'reference': d.get('reference', ''),
    }


def paginate(items: list, page: int, par_page: int = PAGE_SIZE) -> dict:
    """Pagine une liste et retourne le format ReponseAPI."""
    total = len(items)
    start = (page - 1) * par_page
    end = start + par_page
    return {
        'data': items[start:end],
        'meta': {
            'page': page,
            'total_pages': max(1, -(-total // par_page)),  # ceil division
            'total_items': total,
            'par_page': par_page,
        }
    }


def get_page_number(request) -> int:
    try:
        p = int(request.GET.get('page', 1))
        return max(1, min(p, MAX_PAGE))
    except (ValueError, TypeError):
        return 1


# ============================================
# PRODUITS — Recherche et liste
# ============================================

@api_view(['GET'])
def produits_list(request):
    """
    GET /api/v1/produits/
    Params: q, page, categorie, marque

    Logique de recherche :
    - q seul  → Atlas Search (phrase/fuzzy) si index "Text" disponible, sinon fallback regex
    - q + référence détectée → pipeline exact reference match
    - categorie / marque → regex classique sur les champs MongoDB
    - Post-filtrage par pertinence pour queries multi-mots
    """
    q = request.GET.get('q', '').strip()
    categorie = request.GET.get('categorie', '').strip()
    marque = request.GET.get('marque', '').strip()
    page = get_page_number(request)

    if not q and not categorie and not marque:
        return Response({'data': [], 'meta': {'page': 1, 'total_pages': 0, 'total_items': 0, 'par_page': PAGE_SIZE}})

    # Nettoyage de la requête textuelle
    if q:
        q = clean_search_query(q)
        if not q:
            return Response({'data': [], 'meta': {'page': 1, 'total_pages': 0, 'total_items': 0, 'par_page': PAGE_SIZE}})

    raw_docs = []  # docs bruts MongoDB, chacun avec '_source' = store_name

    if q and not categorie and not marque:
        # ── Recherche textuelle pure : Atlas Search ──────────────────────────
        is_reference = is_reference_query(q)
        query_words = q.split()
        num_words = len(query_words)
        fetch_limit = PAGE_SIZE * 3  # marge pour la déduplication

        if is_reference:
            logger.info(f"Recherche référence : {q}")
            pipeline = build_reference_pipeline(q, skip=0, limit=fetch_limit)
        else:
            logger.info(f"Recherche texte Atlas Search : {q}")
            pipeline = build_text_search_pipeline(q, num_words, skip=0, limit=fetch_limit)

        for get_col, store_name in get_all_stores():
            try:
                col = get_col()
                results = list(col.aggregate(pipeline, allowDiskUse=True))
                for doc in results:
                    doc['_source'] = store_name
                raw_docs.extend(results)
                logger.info(f"{store_name} : {len(results)} résultats Atlas Search")
            except Exception as e:
                # Fallback regex si l'index Atlas Search "Text" n'est pas disponible
                logger.warning(f"Atlas Search indisponible pour {store_name}, fallback regex : {e}")
                try:
                    col = get_col()
                    query_filter = {'title': {'$regex': re.escape(q), '$options': 'i'}}
                    for doc in col.find(query_filter, PRODUIT_PROJECTION).limit(fetch_limit):
                        doc['_source'] = store_name
                        raw_docs.append(doc)
                except Exception as e2:
                    logger.error(f"Fallback regex échoué {store_name} : {e2}")

        # Post-filtrage pertinence sur docs bruts (champ `title`)
        if is_reference and raw_docs:
            raw_docs, _ = filter_exact_matches(raw_docs)
        elif num_words >= 2 and raw_docs:
            raw_docs = filter_by_relevance(raw_docs, query_words, num_words)

    else:
        # ── Filtre par catégorie / marque (regex classique) ──────────────────
        for get_col, store_name in get_all_stores():
            try:
                col = get_col()
                query_filter = {}
                if q:
                    query_filter['title'] = {'$regex': re.escape(q), '$options': 'i'}
                if categorie:
                    query_filter['category'] = {'$regex': re.escape(categorie), '$options': 'i'}
                if marque:
                    query_filter['brand'] = {'$regex': re.escape(marque), '$options': 'i'}
                for doc in col.find(query_filter, PRODUIT_PROJECTION).limit(PAGE_SIZE * 2):
                    doc['_source'] = store_name
                    raw_docs.append(doc)
            except Exception as e:
                logger.error(f"Erreur filtre {store_name} : {e}")
                continue

    # ── Formatage ────────────────────────────────────────────────────────────
    produits = [
        format_produit_from_store(doc, doc.pop('_source'))
        for doc in raw_docs
    ]

    # ── Dédoublonnage par référence (garder le meilleur prix) ────────────────
    seen_refs = {}
    deduped = []
    for p in produits:
        ref = p.get('reference', '')
        if ref and ref in seen_refs:
            if (p['prix_min'] or 0) < (seen_refs[ref]['prix_min'] or 9999999):
                seen_refs[ref] = p
        elif ref:
            seen_refs[ref] = p
            deduped.append(p)
        else:
            deduped.append(p)

    final = [seen_refs.get(p.get('reference'), p) if p.get('reference') else p for p in deduped]

    return Response(paginate(final, page))


# ============================================
# PRODUIT — Détail
# ============================================

@api_view(['GET'])
def produit_detail(request, slug: str):
    """
    GET /api/v1/produits/<slug>/
    - Si slug ressemble à un ObjectId (24 hex) → cherche dans les 3 per-store collections
    - Sinon → cherche dans comparatif par Slug
    """
    IS_OBJECT_ID = bool(re.match(r'^[0-9a-f]{24}$', slug, re.I))

    if IS_OBJECT_ID:
        # Recherche par ObjectId dans les per-store collections
        try:
            oid = ObjectId(slug)
        except Exception:
            return Response({'erreur': 'Identifiant invalide'}, status=status.HTTP_400_BAD_REQUEST)

        for get_col, store_name in get_all_stores():
            try:
                doc = get_col().find_one({'_id': oid})
                if doc:
                    prix = safe_price(doc.get('price'))
                    offre = {
                        'boutique': store_name,
                        'prix': prix,
                        'stock': doc.get('etat_stock', ''),
                        'url': doc.get('url', ''),
                        'image': doc.get('product_image', ''),
                    }
                    return Response({
                        'id': str(doc['_id']),
                        'slug': slug,
                        'nom': doc.get('title', ''),
                        'marque': (doc.get('brand') or '').title(),
                        'categorie': doc.get('category', ''),
                        'reference': doc.get('reference', ''),
                        'image': doc.get('product_image', ''),
                        'prix_min': prix,
                        'prix_max': safe_price(doc.get('old_price')) or prix,
                        'en_stock': doc.get('etat_stock') == 'En stock',
                        'boutique': store_name,
                        'url_boutique': doc.get('url', ''),
                        'offres': [offre] if prix else [],
                    })
            except Exception as e:
                logger.error(f"Erreur produit_detail ObjectId {store_name}: {e}")
                continue

        return Response({'erreur': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    # Recherche dans comparatif par Slug
    try:
        col = get_comparatif()
        doc = col.find_one({'Slug': slug})
    except Exception as e:
        logger.error(f"Erreur MongoDB produit_detail {slug}: {e}")
        return Response({'erreur': 'Erreur serveur'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not doc:
        return Response({'erreur': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    d = {key: doc.get(val) for key, val in COMPARATIF_KEYS.items()}

    nom = d['mytek_nom'] or d['tunisianet_nom'] or d['spacenet_nom'] or ''
    image = d['mytek_image'] or d['tunisianet_image'] or d['spacenet_image'] or ''
    marque = nom.split()[0].title() if nom else ''

    offres = []
    for store_key, label in [('mytek', 'Mytek'), ('tunisianet', 'Tunisianet'), ('spacenet', 'Spacenet')]:
        prix = safe_price(d.get(f'{store_key}_prix'))
        if prix:
            offres.append({
                'boutique': label,
                'prix': prix,
                'stock': d.get(f'{store_key}_stock', ''),
                'url': d.get(f'{store_key}_url', ''),
                'image': d.get(f'{store_key}_image', ''),
            })

    offres.sort(key=lambda x: x['prix'])
    prix_list = [o['prix'] for o in offres]

    return Response({
        'id': str(doc.get('_id', '')),
        'slug': slug,
        'nom': nom,
        'marque': marque,
        'reference': d.get('reference', ''),
        'image': image,
        'prix_min': min(prix_list) if prix_list else None,
        'prix_max': max(prix_list) if prix_list else None,
        'offres': offres,
    })


# ============================================
# CATÉGORIES
# ============================================

@api_view(['GET'])
def categories_list(request):
    """
    GET /api/v1/categories/
    Agrège les catégories distinctes depuis les 3 collections per-store.
    """
    cats = {}

    for get_col, store_name in get_all_stores():
        try:
            col = get_col()
            pipeline = [
                {'$match': {'category': {'$exists': True, '$ne': None, '$ne': ''}}},
                {'$group': {
                    '_id': '$category',
                    'nom': {'$first': '$category_path'},
                    'count': {'$sum': 1},
                }},
            ]
            for doc in col.aggregate(pipeline):
                slug = doc['_id']
                if slug:
                    if slug not in cats:
                        nom_brut = doc.get('nom') or ''
                        # Extraire le dernier segment du path "Accueil > ... > Nom"
                        nom_clean = nom_brut.split('>')[-1].strip() if '>' in nom_brut else (nom_brut or slug.replace('-', ' ').title())
                        cats[slug] = {
                            'id': slug,
                            'slug': slug,
                            'nom': nom_clean,
                            'nombre_produits': 0,
                        }
                    cats[slug]['nombre_produits'] += doc['count']
        except Exception as e:
            logger.error(f"Erreur catégories {store_name}: {e}")
            continue

    result = sorted(cats.values(), key=lambda x: -x['nombre_produits'])
    return Response({'data': result, 'meta': {'total_items': len(result)}})


@api_view(['GET'])
def categorie_detail(request, slug: str):
    """
    GET /api/v1/categories/<slug>/
    Retourne la catégorie + ses produits.
    """
    page = get_page_number(request)
    produits = []
    categorie_nom = slug.replace('-', ' ').title()

    for get_col, store_name in get_all_stores():
        try:
            col = get_col()
            query = {'category': {'$regex': f'^{re.escape(slug)}$', '$options': 'i'}}
            results = col.find(query, PRODUIT_PROJECTION).limit(PAGE_SIZE * 3)
            for doc in results:
                if not categorie_nom or categorie_nom == slug:
                    categorie_nom = doc.get('category_path', categorie_nom)
                produits.append(format_produit_from_store(doc, store_name))
        except Exception as e:
            logger.error(f"Erreur catégorie {slug} / {store_name}: {e}")
            continue

    if not produits:
        return Response({'erreur': 'Catégorie introuvable'}, status=status.HTTP_404_NOT_FOUND)

    response = paginate(produits, page)
    response['categorie'] = {'slug': slug, 'nom': categorie_nom}
    return Response(response)


# ============================================
# MARQUES
# ============================================

@api_view(['GET'])
def marques_list(request):
    """
    GET /api/v1/marques/
    Agrège les marques distinctes depuis les 3 collections.
    """
    brands = {}

    for get_col, store_name in get_all_stores():
        try:
            col = get_col()
            pipeline = [
                {'$match': {'brand': {'$exists': True, '$ne': None, '$ne': ''}}},
                {'$group': {
                    '_id': '$brand',
                    'count': {'$sum': 1},
                }},
            ]
            for doc in col.aggregate(pipeline):
                slug = (doc['_id'] or '').lower().strip()
                if slug:
                    if slug not in brands:
                        brands[slug] = {
                            'id': slug,
                            'slug': slug,
                            'nom': doc['_id'].title(),
                            'nombre_produits': 0,
                        }
                    brands[slug]['nombre_produits'] += doc['count']
        except Exception as e:
            logger.error(f"Erreur marques {store_name}: {e}")
            continue

    result = sorted(brands.values(), key=lambda x: -x['nombre_produits'])
    return Response({'data': result, 'meta': {'total_items': len(result)}})


@api_view(['GET'])
def marque_detail(request, nom: str):
    """
    GET /api/v1/marques/<nom>/
    Retourne la marque + ses produits.
    """
    page = get_page_number(request)
    produits = []

    for get_col, store_name in get_all_stores():
        try:
            col = get_col()
            query = {'brand': {'$regex': f'^{re.escape(nom)}$', '$options': 'i'}}
            results = col.find(query, PRODUIT_PROJECTION).limit(PAGE_SIZE * 3)
            for doc in results:
                produits.append(format_produit_from_store(doc, store_name))
        except Exception as e:
            logger.error(f"Erreur marque {nom} / {store_name}: {e}")
            continue

    if not produits:
        return Response({'erreur': 'Marque introuvable'}, status=status.HTTP_404_NOT_FOUND)

    response = paginate(produits, page)
    response['marque'] = {'slug': nom.lower(), 'nom': nom.title()}
    return Response(response)


# ============================================
# BLOG
# ============================================

@api_view(['GET'])
def blog_list(request):
    """GET /api/v1/blog/"""
    page = get_page_number(request)
    posts = list(BlogPost.objects.prefetch_related('summary', 'specs').order_by('-published_date'))
    data = [BlogPostListSerializer(p, context={'request': request}).data for p in posts]
    return Response(paginate(data, page))


@api_view(['GET'])
def blog_detail(request, slug: str):
    """GET /api/v1/blog/<slug>/"""
    try:
        post = BlogPost.objects.prefetch_related('summary', 'specs', 'sections').get(slug=slug)
    except BlogPost.DoesNotExist:
        return Response({'erreur': 'Article introuvable'}, status=status.HTTP_404_NOT_FOUND)

    return Response(BlogPostDetailSerializer(post, context={'request': request}).data)


# ============================================
# BOUTIQUES
# ============================================

@api_view(['GET'])
def boutiques_list(request):
    """GET /api/v1/boutiques/"""
    return Response({'data': BOUTIQUES, 'meta': {'total_items': len(BOUTIQUES)}})


# ============================================
# DEMANDES
# ============================================

@api_view(['POST'])
def demandes_create(request):
    """POST /api/v1/demandes/"""
    serializer = StoreRequestSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Demande enregistrée avec succès.'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
