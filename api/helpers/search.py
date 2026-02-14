"""
============================================
API/HELPERS/SEARCH.PY
============================================
Fonctions utilitaires pour la recherche de produits.
Portage depuis comparer/helpers/search.py (toprix.tn) adapté pour l'API REST.

Fonctionnalités :
- Nettoyage et détection du type de requête
- Construction de pipelines MongoDB Atlas Search
- Filtrage post-recherche par pertinence
- Calcul du minimumShouldMatch dynamique
"""

import re
import math
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger('api')

# ============================================
# PROJECTION POUR LES PIPELINES ATLAS SEARCH
# Inclut tous les champs nécessaires à format_produit_from_store()
# ============================================
SEARCH_PROJECTION = {
    '_id': 1,
    'title': 1,
    'price': 1,
    'old_price': 1,
    'brand': 1,
    'category': 1,
    'category_path': 1,
    'reference': 1,
    'etat_stock': 1,
    'discount': 1,
    'url': 1,
    'product_image': 1,
}


def clean_search_query(query: str) -> str:
    """
    Nettoie une requête de recherche.
    - Remplace les slashes par des espaces
    - Garde uniquement alphanumériques, accents, espaces, tirets
    - Normalise les espaces multiples
    """
    if not query:
        return ''
    query = re.sub(r'\s*/\s*', ' ', query)
    query = re.sub(r'[^\w\s\-éèêëàâäôöùûüçñ]', ' ', query)
    query = re.sub(r'\s+', ' ', query).strip()
    return query


def is_reference_query(query: str) -> bool:
    """
    Détecte si une requête est une référence produit.
    Critères : un seul token, contient des chiffres ou tirets, alphanumérique uniquement.
    Exemples : "TAC-12CHSA" → True, "12000BTU" → True, "PC Portable" → False
    """
    if not query:
        return False
    has_digits_or_separators = bool(re.search(r'[\d\-/]', query))
    is_single_token = ' ' not in query
    matches_pattern = bool(re.fullmatch(r'[A-Za-z0-9\-/]+', query))
    return is_single_token and has_digits_or_separators and matches_pattern


def calculate_min_should_match(num_words: int) -> int:
    """
    Calcule le minimumShouldMatch pour Atlas Search compound query.
    - 1 mot  : 1
    - 2 mots : 1
    - 3-5    : 60%
    - 6+     : 30% (queries longues souples)
    """
    if num_words <= 2:
        return 1
    elif num_words <= 5:
        return math.ceil(num_words * 0.6)
    else:
        return math.ceil(num_words * 0.3)


def build_reference_pipeline(query: str, skip: int = 0, limit: int = 10) -> List[Dict]:
    """
    Pipeline MongoDB pour une recherche par référence produit.

    Étapes :
    1. $match exact sur le champ `reference` (case-insensitive)
    2. $addFields : exact_match (1 si correspondance parfaite)
    3. $sort : exact_match DESC, price ASC
    4. $skip / $limit
    5. $project
    """
    projection = {**SEARCH_PROJECTION, 'exact_match': 1}
    return [
        {
            '$match': {
                'reference': {'$regex': f'^{re.escape(query)}$', '$options': 'i'}
            }
        },
        {
            '$addFields': {
                'exact_match': {
                    '$cond': {
                        'if': {'$eq': [{'$toLower': '$reference'}, query.lower()]},
                        'then': 1,
                        'else': 0
                    }
                }
            }
        },
        {'$sort': {'exact_match': -1, 'price': 1, '_id': 1}},
        {'$skip': skip},
        {'$limit': limit},
        {'$project': projection},
    ]


