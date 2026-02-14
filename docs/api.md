# Référence API — Toprix Backend

Base URL : `https://api.toprix.net/api/v1`

---

## Vue d'ensemble des endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/produits/` | Recherche et liste de produits |
| GET | `/produits/<slug>/` | Détail d'un produit (avec offres par boutique) |
| GET | `/categories/` | Liste de toutes les catégories |
| GET | `/categories/<slug>/` | Catégorie + ses produits |
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
    "par_page": 12
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
| `q` | string | Terme de recherche (regex sur `title`) |
| `categorie` | string | Filtrer par slug catégorie |
| `marque` | string | Filtrer par nom de marque |
| `page` | int | Numéro de page (défaut : 1) |

**Exemple :**
```
GET /api/v1/produits/?q=samsung+galaxy&page=1
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
    "par_page": 12
  }
}
```

> **Note :** `slug` est `null` pour les résultats per-store. Seuls les produits de la collection `comparatif` ont un slug.

---

## `GET /produits/<slug>/`

Détail d'un produit depuis la collection `comparatif` (slug requis, `Matching: "Exact Match"`).

**Exemple :**
```
GET /api/v1/produits/samsung-galaxy-s24/
```

**Réponse :**
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
    {
      "boutique": "Mytek",
      "prix": 2799.0,
      "stock": "En stock",
      "url": "https://www.mytek.tn/...",
      "image": "https://..."
    },
    {
      "boutique": "Tunisianet",
      "prix": 2849.0,
      "stock": "En stock",
      "url": "https://www.tunisianet.com.tn/...",
      "image": "https://..."
    }
  ]
}
```

Les offres sont triées par prix croissant.

---

## `GET /categories/`

Agrège les catégories distinctes depuis les 3 collections per-store.

**Réponse :**
```json
{
  "data": [
    {
      "id": "smartphones",
      "slug": "smartphones",
      "nom": "Smartphones",
      "nombre_produits": 1240
    },
    {
      "id": "ordinateurs-portables",
      "slug": "ordinateurs-portables",
      "nom": "Ordinateurs Portables",
      "nombre_produits": 874
    }
  ],
  "meta": { "total_items": 42 }
}
```

Trié par `nombre_produits` décroissant.

---

## `GET /categories/<slug>/`

Produits d'une catégorie spécifique.

**Exemple :**
```
GET /api/v1/categories/smartphones/?page=2
```

**Réponse :**
```json
{
  "categorie": {
    "slug": "smartphones",
    "nom": "Smartphones"
  },
  "data": [ ... ],
  "meta": {
    "page": 2,
    "total_pages": 8,
    "total_items": 96,
    "par_page": 12
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
      "image": "https://api.toprix.net/media/blog/image.jpg",
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
  "image": "https://api.toprix.net/media/blog/image.jpg",
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
