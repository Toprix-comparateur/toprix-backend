# Référence API — Toprix Backend

Base URL : `https://api.toprix.tn/api/v1`

---

## Vue d'ensemble des endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/produits/` | Recherche et liste de produits |
| GET | `/produits/<slug>/` | Détail d'un produit (offres multi-stores par SKU) |
| GET | `/categories/` | Liste de toutes les catégories avec leurs sous-catégories |
| GET | `/categories/<slug>/` | Catégorie parente + ses produits |
| GET | `/categories/<parent>/<sous>/` | Sous-catégorie + ses produits |
| GET | `/marques/` | Liste de toutes les marques |
| GET | `/marques/<nom>/` | Marque + ses produits |
| GET | `/blog/` | Liste des articles de blog |
| GET | `/blog/<slug>/` | Détail d'un article |
| GET | `/boutiques/` | Liste des boutiques partenaires |
| POST | `/demandes/` | Soumettre une demande (boutique/produit) |

---

## Format de réponse

### Liste paginée (`ReponseAPI<T>`)

```json
{
  "data": [ ... ],
  "meta": {
    "page": 1,
    "total_pages": 5,
    "total_items": 48,
    "par_page": 20
  }
}
```

### Erreur

```json
{ "erreur": "Message d'erreur" }
```

---

## `GET /produits/`

Recherche de produits dans les 3 collections MongoDB (Tunisianet, Mytek, Spacenet).

**Paramètres de requête :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `q` | string | Terme de recherche (Atlas Search ou regex selon mode) |
| `categorie` | string | Filtrer par slug catégorie (regex, case-insensitive) |
| `marque` | string | Filtrer par nom de marque (regex, case-insensitive) |
| `prix_min` | float | Prix minimum en DT |
| `prix_max` | float | Prix maximum en DT |
| `en_promo` | `1`/`true` | Produits en promotion uniquement (`discount > 0`) |
| `page` | int | Numéro de page (défaut : 1, max : 100) |

**Logique de recherche :**

| Cas | Moteur | Détail |
|-----|--------|--------|
| `q` seul (texte libre) | **Atlas Search** | compound : phrase (x10) + texte (x5) + fuzzy (x2), tri par `starts_with` puis `search_score` |
| `q` seul (référence détectée) | **Pipeline référence** | match exact sur `reference`, `exact_match` score, tri prix ASC |
| `q` + `categorie`/`marque` | Regex MongoDB | `$regex` sur `title`, `category`, `brand` |
| `categorie`/`marque`/`en_promo`/`prix` sans `q` | Regex MongoDB | filtres directs au niveau MongoDB |
| `prix_min`/`prix_max` | MongoDB + post-filtrage Python | filtre `price` dans le query MongoDB ET post-filtre Python (double sécurité) |

> Une **référence** est un token sans espace contenant des chiffres ou tirets (ex : `SM-S921B`, `12000BTU`).
> Fallback automatique sur regex si l'index Atlas Search `"Text"` est indisponible.

**Pagination** : 20 produits par page (`PAGE_SIZE = 20`). Dédoublonnage par référence (meilleur prix conservé).

**Équilibrage des boutiques** : les résultats sont interleaved en **round-robin** (Tunisianet → Mytek → Spacenet → ...) pour éviter qu'une seule boutique monopolise la première page. Chaque boutique contribue au maximum `PAGE_SIZE × 2 = 40` documents bruts avant interleaving.

**Exemples :**
```
GET /api/v1/produits/?q=samsung+galaxy&page=1
GET /api/v1/produits/?q=laptop&categorie=ordinateurs-portables&marque=hp
GET /api/v1/produits/?q=smartphone&prix_min=500&prix_max=1500&en_promo=1
GET /api/v1/produits/?en_promo=1&marque=samsung
GET /api/v1/produits/?prix_min=200&prix_max=800
GET /api/v1/produits/?categorie=electromenager&en_promo=1
```

**Réponse :**
```json
{
  "data": [
    {
      "id": "691ef0baf4abe379312e57d0",
      "slug": null,
      "nom": "Samsung Galaxy S24 128Go",
      "marque": "Samsung",
      "categorie": "smartphones",
      "categorie_nom": "Smartphones",
      "prix_min": 2799.0,
      "prix_max": 3199.0,
      "image": "https://www.mytek.tn/media/catalog/product/...",
      "en_stock": true,
      "discount": 0,
      "reference": "SM-S921B",
      "boutique": "Mytek",
      "url_boutique": "https://www.mytek.tn/..."
    }
  ],
  "meta": {
    "page": 1,
    "total_pages": 3,
    "total_items": 32,
    "par_page": 20
  }
}
```

> **Note :** `slug` est `null` pour les résultats per-store. Le frontend utilise `id` (ObjectId) comme identifiant de navigation dans ce cas.

---

## `GET /produits/<id>/`

Accepte deux types d'identifiants :
- **ObjectId MongoDB** (24 hex) → cherche dans les 3 per-store collections, puis recherche le même `reference` dans les 3 stores pour construire la liste d'offres
- **Slug texte** → cherche dans `comparatif`

