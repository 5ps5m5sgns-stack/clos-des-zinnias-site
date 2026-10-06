---
# EXEMPLE — ce fichier commence par « _ » : il est ignoré par le build normal et n'est jamais publié.
# Pour le voir : python3 tools/build_blog.py --include-drafts  (pages en noindex, hors sitemap et flux).
# Les lignes qui commencent par # dans cet en-tête sont des commentaires.

# Titre = titre de la page ET H1 (60 caractères visés, 65 maximum). Pas de « # » dans le texte.
title: EXEMPLE : modèle d'article pour le blog du Clos des Cyprès
# 120 à 155 caractères, 160 maximum. Une phrase qui donne envie de lire, avec le mot-clé.
description: EXEMPLE fictif : un modèle d'article qui montre tous les blocs du blog (sommaire, « En bref », cartes, tableau, FAQ, sources, appel à l'action).
# Adresse de l'article : /blog/<slug>/ (minuscules, tirets, sans accent). Par défaut : le nom du fichier.
slug: exemple-article
# Dates au format AAAA-MM-JJ. « updated » : seulement pour un VRAI changement de fond.
date: 2026-10-05
updated: 2026-10-06
# Une catégorie parmi : acheter-un-terrain, construire-en-provence, vivre-a-gardanne-biver, financer-son-projet, suivi-du-chantier
category: acheter-un-terrain
tags: exemple, modèle, lotissement
# Mot-clé principal : dans le titre, la description, le premier paragraphe et un intertitre.
keyword: modèle d'article
# Image de couverture : chemin depuis la racine du site. Largeur/hauteur lues dans le fichier.
image: /images-optimized/hero-aerial-villas-golden-hour-1024.avif
image_alt: Vue aérienne du lotissement Le Clos des Cyprès à Biver, projection illustrative
# Image de partage (réseaux sociaux), 1200 x 630 de préférence. Facultatif : repli sur « image ».
og_image: /images-optimized/hero-aerial-villas-golden-hour-og.jpg
# Articles à proposer en « À lire aussi » (slugs séparés par des virgules). Facultatif : complété automatiquement.
related:
draft: true
---

EXEMPLE — texte fictif. Ce **modèle d'article** montre comment écrire pour le blog : un premier paragraphe qui répond tout de suite à la question, avec le mot-clé placé naturellement, puis des intertitres clairs. Il pointe aussi vers la page des [huit lots](/lots) dès les premières lignes, comme le fait tout article utile.

:::bref
- list-checks | EXEMPLE : trois à quatre pastilles, seize mots au plus chacune.
- book-open | Chaque pastille reprend un point du texte, sans fait nouveau.
- phone | Le pictogramme se choisit dans /icons.svg (liste dans le guide du système de design).
:::

## Ce que montre ce modèle d'article

Un paragraphe se termine par une ligne vide. On écrit en **gras** pour l'essentiel, en *italique* pour un terme technique, et avec `du code` pour un nom de fichier. Un [lien externe](https://www.service-public.fr/) s'ouvre sans bavardage ; un lien interne commence toujours par une barre oblique, par exemple la page [terrain à bâtir à Gardanne](/terrain-a-batir-gardanne).

Voici une liste à puces, puis une liste numérotée avec un niveau imbriqué :

- une idée courte, sans point final ;
- une deuxième idée qui tient sur plusieurs lignes, pour montrer que le retour à la ligne
  continue le même élément ;
- une troisième, avec une sous-liste :
  - un détail ;
  - un autre détail.

1. Première étape.
2. Deuxième étape, avec un [lien vers la page contact](/contact).
3. Troisième étape.

### Un sous-titre de niveau 3

Les intertitres `##` alimentent le sommaire ; les `###` servent à découper une section longue. Une citation s'écrit avec le signe « > » :

> EXEMPLE : une citation courte, attribuée à sa source, vaut mieux qu'une longue paraphrase.

:::callout À retenir
Un encadré met en avant **une** information importante, par exemple une définition ou un point de vigilance. Il peut contenir une liste :

- un point de vigilance ;
- un autre point, avec un [lien vers les lots](/lots).
:::

## Des cartes à pictogramme

Un bloc `:::cards` met en cartes une énumération (2 à 8 lignes : « - pictogramme | Titre | texte »).

:::cards
- ruler | Première carte | EXEMPLE : le titre tient en cinq mots au plus, le texte peut contenir un [lien](/lots).
- scale | Deuxième carte | EXEMPLE : le texte de la liste d'origine est repris tel quel.
:::

## Un tableau lisible sur téléphone

Tableau : Exemple de tableau fictif (aucune donnée réelle)

| Étape | Qui s'en occupe | Durée indicative |
|:------|:---------------:|-----------------:|
| Étape A (exemple) | Acheteur | 2 semaines |
| Étape B (exemple) | Notaire | 3 mois |
| Étape C (exemple) | Constructeur | à définir |

Sous 48 rem de large, chaque ligne devient une carte (la première colonne en titre) : aucun défilement horizontal. Un tableau « exemple fictif » porte une légende qui commence par « Exemple fictif, pour comprendre le calcul : » et une ligne « Note du tableau : » avec la formule et la source.

Tableau : Exemple fictif, pour comprendre le calcul : somme de deux postes

| Poste | Calcul | Résultat |
|:------|:-------|---------:|
| Poste A | Hypothèse | 10 |
| Poste B | Hypothèse | 20 |
| **Total** | 10 + 20 | **30** |
Note du tableau : Formule : total = poste A + poste B. Source : EXEMPLE, à citer avec sa date de consultation.

![Plan de composition des huit lots du Clos des Cyprès, indicatif non contractuel](/images-optimized/plan-officiel-composition-1024.webp "Plan de composition, 8 lots : indicatif et non contractuel.")

Une image seule sur sa ligne devient une figure avec légende. Le texte alternatif (entre crochets) est obligatoire. Pour un format dont la taille ne se lit pas (certains AVIF, SVG), on ajoute la taille à la fin :

![Illustration : village provençal et son clocher, adossés à la colline boisée](/images-optimized/village-biver-clocher-1024.avif "Illustration : village provençal."){1024x683}

:::cta Parlons de votre projet
EXEMPLE : un bloc d'appel à l'action au milieu de l'article, avec un texte court et sans promesse.

- [Voir les huit lots](/lots)
- [Nous contacter](/contact)
:::

## Questions fréquentes

:::faq
### EXEMPLE : à quoi sert la FAQ d'un article ?
Elle répond aux questions concrètes des lecteurs. Chaque question devient un volet qui s'ouvre au clavier comme à la souris, et le même contenu est repris dans les données structurées de la page.

### EXEMPLE : une réponse peut-elle contenir une liste ?
Oui :

- une réponse courte vaut mieux qu'un long discours ;
- un lien vers la page [terrain à bâtir à Gardanne](/terrain-a-batir-gardanne) est bienvenu.

### EXEMPLE : combien de questions prévoir ?
Entre trois et huit, des questions réelles posées par de vrais acheteurs.
:::

Un bloc de sources termine l'article (pas de titre « ## » devant : le bloc porte son propre titre) :

:::source Sources de cet exemple
- [Service-Public.fr](https://www.service-public.fr/), site officiel de l'administration française (exemple : citez la page précise et la date de consultation).
- [Légifrance](https://www.legifrance.gouv.fr/), pour les textes de loi.
:::
