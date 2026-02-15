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
│   │   ├── page.tsx                  ← Page d'accueil
│   │   ├── rechercher/page.tsx       ← Recherche + filtres
│   │   ├── produit/[slug]/page.tsx   ← Détail produit
│   │   ├── categories/page.tsx       ← Liste catégories
│   │   ├── categories/[slug]/page.tsx← Catégorie produits
│   │   ├── marques/page.tsx          ← Liste marques
│   │   ├── marques/[nom]/page.tsx    ← Marque produits
│   │   ├── blog/page.tsx             ← Liste articles
│   │   ├── blog/[slug]/page.tsx      ← Détail article
│   │   └── ajouter/page.tsx          ← Formulaire boutique
│   ├── layout.tsx                    ← Layout root (Header + Footer)
│   └── globals.css                   ← Tokens Tailwind + animations
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx                ← Navbar sticky (client)
│   │   └── Footer.tsx                ← Pied de page (server)
│   ├── product/
│   │   └── CarteProduit.tsx          ← Carte produit (server)
│   └── ui/
│       ├── CarouselProduits.tsx      ← Carrousel ◀▶ (client)
│       ├── CategoriesPills.tsx       ← Pills navigation (server)
│       └── MarqueeMarques.tsx        ← Défilement marques (server)
│
├── lib/
│   └── api/
│       └── produits.ts               ← getProduits() avec tous les filtres
│
└── types/
    └── index.ts                      ← Types TypeScript globaux
```

---

## Page d'accueil (`page.tsx`)

Server Component — 3 appels API parallèles au rendu :

```ts
const [promosRes, smartphonesRes, electroRes] = await Promise.allSettled([
  getProduits({ en_promo: true }),
  getProduits({ categorie: 'smartphones' }),
  getProduits({ categorie: 'electromenager' }),
])
```

### Sections (dans l'ordre d'affichage)

| # | Section | Composant/JSX | Data source |
|---|---------|---------------|-------------|
| 1 | **Hero** | JSX inline | — |
| 2 | **CategoriesPills** | `<CategoriesPills />` | hardcodé |
| 3 | **Tendances actuelles** | `<CarteProduit>` × 8 | `promos[0..7]` |
| 4 | **Top promos** | `<CarteProduit>` × 8 | `promos[8..15]` |
| 5 | **Catégories populaires** | `<Link>` × 8 | hardcodé |
| 6 | **Smartphones** | `<CarouselProduits>` | `smartphones[0..9]` |
| 7 | **Électroménager** | `<CarouselProduits>` | `electro[0..9]` |
| 8 | **Marques** | `<MarqueeMarques />` | hardcodé |
| 9 | **CTA boutique** | JSX inline | — |

---

## Composants

### `CarteProduit` — Carte produit

**Fichier :** `src/components/product/CarteProduit.tsx`
**Type :** Server Component

Affiche une carte produit avec image, badge promo, marque, boutique, stock et prix.

#### Badge de réduction

```tsx
const pourcent = (hasDiscount && produit.prix_max && produit.prix_max > 0)
  ? Math.round(((produit.prix_max - (produit.prix_min ?? 0)) / produit.prix_max) * 100)
  : 0

// Affichage badge :
// -XX%  si pourcent > 0
// -XX DT  si pourcent = 0 (prix_max absent ou égal à prix_min)
```

#### Couleurs boutiques

| Boutique | Classe Tailwind |
|----------|----------------|
| Mytek | `bg-blue-50 border-blue-100` |
| Tunisianet | `bg-green-50 border-green-100` |
| Spacenet | `bg-purple-50 border-purple-100` |

#### Props

| Prop | Type | Description |
|------|------|-------------|
| `produit` | `Produit` | Objet produit complet |

#### Éléments responsives

- Image : `aspect-[4/3] w-full` (ratio constant, adaptatif)
- Padding : `p-3 sm:p-4`
- Titre : `text-xs sm:text-sm`
- Prix : `text-base sm:text-lg`
- Touch target flèche : `w-9 h-9` (minimum 36px)

---

### `CarouselProduits` — Carrousel horizontal

**Fichier :** `src/components/ui/CarouselProduits.tsx`
**Type :** Client Component (`'use client'`)

Carrousel de produits avec boutons ◀▶ et défilement CSS snap.

#### Fonctionnement

```tsx
const scrollRef = useRef<HTMLDivElement>(null)
const [canLeft, setCanLeft] = useState(false)
const [canRight, setCanRight] = useState(true)

