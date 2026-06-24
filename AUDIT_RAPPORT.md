# Rapport d'audit & d'amélioration — Le Clos des Zinnias (site)

**Date :** juin 2026
**Périmètre :** `C:\Gabriel\clos-des-zinnias\site` — 6 pages HTML + feuille de style et scripts partagés.
**Méthode :** un sous-agent dédié par page (exécution **séquentielle** pour éviter tout conflit sur les fichiers partagés `style.css` / `main.js` / `animations.js`), précédé et suivi d'une **passe « socle » par l'orchestrateur** pour les éléments transverses.

---

## 0. Constat général

Le site était **déjà d'un très haut niveau** : design system cohérent avec tokens, polices `Cormorant Garamond` + `DM Sans` (avec `preconnect` + `display=swap`), HTML sémantique, SEO et données structurées JSON-LD soignés, `prefers-reduced-motion` géré, `:focus-visible` global, reveals/parallax/compteurs/lightbox/accordéon/validation de formulaire déjà en place et bien réalisés.

**Parti pris :** rester **chirurgical** — n'améliorer que ce qui apporte un gain clair, **aucune régression**, **sobriété** stricte (pas de dégradé criard, d'orbe, de pulsing). Le **thème sombre éditorial est conservé tel quel** (décision validée : pas de toggle clair/sombre, qui aurait dénaturé l'identité). Les gains sont donc surtout **performance (CLS)**, **accessibilité** et **cohérence du code**.

**Sécurité :** sauvegarde complète des fichiers source créée avant toute modification (dossier `_backup_pre_audit_*`). Dépôt git en place comme second filet.

---

## 1. Socle partagé (orchestrateur)

| Amélioration | Détail | Pourquoi |
|---|---|---|
| **Bouton « retour en haut »** | Composant `.to-top` injecté par `main.js` (aucun markup dupliqué dans les pages), apparaît après 600 px de défilement, style cohérent navbar (verre dépoli + or), `aria-label`, respecte `prefers-reduced-motion` | Item de la checklist absent ; navigation longue page facilitée |
| **Dimensions d'images** | Manifeste des dimensions réelles des 30 images extrait (parseur WebP) et appliqué sur les 6 pages | Supprime le CLS (cf. §3) |
| **`.scroll-hint` mobile** | Masqué ≤ 600 px (élément décoratif à l'étroit au-dessus de la barre de stats du hero) | Confort mobile, anti-chevauchement |

Vérifié comme **déjà présents** (donc non dupliqués) : `:focus-visible` (anneau or), bloc `prefers-reduced-motion` complet, `::selection` aux couleurs de la marque.

---

## 2. Détail par page

### `index.html` (accueil)
- **5 images** dotées de `width`/`height` (anti-CLS). Hero (LCP) laissée en chargement immédiat + `fetchpriority="high"` ; les 4 images sous la flottaison passées en `loading="lazy"` + `decoding="async"`.
- **7 SVG décoratifs** marqués `aria-hidden="true" focusable="false"` (icône téléphone, listes de features, réassurance).
- Une seule `<h1>` et hiérarchie confirmées conformes. `alt` déjà de qualité (mentions « illustrative / non contractuelle » présentes).
- Aucun bloc CSS ajouté : rien ne le justifiait sans redondance.

### `projet.html`
- **Régression corrigée (P1)** : le `<style>` inline utilisait un token inexistant `var(--font-body)` (le bon est `--font-corps`) → 4 éléments retombaient sur la police système. Corrigé.
- **11 images** dotées de `width`/`height` ; hero en `fetchpriority="high"`, les autres en `lazy` + `decoding="async"`.
- **8 SVG décoratifs** masqués aux technologies d'assistance.
- Animation `pulse` infinie du point de calendrier **désactivée sous `prefers-reduced-motion`** (renommée `cal-pulse` pour éviter toute collision globale).
- CSS inline du `<head>` **migré** dans un bloc dédié `/* ===== PAGE: projet ===== */` de `style.css`.
- `<cite>` redondant du bandeau de clôture corrigé en véritable attribution.

### `lots.html`
- **3 images** dotées de `width`/`height` (+ `fetchpriority`/`lazy`/`decoding`).
- **9 SVG** masqués aux AT.
- **Tableau comparatif accessibilisé** : `type="button"` sur les boutons de tri, `aria-label` explicites (« Trier le tableau par surface / prix / prix au m² »), `<caption>` réservée aux lecteurs d'écran, flèches `↕`/`↑`/`↓` masquées aux AT.
- `aria-label` sur les liens « Appeler », focus clavier renforcé (bloc `/* ===== PAGE: lots ===== */`).
- Valeurs commerciales (prix/surfaces) **non modifiées**.

### `galerie.html`
- **25 images** dotées de `width`/`height` + `decoding="async"` (assets drone en 4032×3024, visuels en ~2048 px).
- **Tous les déclencheurs de lightbox** rendus accessibles au clavier : `role="button"`, `tabindex="0"`, `aria-label="Agrandir : …"`.
- L'image LCP (hero) reste immédiate + `fetchpriority` ; le reste en `lazy`.

### `contact.html`
- Image hero (LCP) dotée de `width`/`height` + `decoding` + `fetchpriority`.
- **6 SVG décoratifs** masqués aux AT (icônes de coordonnées, cadenas de réassurance, coche de succès).
- `<style>` inline du `<head>` **migré** dans un bloc `/* ===== PAGE: contact ===== */` de `style.css` (cohérence avec `projet`).
- Formulaire : labels, `required`, validation e-mail temps réel, carte avec `title` et `loading="lazy"` déjà conformes — non touchés.

### `404.html`
- Image hero dotée de `width`/`height` + `decoding` + `fetchpriority`.
- SVG téléphone décoratif masqué aux AT.

---

## 3. Passe JS d'accessibilité globale (`main.js`)

Améliorations nécessitant le JS partagé, identifiées par les sous-agents et appliquées centralement :

1. **Lightbox** : activation clavier **Entrée / Espace** des déclencheurs `role="button"` (ils étaient focusables mais non activables au clavier) ; `role="dialog"` + `aria-modal="true"` + `aria-label` sur la visionneuse ; **gestion du focus** (déplacé sur le bouton « Fermer » à l'ouverture, rendu au déclencheur à la fermeture).
2. **Accordéon** : synchronisation de `aria-expanded` (état initial + bascule).
3. **Boutons de tri** : synchronisation de `aria-pressed` (état initial + bascule), sans état « mensonger » figé.

Syntaxe validée (`node --check` sur `main.js` et `animations.js`).

---

## 4. Choix de design justifiés

- **Aucun nouvel effet visuel décoratif** ajouté : le site en avait déjà assez et de qualité. Ajouter aurait contredit la consigne de sobriété et risqué la régression. Les seuls « effets » introduits sont des **états de focus clavier** (déjà à la couleur or de la charte) et une **désactivation** d'animation sous `prefers-reduced-motion`.
- **Migration des CSS inline** (`projet`, `contact`) vers des blocs `/* ===== PAGE: xxx ===== */` clairement délimités en fin de `style.css` : une seule source de vérité, code plus propre et lisible, cascade préservée (placés après les règles globales).
- **Thème conservé** : noir + crème/gris + or comme accent unique, sauge en secondaire. Identité Provence naturelle et chaleureuse préservée.

---

## 5. Effets / animations — bilan

| Effet | Statut |
|---|---|
| Reveals au scroll, parallax, compteurs animés | Déjà présents — conservés |
| Hover cartes/boutons/liens, sheen des boutons | Déjà présents — conservés |
| Lightbox (clavier, flèches, swipe) | Conservée + **accessibilité clavier & focus renforcés** |
| Accordéon | Conservé + **`aria-expanded`** |
| Bouton « retour en haut » | **Ajouté** (sobre, discret) |
| Pulsing du calendrier (projet) | **Neutralisé sous reduced-motion** |

---

## 6. Points de vigilance restants (à arbitrer côté client)

1. **E-mail `zinias@ponthieu.fr`** (sans 2ᵉ « n », présent dans le footer des 6 pages **et sur la plaquette Figma**) : très probablement la **vraie adresse**, donc **laissé tel quel**. À confirmer côté client — ne pas « corriger » à l'aveugle (risque de casser la réception des demandes).
2. **Prix Lot 1 = Lot 2 = 262 500 €** (cohérent partout : cartes, tableau, JSON-LD) : valeurs **non modifiées**. À vérifier si c'est bien volontaire commercialement.
3. **`.info-item { border-left: 1px solid var(--or) }`** (page contact, règle globale existante) : c'est une bordure-gauche colorée, motif que la consigne déconseille. Non touché car **pré-existant et global** (impacterait d'autres usages). À refondre globalement si souhaité (ex. filet en haut plutôt qu'à gauche).
4. **Dossier de sauvegarde `_backup_pre_audit_*`** : à supprimer une fois les changements validés (ne pas le déployer en production — `.gitignore` / `.assetsignore` à vérifier).
5. **Vérification sur appareils réels** recommandée à 375 px et 1280 px (les corrections sont raisonnées mais un contrôle visuel final est sain), notamment la galerie (densité d'images) et le formulaire de contact.

---

## 7. Récapitulatif des fichiers modifiés

- **HTML** : `index.html`, `projet.html`, `lots.html`, `galerie.html`, `contact.html`, `404.html` (dimensions d'images, `lazy`/`decoding`/`fetchpriority`, `aria-hidden` sur SVG décoratifs, accessibilité tableau & lightbox, corrections ponctuelles).
- **`style.css`** : bouton `.to-top`, ajustement global `.scroll-hint`, blocs page `projet` / `lots` / `contact` (migrations + affinages a11y). **Aucun token `:root` ni règle globale existante modifiés.**
- **`main.js`** : bouton retour-en-haut, accessibilité lightbox / accordéon / tri.
- **`animations.js`** : non modifié.

Aucune régression introduite : navigation, transitions de page, tri du tableau, deep-link `?lot=N`, validation de formulaire, SEO, JSON-LD, balises Open Graph/Twitter et ordre des sections sont préservés.
