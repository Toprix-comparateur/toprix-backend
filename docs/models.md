# Modèles SQLite — Toprix Backend

> Les produits sont dans MongoDB (lecture seule).
> SQLite gère uniquement le **blog** et les **demandes**.

---

## Blog

### `BlogPost`

Article principal du blog.

| Champ | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Clé primaire |
| `title` | CharField(200) | Titre de l'article |
| `slug` | SlugField unique | URL-friendly identifier |
| `content` | TextField | Contenu HTML (généré via admin) |
| `image` | ImageField | Image principale (`blog/`) |
| `published_date` | DateTimeField | Date de publication (défaut: now) |
| `launch_date` | DateField | Date de lancement produit (optionnel) |
| `estimated_price` | CharField(100) | Prix estimatif (optionnel) |

**Tri par défaut :** `-published_date`

---

### `BlogSummary`

Avantages et inconvénients liés à un article (relation `OneToOne`).

| Champ | Type | Description |
|-------|------|-------------|
| `post` | OneToOneField → BlogPost | Relation |
| `advantages` | TextField | Avantages (une ligne par avantage) |
| `disadvantages` | TextField | Inconvénients (une ligne par inconvénient) |

**Exemple de contenu `advantages` :**
```
Excellente autonomie (48h)
Appareil photo 200MP
Résistance à l'eau IP68
```

L'API retourne ce texte splitté en tableau :
```json
"avantages": ["Excellente autonomie (48h)", "Appareil photo 200MP", "Résistance à l'eau IP68"]
```

---

### `BlogSpecifications`

Spécifications techniques (OneToOne).

| Champ | Type | Description |
|-------|------|-------------|
| `post` | OneToOneField → BlogPost | Relation |
| `ram` | CharField(100) | Ex: "12 Go" |
| `storage` | CharField(100) | Ex: "256 Go" |
| `processor` | CharField(100) | Ex: "Snapdragon 8 Gen 3" |
| `screen` | CharField(100) | Ex: "6.8\" AMOLED 120Hz" |
| `battery` | CharField(100) | Ex: "5000 mAh" |
| `audio` | CharField(100) | Ex: "Dolby Atmos" |
| `camera` | CharField(100) | Ex: "200MP + 12MP + 10MP" |

---

### `BlogSection`

Sections libres dans un article (relation `ForeignKey`, plusieurs par article).

| Champ | Type | Description |
|-------|------|-------------|
| `post` | ForeignKey → BlogPost | Article parent |
| `order` | PositiveIntegerField | Ordre d'affichage |
| `h2_title` | CharField(200) | Titre de section (optionnel) |
| `paragraph` | TextField | Contenu textuel (optionnel) |
| `image` | ImageField | Image de section (`blog/sections/`) |
| `banner` | ImageField | Bannière cliquable (`blog/banners/`) |
| `banner_url` | URLField | URL de destination de la bannière |

**Tri :** `order` croissant.

---

## Demandes

### `StoreRequest`

Demandes d'ajout de boutique ou de produit soumises via le formulaire `/ajouter`.

| Champ | Type | Description |
|-------|------|-------------|
| `request_type` | CharField | `"store"` ou `"product"` |
| `store_name` | CharField(200) | Nom boutique (si store) |
| `website` | URLField | Site web boutique |
| `product_name` | CharField(200) | Nom produit (si product) |
| `product_url` | URLField | URL produit |
| `contact_person` | CharField(200) | Nom du contact |
| `email` | EmailField | Email du contact |
| `phone` | CharField(20) | Téléphone |
| `message` | TextField | Message libre |
| `status` | CharField | `"pending"` / `"approved"` / `"rejected"` |
| `created_at` | DateTimeField | Date de création (auto) |
| `updated_at` | DateTimeField | Date de modification (auto) |

**Statut par défaut :** `"pending"`
**Tri :** `-created_at`

---

## Gestion via l'admin Django

Accessible sur `/admin/` :

- **BlogPost** : créer / modifier des articles avec inlines (Summary, Specs, Sections)
- **StoreRequest** : voir les demandes, changer leur statut (`list_editable`)

```
/admin/api/blogpost/      ← Liste articles
/admin/api/storerequest/  ← Liste demandes
```
