# Architecture Technique — Toprix Backend

---

## Structure des dossiers

```
toprix-backend/
├── core/                      ← Projet Django (settings, urls, wsgi)
│   ├── settings.py            ← Config complète (MongoDB, cache, email, logging)
│   ├── urls.py                ← Routes root : /admin/ + /api/v1/
│   └── wsgi.py                ← Point d'entrée WSGI (Serv00 / gunicorn)
│
├── api/                       ← Application DRF principale
│   ├── models.py              ← Modèles SQLite (Blog + Demandes)
│   ├── views.py               ← Tous les endpoints API
│   ├── serializers.py         ← Sérialiseurs DRF (Blog, Demandes)
│   ├── urls.py                ← Routes /api/v1/
│   ├── admin.py               ← Interface admin Django
│   └── migrations/            ← Migrations SQLite
│
├── db/
│   └── mongo.py               ← Connexion MongoDB poolée (singleton)
│
├── docs/                      ← Documentation (ce dossier)
├── logs/                      ← Logs rotatifs (auto-créé)
├── public/
│   ├── static/                ← Fichiers statiques collectés
│   └── media/                 ← Uploads (images blog)
│
├── manage.py
├── requirements.txt
└── .env.example
```

---

## Bases de données

### SQLite — données gérées manuellement

| Modèle | Rôle |
|--------|------|
| `BlogPost` | Articles de blog |
| `BlogSummary` | Avantages / inconvénients (OneToOne → BlogPost) |
| `BlogSpecifications` | Specs techniques (RAM, écran…) (OneToOne → BlogPost) |
| `BlogSection` | Sections libres de l'article (ForeignKey → BlogPost) |
| `StoreRequest` | Demandes d'ajout boutique ou produit |

### MongoDB — données produits (en lecture seule depuis l'API)

| Collection | Contenu | Accès |
|-----------|---------|-------|
| `tunisianet` | Produits Tunisianet | lecture |
| `mytek` | Produits Mytek | lecture |
| `spacenet` | Produits Spacenet | lecture |
| `comparatif` | Produits unifiés avec slugs (matching multi-boutiques) | lecture |

---

## Connexion MongoDB (`db/mongo.py`)

Implémentation **Singleton + Connection Pooling** identique au projet original `toprix` :

```python
# db/mongo.py
class MongoDBPool:
    """Singleton — une instance par store, réutilisée entre les requêtes."""
    _clients = {}   # { store_name: MongoClient }

# Fonctions publiques
get_tunisianet()   # → Collection Tunisianet
get_mytek()        # → Collection Mytek
get_spacenet()     # → Collection Spacenet
get_comparatif()   # → Collection Comparatif
get_all_stores()   # → [(fn, nom), ...] pour itérer les 3 boutiques
```

**Paramètres de pooling :**
- `maxPoolSize=20`, `minPoolSize=2`
- `maxIdleTimeMS=30000` (ferme les connexions inactives > 30s)
- `serverSelectionTimeoutMS=5000`

---

## Structure d'un document MongoDB (per-store)

Champs disponibles dans les collections `tunisianet`, `mytek`, `spacenet` :

```json
{
  "_id": "ObjectId",
  "title": "Montre Femme SUPERDRY - Star Gris (SYL-275E)",
  "brand": "superdry",
  "category": "montre",
  "category_path": "Montre",
  "price": 199.5,
  "old_price": 239.5,
  "discount": 40,
  "etat_stock": "En stock",
  "product_image": "https://www.mytek.tn/media/catalog/product/s/y/syl-275e.jpg",
  "url": "https://www.mytek.tn/montre-femme-superdry-star-gris-syl-275e.html",
  "reference": "SYL-275E",
  "fiche_technique": "Description longue...",
  "identification_date": "2026-02-13T14:23",
  "embedding_ref": [/* vecteur 384 dimensions */]
}
```

---

## Structure d'un document MongoDB (comparatif)

Collection `comparatif` — produits matchés entre boutiques avec slug SEO :

```json
{
  "_id": "ObjectId",
  "Slug": "samsung-galaxy-s24",
  "Matching": "Exact Match",
  "Réf Mytek": "SM-S921B",
  "Produit Mytek": "Samsung Galaxy S24 128Go",
  "Prix Mytek": "2799",
  "Stock Mytek": "En stock",
  "URL Mytek": "https://...",
  "Image Mytek": "https://...",
  "Produit Tunisianet": "Samsung Galaxy S24",
  "Prix Tunisianet": "2849",
  "Stock Tunisianet": "En stock",
  "URL Tunisianet": "https://...",
  "Image Tunisianet": "https://...",
  "Produit Spacenet": null,
  "Prix Spacenet": null
}
```

---

## Flux de données

```
Client Next.js (SSR)
        │
        ▼ GET /api/v1/...
Django REST API (toprix-backend)
        │
        ├── MongoDB (produits, catégories, marques)
        │       collections : tunisianet / mytek / spacenet / comparatif
        │
        └── SQLite (blog, demandes)
                modèles : BlogPost, StoreRequest
```

---

## Décisions architecturales

### 1. Séparation backend / frontend
- Le backend expose **uniquement** une API REST, aucune vue HTML
- Le frontend Next.js (dépôt séparé) consomme l'API en SSR

### 2. MongoDB en lecture seule
- L'API ne modifie jamais les données MongoDB (scraped par des jobs externes)
- Toutes les écritures passent par SQLite (blog géré via admin Django)

### 3. Format de réponse unifié
Toutes les réponses liste suivent le format `ReponseAPI<T>` :
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "total_pages": 5,
    "total_items": 48,
    "par_page": 12
  }
}
```

### 4. Pagination manuelle
Gérée dans `api/views.py` via la fonction `paginate()` — pas de `PageNumberPagination` DRF pour garder le contrôle du format.

### 5. Config identique à public_python
- Même `MONGODB_CONFIG`, même `CACHES` (LocMem), même `SESSION_ENGINE`, même `LOGGING` rotatif
- Facilite la migration des données et la cohérence des deux projets
