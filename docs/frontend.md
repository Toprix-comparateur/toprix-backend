# Frontend — Composants & Architecture

Dépôt : `Toprix-comparateur/toprix`
URL prod : `https://toprix-mu.vercel.app`
Stack : **Next.js 15 App Router · Tailwind CSS 4 · TypeScript**

---

## Stack technique

| Élément | Technologie |
|---------|-------------|
| Framework | Next.js 15 (App Router) |
| Rendu | SSR intégral (`force-dynamic` sur toutes les pages) |
| CSS | Tailwind CSS 4 (CSS-first, sans `tailwind.config.ts`) |
| Fonts | Inter (body) + Space Grotesk (titres) via `next/font` |
| Images | `next/image` avec `remotePatterns` |
| Déploiement | Vercel (auto-deploy sur push `main`) |

---

## Structure des dossiers

```
src/
├── app/
│   ├── (public)/
│   │   ├── page.tsx                     ← Page d'accueil (13 sections)
│   │   ├── rechercher/page.tsx          ← Recherche + filtres (2 cols mobile)
│   │   ├── produit/[slug]/page.tsx      ← Détail produit + produits similaires
│   │   ├── categories/page.tsx          ← Liste catégories
│   │   ├── categories/[slug]/page.tsx   ← Catégorie produits
│   │   ├── marques/page.tsx             ← Liste marques
│   │   ├── marques/[nom]/page.tsx       ← Marque produits
│   │   ├── blog/page.tsx                ← Liste articles
│   │   ├── blog/[slug]/page.tsx         ← Détail article
│   │   └── ajouter/page.tsx             ← Formulaire boutique
│   ├── layout.tsx                       ← Layout root (Header + Footer)
│   └── globals.css                      ← Tokens Tailwind + @keyframes marquee
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx                   ← Navbar sticky (client)
│   │   └── Footer.tsx                   ← Pied de page (server)
│   ├── product/
│   │   └── CarteProduit.tsx             ← Carte produit (server)
│   └── ui/
│       ├── CarouselProduits.tsx         ← Carrousel ◀▶ (client)
│       ├── StoriesCategories.tsx        ← Cercles catégories style Stories (server)
│       ├── CampagneTeasers.tsx          ← 2 bannières gradient promo (server)
│       ├── TuilesCategoriesCarousel.tsx ← Tuiles catégories colorées (server)
│       ├── Banners.tsx                  ← BannerStats + BannerHowItWorks + BannerBoutiques
│       └── MarqueeMarques.tsx           ← Défilement infini marques (server)
│
├── lib/
│   └── api/
│       └── produits.ts                  ← getProduits() + getProduit()
│
└── types/
    └── index.ts                         ← Types TypeScript globaux
```

---

## Page d'accueil (`page.tsx`)

Server Component — 3 appels API parallèles :

```ts
const [promosRes, smartphonesRes, electroRes] = await Promise.allSettled([
  getProduits({ en_promo: true }),
  getProduits({ categorie: 'smartphones' }),
  getProduits({ categorie: 'electromenager' }),
])
```

### Sections (dans l'ordre)

| # | Section | Composant | Data |
|---|---------|-----------|------|
| 1 | **Hero** | JSX inline | — |
| 2 | **Stories catégories** | `StoriesCategories` | hardcodé (10 catégories) |
| 3 | **Campaign teasers** | `CampagneTeasers` | hardcodé (2 teasers) |
| 4 | **Tendances actuelles** | `CarouselProduits` | `promos[0..7]` |
| 5 | **Top promos** | `CarouselProduits` | `promos[8..15]` |
| 6 | **BannerStats** | `BannerStats` | hardcodé |
| 7 | **Catégories tuiles** | `TuilesCategoriesCarousel` | hardcodé (10 tuiles) |
| 8 | **BannerHowItWorks** | `BannerHowItWorks` | hardcodé |
| 9 | **Smartphones** | `CarouselProduits` | `smartphones[0..9]` |
| 10 | **Électroménager** | `CarouselProduits` | `electro[0..9]` |
| 11 | **BannerBoutiques** | `BannerBoutiques` | hardcodé |
| 12 | **Marques** | `MarqueeMarques` | hardcodé (16×2) |
| 13 | **CTA boutique** | JSX inline | — |