**Exemples :**
```
GET /api/v1/produits/68a45751dc1cf04413890156/
GET /api/v1/produits/samsung-galaxy-s24/
```

**Réponse (ObjectId — comparaison multi-stores par SKU) :**

Le produit est cherché par ObjectId. Si le champ `reference` est renseigné, les 3 stores sont interrogés pour trouver le même SKU. Le tableau `offres` contiendra toutes les boutiques proposant ce produit, trié par prix croissant.

```json
{
  "id": "691ef0baf4abe379312e57d0",
  "slug": "691ef0baf4abe379312e57d0",
  "nom": "Samsung Galaxy S24 128Go",
  "marque": "Samsung",
  "categorie": "smartphones",
  "categorie_nom": "Smartphones",
  "reference": "SM-S921B",
  "image": "https://www.mytek.tn/media/catalog/product/...",
  "description": "Écran 6.2\" Dynamic AMOLED 2X - 50MP - 8 Go RAM...",
  "prix_min": 2799.0,
  "prix_max": 2999.0,
  "discount": 200.0,
  "en_stock": true,
  "boutique": "Mytek",
  "url_boutique": "https://www.mytek.tn/...",
  "offres": [
    { "boutique": "Mytek",      "prix": 2799.0, "stock": "En stock", "url": "...", "image": "..." },
    { "boutique": "Tunisianet", "prix": 2849.0, "stock": "En stock", "url": "...", "image": "..." },
    { "boutique": "Spacenet",   "prix": 2999.0, "stock": "Rupture",  "url": "...", "image": "..." }
  ]
}
```

> `prix_max` = `old_price` (avant réduction). `discount` = montant de la réduction en DT (ex: 200.0 DT). `description` = contenu du champ `fiche_technique`.
> `prix_max` est `null` si identique à `prix_min` (pas de réduction).
> `offres` contient 1 à 3 entrées selon la disponibilité du SKU dans les stores. Si `reference` est vide, seule la boutique source est incluse.

**Réponse (Slug — comparatif, multi-boutiques) :**
```json
{
  "id": "665abc123...",
  "slug": "samsung-galaxy-s24",
  "nom": "Samsung Galaxy S24 128Go",
  "marque": "Samsung",
  "reference": "SM-S921B",
  "image": "https://...",
  "prix_min": 2799.0,
  "prix_max": 2849.0,
  "offres": [
    { "boutique": "Mytek",      "prix": 2799.0, "stock": "En stock", "url": "...", "image": "..." },
    { "boutique": "Tunisianet", "prix": 2849.0, "stock": "En stock", "url": "...", "image": "..." }
  ]
}
```

Les offres sont triées par prix croissant.

---

## `GET /categories/`

Agrège les catégories distinctes depuis les 3 collections per-store. Retourne aussi les sous-catégories (2ème niveau du `category_path`).

Les slugs de sous-catégories sont dérivés de `category_path` via `slugify_fr()` (ex : `"Smartphone & Mobile"` → `"smartphone-mobile"`).

**Réponse :**
```json
{
  "data": [
    {
      "id": "informatique",
      "slug": "informatique",
      "nom": "Informatique",
      "nombre_produits": 2648,
      "sous_categories": [
        { "id": "informatique/imprimante", "slug": "informatique/imprimante", "nom": "Imprimante", "parent_slug": "informatique", "nombre_produits": 1200 },
        { "id": "informatique/stockage",   "slug": "informatique/stockage",   "nom": "Stockage",   "parent_slug": "informatique", "nombre_produits": 400 }
      ]
    },
    {
      "id": "telephonie",
      "slug": "telephonie",
      "nom": "Téléphonie",
      "nombre_produits": 1456,
      "sous_categories": [
        { "id": "telephonie/smartphone-mobile", "slug": "telephonie/smartphone-mobile", "nom": "Smartphone & Mobile", "parent_slug": "telephonie", "nombre_produits": 1456 }
      ]
    }
  ],
  "meta": { "total_items": 14 }
}
```

Trié par `nombre_produits` décroissant. `sous_categories` est également trié par `nombre_produits` décroissant.

---

## `GET /categories/<slug>/`

Produits d'une catégorie parente. Filtre sur `category = slug` (exact, case-insensitive).

**Exemple :**
```
GET /api/v1/categories/telephonie/?page=2
```

**Réponse :**
```json
{
  "categorie": {
    "slug": "telephonie",
    "nom": "Téléphonie"
  },
  "data": [ ... ],
  "meta": {
    "page": 2,
    "total_pages": 8,
    "total_items": 96,
    "par_page": 20
  }
}
```

---

## `GET /categories/<parent>/<sous>/`

Produits d'une sous-catégorie. Filtre sur `category = parent` ET `category_path` contient le 2ème segment correspondant au slug `<sous>`.

La correspondance est faite en résolvant le slug vers les noms réels via `distinct('category_path')`.

