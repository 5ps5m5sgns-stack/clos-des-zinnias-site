#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crée le squelette d'un nouvel article du blog : content/blog/<slug>.md

Usage (depuis la racine du dépôt) :
    python3 tools/new_article.py "Titre de l'article" --slug mon-article --keyword "mot-clé principal"
    python3 tools/new_article.py "Titre" --keyword "..." --category suivi-du-chantier --date 2026-11-03

Le fichier est créé avec `draft: true` : il n'est pas publié tant que vous n'avez pas
remplacé tous les textes « À RÉDIGER » et mis `draft: false`.
Python 3.9, bibliothèque standard uniquement.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_blog import CATEGORIES, slugify  # noqa: E402  (mêmes catégories et même règle de slug que le générateur)

TEMPLATE = """---
# Les lignes qui commencent par # sont des commentaires : voir content/README.md pour le détail de chaque champ.
title: {title}
# 120 à 155 caractères (160 maximum), avec le mot-clé principal.
description: À RÉDIGER : une phrase de 120 à 155 caractères qui résume l'article et contient « {keyword} ».
slug: {slug}
date: {date}
# updated: AAAA-MM-JJ   (seulement si le fond de l'article change vraiment après publication)
category: {category}
tags: {tags}
keyword: {keyword}
# Image de couverture (1600 x 900 de préférence, WebP, 120 Ko au plus) : à déposer dans images-optimized/blog/{slug}/
# image: /images-optimized/blog/{slug}/couverture.webp
# image_alt: Description réelle de l'image (obligatoire si image)
# og_image: /images-optimized/blog/{slug}/partage.jpg   (1200 x 630, facultatif)
# Autres articles à proposer en fin de page (slugs séparés par des virgules), facultatif :
related:
draft: true
---

À RÉDIGER : chapô de deux ou trois phrases qui répond tout de suite à la question du lecteur, avec le mot-clé « {keyword} » et un premier lien vers la page de référence, par exemple [les huit lots](/lots) ou [le terrain à bâtir à Gardanne](/terrain-a-batir-gardanne).

## À RÉDIGER : l'essentiel en bref

À RÉDIGER : la réponse courte, en quelques lignes.

:::callout À retenir
À RÉDIGER : le point essentiel ou le point de vigilance, en deux ou trois lignes.
:::

## À RÉDIGER : première partie (un intertitre = une question que se pose le lecteur)

À RÉDIGER : texte. Chaque fait (règle, chiffre, délai, distance) doit venir d'une source citée en fin d'article. Aucun prix.

### À RÉDIGER : un détail si nécessaire

À RÉDIGER : texte.

## À RÉDIGER : deuxième partie

À RÉDIGER : texte.

:::cta Un projet de terrain à Biver ou à Gardanne ?
À RÉDIGER : une phrase d'invitation, sans promesse ni fausse rareté.

- [Voir les huit lots](/lots)
- [Nous contacter](/contact)
:::

## Questions fréquentes

:::faq
### À RÉDIGER : question 1 ?
À RÉDIGER : réponse courte (40 à 120 mots).

### À RÉDIGER : question 2 ?
À RÉDIGER : réponse courte.
:::

:::source
- [À RÉDIGER : intitulé de la source officielle](https://www.service-public.fr/), éditeur, consulté le JJ/MM/AAAA.
:::
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Crée le squelette d'un article du blog (content/blog/<slug>.md).")
    ap.add_argument("title", help="titre de l'article (le H1 de la page ; 60 caractères visés, 65 maximum)")
    ap.add_argument("--slug", help="adresse de l'article : /blog/<slug>/ (défaut : tiré du titre)")
    ap.add_argument("--keyword", required=True, help="mot-clé principal (une requête réelle de lecteur)")
    ap.add_argument("--category", default="acheter-un-terrain", help="une parmi : " + ", ".join(CATEGORIES))
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="date de publication AAAA-MM-JJ (défaut : aujourd'hui)")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="racine du site")
    args = ap.parse_args(argv)

    slug = args.slug or slugify(args.title)[:60].rstrip("-")
    errors = []
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", slug):
        errors.append("slug invalide « %s » : minuscules, chiffres et tirets seulement" % slug)
    if args.category not in CATEGORIES:
        errors.append("catégorie « %s » inconnue : %s" % (args.category, ", ".join(CATEGORIES)))
    try:
        datetime.date.fromisoformat(args.date)
    except ValueError:
        errors.append("date invalide « %s » (format AAAA-MM-JJ)" % args.date)
    if len(args.title) > 65:
        errors.append("titre trop long (%d caractères, 65 maximum)" % len(args.title))
    target = Path(args.root) / "content" / "blog" / (slug + ".md")
    if target.exists():
        errors.append("%s existe déjà : rien n'a été écrit" % target)
    if errors:
        for e in errors:
            print("ERREUR : " + e)
        return 1

    tags = ", ".join(dict.fromkeys([args.keyword] + [CATEGORIES[args.category].lower()]))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(TEMPLATE.format(title=args.title, slug=slug, keyword=args.keyword, date=args.date,
                                      category=args.category, tags=tags), encoding="utf-8")
    print("Créé : %s" % target)
    print("Étapes suivantes : rédigez les passages « À RÉDIGER », puis passez draft: true à draft: false,")
    print("contrôlez avec  python3 tools/build_blog.py --check  et aperçu avec  --include-drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