---

## Composants

### `CarteProduit`

**Fichier :** `src/components/product/CarteProduit.tsx` · Server Component

Carte produit avec image, badge réduction %, marque, store, stock et prix.

#### Badge de réduction

```tsx
const pourcent = (hasDiscount && produit.prix_max && produit.prix_max > 0)
  ? Math.round(((produit.prix_max - (produit.prix_min ?? 0)) / produit.prix_max) * 100)
  : 0
// -XX%  si pourcent > 0  |  -XX DT  si pourcent = 0
```

#### Image

- Fond : `bg-white`, ratio `aspect-[4/3]`, `object-contain`

#### Couleurs boutiques

| Boutique | Classes |
|----------|---------|
| Mytek | `bg-blue-50 border-blue-100 text-blue-600` |
| Tunisianet | `bg-green-50 border-green-100 text-green-600` |
| Spacenet | `bg-purple-50 border-purple-100 text-purple-600` |

---

### `CarouselProduits`

**Fichier :** `src/components/ui/CarouselProduits.tsx` · Client Component

Carrousel avec boutons ◀▶ et CSS scroll snap. Utilisé sur 4 sections homepage + produits similaires.

#### Largeurs cartes

| Breakpoint | Largeur | Cartes visibles (~) |
|-----------|---------|---------------------|
| Mobile `<640px` | `w-36` (144px) | ~2.5 |
| sm `640px+` | `w-44` (176px) | ~4 |
| lg `1024px+` | `w-48` (192px) | ~6 |

```tsx
// scroll de ~700px par clic
scrollRef.current?.scrollBy({ left: 700, behavior: 'smooth' })
// Boutons opacity-0 quand canLeft/canRight = false
```

---

### `StoriesCategories`

**Fichier :** `src/components/ui/StoriesCategories.tsx` · Server Component

Rangée de cercles colorés par catégorie, style Instagram Stories.

- Cercles `w-12 sm:w-14`, couleur solide unique par catégorie
- Ring orange au hover : `ring-[#F97316] ring-offset-2`
- Scrollable horizontal sans scrollbar
- Remplace l'ancienne barre `CategoriesPills`

---

### `CampagneTeasers`

**Fichier :** `src/components/ui/CampagneTeasers.tsx` · Server Component

2 cartes gradient (1 col mobile → 2 cols sm+) avec badge, titre, sous-titre et CTA pill.

| Teaser | Gradient | Icon | Href |
|--------|----------|------|------|
| Offres Ramadan | `#F97316 → #C2410C` | 🌙 | `/rechercher?en_promo=1` |
| Nouvelles arrivées | `#3B82F6 → #1D4ED8` | ✨ | `/categories/smartphones` |

---

### `TuilesCategoriesCarousel`

**Fichier :** `src/components/ui/TuilesCategoriesCarousel.tsx` · Server Component

Carousel horizontal de tuiles carrées `w-24 sm:w-28 h-24 sm:h-28` avec fond teinté par catégorie.

- Fond coloré unique (blue-50, rose-50, emerald-50…), border colorée au hover
- Emoji `text-3xl/4xl` avec `scale-110` au hover
- CSS snap scroll — remplace la grille fixe `grid-cols-4 lg:grid-cols-8`

---

### `Banners.tsx` — 3 composants

**Fichier :** `src/components/ui/Banners.tsx` · Server Components (exports nommés)

#### `BannerStats`

Bande fond `#0F172A`, 4 chiffres clés en grid 2→4 cols avec icônes Lucide oranges.

| Icône | Valeur | Label |
|-------|--------|-------|
| `Package` | 50 000+ | Produits référencés |
| `Star` | 120+ | Marques disponibles |
| `Store` | 3 | Boutiques partenaires |
| `TrendingDown` | -40% | De réduction max |

#### `BannerHowItWorks`

3 cartes blanches avec numéro badge orange, icône colorée et description.