**Exemple :**
```
GET /api/v1/categories/informatique/stockage/?page=1
GET /api/v1/categories/telephonie/smartphone-mobile/?page=1
```

**Réponse :**
```json
{
  "categorie": {
    "slug": "informatique/stockage",
    "nom": "Stockage",
    "parent_slug": "informatique",
    "parent_nom": "Informatique"
  },
  "data": [ ... ],
  "meta": {
    "page": 1,
    "total_pages": 3,
    "total_items": 45,
    "par_page": 20
  }
}
```

---

## `GET /marques/`

Agrège les marques distinctes depuis les 3 collections.

**Réponse :**
```json
{
  "data": [
    {
      "id": "samsung",
      "slug": "samsung",
      "nom": "Samsung",
      "nombre_produits": 520
    }
  ],
  "meta": { "total_items": 185 }
}
```

---

## `GET /marques/<nom>/`

Produits d'une marque. `<nom>` est case-insensitive.

**Exemple :**
```
GET /api/v1/marques/samsung/?page=1
```

**Réponse :**
```json
{
  "marque": { "slug": "samsung", "nom": "Samsung" },
  "data": [ ... ],
  "meta": { ... }
}
```

---

## `GET /blog/`

Liste des articles de blog depuis SQLite, triés par date de publication décroissante.

**Réponse :**
```json
{
  "data": [
    {
      "id": "1",
      "slug": "meilleur-smartphone-2026",
      "titre": "Meilleur Smartphone 2026",
      "image": "https://api.toprix.tn/media/blog/image.jpg",
      "date_publication": "2026-01-15T10:00:00+01:00",
      "resume": "Les 300 premiers caractères du contenu..."
    }
  ],
  "meta": { "page": 1, "total_pages": 2, "total_items": 18, "par_page": 12 }
}
```

---

## `GET /blog/<slug>/`

Détail complet d'un article.

**Réponse :**
```json
{
  "id": "1",
  "slug": "meilleur-smartphone-2026",
  "titre": "Meilleur Smartphone 2026",
  "contenu": "<h2>Introduction</h2><p>...</p>",
  "image": "https://api.toprix.tn/media/blog/image.jpg",
  "date_publication": "2026-01-15T10:00:00+01:00",
  "resume": "Les 300 premiers caractères...",
  "avantages": [
    "Excellente autonomie",
    "Appareil photo 200MP"
  ],
  "inconvenients": [
    "Prix élevé",
    "Pas de jack audio"
  ],
  "specifications": {
    "ram": "12 Go",
    "stockage": "256 Go",
    "processeur": "Snapdragon 8 Gen 3",
    "ecran": "6.8\" AMOLED 120Hz",
    "batterie": "5000 mAh",
    "audio": null,
    "camera": "200MP + 12MP + 10MP"
  }
}
```

> Le champ `contenu` est du HTML brut généré par l'admin Django. Le frontend doit l'afficher via `dangerouslySetInnerHTML` (contenu sanitisé côté admin).

---

## `GET /boutiques/`

Liste fixe des 3 boutiques partenaires.

**Réponse :**
```json
{
  "data": [
    { "id": "mytek",      "nom": "Mytek",      "site_web": "https://www.mytek.tn" },
    { "id": "tunisianet", "nom": "Tunisianet", "site_web": "https://www.tunisianet.com.tn" },
    { "id": "spacenet",   "nom": "Spacenet",   "site_web": "https://spacenet.tn" }
  ],
  "meta": { "total_items": 3 }
}
```

---

## `POST /demandes/`

Soumettre une demande d'ajout de boutique ou de produit.

**Corps de la requête (JSON) :**

```json
{
  "request_type": "store",
  "store_name": "TechStore",
  "website": "https://techstore.tn",
  "contact_person": "Ali Ben Ahmed",
  "email": "ali@techstore.tn",
  "phone": "+216 99 000 000",
  "message": "Nous souhaitons référencer notre boutique."
}
```

| Champ | Requis | Description |
|-------|--------|-------------|
| `request_type` | Oui | `"store"` ou `"product"` |
| `store_name` | Non | Nom boutique (si `request_type=store`) |
| `website` | Non | URL boutique |
| `product_name` | Non | Nom produit (si `request_type=product`) |
| `product_url` | Non | URL produit |
| `contact_person` | Oui | Nom du contact |
| `email` | Oui | Email |
| `phone` | Oui | Téléphone |
| `message` | Non | Message libre |

**Réponse succès (201) :**
```json
{ "message": "Demande enregistrée avec succès." }
```

**Réponse erreur (400) :**
```json
{
  "email": ["Saisissez une adresse e-mail valide."],
  "contact_person": ["Ce champ est obligatoire."]
}
```

---

## Codes HTTP

| Code | Signification |
|------|--------------|
| 200 | Succès |
| 201 | Ressource créée (POST /demandes/) |
| 400 | Erreur de validation |
| 404 | Ressource introuvable |
| 500 | Erreur serveur |
