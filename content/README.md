# Le blog du Clos des Cyprès : écrire, contrôler, publier

Ce dossier contient les **textes** du blog. Chaque article est un fichier `.md` (du texte simple, sans HTML) dans `content/blog/`. Un petit programme (`tools/build_blog.py`) transforme ces textes en pages web : vous n'écrivez jamais de HTML et vous ne touchez jamais au dossier `blog/` (il est fabriqué automatiquement).

Rien ici n'est publié tel quel : le dossier `content/` est exclu du déploiement (`.assetsignore`).

---

## 1. En bref : écrire un article en 5 commandes

À taper dans le Terminal, depuis le dossier du site.

```sh
# 1. Créer le squelette (le fichier est un brouillon tant que vous ne le dites pas)
python3 tools/new_article.py "Viabilisation d'un terrain : ce que ça comprend" --keyword "viabilisation d'un terrain"

# 2. Remplir le fichier content/blog/<adresse>.md (voir plus bas), puis passer « draft: true » à « draft: false »

# 3. Contrôler (n'écrit rien ; affiche les erreurs et les conseils)
python3 tools/build_blog.py --check

# 4. Construire les pages
python3 tools/build_blog.py

# 5. Publier : voir la section 7
```

Pour **voir** un brouillon avant de le publier : `python3 tools/build_blog.py --include-drafts` fabrique des pages d'aperçu (marquées « noindex » : Google ne les indexe pas, et elles ne figurent ni dans le plan du site ni dans le flux RSS). Ouvrez ensuite le site en local (`python3 -m http.server` à la racine, puis `http://localhost:8000/blog/<adresse>/`) ; avec ce serveur simple, les liens vers `/lots`, `/contact`… ne s'ouvrent pas (il ne sait pas ajouter `.html`), ce qui est normal : ils fonctionnent en ligne. **Ne publiez jamais un dossier construit avec `--include-drafts`** : relancez le build normal avant de publier (il supprime les pages d'aperçu).

Le modèle complet qui montre toutes les possibilités est `content/blog/_exemple-article.md` (il commence par `_` : il est ignoré, sauf avec `--include-drafts`).

---

## 2. L'en-tête d'un article (le « front matter »)

Chaque fichier commence par un bloc entre deux lignes `---`. Une ligne = un champ, au format `nom: valeur`. Les lignes qui commencent par `#` sont des commentaires.

```
---
title: Viabilisation d'un terrain : ce que comprend la viabilisation
description: Voirie, eau, électricité, fibre, assainissement : ce que comprend la viabilisation d'un terrain à bâtir et qui la paie.
slug: viabilisation-terrain
date: 2026-10-12
updated: 2026-10-12
category: acheter-un-terrain
tags: viabilisation, lotissement, terrain à bâtir
keyword: viabilisation d'un terrain
image: /images-optimized/blog/viabilisation-terrain/couverture.webp
image_alt: Description réelle de l'image
related: lotissement-ou-terrain-en-diffus, permis-d-amenager
draft: false
---
```

| Champ | Obligatoire | Règle |
|---|---|---|
| `title` | oui | Titre de la page ET titre principal (H1). **60 caractères visés, 65 maximum.** Contient le mot-clé. Écrit pour un lecteur, pas pour un robot. |
| `description` | oui | Résumé affiché sous le titre dans Google. **120 à 155 caractères, 160 maximum.** Contient le mot-clé. |
| `slug` | non | Adresse de l'article : `/blog/<slug>/`. Minuscules, chiffres et tirets, sans accent ni espace (3 à 6 mots). Par défaut : le nom du fichier. **Ne le changez plus après publication.** |
| `date` | oui | Date de publication, `AAAA-MM-JJ` (par exemple `2026-10-12`). |
| `updated` | non | Date de la dernière **vraie** mise à jour (le fond a changé : règle, chiffre, délai). Jamais pour une simple correction de virgule. Doit être postérieure ou égale à `date`. Par défaut = `date`. |
| `category` | oui | Une parmi : `acheter-un-terrain`, `construire-en-provence`, `vivre-a-gardanne-biver`, `financer-son-projet`, `suivi-du-chantier`. |
| `tags` | non | Quelques mots, séparés par des virgules. Servent à proposer des articles proches. |
| `keyword` | oui | Le mot-clé principal : une expression qu'un lecteur tape vraiment dans Google. Il doit apparaître dans le titre, la description, le premier paragraphe et un intertitre (le contrôle le vérifie, en avertissement). |
| `image` | conseillé | Image de couverture, chemin depuis la racine du site. Largeur et hauteur sont lues dans le fichier. |
| `image_alt` | si `image` | Texte alternatif : décrit ce qu'on voit, vraiment. Obligatoire. |
| `image_width`, `image_height` | rare | Seulement si le programme ne peut pas lire la taille de l'image (certains AVIF, SVG). |
| `og_image` | non | Image de partage (réseaux sociaux), 1200 × 630 px de préférence, JPG. Sinon `image` est utilisée. |
| `related` | non | Adresses (`slug`) d'autres articles à proposer en fin de page, séparées par des virgules. Le programme complète automatiquement jusqu'à 3. |
| `draft` | non | `true` = brouillon, jamais publié. `false` ou absent = publié. |

Aucun champ « auteur » : tous les articles sont signés **« L'équipe du Clos des Cyprès »**. N'inventez jamais un nom d'auteur.

---

## 3. Écrire le texte

Après l'en-tête, on écrit en Markdown, c'est-à-dire du texte avec quelques signes simples :

| Pour obtenir | On écrit |
|---|---|
| Intertitre (sommaire) | `## Mon intertitre` |
| Sous-titre | `### Mon sous-titre` (toujours après un `##`) |
| Paragraphe | du texte, puis une **ligne vide** |
| **Gras** | `**texte**` |
| *Italique* | `*texte*` |
| Lien vers une page du site | `[les huit lots](/lots)` : toujours commencer par `/`, **sans `.html`** |
| Lien vers un article | `[mon article](/blog/mon-slug/)` : **avec la barre finale** |
| Lien vers un autre site | `[Service-Public](https://www.service-public.fr/)` |
| Liste à puces | `- une idée` (une ligne par idée) |
| Liste numérotée | `1. première étape` |
| Citation | `> texte cité` |
| Image avec légende | `![Description de l'image](/images-optimized/blog/slug/photo.webp "Légende visible")` (seule sur sa ligne) |
| Tableau | voir ci-dessous |

À savoir :

- Le titre principal (H1) vient du champ `title` : **n'écrivez jamais `# Titre`** dans le texte (le contrôle refuse).
- Le HTML brut n'est pas accepté : tout ce qui ressemble à du code est affiché comme du texte.
- La typographie française (espace insécable avant `:` `;` `!` `?`, guillemets « ») est appliquée automatiquement.
- Le premier paragraphe est mis en valeur (chapô) : il doit répondre à la question tout de suite.
- Le **sommaire** est créé automatiquement à partir des `##` (à partir de 3 intertitres), avec le temps de lecture, la date de publication et la date de mise à jour.

### Tableau

```
Tableau : Titre du tableau (facultatif, une ligne juste avant)

| Étape | Qui s'en occupe | Durée |
|:------|:---------------:|------:|
| Première étape | L'acheteur | 2 semaines |
| Deuxième étape | Le notaire | à confirmer |
```

Les deux-points de la ligne `|:---|` règlent l'alignement (gauche, centré, droite). Le tableau défile sur téléphone sans casser la page.

### Les blocs spéciaux (`:::`)

Un bloc commence par une ligne `:::nom` et se termine par une ligne `:::` seule. Les blocs ne s'imbriquent pas.

**Encadré** (une information importante) :

```
:::callout À retenir
Texte de l'encadré, avec du **gras**, des listes ou des liens.
:::
```

**Questions fréquentes** (devient des volets qui s'ouvrent, ET les données structurées Google « FAQ ») : une question = une ligne `### Question ?`, puis la réponse.

```
## Questions fréquentes

:::faq
### Qui paie la viabilisation dans un lotissement ?
Réponse courte, 40 à 120 mots, avec si utile une [liste](/lots) ou un lien.

### Combien de temps dure la procédure ?
Réponse.
:::
```

**Appel à l'action** (au milieu de l'article, après environ 40 % du texte). Le titre après `:::cta` est facultatif ; chaque ligne `- [texte](adresse)` devient un bouton (le premier en doré) ; sans ligne de ce type, deux boutons par défaut : les lots et le contact.

```
:::cta Un projet de terrain à Biver ?
Une phrase d'invitation, sans promesse.

- [Voir les huit lots](/lots)
- [Nous contacter](/contact)
:::
```

Un second appel à l'action est **ajouté automatiquement** sous chaque article (lots, terrain à bâtir à Gardanne, contact, téléphone), avec la mention « Information générale, non contractuelle ».

**Sources** (à mettre en fin d'article, sans `##` devant : le bloc a son propre titre) :

```
:::source
- [Titre de la page](https://adresse-officielle), éditeur, consulté le 05/10/2026.
- [Légifrance](https://www.legifrance.gouv.fr/), texte de loi cité.
:::
```

### Liens : la règle d'or

Chaque article doit contenir **au moins un lien dans le texte vers une page commerciale** : `/lots`, `/terrain-a-batir-gardanne` ou `/contact` (de préférence dans la première moitié, avec une ancre descriptive : « terrain à bâtir à Gardanne », « les huit lots », jamais « cliquez ici »). Le contrôle refuse un article qui n'en a aucun. Reliez aussi les articles entre eux (`related` ou liens dans le texte) : un article que personne ne cite est signalé.

---

## 4. Les images

- Dossier conseillé : `images-optimized/blog/<slug>/` (créez-le).
- **Couverture** : 1600 × 900 px, WebP, 120 Ko au plus. **Image de partage** (facultative) : 1200 × 630, JPG.
- Noms de fichiers descriptifs, en minuscules, sans accent ni espace (`terrassement-voirie.webp`).
- **Ne remplacez jamais une image déjà publiée sous le même nom** : le navigateur la garde un an. Donnez un nouveau nom.
- Le texte alternatif est obligatoire (le contrôle refuse une image sans description) : il décrit l'image, il ne répète pas la légende et ne contient pas de mots-clés ajoutés artificiellement.
- Une visualisation 3D ou une projection doit être étiquetée comme telle dans la légende (« visualisation non contractuelle »).
- Dans le texte, les images sont chargées « à la demande » (`loading="lazy"`), la couverture est chargée en priorité.
- Les photos de chantier : datées, prises sur place, sans personne identifiable sans accord.

---

## 5. Construire et contrôler

| Commande | Effet |
|---|---|
| `python3 tools/build_blog.py --check` | **Contrôle seulement : n'écrit rien.** Code retour non nul s'il y a une erreur. Vérifie liens internes, images, descriptions, titres, adresses, dates, données structurées, HTML (avec `tidy` s'il est installé), articles orphelins. |
| `python3 tools/build_blog.py` | Construit `blog/`, `feed.xml`, `sitemap.xml`. Refuse d'écrire s'il y a une erreur. Peut être relancé sans risque : s'il n'y a rien de neuf, il ne change aucun fichier. |
| `python3 tools/build_blog.py --include-drafts` | Aperçu avec les brouillons (noindex). |
| `python3 tools/build_blog.py --strict` | Les conseils (avertissements) deviennent bloquants. |

Les messages indiquent le fichier et la ligne : `content/blog/mon-article.md:42 : lien « /lot » : page introuvable`. Les **erreurs** bloquent ; les **avertissements** sont des conseils (mot-clé absent du titre, article court, aucune source…) à traiter avant de publier.

Cas particuliers :

- **Aucun article publié** (dossier vide ou seulement des brouillons) : le programme ne crée ni `blog/` ni `feed.xml` (pas de page « blog » vide) et le dit. Le lien « Blog » du menu répond alors 404 : publiez le premier article avant de mettre le site en ligne.
- Le plan du site `sitemap.xml` est **entièrement régénéré** à chaque construction : ne le modifiez plus à la main. Il reprend les pages de la racine telles qu'elles sont dans le fichier actuel (avec leurs images), ajoute `/blog/` et chaque article, et exclut `/merci` et `/404`. La date `lastmod` d'une page de la racine est la date de son dernier commit git (ou de sa dernière modification si elle n'est pas encore commitée) ; celle d'un article est son champ `updated` (sinon `date`).
- Si une page de la racine change de menu, de pied de page ou de polices, **relancez simplement le build** : le blog les relit dans `index.html` à chaque fois.

---

## 6. Calendrier éditorial recommandé

L'objectif est de répondre aux vraies questions des acheteurs, pas de « publier pour publier ».

- **Lancement** : 3 à 5 contenus de fond en 2 à 4 semaines (guide « acheter un terrain en lotissement à Gardanne », « ce qu'il faut vérifier avant d'acheter à Biver », budget d'un projet…).
- **Rythme de croisière** : **1 article de fond par mois** (2 au maximum, jamais « pour remplir »), de 1 200 à 2 000 mots, sujets issus des questions réelles (appels, e-mails, mairie, notaire, Google Search Console).
- **Journal de chantier** : **une courte entrée (250 à 500 mots, 6 à 10 photos datées) à chaque étape réelle** des travaux, soit toutes les 2 à 4 semaines, rubrique `suivi-du-chantier`. Jamais d'entrée sans étape réelle.
- **Relecture tous les 6 mois** de chaque article de fond (règles d'urbanisme, délais, textes cités, liens externes encore valables). Relecture immédiate si la règle change. On met `updated` à jour **seulement** si le fond a changé.
- **Contrôle à 3 mois** de chaque article avec la Search Console (impressions, requêtes) pour le compléter si besoin.
- **Arrêt** : on cesse de publier quand les 8 lots sont sous promesse (on garde les pages, on met à jour les statuts) ; ou quand la liste des vraies questions est épuisée (environ 10 à 12 contenus) ; ou si on ne peut plus apporter d'information nouvelle, vérifiable ou de première main.

---

## 7. Publier (commit + push)

Rien ne part en ligne tant que vous n'avez pas « poussé » les fichiers dans le dépôt GitHub : le site se met à jour au déploiement qui suit.

```sh
python3 tools/build_blog.py --check     # doit finir par « OK »
python3 tools/build_blog.py             # fabrique blog/, feed.xml, sitemap.xml
git status                              # vérifier : content/, blog/, feed.xml, sitemap.xml, images-optimized/blog/
git add content blog feed.xml sitemap.xml images-optimized
git commit -m "Blog : <titre de l'article>"
git push
```

Après le déploiement (quelques minutes), vérifier :

1. `https://clos-des-cypres.fr/blog/<slug>/` s'affiche avec son style, ses images et le menu (jamais de page « sans style »).
2. Dans le code source de la page, la ligne `canonical` est bien `https://clos-des-cypres.fr/blog/<slug>/`.
3. `curl -I https://clos-des-cypres.fr/blog/<slug>` redirige une fois vers la forme avec barre finale (c'est normal ; ne jamais écrire la forme sans barre dans un lien).
4. Dans la Search Console : envoyer `https://clos-des-cypres.fr/sitemap.xml`, puis « Inspecter l'URL » et « Demander l'indexation » de l'article (quelques demandes par jour suffisent).
5. Tester le partage (Facebook, LinkedIn) : l'image de partage s'affiche.

---

## 8. Check-list qualité avant de passer `draft: false`

- [ ] **Chaque fait est sourcé** : règle d'urbanisme, chiffre, distance, délai, taux, date. Une source officielle (Service-Public, Légifrance, mairie, notaires, ADIL, Géorisques) est citée dans un bloc `:::source` avec la date de consultation. **Ce qu'on ne peut pas vérifier, on ne l'écrit pas.**
- [ ] **Aucun prix** (décision de réunion du 18/07) : ni tarif, ni « à partir de », ni fourchette de prix des lots. Les fourchettes de coûts généraux ne sont admises qu'avec une source datée.
- [ ] **Aucune promesse** (« votre lot est bloqué », « garanti », « sans risque »), **aucune fausse rareté** (« derniers lots » sans que ce soit vrai), **aucun avis ou témoignage inventé**.
- [ ] **La source de chaque chiffre local est mentionnée** (par exemple « selon le plan local d'urbanisme de Gardanne, consulté le … »).
- [ ] Le titre et la description respectent les longueurs ; le mot-clé est dans le titre, la description, le premier paragraphe et un intertitre.
- [ ] Au moins un lien dans le texte vers `/lots`, `/terrain-a-batir-gardanne` ou `/contact` ; 2 à 3 liens vers d'autres articles ou pages utiles.
- [ ] Image de couverture avec texte alternatif réel ; visuels de synthèse étiquetés « non contractuel ».
- [ ] Aucun texte provisoire (« À RÉDIGER ») ; relu à voix haute ; fautes corrigées ; vouvoiement, ton sobre.
- [ ] Les sujets d'urbanisme, de fiscalité ou de financement ont été relus par un professionnel (notaire, géomètre, ADIL) avant publication.
- [ ] `python3 tools/build_blog.py --check` : aucune erreur, avertissements examinés.

---

## 9. Rappels juridiques (à relire avant chaque publication)

- **Aucune donnée inventée.** Tout chiffre, nom, règle, distance ou date doit être soit déjà présent sur le site, soit vérifié par une source citée (fichier des faits vérifiés du projet). À défaut, on ne l'écrit pas, on le signale « à fournir » à l'équipe.
- **Mentions légales de la publicité d'un lotissement.** Les annonces de lots doivent mentionner la **date de la décision du permis d'aménager** et que **le dossier est consultable en mairie**. Cette mention est portée par le **pied de page commun à toutes les pages** (le blog le reprend automatiquement depuis `index.html`) ; tant que la date n'est pas fournie par le porteur du projet, on ne l'invente pas. Un article qui parle des lots ou du permis ne doit rien affirmer de plus que ce qui est vérifié (numéro de permis, modificatif, date).
- **Aménageur, pas agence.** Le Clos des Cyprès est vendu en direct par l'aménageur-lotisseur : ne pas se présenter comme une agence immobilière (pas de « nos agents », pas d'horaires d'agence).
- **Pratiques commerciales loyales** : pas de pression, pas de disponibilité affichée si elle est inexacte ; les statuts des lots (disponible, sous promesse, vendu) se mettent à jour sous 24 à 48 h.
- **Information générale** : les articles ne sont pas des conseils juridiques ou fiscaux personnalisés (la mention est ajoutée automatiquement sous chaque article).
- **Données personnelles** : aucun nom, photo ou témoignage d'acheteur sans son accord écrit. Pas de faux témoignage, jamais.
- **Contenu écrit avec une aide automatique** (IA ou autre) : relecture humaine complète obligatoire, vérification de **chaque** fait à la source.

---

## 10. En cas de problème

| Message | Que faire |
|---|---|
| `lien « /xxx » : page introuvable` | Faute de frappe dans l'adresse, ou la page n'existe pas. Les pages sont `/lots`, `/projet`, `/environnement`, `/galerie`, `/contact`, `/terrain-a-batir-gardanne`. |
| `ne mettez pas « .html »` | Écrivez `/lots` et non `/lots.html` (le serveur redirigerait). |
| `ajoutez la barre finale` | Un article se lie ainsi : `/blog/mon-slug/`. |
| `image sans texte alternatif` | Renseignez `image_alt` (couverture) ou le texte entre crochets `![ici](...)`. |
| `bloc « :::xxx » ouvert ici mais jamais fermé` | Il manque la ligne `:::` seule qui ferme le bloc. |
| `aucun lien vers une page commerciale` | Ajoutez un lien vers `/lots`, `/terrain-a-batir-gardanne` ou `/contact` dans le texte. |
| `article orphelin` / `aucun autre article ne pointe vers celui-ci` | Ajoutez le `slug` dans le champ `related` d'un autre article, ou un lien dans son texte. |
| `texte provisoire « À RÉDIGER »` | Remplacez tous les passages « À RÉDIGER » du squelette. |

---

## 11. Pour les développeurs

- `tools/build_blog.py` : Python 3.9, bibliothèque standard uniquement. Réglages (adresse du site `SITE_URL`, catégories, textes de l'introduction et du bloc final, taille de page, mots-clés de préchargement des polices) en tête du fichier.
- **Écrit uniquement** : `blog/`, `feed.xml`, `sitemap.xml` (liste blanche). Il supprime seulement les fichiers qu'il a lui-même générés (repérés par la balise `generator`) et qui ne sont plus produits (article repassé en brouillon).
- **Gabarit** : le `<head>` technique (polices, CSS critique, feuilles, favicons, scripts), l'en-tête, le menu mobile, le pied de page et les bulles de contact sont **extraits de `index.html` à chaque exécution**, tous chemins en absolu (`/style.min.css`, `/fonts/...`). Les règles du CSS critique propres à l'accueil (`.hero`, `.scroll-hint`, `.reveal`) sont retirées. Si `index.html` perd un de ces repères, le build échoue avec un message explicite.
- **URLs** : `/blog/` et `/blog/<slug>/` avec barre finale (comportement `auto-trailing-slash` de Cloudflare) ; pages de la racine sans extension. Pagination `/blog/page/N/` au-delà de 12 articles.
- **Données structurées** : `BlogPosting` (auteur `Organization`, éditeur par `@id`), `BreadcrumbList`, `FAQPage` si bloc `:::faq`, `CollectionPage` pour l'index ; les nœuds `Organization`, `Place` et `WebSite` sont repris de `index.html`.
- **Déploiement automatique (option)** : la commande de build Cloudflare peut être `python3 tools/build_blog.py --check && python3 tools/build_blog.py` ; un article invalide ne part alors pas en ligne. À confirmer dans les réglages du projet Cloudflare.
- Le contrôle de la date de dernière modification des pages de la racine (`tools/lastmod_check.py`) ne connaît pas `/blog/` : il signale un écart pour ces lignes tant qu'il n'est pas adapté.