| Badge | Titre | Icône | Fond icône |
|-------|-------|-------|------------|
| 01 | Recherchez | `Search` | `bg-blue-50 text-blue-500` |
| 02 | Comparez | `BarChart2` | `bg-orange-50 text-[#F97316]` |
| 03 | Achetez | `ShoppingCart` | `bg-green-50 text-green-500` |

#### `BannerBoutiques`

3 cartes boutiques en `grid-cols-3` avec logo `next/image`, badge catégorie et lien.

| Boutique | Logo | Badge | Border hover |
|----------|------|-------|-------------|
| Mytek | `/stores/mytek.png` | Informatique & High-Tech | `hover:border-blue-300` |
| Tunisianet | `/stores/tunisianet.png` | Électronique & Photo | `hover:border-green-300` |
| Spacenet | `/stores/spacenet.png` | Multimédia & Gaming | `hover:border-purple-300` |

---

### `MarqueeMarques`

**Fichier :** `src/components/ui/MarqueeMarques.tsx` · Server Component

16 marques doublées (×2 = 32 items) pour boucle CSS sans saut.

```css
/* globals.css */
@keyframes marquee {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
.animate-marquee { animation: marquee 30s linear infinite; }
.animate-marquee:hover { animation-play-state: paused; }
```

---

## Page détail produit

**Fichier :** `src/app/(public)/produit/[slug]/page.tsx`

Chargement séquentiel : `getProduit(slug)` puis `getProduits({ categorie })` pour les similaires.

```ts
const res = await getProduits({ categorie: produit.categorie })
similaires = res.data.filter(p => p.id !== produit.id).slice(0, 3)
```

Section similaires : `grid grid-cols-3 gap-3 sm:gap-4`, affichée uniquement si `similaires.length > 0`.

---

## Page recherche

**Fichier :** `src/app/(public)/rechercher/page.tsx`

Grille résultats : `grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-5`

- Mobile : **2 cartes par ligne**
- lg : 3 colonnes · xl : 4 colonnes

---

## Appel API — `getProduits()`

**Fichier :** `src/lib/api/produits.ts`

| Paramètre | Type | Description |
|-----------|------|-------------|
| `q` | `string` | Terme de recherche |
| `categorie` | `string` | Slug catégorie |
| `marque` | `string` | Nom marque |
| `prix_min` | `number` | Prix minimum DT |
| `prix_max` | `number` | Prix maximum DT |
| `en_promo` | `boolean` | Produits en promo uniquement |
| `page` | `number` | Page (défaut 1) |

Retourne `{ data: Produit[], meta: { page, total_pages, total_items, par_page } }`.

> **Note :** Toujours filtrer les paramètres `undefined` avant `URLSearchParams` — évite les chaînes `"undefined"` dans l'URL.

---

## Types TypeScript

**Fichier :** `src/types/index.ts`

```ts
interface Produit {
  id: string
  slug: string | null
  nom: string
  marque: string
  categorie: string
  categorie_nom: string
  prix_min: number | null
  prix_max: number | null
  image: string | null
  en_stock: boolean | undefined
  discount: number
  reference: string | null
  boutique: string | null
  url_boutique: string | null
}
```

---

## Design tokens (`globals.css`)

```css
@theme inline {
  --color-brand-primary:      #0F172A;
  --color-brand-accent:       #F97316;
  --color-brand-accent-hover: #EA6C0A;
  --color-brand-muted:        #F8FAFC;
  --color-brand-surface:      #FFFFFF;
  --color-brand-text:         #1E293B;
  --color-brand-subtle:       #64748B;
  --color-brand-border:       #E2E8F0;
  --font-sans:    var(--font-inter);
  --font-heading: var(--font-space-grotesk);
}
```

---

## Déploiement (Vercel)

```bash
cd D:/github/toprix-frontend
git push origin main
# Vercel redéploie automatiquement → https://toprix-mu.vercel.app
```

| Variable Vercel | Valeur |
|-----------------|--------|
| `NEXT_PUBLIC_API_URL` | `https://api.toprix.tn/api/v1` |