def build_text_search_pipeline(query: str, num_words: int, skip: int = 0, limit: int = 10) -> List[Dict]:
    """
    Pipeline MongoDB Atlas Search pour une recherche textuelle.

    Priorités (compound should) :
    1. Phrase exacte complète  → boost x10
    2. Mots exacts dans titre  → boost x5
    3. Fuzzy match (maxEdits 1) → boost x2

    minimumShouldMatch calculé dynamiquement selon le nombre de mots.
    Tri : starts_with_query DESC, search_score DESC.

    Nécessite un index Atlas Search nommé "Text" sur le champ `title`.
    """
    min_should_match = calculate_min_should_match(num_words)
    projection = {**SEARCH_PROJECTION, 'search_score': 1, 'starts_with_query': 1}

    return [
        {
            '$search': {
                'index': 'Text',
                'compound': {
                    'should': [
                        # Priorité 1 : phrase exacte complète
                        {
                            'phrase': {
                                'query': query,
                                'path': 'title',
                                'score': {'boost': {'value': 10}}
                            }
                        },
                        # Priorité 2 : mots exacts
                        {
                            'text': {
                                'query': query,
                                'path': 'title',
                                'score': {'boost': {'value': 5}}
                            }
                        },
                        # Priorité 3 : fuzzy (tolérance fautes de frappe)
                        {
                            'text': {
                                'query': query,
                                'path': 'title',
                                'fuzzy': {'maxEdits': 1},
                                'score': {'boost': {'value': 2}}
                            }
                        },
                    ],
                    'minimumShouldMatch': min_should_match
                }
            }
        },
        {
            '$addFields': {
                'search_score': {'$meta': 'searchScore'},
                'starts_with_query': {
                    '$cond': {
                        'if': {
                            '$regexMatch': {
                                'input': '$title',
                                'regex': f'^{re.escape(query)}',
                                'options': 'i'
                            }
                        },
                        'then': 1,
                        'else': 0
                    }
                }
            }
        },
        {'$sort': {'starts_with_query': -1, 'search_score': -1, '_id': 1}},
        {'$skip': skip},
        {'$limit': limit},
        {'$project': projection},
    ]


def filter_by_relevance(raw_docs: List[Dict], query_words: List[str], num_words: int) -> List[Dict]:
    """
    Post-filtre par pertinence pour les recherches multi-mots.

    Vérifie que le titre contient suffisamment de mots de la requête :
    - 2 mots : ≥ 1 mot présent (50%)
    - 3-5 mots : ≥ 60%
    - 6+ mots : ≥ 30%

    Les docs sont triés par score de pertinence décroissant.
    Travaille sur les docs bruts MongoDB (champ `title`).
    """
    if num_words < 2 or not raw_docs:
        return raw_docs

    required_words = [w.lower() for w in query_words if len(w) >= 2]
    if not required_words:
        return raw_docs

    filtered = []
    for doc in raw_docs:
        title_lower = doc.get('title', '').lower()
        words_found = sum(1 for word in required_words if word in title_lower)

        if num_words == 2:
            is_relevant = words_found >= 1
        elif num_words <= 5:
            is_relevant = words_found >= math.ceil(len(required_words) * 0.6)
        else:
            is_relevant = words_found >= math.ceil(len(required_words) * 0.3)

        if is_relevant:
            doc['_relevance_score'] = words_found / len(required_words)
            filtered.append(doc)

    filtered.sort(key=lambda d: d.get('_relevance_score', 0), reverse=True)
    for doc in filtered:
        doc.pop('_relevance_score', None)

    if len(raw_docs) > len(filtered):
        logger.info(f"Filtrage pertinence : {len(raw_docs)} → {len(filtered)} produits")

    return filtered


def filter_exact_matches(raw_docs: List[Dict]) -> Tuple[List[Dict], bool]:
    """
    Garde uniquement les correspondances exactes (exact_match == 1).
    Si aucune correspondance exacte, retourne tous les docs.
    Nettoie le champ temporaire `exact_match` dans tous les cas.
    """
    if not raw_docs:
        return raw_docs, False

    exact = [doc for doc in raw_docs if doc.get('exact_match', 0) == 1]

    if exact:
        for doc in exact:
            doc.pop('exact_match', None)
        logger.info(f"{len(exact)} exact match(es) référence")
        return exact, True
    else:
        for doc in raw_docs:
            doc.pop('exact_match', None)
        return raw_docs, False