const checkScroll = useCallback(() => {
  const el = scrollRef.current
  if (!el) return
  setCanLeft(el.scrollLeft > 4)
  setCanRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4)
}, [])

// scroll de 700px par clic (~3 cartes)
const scroll = (dir: 'left' | 'right') => {
  scrollRef.current?.scrollBy({ left: dir === 'right' ? 700 : -700, behavior: 'smooth' })
}
```

- Écoute `scroll` (passive) et `resize` sur `window`
- Les boutons sont `opacity-0 pointer-events-none` quand le défilement est impossible
- CSS : `overflow-x-auto snap-x snap-mandatory [scrollbar-width:none]`
- Chaque carte : `snap-start shrink-0 w-[calc(50%-6px)] sm:w-[calc(33.33%-8px)] lg:w-[calc(25%-9px)]`

#### Props

| Prop | Type | Description |
|------|------|-------------|
| `produits` | `Produit[]` | Liste de produits à afficher |

---

### `CategoriesPills` — Navigation catégories

**Fichier :** `src/components/ui/CategoriesPills.tsx`
**Type :** Server Component

Barre de navigation rapide horizontale, scrollable sur mobile.

#### Catégories affichées

| Label | Href | Icône |
|-------|------|-------|
| Smartphones | `/categories/smartphones` | 📱 |
| Laptops | `/categories/ordinateurs-portables` | 💻 |
| Tablettes | `/categories/tablettes` | 📟 |
| Audio | `/categories/audio` | 🎧 |
| Gaming | `/categories/gaming` | 🎮 |
| Électroménager | `/categories/electromenager` | 🏠 |
| Photo & Vidéo | `/categories/photo` | 📷 |
| Imprimantes | `/categories/imprimantes` | 🖨️ |
| Moniteurs | `/categories/moniteurs` | 🖥️ |
| Tout voir | `/categories` | → |

#### Comportement

- Barre statique (`bg-white border-b border-[#E2E8F0]`), non sticky
- Défilement horizontal masqué (`[scrollbar-width:none] [&::-webkit-scrollbar]:hidden`)
- Hover : `border-[#F97316]/40 text-[#F97316] bg-orange-50`

---

### `MarqueeMarques` — Défilement marques

**Fichier :** `src/components/ui/MarqueeMarques.tsx`
**Type :** Server Component

Défilement infini horizontal des marques référencées, pause au survol.

#### Technique

```tsx
const MARQUES = ['Apple', 'Samsung', 'Sony', 'LG', 'Xiaomi', ...]  // 16 marques
const doubled = [...MARQUES, ...MARQUES]  // 32 items pour loop sans saut

// Animation CSS dans globals.css :
// @keyframes marquee : translateX(0) → translateX(-50%)
// .animate-marquee { animation: marquee 30s linear infinite }
// .animate-marquee:hover { animation-play-state: paused }
```

- Durée : 30s (ajustable dans `globals.css`)
- Les 16 marques sont dupliquées pour que la liste soit exactement 2× la largeur visible
- Chaque marque est un `<Link>` vers `/marques/{marque.toLowerCase()}`

---

## Appel API — `getProduits()`

**Fichier :** `src/lib/api/produits.ts`

Appelle `GET /api/v1/produits/` avec les filtres supportés :

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

> **Note :** Toujours filtrer les paramètres `undefined` avant de construire `URLSearchParams` pour éviter les chaînes `"undefined"` dans l'URL.

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

## Design tokens (globals.css)

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

## Déploiement frontend (Vercel)

```bash
# Déployer
cd D:\github\toprix-frontend
git push origin main
# → Vercel détecte le push et redéploie automatiquement

# URL de production
https://toprix-mu.vercel.app
```

Variables d'environnement Vercel :

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | URL de l'API backend (`https://api.toprix.tn/api/v1`) |
