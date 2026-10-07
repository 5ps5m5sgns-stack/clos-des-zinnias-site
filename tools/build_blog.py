#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Générateur du blog du site statique « Le Clos des Cyprès ».

Python 3.9, bibliothèque standard UNIQUEMENT. Aucune installation nécessaire.

Ce que fait le script
---------------------
Il lit les articles écrits en Markdown dans `content/blog/*.md` et produit :
  - blog/index.html (+ blog/page/N/index.html au-delà de 12 articles) ;
  - blog/<slug>/index.html pour chaque article ;
  - feed.xml (flux RSS 2.0) ;
  - sitemap.xml (pages de la racine reprises du sitemap existant + blog + articles).
Il n'écrit QUE ces fichiers (liste blanche). Les 11 pages HTML de la racine, les
feuilles de style et les scripts ne sont jamais modifiés : l'en-tête, le menu, le pied
de page et le <head> technique sont LUS dans index.html à chaque exécution, pour que le
blog reste synchrone avec le reste du site.

Usage (depuis la racine du dépôt)
---------------------------------
    python3 tools/build_blog.py                  construit le blog
    python3 tools/build_blog.py --check          contrôle sans rien écrire (code retour != 0 si erreur)
    python3 tools/build_blog.py --include-drafts prévisualise aussi les brouillons (noindex)
    python3 tools/build_blog.py --strict         les avertissements deviennent des erreurs
    python3 tools/build_blog.py --root DIR       travaille sur une copie du dépôt (tests)

Sans aucun article publié (rien dans content/blog, ou uniquement des brouillons), le script
NE génère PAS blog/ ni feed.xml (pas de page « blog » vide), et le dit clairement.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True

# =====================================================================================
# 1. RÉGLAGES (tout ce qui peut changer un jour est ici)
# =====================================================================================

SITE_URL = "https://clos-des-cypres.fr"          # UNE seule constante (décision D1)
SITE_NAME = "Le Clos des Cyprès"
FEED_TITLE = "Blog du Clos des Cyprès"
AUTHOR_DISPLAY = "L'équipe du Clos des Cyprès"    # nom affiché (jamais de personne inventée)
AUTHOR_LD_NAME = "Le Clos des Cyprès"             # auteur dans le JSON-LD : l'Organization
PHONE_DISPLAY = "06 09 20 45 90"
PHONE_TEL = "+33609204590"

PAGE_SIZE = 12            # articles par page d'index
FEED_SIZE = 20            # articles dans le flux RSS
RELATED_MAX = 3           # « À lire aussi »
TOC_MIN_H2 = 3            # sommaire affiché à partir de 3 intertitres H2
WORDS_PER_MINUTE = 220    # vitesse de lecture
MIN_WORDS_WARN = 250      # en dessous : article jugé mince (avertissement)

COMMERCIAL_PATHS = ("/lots", "/terrain-a-batir-gardanne", "/contact")
SITEMAP_EXCLUDED = ("/merci", "/404")
RESERVED_SLUGS = {"page", "categorie", "index", "feed", "auteur", "tag"}
RESERVED_IDS = {"contenu", "mobile-menu", "toc-title", "related-title"}

# Catégories admises (slug -> libellé). Une faute de frappe fait échouer le contrôle.
CATEGORIES = {
    "acheter-un-terrain": "Acheter un terrain",
    "construire-en-provence": "Construire en Provence",
    "vivre-a-gardanne-biver": "Vivre à Gardanne et Biver",
    "financer-son-projet": "Financer son projet",
    "suivi-du-chantier": "Suivi du chantier",
}

# Page d'index du blog (texte éditorial STABLE : aucune date, aucun prix, aucun chiffre qui change)
INDEX_TITLE = "Construire sa maison : le blog"                  # + « | Le Clos des Cyprès »
INDEX_H1 = "Le blog : acheter un terrain à bâtir à Gardanne et Biver"
INDEX_DESCRIPTION = ("Guides pratiques pour acheter un terrain à bâtir et construire sa maison en Provence, "
                     "à Gardanne et à Biver : démarches, règles, budget et financement.")
# Chapô sur fond sombre (texte brut, sans lien : les appels cliquables sont juste dessous)
INDEX_INTRO = ("Des guides pratiques pour acheter un terrain en lotissement, construire sa maison en Provence et "
               "connaître les règles à respecter. Chaque article cite ses sources officielles et indique la date de sa "
               "dernière mise à jour.")
# Texte d'accueil de l'index (Markdown, même moteur que les articles : liens, encadré). Il porte les deux appels
# exigés (D55) : « Appelez-nous au … » (tel:) et « Envoyez-nous un message » (/contact), les liens vers les pages
# commerciales (une ancre par cible) et le parcours de lecture. Un seul lien par ancre et par cible.
INDEX_BODY_MD = """Le Clos des Cyprès, à Biver (Gardanne), réunit huit [terrains libres de constructeur](/lots) proposés par l'aménageur PONTHIEU DH. Une question, un projet ? [Appelez-nous au 06 09 20 45 90](tel:+33609204590) ou [envoyez-nous un message](/contact) : nous vous répondons simplement, sans pression.

Pour voir les terrains : le [terrain à bâtir à Gardanne](/terrain-a-batir-gardanne), le [terrain à bâtir près d'Aix-en-Provence](/terrain-a-batir-aix-en-provence), le [terrain à bâtir près de Marseille](/terrain-a-batir-marseille) et le [terrain à bâtir en Provence](/terrain-a-batir-provence).

:::callout Par où commencer ?
1. [Terrain à bâtir, constructible, viabilisé : les différences](/blog/terrain-a-batir-constructible-viabilise-differences/)
2. [Terrain libre de constructeur : sens, avantages et limites](/blog/terrain-libre-de-constructeur-definition/)
3. [Terrain constructible à Gardanne : ce qu'il faut vérifier](/blog/verifier-avant-dacheter-terrain-biver-gardanne/)
4. [Acheter un terrain en lotissement à Gardanne : les étapes](/blog/guide-acheter-terrain-lotissement-gardanne-biver/)
5. [Budget pour construire une maison près d'Aix-en-Provence](/blog/budget-terrain-maison-pres-aix-gardanne/)
6. [Construire sa maison : les étapes, du terrain aux clés](/blog/construire-sa-maison-etapes-du-terrain-aux-cles/)
7. [Quelle surface de terrain pour une maison avec piscine ?](/blog/surface-terrain-maison-piscine/)
8. [Construire sur un terrain en pente en Provence : sol, budget](/blog/construire-sur-terrain-en-pente-restanques-provence/)
:::
"""
INDEX_GUIDES_TITLE = "Tous les guides"
# Bloc d'appel en bas de l'index (page 1)
INDEX_CTA_MD = """:::cta Un projet de terrain à Biver ?
Le Clos des Cyprès réunit huit terrains à bâtir à Biver (Gardanne), libres de constructeur et proposés par l'aménageur PONTHIEU DH. Le prix et les informations de chaque lot vous sont présentés lors de notre échange.

- [Appelez-nous au 06 09 20 45 90](tel:+33609204590)
- [Envoyez-nous un message](/contact)
- [Voir les huit lots](/lots)
:::
"""

# Bloc d'appel à l'action final (ajouté automatiquement sous chaque article)
CTA_FINAL_TITLE = "Un projet de terrain à Biver, pour construire votre maison ?"
CTA_FINAL_TEXT = ("Le Clos des Cyprès réunit huit terrains à bâtir à Biver (Gardanne), libres de constructeur "
                  "et proposés par l'aménageur PONTHIEU DH. Appelez-nous au 06 09 20 45 90 ou envoyez-nous "
                  "un message : le prix et les informations de chaque lot vous sont présentés lors de notre échange.")
# Libellé du bouton vers la page « /terrain-a-batir-gardanne » : varié d'un article à l'autre (pas cinq liens
# identiques vers la même page). Clé = slug ; un nouvel article reçoit le libellé par défaut.
CTA_PILLAR_DEFAULT = "Présentation du programme"
CTA_PILLAR_LABELS = {
    "budget-terrain-maison-pres-aix-gardanne": "Découvrir le programme",
    "construire-sur-terrain-en-pente-restanques-provence": "Les terrains du lotissement",
    "guide-acheter-terrain-lotissement-gardanne-biver": "Le Clos des Cyprès en détail",
    "terrain-libre-de-constructeur-definition": "Présentation des terrains",
    "verifier-avant-dacheter-terrain-biver-gardanne": "La page du terrain à Biver",
    "terrain-a-batir-constructible-viabilise-differences": "Le terrain à bâtir à Gardanne",
    "construire-sa-maison-etapes-du-terrain-aux-cles": "Découvrir le terrain à bâtir",
    "surface-terrain-maison-piscine": "Le terrain à Gardanne en détail",
}
CTA_FINAL_BUTTONS = (("Appelez-nous au " + PHONE_DISPLAY.replace(" ", "\u00a0"), "tel:" + PHONE_TEL),
                     ("Voir les huit lots", "/lots"),
                     (CTA_PILLAR_DEFAULT, "/terrain-a-batir-gardanne"),
                     ("Envoyez-nous un message", "/contact"))
CTA_DEFAULT_BUTTONS = (("Voir les huit lots", "/lots"), ("Envoyez-nous un message", "/contact"))
# Couvertures : variantes allégées « <nom>-<largeur>.<ext> » placées à côté de l'image (ex. couverture-640.avif,
# couverture-1024.avif). Si elles existent, la page déclare un srcset (la largeur d'origine reste le dernier choix) ;
# sinon l'image est servie seule, comme avant. « sizes » = largeur d'affichage réelle (voir blog.css).
COVER_VARIANT_WIDTHS = (640, 1024)
COVER_SIZES = "(min-width: 62rem) 864px, calc(100vw - 2.5rem)"          # couverture de l'article
CARD_SIZES = "(min-width: 40rem) 300px, calc(100vw - 2.5rem)"           # vignettes (index, « À lire aussi »)
NOTE_INFO = ("Information générale, non contractuelle. Elle ne remplace pas l'avis d'un notaire, "
             "d'un géomètre ou de la mairie.")

# Polices préchargées par les pages du blog (texte courant et titres). Liste PROPRE au blog : les pages du site
# n'en préchargent que celles de leur premier écran, ce ne sont donc plus elles qui dictent celles du blog.
BLOG_FONT_PRELOADS = ("cormorant-garamond-400-normal-20", "dm-sans-400-normal-4")

# Extraction du gabarit depuis index.html : règles du CSS critique qui ne servent pas au blog (retirées)
HOME_ONLY_CSS_PREFIXES = (".hero", ".scroll-hint", ".reveal", ".fullimg__cap", ".lots-sr-only",
                          ".section-head", ".kicker", ".chapter-title")
HOME_ONLY_KEYFRAMES = ("heroRise", "heroFade", "scrollPulse")

PLACEHOLDER_MARKERS = ("À RÉDIGER", "À COMPLÉTER", "TODO")
GENERATOR = "build_blog.py"

MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
             "septembre", "octobre", "novembre", "décembre"]

FM_FIELDS = ("title", "description", "slug", "date", "updated", "category", "tags", "keyword",
             "image", "image_alt", "image_width", "image_height", "og_image", "related", "draft")
FM_REQUIRED = ("title", "description", "date", "category", "keyword")
DIRECTIVES = ("callout", "faq", "cta", "source")
NBSP = " "


# =====================================================================================
# 2. OUTILS GÉNÉRAUX
# =====================================================================================

def esc(text, quote=True):
    """Échappe un texte pour le HTML. quote=True : pour un attribut entre guillemets doubles
    (seul le guillemet double est alors échappé : l'apostrophe reste lisible)."""
    out = html.escape(text, quote=False)
    return out.replace('"', "&quot;") if quote else out


def slugify(text):
    """« Où construire à l'ombre ? » -> « ou-construire-a-l-ombre » (sans accent, minuscules)."""
    t = text.replace("œ", "oe").replace("Œ", "oe").replace("æ", "ae").replace("’", "'")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def strip_tags(fragment):
    """Texte brut d'un fragment HTML (balises retirées, entités décodées, espaces normalisés)."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace(NBSP, " ")
    return re.sub(r"\s+", " ", t).strip()


def fr_date(d):
    """datetime.date -> « 1er octobre 2026 » (espaces insécables)."""
    day = "1er" if d.day == 1 else str(d.day)
    return "%s%s%s%s%d" % (day, NBSP, MONTHS_FR[d.month - 1], NBSP, d.year)


def typo(text):
    """Typographie française minimale sur du texte brut : espaces insécables avant : ; ! ? % et
    dans les guillemets « », séparateur des milliers, espace avant les unités et le signe €,
    après « n° », et dans le numéro du permis d'aménager (PA 013 041 22 K0001)."""
    t = re.sub(r"PA 013 041 22 K0001", NBSP.join(["PA", "013", "041", "22", "K0001"]), text)
    t = t.replace("n° ", "n°" + NBSP)
    t = re.sub(r" ([:;!?%»])", NBSP + r"\1", t)
    t = t.replace("« ", "«" + NBSP)
    t = re.sub(r"(?<=\d) (?=\d{3}\b)", NBSP, t)
    t = re.sub(r"(?<=\d) (?=(?:m²|m2|km|min|ha|h|cm|mm|m)\b)", NBSP, t)
    t = re.sub(r"(?<=\d) (?=€)", NBSP, t)
    return t


def nbsp_entities(escaped):
    """Écrit les espaces insécables en &nbsp; (plus lisible dans le source, comme le reste du site)."""
    return escaped.replace(NBSP, "&nbsp;")


def reading_minutes(words):
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def parse_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def rel_posix(path, root):
    return Path(path).relative_to(root).as_posix()


def truncate(text, limit):
    """Coupe à la limite sans couper un mot, avec « … »."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip(" ,;:") + "…"


class Report:
    """Collecte les erreurs (bloquantes) et avertissements, avec « fichier:ligne »."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, msg):
        self.errors.append((str(where), msg))

    def warn(self, where, msg):
        self.warnings.append((str(where), msg))

    def show(self, strict=False):
        for where, msg in sorted(self.warnings):
            print("  %s %s : %s" % ("ERREUR (--strict)" if strict else "avertissement", where, msg))
        for where, msg in sorted(self.errors):
            print("  ERREUR %s : %s" % (where, msg))

    def failed(self, strict=False):
        return bool(self.errors) or (strict and bool(self.warnings))


# =====================================================================================
# 3. IMAGES : dimensions lues dans l'en-tête du fichier (PNG, JPEG, WebP, GIF, AVIF)
# =====================================================================================

def image_size(path):
    """Retourne (largeur, hauteur) ou None si le format n'est pas reconnu."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")
    if data[:2] == b"\xff\xd8":
        return _jpeg_size(data)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return _webp_size(data)
    if data[4:8] == b"ftyp" and b"avif" in data[8:32]:
        return _avif_size(data)
    return None


def _jpeg_size(data):
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg = int.from_bytes(data[i + 2:i + 4], "big")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + seg
    return None


def _webp_size(data):
    kind = data[12:16]
    if kind == b"VP8 " and len(data) >= 30:
        return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    if kind == b"VP8L" and len(data) >= 25:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if kind == b"VP8X" and len(data) >= 30:
        return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
    return None


def _avif_size(data):
    idx = data.find(b"ispe")
    if idx < 0 or idx + 16 > len(data):
        return None
    return int.from_bytes(data[idx + 8:idx + 12], "big"), int.from_bytes(data[idx + 12:idx + 16], "big")


# =====================================================================================
# 4. MODÈLE D'ARTICLE ET FRONT MATTER
# =====================================================================================

@dataclass
class Article:
    path: Path
    rel: str                      # content/blog/xxx.md (pour les messages)
    meta: dict = field(default_factory=dict)
    body: str = ""
    body_line: int = 1            # numéro de la 1re ligne du corps dans le fichier
    slug: str = ""
    title: str = ""
    description: str = ""
    date: object = None
    updated: object = None
    category: str = ""
    tags: list = field(default_factory=list)
    keyword: str = ""
    image: str = ""
    image_alt: str = ""
    image_w: int = 0
    image_h: int = 0
    og_image: str = ""
    related: list = field(default_factory=list)
    draft: bool = False
    lines: dict = field(default_factory=dict)    # clé du front matter -> numéro de ligne
    # rempli au rendu
    html: str = ""
    toc: list = field(default_factory=list)       # [(id, texte)]
    faq: list = field(default_factory=list)       # [(question, html réponse, texte réponse)]
    links: list = field(default_factory=list)     # [(href, ligne)]
    words: int = 0
    minutes: int = 1

    def at(self, key):
        """« fichier:ligne » de la clé du front matter (ou le fichier seul si la clé est absente)."""
        return "%s:%d" % (self.rel, self.lines[key]) if key in self.lines else self.rel

    def line(self, key):
        return self.lines.get(key, 1)

    @property
    def path_url(self):
        return "/blog/%s/" % self.slug

    @property
    def url(self):
        return SITE_URL + self.path_url

    @property
    def lastmod(self):
        return self.updated or self.date

    @property
    def category_label(self):
        return CATEGORIES.get(self.category, self.category)


def parse_value_list(value):
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [x.strip().strip("\"'") for x in v.split(",") if x.strip()]


def unquote(value):
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_front_matter(text, rel, report):
    """Sépare le front matter (clé: valeur entre deux lignes ---) du corps.
    Retourne (meta, corps, numéro de la 1re ligne du corps) ou None si illisible."""
    lines = text.lstrip("﻿").split("\n")
    if not lines or lines[0].strip() != "---":
        report.error("%s:1" % rel, "le fichier doit commencer par une ligne « --- » (début du front matter)")
        return None
    meta = {}
    for i in range(1, len(lines)):
        line = lines[i].rstrip("\r")
        if line.strip() == "---":
            return meta, "\n".join(lines[i + 1:]), i + 2
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([a-z_]+)\s*:\s*(.*)$", line)
        if not m:
            report.error("%s:%d" % (rel, i + 1), "ligne de front matter illisible (attendu « clé: valeur ») : %r" % line[:60])
            continue
        key, value = m.group(1), unquote(m.group(2))
        if key not in FM_FIELDS:
            report.error("%s:%d" % (rel, i + 1), "clé inconnue « %s » (clés admises : %s)" % (key, ", ".join(FM_FIELDS)))
        elif key in meta:
            report.error("%s:%d" % (rel, i + 1), "clé « %s » répétée" % key)
        else:
            meta[key] = (value, i + 1)
    report.error("%s:1" % rel, "front matter non fermé : il manque la ligne « --- » de fin")
    return None


def load_article(path, root, report):
    rel = rel_posix(path, root)
    parsed = parse_front_matter(path.read_text(encoding="utf-8"), rel, report)
    if parsed is None:
        return None
    meta, body, body_line = parsed
    a = Article(path=path, rel=rel, meta={k: v[0] for k, v in meta.items()}, body=body, body_line=body_line,
                lines={k: v[1] for k, v in meta.items()})
    at = a.at

    for key in FM_REQUIRED:
        if not a.meta.get(key, "").strip():
            report.error(at(key), "champ obligatoire « %s » absent ou vide" % key)
    a.title = a.meta.get("title", "").strip()
    a.description = a.meta.get("description", "").strip()
    a.keyword = a.meta.get("keyword", "").strip()
    a.slug = a.meta.get("slug", path.stem).strip()
    a.category = a.meta.get("category", "").strip()
    a.tags = parse_value_list(a.meta.get("tags", ""))
    a.related = parse_value_list(a.meta.get("related", ""))
    draft = a.meta.get("draft", "false").strip().lower()
    if draft not in ("true", "false", "oui", "non", "yes", "no"):
        report.error(at("draft"), "draft doit valoir true ou false (reçu « %s »)" % draft)
    a.draft = draft in ("true", "oui", "yes")
    a.image, a.og_image = a.meta.get("image", "").strip(), a.meta.get("og_image", "").strip()
    a.image_alt = a.meta.get("image_alt", "").strip()
    for key, attr in (("image_width", "image_w"), ("image_height", "image_h")):
        raw = a.meta.get(key, "").strip()
        if raw:
            if raw.isdigit() and int(raw) > 0:
                setattr(a, attr, int(raw))
            else:
                report.error(at(key), "« %s » doit être un nombre entier de pixels" % key)
    a.date = parse_date(a.meta.get("date", ""))
    if "date" in meta and a.date is None:
        report.error(at("date"), "date invalide « %s » (format AAAA-MM-JJ, par exemple 2026-10-12)" % a.meta["date"])
    a.updated = parse_date(a.meta["updated"]) if a.meta.get("updated") else a.date
    if a.meta.get("updated") and a.updated is None:
        report.error(at("updated"), "date de mise à jour invalide « %s » (format AAAA-MM-JJ)" % a.meta["updated"])
    return a


# =====================================================================================
# 5. CONVERTISSEUR MARKDOWN (maison, sûr : tout le texte est échappé, aucun HTML brut accepté)
# =====================================================================================

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,2}[.)])\s+(.*)$")
DIRECTIVE_RE = re.compile(r"^:::\s*([A-Za-z]+)\s*(.*?)\s*$")
IMAGE_RE = re.compile(r'^!\[([^\]]*)\]\(\s*(\S+?)(?:\s+"([^"]*)")?\s*\)(?:\{(\d+)x(\d+)\})?\s*$')
HR_RE = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
TABLE_SEP_CELL = re.compile(r"^:?-+:?$")
ESCAPABLE = set("\\`*_{}[]()#+-.!|>~<:")


def split_row(line):
    """Découpe une ligne de tableau « | a | b | » en cellules (le \\| est un | littéral)."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def is_table_start(lines, i):
    if i + 1 >= len(lines) or "|" not in lines[i]:
        return False
    cells = split_row(lines[i + 1])
    return len(cells) >= 1 and "-" in lines[i + 1] and all(TABLE_SEP_CELL.match(c) for c in cells)


class MarkdownRenderer:
    """Convertit le corps d'un article en HTML et collecte ce dont le reste du script a besoin
    (intertitres, liens, images, FAQ). Les erreurs sont signalées avec « fichier:ligne »."""

    def __init__(self, builder, article):
        self.b = builder
        self.a = article
        self.rel = article.rel
        self.toc = []
        self.links = []          # (href, ligne)
        self.faq = []
        self.used_ids = set(RESERVED_IDS)
        self.h2_seen = False
        self.has_cta = False
        self.has_sources = False

    # ---- erreurs --------------------------------------------------------------------
    def err(self, ln, msg):
        self.b.report.error("%s:%d" % (self.rel, ln), msg)

    def warn(self, ln, msg):
        self.b.report.warn("%s:%d" % (self.rel, ln), msg)

    # ---- API ------------------------------------------------------------------------
    def render(self):
        lines = [l.rstrip("\r") for l in self.a.body.split("\n")]
        out = self.blocks(lines, self.a.body_line, nested=False)
        return out

    # ---- blocs ----------------------------------------------------------------------
    def starts_block(self, lines, i):
        line = lines[i]
        return bool(DIRECTIVE_RE.match(line) or line.strip() == ":::" or HEADING_RE.match(line)
                    or line.lstrip().startswith("```") or line.startswith(">") or HR_RE.match(line)
                    or LIST_RE.match(line) or IMAGE_RE.match(line.strip()) or is_table_start(lines, i))

    def blocks(self, lines, start_line, nested):
        out, i, n, caption = [], 0, len(lines), None
        while i < n:
            line, ln = lines[i], start_line + i
            if not line.strip():
                i += 1
                continue
            if line.strip() == ":::":
                self.err(ln, "« ::: » de fermeture sans bloc ouvert")
                i += 1
                continue
            m = DIRECTIVE_RE.match(line)
            if m:
                i = self.directive(m, lines, i, start_line, nested, out)
                continue
            if line.lstrip().startswith("```"):
                i = self.fence(lines, i, start_line, out)
                continue
            m = HEADING_RE.match(line)
            if m:
                self.heading(m, ln, nested, out)
                i += 1
                continue
            if HR_RE.match(line):
                out.append("<hr>")
                i += 1
                continue
            if line.startswith(">"):
                i = self.quote(lines, i, start_line, nested, out)
                continue
            if is_table_start(lines, i):
                i = self.table(lines, i, ln, caption, out)
                caption = None
                continue
            if LIST_RE.match(line):
                i = self.list(lines, i, start_line, out)
                continue
            m = IMAGE_RE.match(line.strip())
            if m:
                out.append(self.figure(m, ln))
                i += 1
                continue
            # paragraphe : lignes jusqu'à une ligne vide ou le début d'un autre bloc
            j = i + 1
            while j < n and lines[j].strip() and not self.starts_block(lines, j):
                j += 1
            para = lines[i:j]
            cm = re.match(r"^Tableau\s*:\s*(.+)$", para[0].strip()) if len(para) == 1 else None
            if cm and self.next_is_table(lines, j):
                caption = cm.group(1)
            else:
                out.append("<p>%s</p>" % self.inline(self.join_lines(para), ln))
            i = j
        return "\n".join(out)

    def next_is_table(self, lines, j):
        while j < len(lines) and not lines[j].strip():
            j += 1
        return j < len(lines) and is_table_start(lines, j)

    @staticmethod
    def join_lines(para):
        """Joint les lignes d'un paragraphe ; deux espaces ou « \\ » en fin de ligne = saut de ligne."""
        parts = []
        for k, l in enumerate(para):
            hard = k < len(para) - 1 and (l.endswith("  ") or l.endswith("\\"))
            parts.append(l.strip().rstrip("\\").rstrip() + ("\u0001" if hard else ""))
        return " ".join(p for p in parts).replace("\u0001 ", "\u0001")

    def heading(self, m, ln, nested, out):
        level, raw = len(m.group(1)), m.group(2)
        if nested:
            self.err(ln, "titre interdit à l'intérieur d'un bloc ::: : placez-le avant ou après le bloc")
            return
        if level == 1:
            self.err(ln, "titre « # » interdit : le H1 est le champ title du front matter (utilisez « ## »)")
            return
        if level > 3:
            self.err(ln, "niveau de titre trop profond : n'utilisez que « ## » et « ### »")
            return
        inner = self.inline(raw, ln)
        text = strip_tags(inner)
        if level == 3 and not self.h2_seen:
            self.err(ln, "un « ### » doit suivre un « ## » (ordre des titres)")
        if level == 2:
            self.h2_seen = True
        hid = self.unique_id(slugify(text) or "section")
        if level == 2:
            self.toc.append((hid, text))
        out.append('<h%d id="%s">%s</h%d>' % (level, hid, inner, level))

    def unique_id(self, base):
        cand, k = base, 2
        while cand in self.used_ids:
            cand = "%s-%d" % (base, k)
            k += 1
        self.used_ids.add(cand)
        return cand

    def fence(self, lines, i, start_line, out):
        j = i + 1
        while j < len(lines) and not lines[j].lstrip().startswith("```"):
            j += 1
        if j >= len(lines):
            self.err(start_line + i, "bloc de code « ``` » jamais fermé")
            return len(lines)
        out.append("<pre><code>%s</code></pre>" % esc("\n".join(lines[i + 1:j]), quote=False))
        return j + 1

    def quote(self, lines, i, start_line, nested, out):
        j = i
        while j < len(lines) and lines[j].startswith(">"):
            j += 1
        inner = [re.sub(r"^> ?", "", l) for l in lines[i:j]]
        out.append("<blockquote>\n%s\n</blockquote>" % self.blocks(inner, start_line + i, nested=True))
        return j

    def figure(self, m, ln):
        alt, src, caption, w, h = m.group(1).strip(), m.group(2), m.group(3), m.group(4), m.group(5)
        if not alt:
            self.err(ln, "image sans texte alternatif : ![description](%s)" % src)
        if not src.startswith("/") or src.startswith("//"):
            self.err(ln, "chemin d'image « %s » : il doit commencer par « / » (ex. /images-optimized/...)" % src)
            return ""
        size = self.b.image_dims(src, int(w) if w else 0, int(h) if h else 0, self.rel, ln)
        attrs = ' width="%d" height="%d"' % size if size else ""
        cap = "<figcaption>%s</figcaption>" % self.inline(caption, ln) if caption else ""
        return ('<figure class="post-figure"><img src="%s" alt="%s"%s loading="lazy" decoding="async">%s</figure>'
                % (esc(src), esc(alt), attrs, cap))

    # ---- tableaux -------------------------------------------------------------------
    def table(self, lines, i, ln0, caption, out):
        head = split_row(lines[i])
        aligns = []
        for c in split_row(lines[i + 1]):
            aligns.append("c" if c.startswith(":") and c.endswith(":") else "r" if c.endswith(":") else "")
        j, rows = i + 2, []
        while j < len(lines) and lines[j].strip() and "|" in lines[j]:
            rows.append((split_row(lines[j]), ln0 + (j - i)))
            j += 1

        def cell(tag, text, k, ln, scope=""):
            cls = ' class="al-%s"' % aligns[k] if k < len(aligns) and aligns[k] else ""
            return "<%s%s%s>%s</%s>" % (tag, scope, cls, self.inline(text, ln), tag)

        if len(set(len(r) for r, _ in rows) | {len(head)}) > 1:
            self.err(ln0, "tableau irrégulier : toutes les lignes doivent avoir %d colonne(s)" % len(head))
        thead = "<thead><tr>%s</tr></thead>" % "".join(cell("th", c, k, ln0, ' scope="col"') for k, c in enumerate(head))
        tbody = "<tbody>\n%s\n</tbody>" % "\n".join(
            "<tr>%s</tr>" % "".join(cell("td", c, k, ln) for k, c in enumerate(r)) for r, ln in rows)
        cap = "<caption>%s</caption>" % self.inline(caption, ln0) if caption else ""
        label = esc(strip_tags(self.inline(caption, ln0))) if caption else "Tableau"
        out.append('<div class="table-scroll" role="region" aria-label="%s" tabindex="0"><table>%s%s%s</table></div>'
                   % (label, cap, thead, tbody))
        return j

    # ---- listes ---------------------------------------------------------------------
    def list(self, lines, i, start_line, out):
        first = LIST_RE.match(lines[i])
        base = len(first.group(1).expandtabs(4))
        ordered = first.group(2)[0].isdigit()
        items, n = [], len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                nxt = LIST_RE.match(lines[j]) if j < n else None
                if nxt and len(nxt.group(1).expandtabs(4)) >= base and (
                        len(nxt.group(1).expandtabs(4)) > base or nxt.group(2)[0].isdigit() == ordered):
                    i = j
                    continue
                break
            mm = LIST_RE.match(line)
            indent = len(line) - len(line.lstrip())
            if mm:
                ind = len(mm.group(1).expandtabs(4))
                if ind < base:
                    break
                if ind > base and items:
                    items[-1][1].append(line)
                elif mm.group(2)[0].isdigit() != ordered:
                    break
                else:
                    items.append([[mm.group(3)], [], start_line + i])
                i += 1
                continue
            if items and indent > base:
                (items[-1][1] if items[-1][1] else items[-1][0]).append(line if items[-1][1] else line.strip())
                i += 1
                continue
            if items and not self.starts_block(lines, i) and lines[i - 1].strip():
                items[-1][0].append(line.strip())      # continuation « paresseuse »
                i += 1
                continue
            break
        tag = "ol" if ordered else "ul"
        start = int(first.group(2)[:-1]) if ordered and int(first.group(2)[:-1]) != 1 else None
        lis = []
        for text_lines, sub, ln in items:
            body = self.inline(" ".join(text_lines), ln)
            if sub:
                body += "\n" + self.blocks(sub, ln + 1, nested=True) + "\n"
            lis.append("<li>%s</li>" % body)
        attr = ' start="%d"' % start if start else ""
        out.append("<%s%s>\n%s\n</%s>" % (tag, attr, "\n".join(lis), tag))
        return i

    # ---- blocs ::: ------------------------------------------------------------------
    def directive(self, m, lines, i, start_line, nested, out):
        name, arg, ln = m.group(1).lower(), m.group(2), start_line + i
        j = i + 1
        while j < len(lines) and lines[j].strip() != ":::":
            if DIRECTIVE_RE.match(lines[j]):
                self.err(start_line + j, "bloc « :::%s » imbriqué dans « :::%s » (ouvert ligne %d) : "
                         "fermez d'abord le bloc par « ::: »" % (DIRECTIVE_RE.match(lines[j]).group(1), name, ln))
                return j
            j += 1
        if j >= len(lines):
            self.err(ln, "bloc « :::%s » ouvert ici mais jamais fermé (il manque une ligne « ::: »)" % name)
            return len(lines)
        if nested:
            self.err(ln, "bloc « :::%s » interdit à l'intérieur d'un autre bloc" % name)
        elif name not in DIRECTIVES:
            self.err(ln, "bloc inconnu « :::%s » (blocs admis : %s)" % (name, ", ".join(DIRECTIVES)))
        else:
            inner = lines[i + 1:j]
            out.append(getattr(self, "d_" + name)(arg, inner, ln + 1, ln))
        return j + 1

    def d_callout(self, arg, inner, first, ln):
        body = self.blocks(inner, first, nested=True)
        title = '<p class="callout__title">%s</p>\n' % self.inline(arg, ln) if arg else ""
        return '<div class="callout" role="note">\n%s%s\n</div>' % (title, body)

    def d_source(self, arg, inner, first, ln):
        self.has_sources = True
        body = self.blocks(inner, first, nested=True)
        if "<li>" not in body:
            self.warn(ln, "le bloc :::source devrait contenir une liste de sources (« - [Titre](https://...) »)")
        return '<div class="sources">\n<p class="sources__title">%s</p>\n%s\n</div>' % (
            self.inline(arg or "Sources", ln), body)

    def d_cta(self, arg, inner, first, ln):
        self.has_cta = True
        text_lines, buttons = [], []
        for k, l in enumerate(inner):
            lm = re.match(r"^\s*[-*+]\s+\[([^\]]+)\]\(([^)\s]+)\)\s*$", l)
            if lm:
                buttons.append((lm.group(1), lm.group(2), first + k))
            else:
                text_lines.append(l)
        body = self.blocks(text_lines, first, nested=True)
        if not buttons:
            buttons = [(label, href, ln) for label, href in CTA_DEFAULT_BUTTONS]
        btns = []
        for k, (label, href, bln) in enumerate(buttons):
            self.links.append((href, bln))
            btns.append('<a class="btn %s" href="%s">%s</a>' % (
                "btn-gold" if k == 0 else "btn-outline", esc(href), nbsp_entities(esc(typo(label), False))))
        title = '<p class="cta-block__title">%s</p>\n' % self.inline(arg, ln) if arg else ""
        return '<div class="cta-block">\n%s%s\n<p class="cta-block__btns">%s</p>\n</div>' % (title, body, " ".join(btns))

    def d_faq(self, arg, inner, first, ln):
        pairs, cur = [], None
        for k, l in enumerate(inner):
            hm = re.match(r"^###\s+(.*\S)\s*$", l)
            if hm:
                cur = [hm.group(1), [], first + k]
                pairs.append(cur)
            elif cur is not None:
                cur[1].append(l)
            elif l.strip():
                self.err(first + k, "dans un bloc :::faq, chaque question commence par « ### Question ? »")
        if not pairs:
            self.err(ln, "le bloc :::faq ne contient aucune question (« ### Question ? » puis la réponse)")
        items = []
        for q, ans, qln in pairs:
            ans_html = self.blocks(ans, qln + 1, nested=True)
            if not strip_tags(ans_html):
                self.err(qln, "question « %s » sans réponse" % q)
            q_html = self.inline(q, qln)
            self.faq.append((strip_tags(q_html), ans_html, strip_tags(ans_html)))
            items.append('<details class="faq__item">\n<summary>%s</summary>\n<div class="faq__answer">\n%s\n</div>\n</details>'
                         % (q_html, ans_html))
        return '<div class="faq">\n%s\n</div>' % "\n".join(items)

    # ---- inline ---------------------------------------------------------------------
    def text(self, raw):
        return nbsp_entities(esc(typo(raw), quote=False))

    def inline(self, s, ln):
        out, buf, i, n = [], [], 0, len(s)

        def flush():
            if buf:
                out.append(self.text("".join(buf)))
                buf.clear()

        while i < n:
            c = s[i]
            if c == "\\" and i + 1 < n and s[i + 1] in ESCAPABLE:
                buf.append(s[i + 1])
                i += 2
            elif c == "\u0001":
                flush()
                out.append("<br>")
                i += 1
            elif c == "`" and s.find("`", i + 1) > i + 1:
                j = s.find("`", i + 1)
                flush()
                out.append("<code>%s</code>" % esc(s[i + 1:j], quote=False))
                i = j + 1
            elif c == "[" and self.link(s, i, ln, out, flush):
                i = self._link_end
            elif s.startswith("![", i):
                self.err(ln, "une image doit être seule sur sa ligne : ![description](/chemin.webp \"légende\")")
                buf.append(c)
                i += 1
            elif s.startswith(("**", "__"), i) and self.span(s, i, s[i:i + 2], "strong", ln, out, flush):
                i = self._span_end
            elif c in "*_" and not s.startswith(c * 2, i) and self.span(s, i, c, "em", ln, out, flush):
                i = self._span_end
            else:
                buf.append(c)
                i += 1
        flush()
        return "".join(out)

    def span(self, s, i, marker, tag, ln, out, flush):
        """Gras / italique : cherche le marqueur fermant ; « _ » exige une frontière de mot."""
        start = i + len(marker)
        if marker in ("_", "__") and i > 0 and s[i - 1].isalnum():
            return False
        j = start
        while True:
            j = s.find(marker, j)
            if j < 0:
                return False
            if marker == "*" and (s.startswith("**", j) or s[j - 1] == "*"):
                j += 1
                continue
            if marker in ("_", "__") and j + len(marker) < len(s) and s[j + len(marker)].isalnum():
                j += 1
                continue
            break
        inner = s[start:j]
        if not inner.strip() or inner[0].isspace() or inner[-1].isspace():
            return False
        flush()
        out.append("<%s>%s</%s>" % (tag, self.inline(inner, ln), tag))
        self._span_end = j + len(marker)
        return True

    def link(self, s, i, ln, out, flush):
        """[texte](adresse "titre") -> <a>. Retourne False si ce n'est pas un lien."""
        n, depth, j = len(s), 0, i
        while j < n:
            ch = s[j]
            if ch == "\\":
                j += 2
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n or j + 1 >= n or s[j + 1] != "(":
            return False
        k, pd = j + 2, 1
        while k < n:
            if s[k] == "(":
                pd += 1
            elif s[k] == ")":
                pd -= 1
                if pd == 0:
                    break
            k += 1
        if k >= n:
            return False
        dm = re.match(r'^(\S+)(?:\s+"([^"]*)")?$', s[j + 2:k].strip())
        if not dm:
            self.err(ln, "lien mal formé : %r" % s[i:k + 1][:70])
            return False
        href, title = dm.group(1), dm.group(2)
        label = s[i + 1:j]
        if not label.strip():
            self.err(ln, "lien sans texte : %r" % s[i:k + 1][:70])
        flush()
        self.links.append((href, ln))
        attrs = ' href="%s"' % esc(href)
        if title:
            attrs += ' title="%s"' % esc(title)
        if re.match(r"^https?://", href):
            attrs += ' rel="noopener"'
        out.append("<a%s>%s</a>" % (attrs, self.inline(label, ln)))
        self._link_end = k + 1
        return True


# =====================================================================================
# 6. CSS CRITIQUE : retrait des règles propres à l'accueil
# =====================================================================================

def split_css_rules(css):
    """Découpe une feuille en règles de premier niveau (accolades équilibrées, chaînes respectées)."""
    rules, start, depth, quote, i = [], 0, 0, None, 0
    while i < len(css):
        c = css[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                rules.append(css[start:i + 1])
                start = i + 1
        elif c == ";" and depth == 0:
            rules.append(css[start:i + 1])
            start = i + 1
        i += 1
    if css[start:].strip():
        rules.append(css[start:])
    return rules


def split_top_level(text, sep=","):
    """Découpe selon sep hors parenthèses : « :is(a,b),.c » -> [« :is(a,b) », « .c »]."""
    parts, depth, cur = [], 0, []
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def filter_home_css(css):
    """Retire du CSS critique les règles qui ne servent qu'à l'accueil (.hero, .scroll-hint, .reveal)."""
    kept = []
    for rule in split_css_rules(css):
        if "{" not in rule:
            kept.append(rule)
            continue
        prelude, _, rest = rule.partition("{")
        body = rest[:rest.rfind("}")]
        p = prelude.strip()
        if p.startswith("@keyframes"):
            if any(p.endswith(" " + k) for k in HOME_ONLY_KEYFRAMES):
                continue
        elif p.startswith(("@media", "@supports")):
            inner = filter_home_css(body)
            if not inner.strip():
                continue
            rule = "%s{%s}" % (prelude, inner)
        elif not p.startswith("@"):
            sels = [s.strip() for s in split_top_level(p)]
            if all(s.startswith(HOME_ONLY_CSS_PREFIXES) for s in sels):
                continue
        kept.append(rule)
    return "".join(kept)


# =====================================================================================
# 7. GABARIT : extrait de index.html à chaque exécution
# =====================================================================================

HEAD_ITEM_RE = re.compile(
    r"<!--.*?-->"
    r"|<title>.*?</title>"
    r"|<script\b[^>]*>.*?</script>"
    r"|<style\b[^>]*>.*?</style>"
    r"|<noscript>.*?</noscript>"
    r"|<(?:meta|link|base)\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>", re.S | re.I)


def attr(tag, name):
    m = re.search(r'\b%s\s*=\s*"([^"]*)"' % re.escape(name), tag)
    return m.group(1) if m else None


def extract_element(text, open_re, tag):
    """Retourne l'élément (balises comprises) qui commence par open_re, en équilibrant les balises."""
    m = re.search(open_re, text)
    if not m:
        return None
    depth = 0
    for t in re.finditer(r"<(/?)%s\b[^>]*>" % tag, text[m.start():]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return text[m.start():m.start() + t.end()]
    return None


def strip_comments(fragment):
    return re.sub(r"[ \t]*<!--.*?-->[ \t]*\n?", "", fragment, flags=re.S)


class Template:
    """Morceaux de index.html réutilisés par toutes les pages du blog."""

    def __init__(self, root, report):
        self.ok = False
        path = Path(root) / "index.html"
        if not path.exists():
            report.error("index.html", "introuvable : impossible d'extraire le gabarit (en-tête, menu, pied de page)")
            return
        text = path.read_text(encoding="utf-8")
        head_m = re.search(r"<head>(.*?)</head>", text, re.S)
        if not head_m:
            report.error("index.html", "balise <head> introuvable")
            return
        self.head_items, self.ld_nodes, self.og = self.parse_head(head_m.group(1))
        self.header = extract_element(text, r'<header class="nav"', "header")
        self.mobile = extract_element(text, r'<nav id="mobile-menu"', "nav")
        self.footer = extract_element(text, r"<footer\b", "footer")
        self.fab = extract_element(text, r'<div class="fab-contact"', "div")
        skip = re.search(r'<a class="skip-link"[^>]*>.*?</a>', text, re.S)
        self.skip = skip.group(0) if skip else '<a class="skip-link" href="#contenu">Aller au contenu principal</a>'
        missing = [n for n, v in (("en-tête <header class=\"nav\">", self.header), ("menu mobile #mobile-menu", self.mobile),
                                  ("pied de page <footer>", self.footer), ("bulles .fab-contact", self.fab)) if not v]
        joined = "\n".join(self.head_items)
        for needle, label in (("data-critical", "CSS critique <style data-critical>"),
                              ("style.min.css", "feuille /style.min.css"), ("main.min.js", "script /main.min.js")):
            if needle not in joined:
                missing.append(label)
        for m in missing:
            report.error("index.html", "gabarit : %s introuvable (le blog ne peut pas être construit)" % m)
        self.ok = not missing
        if self.ok and 'href="/blog/"' not in self.header:
            report.warn("index.html", "le menu ne contient pas de lien href=\"/blog/\" : à ajouter par le coordinateur")
        for part in ("header", "mobile", "footer", "fab"):
            setattr(self, part, strip_comments(getattr(self, part) or ""))

    def parse_head(self, head):
        items, nodes, og = [], [], {}
        for m in HEAD_ITEM_RE.finditer(head):
            it = m.group(0)
            low = it.lower()
            if low.startswith(("<!--", "<title")):
                continue
            if low.startswith("<meta"):
                name, prop = attr(it, "name") or "", attr(it, "property") or ""
                if prop.startswith("og:image"):
                    og[prop] = attr(it, "content") or ""
                if prop.startswith(("og:", "article:")) or name in ("description", "robots", "author", "ICBM") \
                        or name.startswith(("twitter:", "geo.")) or "charset" in low or name == "viewport":
                    continue
            elif low.startswith("<link"):
                rel, as_ = attr(it, "rel") or "", attr(it, "as") or ""
                if rel in ("canonical", "alternate") or (rel == "preload" and as_ == "image"):
                    continue
                if rel == "preload" and as_ == "font":
                    if not any(kind == "FONTS" for kind, _ in items):
                        items.append(("FONTS", None))   # emplacement des préchargements du blog
                    continue
            elif low.startswith("<script"):
                if "application/ld+json" in low:
                    try:
                        data = json.loads(re.search(r">(.*)</script>", it, re.S).group(1))
                        nodes = [n for n in data.get("@graph", []) if n.get("@type") in ("Organization", "Place", "WebSite")]
                    except (ValueError, AttributeError):
                        pass
                    continue
            elif low.startswith("<style") and "data-critical" in low:
                body = re.search(r"<style[^>]*>(.*)</style>", it, re.S).group(1)
                it = re.sub(r"(<style[^>]*>).*(</style>)", lambda mm: mm.group(1) + filter_home_css(body) + mm.group(2), it, flags=re.S)
            items.append(("ITEM", it))
        font_tags = ['<link rel="preload" as="font" type="font/woff2" href="/fonts/%s.woff2" crossorigin>' % n
                     for n in BLOG_FONT_PRELOADS]
        ordered = []
        for kind, it in items:
            if kind == "ITEM":
                ordered.append(it)
            else:
                ordered.extend(font_tags)
        return ordered, nodes, og


def set_active(fragment, href, aria):
    """Retire l'état « actif » des liens du fragment, puis le pose sur le lien `href`
    (classe `active` + aria-current). Les autres liens ne sont pas touchés."""
    def fix(m):
        tag = m.group(0)
        h = attr(tag, "href")
        classes = (attr(tag, "class") or "").split()
        if h is None or not ("active" in classes or "aria-current=" in tag or h == href):
            return tag
        new = re.sub(r'\s+aria-current="[^"]*"', "", tag)
        new = re.sub(r'\s+class="[^"]*"', "", new)
        classes = [c for c in classes if c != "active"] + (["active"] if h == href else [])
        extra = ' class="%s"' % " ".join(classes) if classes else ""
        if h == href and aria:
            extra += ' aria-current="%s"' % aria
        return re.sub(r"^<a\b", "<a" + extra, new, count=1)

    return re.sub(r"<a\b[^>]*>", fix, fragment)


# =====================================================================================
# 8. CONSTRUCTEUR PRINCIPAL
# =====================================================================================

class Builder:
    def __init__(self, root, include_drafts=False):
        self.root = Path(root).resolve()
        self.include_drafts = include_drafts
        self.report = Report()
        self.articles = []            # articles listés (publiés + brouillons si demandé)
        self.ignored = []             # (fichier, raison)
        self.draft_slugs = set()      # slugs des brouillons ignorés (pour un message d'erreur précis)
        self.outputs = {}             # chemin relatif -> contenu
        self.template = None
        self.stale = []               # fichiers générés autrefois, devenus inutiles (supprimés à l'écriture)
        self._dirs = {}
        self._size_cache = {}

    # ---------------------------------------------------------------- fichiers du site
    def listing(self, directory):
        if directory not in self._dirs:
            try:
                self._dirs[directory] = set(os.listdir(directory))
            except OSError:
                self._dirs[directory] = set()
        return self._dirs[directory]

    def file_exists(self, rel):
        """Existence EXACTE (casse comprise : le serveur de production est sensible à la casse)."""
        cur = self.root
        for part in rel.strip("/").split("/"):
            if part not in self.listing(cur):
                return False
            cur = cur / part
        return cur.exists()

    def image_dims(self, src, w, h, rel, ln):
        """Dimensions d'une image du site (src commençant par /). Signale fichier absent ou incohérent."""
        where = "%s:%d" % (rel, ln)
        if not self.file_exists(src):
            self.report.error(where, "image introuvable : %s" % src)
            return None
        key = src
        if key not in self._size_cache:
            self._size_cache[key] = image_size(self.root / src.lstrip("/"))
        real = self._size_cache[key]
        if real is None:
            if not (w and h):
                self.report.error(where, "dimensions de %s illisibles (format non reconnu ou AVIF atypique) : "
                                         "ajoutez {LARGEURxHAUTEUR} après l'image, ou image_width/image_height" % src)
                return None
            return w, h
        if (w and h) and (w, h) != real:
            self.report.error(where, "dimensions déclarées %dx%d différentes du fichier %s (%dx%d réels)" % (w, h, src, real[0], real[1]))
        return real

    # ---------------------------------------------------------------- chargement des articles
    def load(self):
        folder = self.root / "content" / "blog"
        files = sorted(folder.glob("*.md")) if folder.is_dir() else []
        for path in files:
            rel = rel_posix(path, self.root)
            if path.name.startswith("_") and not self.include_drafts:
                self.ignored.append((rel, "fichier commençant par « _ »"))
                continue
            a = load_article(path, self.root, self.report)
            if a is None:
                continue
            if a.draft and not self.include_drafts:
                self.ignored.append((rel, "brouillon (draft: true)"))
                self.draft_slugs.add(a.slug)
                continue
            self.articles.append(a)
        # plus récent d'abord ; à égalité : mise à jour la plus récente, puis ordre alphabétique du slug
        mini = datetime.date.min
        self.articles.sort(key=lambda a: (-(a.date or mini).toordinal(), -(a.lastmod or mini).toordinal(), a.slug))

    @property
    def published(self):
        return [a for a in self.articles if not a.draft]

    def by_slug(self):
        return {a.slug: a for a in self.articles}

    # ---------------------------------------------------------------- validations d'en-tête
    def validate_meta(self):
        seen, titles = {}, {}
        for a in self.articles:
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", a.slug) or len(a.slug) > 90:
                self.report.error(a.at("slug") if "slug" in a.meta else a.rel,
                                  "slug invalide « %s » (minuscules, chiffres et tirets, sans accent ni espace, 90 caractères max.)" % a.slug)
            elif a.slug in RESERVED_SLUGS:
                self.report.error(a.rel, "slug « %s » réservé par le site" % a.slug)
            if a.slug in seen:
                self.report.error(a.rel, "slug « %s » déjà utilisé par %s" % (a.slug, seen[a.slug]))
            seen[a.slug] = a.rel
            key = " ".join(a.title.lower().split())
            if key and key in titles:
                self.report.error(a.at("title"), "titre identique à celui de %s : chaque article a son propre titre" % titles[key])
            titles[key] = a.rel
            if "slug" in a.meta and a.slug != a.path.stem and not a.path.name.startswith("_"):
                self.report.warn(a.rel, "le nom du fichier (%s) diffère du slug (%s)" % (a.path.stem, a.slug))
            if a.title and len(a.title) > 65:
                self.report.error(a.at("title"), "titre trop long (%d caractères, 65 maximum, 60 visés)" % len(a.title))
            elif a.title and len(a.title) > 60:
                self.report.warn(a.at("title"), "titre de %d caractères : visez 60 ou moins" % len(a.title))
            if a.description and len(a.description) > 160:
                self.report.error(a.at("description"), "description trop longue (%d caractères, 160 maximum, 155 visés)" % len(a.description))
            elif a.description and len(a.description) > 155:
                self.report.warn(a.at("description"), "description de %d caractères : visez 155 ou moins" % len(a.description))
            elif a.description and len(a.description) < 70:
                self.report.warn(a.at("description"), "description courte (%d caractères) : 120 à 155 est idéal" % len(a.description))
            if a.category and a.category not in CATEGORIES:
                self.report.error(a.at("category"), "catégorie « %s » inconnue (admises : %s)" % (a.category, ", ".join(CATEGORIES)))
            if a.date and a.updated and a.updated < a.date:
                self.report.error(a.at("updated"), "updated (%s) antérieur à date (%s)" % (a.updated, a.date))
            if a.date and a.date > datetime.date.today():
                self.report.warn(a.at("date"), "date dans le futur (%s) : l'article serait publié dès le prochain déploiement" % a.date)
            self.validate_image(a)
            if a.keyword and a.title and slugify(a.keyword) not in slugify(a.title):
                self.report.warn(a.rel, "le mot-clé « %s » n'apparaît pas dans le titre" % a.keyword)
            if a.keyword and a.description and a.keyword.lower() not in a.description.lower():
                self.report.warn(a.rel, "le mot-clé « %s » n'apparaît pas dans la description" % a.keyword)
        slugs = set(seen)
        for a in self.articles:
            for r in a.related:
                if r not in slugs:
                    self.report.error(a.at("related"), "article lié « %s » introuvable (ou brouillon)" % r)
                elif r == a.slug:
                    self.report.error(a.at("related"), "un article ne peut pas se lier à lui-même")

    def validate_image(self, a):
        if not a.image:
            if a.image_alt:
                self.report.error(a.at("image_alt"), "image_alt renseigné sans champ image")
            self.report.warn(a.rel, "pas d'image de couverture : l'image de l'accueil servira au partage (champ image)")
            return
        where = a.at("image")
        if not a.image.startswith("/"):
            self.report.error(where, "image « %s » : le chemin doit commencer par « / »" % a.image)
            return
        if not a.image_alt:
            self.report.error(where, "image sans texte alternatif : renseignez image_alt (obligatoire)")
        size = self.image_dims(a.image, a.image_w, a.image_h, a.rel, a.line("image"))
        if size:
            a.image_w, a.image_h = size
        if a.og_image:
            if not a.og_image.startswith("/") or not self.file_exists(a.og_image):
                self.report.error(a.at("og_image"), "og_image introuvable : %s" % a.og_image)
        weight = (self.root / a.image.lstrip("/")).stat().st_size if self.file_exists(a.image) else 0
        if weight > 150_000:
            self.report.warn(where, "image de couverture lourde (%d Ko) : visez 120 Ko au plus (WebP 1600 x 900)" % (weight // 1000))
        shared = a.og_image or a.image
        s2 = image_size(self.root / shared.lstrip("/")) if self.file_exists(shared) else None
        if s2 and s2[0] < 1200:
            self.report.warn(where, "image de partage large de %d px (1200 px conseillés pour Facebook/LinkedIn)" % s2[0])

    # ---------------------------------------------------------------- rendu des corps
    def render_bodies(self):
        for a in self.articles:
            md = MarkdownRenderer(self, a)
            a.html = md.render()
            a.toc, a.faq, a.links = md.toc, md.faq, md.links
            text = strip_tags(a.html)
            a.words = len(re.findall(r"[\w'’-]+", text))
            a.minutes = reading_minutes(a.words)
            self.validate_body(a, md)

    def validate_body(self, a, md):
        by = self.by_slug()
        commercial = []
        anchors = {i for i, _ in a.toc} | set(re.findall(r'id="([^"]+)"', a.html))
        for href, ln in a.links:
            where = "%s:%d" % (a.rel, ln)
            problem = self.check_link(href, by, a, own_anchors=anchors)
            if problem:
                self.report.error(where, "lien « %s » : %s" % (href, problem))
            path = re.split(r"[#?]", href)[0]
            if path in COMMERCIAL_PATHS:
                commercial.append(ln)
        if not commercial:
            self.report.error(a.rel, "aucun lien vers une page commerciale dans le texte (%s) : "
                                     "ajoutez-en un, avec une ancre descriptive" % ", ".join(COMMERCIAL_PATHS))
        else:
            total = a.body_line + a.body.count("\n") + 1
            if (min(commercial) - a.body_line) > 0.5 * (total - a.body_line):
                self.report.warn(a.rel, "le premier lien vers une page commerciale arrive dans la seconde moitié du texte")
        for marker in PLACEHOLDER_MARKERS:
            if marker in a.body:
                (self.report.warn if a.draft else self.report.error)(
                    a.rel, "texte provisoire « %s » encore présent : à rédiger avant publication" % marker)
        if not a.draft:
            if "EXEMPLE" in a.title.upper():
                self.report.error(a.rel, "le titre contient « EXEMPLE » : article d'exemple, non publiable")
        if a.words < MIN_WORDS_WARN:
            self.report.warn(a.rel, "article court (%d mots) : moins de %d mots risque d'être jugé « mince »" % (a.words, MIN_WORDS_WARN))
        if not md.toc:
            self.report.warn(a.rel, "aucun intertitre « ## » : structurez l'article")
        if not md.has_sources and not any(re.match(r"^https?://", h) for h, _ in a.links):
            self.report.warn(a.rel, "aucune source citée (bloc :::source ou lien externe) : les faits doivent être sourcés")
        first_p = re.search(r"<p>(.*?)</p>", a.html, re.S)
        if a.keyword and first_p and a.keyword.lower() not in strip_tags(first_p.group(1)).lower():
            self.report.warn(a.rel, "le mot-clé « %s » n'apparaît pas dans le premier paragraphe" % a.keyword)
        if a.keyword and not any(a.keyword.lower() in t.lower() for _, t in md.toc):
            self.report.warn(a.rel, "le mot-clé « %s » n'apparaît dans aucun intertitre H2" % a.keyword)
        dup = [t for t in [x[1] for x in md.toc] if [x[1] for x in md.toc].count(t) > 1]
        if dup:
            self.report.warn(a.rel, "intertitres H2 en double : %s" % ", ".join(sorted(set(dup))))

    # ---------------------------------------------------------------- liens internes
    def generated_paths(self):
        return set(self.outputs)

    def check_link(self, href, by_slug, article=None, own_anchors=None):
        """Retourne None si le lien est bon, sinon la raison de l'erreur."""
        if href.startswith(("mailto:", "tel:")):
            return None
        if href.startswith("#"):
            if len(href) > 1 and own_anchors is not None and href[1:] not in own_anchors:
                return "l'ancre n'existe pas dans cet article"
            return None
        if re.match(r"^https?://", href):
            if href.startswith(SITE_URL):
                return "adresse complète du site : écrivez un lien interne (%s)" % (href[len(SITE_URL):] or "/")
            if href.startswith("http://"):
                self.report.warn(article.rel if article else "liens", "lien non sécurisé (http://) : %s" % href)
            return None
        if not href.startswith("/") or href.startswith("//"):
            return "lien relatif ou inconnu : un lien interne commence par « / » (ex. /lots)"
        path, _, frag = re.split(r"\?", href)[0].partition("#")
        problem = self.resolve_path(path, by_slug)
        if problem:
            return problem
        if frag:
            page = self.page_source(path)
            if page and frag not in set(re.findall(r'\bid="([^"]+)"', page)):
                return "l'ancre #%s n'existe pas dans %s" % (frag, path)
        return None

    def page_source(self, path):
        """Source d'une page de la racine (pour vérifier ses ancres) ; None pour les pages générées."""
        if path.endswith("/") and path != "/":
            return None
        rel = "index.html" if path == "/" else path.lstrip("/") + ".html"
        return (self.root / rel).read_text(encoding="utf-8") if self.file_exists(rel) else None

    def resolve_path(self, path, by_slug):
        if path == "/":
            return None if self.file_exists("index.html") else "index.html introuvable"
        gen = self.generated_paths()
        if path.endswith("/"):
            rel = path.lstrip("/") + "index.html"
            if rel in gen or self.file_exists(rel):
                return None
            m = re.match(r"^/blog/([^/]+)/$", path)
            if m and m.group(1) in self.draft_slugs:
                return "cet article est un brouillon, non publié"
            if self.file_exists(path.strip("/") + ".html"):
                return "page sans barre finale : écrivez %s" % path.rstrip("/")
            return "page introuvable"
        if path.endswith(".html"):
            return "ne mettez pas « .html » : écrivez %s" % (path[:-5] or "/")
        if re.search(r"\.[A-Za-z0-9]+$", path):
            return None if path.lstrip("/") in gen or self.file_exists(path) else "fichier introuvable"
        if self.file_exists(path.lstrip("/") + ".html"):
            return None
        if path.lstrip("/") + "/index.html" in gen or self.file_exists(path.lstrip("/") + "/index.html"):
            return "ajoutez la barre finale : %s/" % path
        return "page introuvable (pas de fichier %s.html)" % path.lstrip("/")

    # ---------------------------------------------------------------- JSON-LD
    def org_nodes(self):
        nodes = list(self.template.ld_nodes)
        if not any(n.get("@type") == "Organization" for n in nodes):
            nodes.insert(0, {"@type": "Organization", "@id": SITE_URL + "/#organization", "name": SITE_NAME, "url": SITE_URL + "/"})
        return nodes

    def breadcrumb(self, url, trail):
        items = [{"@type": "ListItem", "position": k + 1, "name": name, "item": href} for k, (name, href) in enumerate(trail)]
        return {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": items}

    def og_image_for(self, a):
        """(url, largeur, hauteur, alt) de l'image de partage ; repli sur l'image de l'accueil."""
        if a is not None and a.image:
            src = a.og_image or a.image
            size = image_size(self.root / src.lstrip("/")) or (a.image_w, a.image_h)
            return SITE_URL + src, size[0], size[1], a.image_alt
        og = self.template.og
        return (og.get("og:image", ""), og.get("og:image:width", ""), og.get("og:image:height", ""), og.get("og:image:alt", ""))

    def article_ld(self, a):
        img, _, _, _ = self.og_image_for(a)
        org_id = SITE_URL + "/#organization"
        post = {
            "@type": "BlogPosting", "@id": a.url + "#article",
            "mainEntityOfPage": {"@type": "WebPage", "@id": a.url},
            "headline": a.title, "description": a.description, "image": [img],
            "datePublished": a.date.isoformat(), "dateModified": a.lastmod.isoformat(),
            "inLanguage": "fr-FR", "articleSection": a.category_label, "wordCount": a.words,
            "author": {"@type": "Organization", "name": AUTHOR_LD_NAME, "url": SITE_URL + "/"},
            "publisher": {"@id": org_id},
            "isPartOf": {"@id": SITE_URL + "/#website"},
        }
        if a.tags:
            post["keywords"] = ", ".join(a.tags)
        graph = self.org_nodes() + [post, self.breadcrumb(a.url, [("Accueil", SITE_URL + "/"), ("Blog", SITE_URL + "/blog/"), (a.title, a.url)])]
        if a.faq:
            graph.append({"@type": "FAQPage", "@id": a.url + "#faq", "inLanguage": "fr-FR", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": t}} for q, _, t in a.faq]})
        return {"@context": "https://schema.org", "@graph": graph}

    def index_ld(self, page, page_articles, url):
        listing = {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": k + 1, "url": a.url, "name": a.title} for k, a in enumerate(page_articles)]}
        trail = [("Accueil", SITE_URL + "/"), ("Blog", SITE_URL + "/blog/")]
        coll = {"@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": INDEX_H1,
                "description": INDEX_DESCRIPTION, "inLanguage": "fr-FR",
                "isPartOf": {"@id": SITE_URL + "/#website"}, "mainEntity": listing}
        return {"@context": "https://schema.org", "@graph": self.org_nodes() + [coll, self.breadcrumb(url, trail)]}

    # ---------------------------------------------------------------- gabarit de page
    def head(self, *, title, og_title, description, url, robots, og_type, ld, a=None, extra=""):
        t = self.template
        img, iw, ih, ialt = self.og_image_for(a)
        lines = ['<meta charset="UTF-8">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
                 "<title>%s</title>" % esc(title, quote=False),
                 '<meta name="description" content="%s">' % esc(description),
                 '<meta name="robots" content="%s">' % robots,
                 '<meta name="author" content="%s">' % esc(AUTHOR_DISPLAY),
                 '<meta name="generator" content="%s">' % GENERATOR,
                 '<link rel="canonical" href="%s">' % esc(url)]
        if self.published:
            lines.append('<link rel="alternate" type="application/rss+xml" title="%s" href="%s/feed.xml">' % (FEED_TITLE, SITE_URL))
        lines += ['<meta property="og:type" content="%s">' % og_type,
                  '<meta property="og:site_name" content="%s">' % SITE_NAME,
                  '<meta property="og:locale" content="fr_FR">',
                  '<meta property="og:title" content="%s">' % esc(og_title),
                  '<meta property="og:description" content="%s">' % esc(description),
                  '<meta property="og:url" content="%s">' % esc(url),
                  '<meta property="og:image" content="%s">' % esc(img)]
        if iw and ih:
            lines += ['<meta property="og:image:width" content="%s">' % iw, '<meta property="og:image:height" content="%s">' % ih]
        lines.append('<meta property="og:image:alt" content="%s">' % esc(ialt))
        lines += extra.splitlines() if extra else []
        lines += ['<meta name="twitter:card" content="summary_large_image">',
                  '<meta name="twitter:title" content="%s">' % esc(og_title),
                  '<meta name="twitter:description" content="%s">' % esc(description),
                  '<meta name="twitter:image" content="%s">' % esc(img),
                  '<meta name="twitter:image:alt" content="%s">' % esc(ialt)]
        items = list(t.head_items)
        k = next((n for n, it in enumerate(items) if it.lower().startswith("<script")), len(items))
        items.insert(k, '<link rel="stylesheet" href="/blog.css">')
        lines += items
        ld_text = json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        lines.append('<script type="application/ld+json">\n%s\n</script>' % ld_text)
        return "\n".join("  " + l for l in lines)

    def shell(self, head, main, aria):
        t = self.template
        return "\n".join([
            "<!DOCTYPE html>", '<html lang="fr">', "<head>", head, "</head>", '<body class="blog">',
            "  " + t.skip, "",
            "  " + set_active(t.header, "/blog/", aria).strip(), "",
            "  " + set_active(t.mobile, "/blog/", aria).strip(), "",
            main, "",
            "  " + t.footer.strip(), "",
            "  " + t.fab.strip(), "", "</body>", "</html>", ""])

    # ---------------------------------------------------------------- pages
    def meta_line(self, a):
        return ('<p class="post-meta">Par %s · Publié le <time datetime="%s">%s</time> · Mis à jour le '
                '<time datetime="%s">%s</time> · %d&nbsp;min de lecture</p>') % (
            nbsp_entities(esc(AUTHOR_DISPLAY, False)), a.date.isoformat(), nbsp_entities(fr_date(a.date)),
            a.lastmod.isoformat(), nbsp_entities(fr_date(a.lastmod)), a.minutes)

    def crumbs(self, trail):
        lis = []
        for k, (name, href) in enumerate(trail):
            last = k == len(trail) - 1
            lis.append('<li><span aria-current="page">%s</span></li>' % nbsp_entities(esc(typo(name), False)) if last
                       else '<li><a href="%s">%s</a></li>' % (href, esc(name, False)))
        return '<nav class="crumbs" aria-label="Fil d\'Ariane"><ol>%s</ol></nav>' % "".join(lis)

    def srcset_attrs(self, a, sizes):
        """' srcset="..." sizes="..."' pour une image de l'article, ou '' si aucune variante n'existe sur le disque."""
        stem, dot, ext = a.image.rpartition(".")
        if not dot or not a.image_w:
            return ""
        parts = []
        for w in COVER_VARIANT_WIDTHS:
            variant = "%s-%d.%s" % (stem, w, ext)
            if w < a.image_w and self.file_exists(variant):
                parts.append("%s %dw" % (esc(variant), w))
        if not parts:
            return ""
        parts.append("%s %dw" % (esc(a.image), a.image_w))
        return ' srcset="%s" sizes="%s"' % (", ".join(parts), sizes)

    def card(self, a, level):
        media = ""
        if a.image and a.image_w:
            media = ('<div class="post-card__media"><img src="%s"%s alt="" width="%d" height="%d" loading="lazy" decoding="async"></div>\n'
                     % (esc(a.image), self.srcset_attrs(a, CARD_SIZES), a.image_w, a.image_h))
        draft = '<span class="post-card__draft">Brouillon</span> · ' if a.draft else ""
        return ('<li class="post-card">\n%s<div class="post-card__body">\n'
                '<p class="post-card__meta">%s<span>%s</span> · <time datetime="%s">%s</time> · %d&nbsp;min</p>\n'
                '<h%d class="post-card__title"><a href="%s">%s</a></h%d>\n'
                '<p class="post-card__excerpt">%s</p>\n</div>\n</li>') % (
            media, draft, esc(a.category_label, False), a.date.isoformat(), nbsp_entities(fr_date(a.date)), a.minutes,
            level, a.path_url, nbsp_entities(esc(typo(a.title), quote=False)), level,
            nbsp_entities(esc(typo(a.description), quote=False)))

    def related_for(self, a):
        pool = [x for x in self.articles if x.slug != a.slug and (a.draft or not x.draft)]
        chosen = [x for r in a.related for x in pool if x.slug == r]
        rest = [x for x in pool if x not in chosen]
        rest.sort(key=lambda x: (x.category == a.category, len(set(x.tags) & set(a.tags)), x.date), reverse=True)
        return (chosen + rest)[:RELATED_MAX]

    def cta_final(self, a):
        def label(l, h):
            return CTA_PILLAR_LABELS.get(a.slug, l) if h == "/terrain-a-batir-gardanne" else l
        btns = " ".join('<a class="btn %s" href="%s">%s</a>' % ("btn-gold" if k == 0 else "btn-outline", h, esc(typo(label(l, h)), False))
                        for k, (l, h) in enumerate(CTA_FINAL_BUTTONS))
        return ('<div class="cta-block cta-block--final">\n<p class="cta-block__title">%s</p>\n<p>%s</p>\n'
                '<p class="cta-block__btns">%s</p>\n</div>') % (
            nbsp_entities(esc(typo(CTA_FINAL_TITLE), False)), nbsp_entities(esc(typo(CTA_FINAL_TEXT), False)), nbsp_entities(btns))

    def toc_html(self, a):
        if len(a.toc) < TOC_MIN_H2:
            return ""
        lis = "\n".join('<li><a href="#%s">%s</a></li>' % (i, nbsp_entities(esc(typo(t), quote=False))) for i, t in a.toc)
        return ('<nav class="toc" aria-labelledby="toc-title"><p class="toc__title" id="toc-title">Sommaire</p>\n<ol>\n%s\n</ol></nav>' % lis)

    def render_article(self, a):
        title_tag = "%s | %s" % (a.title, SITE_NAME)
        if len(title_tag) > 65:
            title_tag = a.title
        robots = "noindex, nofollow" if a.draft else "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
        extra = "\n".join(['<meta property="article:published_time" content="%s">' % a.date.isoformat(),
                           '<meta property="article:modified_time" content="%s">' % a.lastmod.isoformat(),
                           '<meta property="article:section" content="%s">' % esc(a.category_label)]
                          + ['<meta property="article:tag" content="%s">' % esc(t) for t in a.tags])
        head = self.head(title=title_tag, og_title=a.title, description=a.description, url=a.url, robots=robots, og_type="article",
                         ld=self.article_ld(a), a=a, extra=extra)
        cover = ""
        if a.image:
            cover = ('\n<figure class="post-cover"><img src="%s"%s alt="%s" width="%d" height="%d" fetchpriority="high" decoding="async"></figure>'
                     % (esc(a.image), self.srcset_attrs(a, COVER_SIZES), esc(a.image_alt), a.image_w, a.image_h))
        draft = '\n<p class="draft-note">BROUILLON : cette page n\'est pas publiée (noindex).</p>' if a.draft else ""
        related = self.related_for(a)
        rel_html = ""
        if related:
            rel_html = ('<section class="post-related" aria-labelledby="related-title">\n<div class="wrap">\n'
                        '<h2 id="related-title">À lire aussi</h2>\n<ul class="post-grid">\n%s\n</ul>\n</div>\n</section>'
                        % "\n".join(self.card(x, 3) for x in related))
        toc = self.toc_html(a)
        main = "\n".join([
            '  <main id="contenu" tabindex="-1">', '    <article class="post">', '      <header class="post-head">',
            '        <div class="wrap post-head__inner">',
            "          " + self.crumbs([("Accueil", "/"), ("Blog", "/blog/"), (truncate(a.title, 48), a.path_url)]) + draft,
            '          <p class="label">%s</p>' % esc(a.category_label, False),
            "          <h1>%s</h1>" % nbsp_entities(esc(typo(a.title), quote=False)),
            "          " + self.meta_line(a) + cover, "        </div>", "      </header>",
            '      <div class="post-body">', '        <div class="wrap post-layout">',
            toc, '          <div class="post-main">', '<div class="prose">', a.html, "</div>",
            self.cta_final(a), '<p class="post-note">%s</p>' % esc(NOTE_INFO, False), "          </div>", "        </div>",
            rel_html, "      </div>", "    </article>", "  </main>"])
        return self.shell(head, main, "true")

    def render_md_block(self, md, where):
        """Rend un court texte Markdown écrit dans ce fichier (texte de l'index) avec le même moteur que les articles ;
        les liens sont contrôlés comme ceux d'un article (page existante, forme propre, barre finale)."""
        stub = Article(path=Path(__file__), rel=where, body=md, body_line=1)
        renderer = MarkdownRenderer(self, stub)
        out = renderer.render()
        by = self.by_slug()
        for href, ln in renderer.links:
            problem = self.check_link(href, by, stub)
            if problem:
                self.report.error("%s:%d" % (where, ln), "lien « %s » : %s" % (href, problem))
        return out

    def render_index_page(self, n, pages, chunk):
        url = SITE_URL + ("/blog/" if n == 1 else "/blog/page/%d/" % n)
        title = "%s%s | %s" % (INDEX_TITLE, "" if n == 1 else " (page %d)" % n, SITE_NAME)
        has_draft = any(a.draft for a in self.articles)
        robots = "noindex, nofollow" if has_draft else "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
        head = self.head(title=title, og_title=title, description=INDEX_DESCRIPTION, url=url, robots=robots, og_type="website",
                         ld=self.index_ld(n, chunk, url))
        draft = '\n<p class="draft-note">APERÇU : des brouillons sont inclus (noindex).</p>' if has_draft else ""
        intro = '\n          <p class="post-lead">%s</p>' % nbsp_entities(esc(typo(INDEX_INTRO), quote=False)) if n == 1 else \
            '\n          <p class="post-lead">Page %d sur %d</p>' % (n, pages)
        pagination = self.pagination(n, pages)
        body_top, body_bottom = [], []
        if n == 1:
            body_top = ['      <div class="wrap">', '        <div class="post-main"><div class="prose">',
                        self.render_md_block(INDEX_BODY_MD, "tools/build_blog.py (INDEX_BODY_MD)"), "        </div></div>", "      </div>"]
            body_bottom = ['      <div class="wrap">', '        <div class="post-main">',
                           self.render_md_block(INDEX_CTA_MD, "tools/build_blog.py (INDEX_CTA_MD)"), "        </div>", "      </div>"]
        main = "\n".join([
            '  <main id="contenu" tabindex="-1">', '    <header class="post-head">', '      <div class="wrap post-head__inner">',
            "        " + self.crumbs([("Accueil", "/"), ("Blog", "/blog/")]) + draft,
            '        <p class="label">Blog</p>', "        <h1>%s</h1>%s" % (nbsp_entities(esc(typo(INDEX_H1), quote=False)), intro),
            "      </div>", "    </header>", '    <div class="post-body">'] + body_top + [
            '      <section class="post-related" aria-labelledby="guides-title">', '        <div class="wrap">',
            '          <h2 id="guides-title">%s</h2>' % esc(INDEX_GUIDES_TITLE, False),
            '          <ul class="post-grid post-grid--index">', "\n".join(self.card(a, 3) for a in chunk), "          </ul>",
            pagination, "        </div>", "      </section>"] + body_bottom + ["    </div>", "  </main>"])
        return self.shell(head, main, "page")

    @staticmethod
    def pagination(n, pages):
        if pages <= 1:
            return ""
        def href(k):
            return "/blog/" if k == 1 else "/blog/page/%d/" % k
        lis = []
        if n > 1:
            lis.append('<li><a href="%s" rel="prev">Page précédente</a></li>' % href(n - 1))
        for k in range(1, pages + 1):
            if k == n:
                lis.append('<li><a href="%s" aria-current="page" aria-label="Page %d">%d</a></li>' % (href(k), k, k))
            else:
                lis.append('<li><a href="%s" aria-label="Page %d">%d</a></li>' % (href(k), k, k))
        if n < pages:
            lis.append('<li><a href="%s" rel="next">Page suivante</a></li>' % href(n + 1))
        return '<nav class="pagination" aria-label="Pagination"><ul>\n%s\n</ul></nav>' % "\n".join(lis)

    # ---------------------------------------------------------------- flux RSS
    def render_feed(self):
        pub = self.published[:FEED_SIZE]
        def rfc(d):
            return format_datetime(datetime.datetime(d.year, d.month, d.day, 8, 0, tzinfo=datetime.timezone.utc), usegmt=True)
        items = []
        for a in pub:
            items.append("    <item>\n      <title>%s</title>\n      <link>%s</link>\n      <guid isPermaLink=\"true\">%s</guid>\n"
                         "      <pubDate>%s</pubDate>\n      <category>%s</category>\n      <description>%s</description>\n    </item>"
                         % (esc(a.title, False), a.url, a.url, rfc(a.date), esc(a.category_label, False), esc(a.description, False)))
        last = max(a.lastmod for a in pub)
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n  <channel>\n'
                "    <title>%s</title>\n    <link>%s/blog/</link>\n    <description>%s</description>\n"
                "    <language>fr-FR</language>\n    <lastBuildDate>%s</lastBuildDate>\n    <generator>%s</generator>\n"
                '    <atom:link href="%s/feed.xml" rel="self" type="application/rss+xml"/>\n%s\n  </channel>\n</rss>\n') % (
            FEED_TITLE, SITE_URL, esc(INDEX_DESCRIPTION, False), rfc(last), GENERATOR, SITE_URL, "\n".join(items))

    # ---------------------------------------------------------------- sitemap
    def git(self, *args):
        try:
            return subprocess.run(["git", "-C", str(self.root)] + list(args), capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None

    def page_lastmod(self, rel):
        """Date du dernier commit qui a touché le fichier ; si le fichier est modifié mais pas
        commité (ou hors dépôt git), date de sa dernière modification sur disque."""
        full = self.root / rel
        mtime = datetime.date.fromtimestamp(full.stat().st_mtime).isoformat()
        top = self.git("rev-parse", "--show-toplevel")
        if not top or top.returncode != 0 or Path(top.stdout.strip()).resolve() != self.root:
            return mtime
        st = self.git("status", "--porcelain", "--", rel)
        if st is None or st.stdout.strip():
            return mtime
        log = self.git("log", "-1", "--format=%cs", "--", rel)
        return (log.stdout.strip() if log else "") or mtime

    def existing_sitemap(self):
        """Pages de la racine du sitemap actuel : [(loc, [(image_loc, image_title)])], dans l'ordre."""
        path = self.root / "sitemap.xml"
        if not path.exists():
            self.report.error("sitemap.xml", "introuvable : impossible de reprendre les pages de la racine")
            return []
        try:
            tree = ET.parse(path)
        except ET.ParseError as e:
            self.report.error("sitemap.xml", "XML illisible : %s" % e)
            return []
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "i": "http://www.google.com/schemas/sitemap-image/1.1"}
        entries = []
        for u in tree.getroot().findall("s:url", ns):
            loc = (u.findtext("s:loc", default="", namespaces=ns) or "").strip()
            if not loc.startswith(SITE_URL):
                self.report.error("sitemap.xml", "URL « %s » hors du domaine %s" % (loc, SITE_URL))
                continue
            route = loc[len(SITE_URL):]
            if route.startswith("/blog") or route in SITEMAP_EXCLUDED:
                continue
            imgs = [((im.findtext("i:loc", default="", namespaces=ns) or "").strip(),
                     (im.findtext("i:title", default="", namespaces=ns) or "").strip()) for im in u.findall("i:image", ns)]
            entries.append((loc, imgs))
        return entries

    def render_sitemap(self):
        blocks = []
        known = set()
        for loc, imgs in self.existing_sitemap():
            route = loc[len(SITE_URL):] if loc.startswith(SITE_URL) else loc
            rel = "index.html" if route in ("", "/") else route.strip("/") + ".html"
            known.add(rel)
            if not self.file_exists(rel):
                self.report.error("sitemap.xml", "%s est listée mais %s n'existe pas" % (loc, rel))
                continue
            blocks.append(self.url_block(loc, self.page_lastmod(rel), imgs))
        for f in sorted(self.root.glob("*.html")):
            if f.name not in known and "/" + f.stem not in SITEMAP_EXCLUDED and "noindex" not in f.read_text(encoding="utf-8"):
                self.report.warn("sitemap.xml", "%s est indexable mais absente du sitemap : à ajouter par le coordinateur" % f.name)
        pub = self.published
        if pub:
            blocks.append(self.url_block(SITE_URL + "/blog/", max(a.lastmod for a in pub).isoformat(), []))
        for a in pub:
            imgs = [(SITE_URL + a.image, a.image_alt)] if a.image else []
            blocks.append(self.url_block(a.url, a.lastmod.isoformat(), imgs))
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
                '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n%s\n</urlset>\n' % "\n".join(blocks))

    @staticmethod
    def url_block(loc, lastmod, imgs):
        lines = ["  <url>", "    <loc>%s</loc>" % esc(loc, False), "    <lastmod>%s</lastmod>" % lastmod]
        for iloc, ititle in imgs:
            lines += ["    <image:image>", "      <image:loc>%s</image:loc>" % esc(iloc, False)]
            if ititle:
                lines.append("      <image:title>%s</image:title>" % esc(ititle, False))
            lines.append("    </image:image>")
        lines.append("  </url>")
        return "\n".join(lines)

    # ---------------------------------------------------------------- assemblage
    def build_outputs(self):
        listed = self.articles
        if listed:
            self.template = Template(self.root, self.report)
            if not self.template.ok:
                return
            pages = max(1, math.ceil(len(listed) / PAGE_SIZE))
            # les chemins générés doivent être connus AVANT de vérifier les liens internes
            for a in listed:
                self.outputs["blog/%s/index.html" % a.slug] = ""
            for n in range(1, pages + 1):
                self.outputs["blog/index.html" if n == 1 else "blog/page/%d/index.html" % n] = ""
            if self.published:
                self.outputs["feed.xml"] = ""
        self.render_bodies()
        if self.report.errors:
            return          # on s'arrête là : toutes les erreurs de contenu sont déjà listées
        if listed:
            for a in listed:
                self.outputs["blog/%s/index.html" % a.slug] = self.render_article(a)
            for n in range(1, pages + 1):
                chunk = listed[(n - 1) * PAGE_SIZE:n * PAGE_SIZE]
                self.outputs["blog/index.html" if n == 1 else "blog/page/%d/index.html" % n] = self.render_index_page(n, pages, chunk)
            if self.published:
                self.outputs["feed.xml"] = self.render_feed()
        self.outputs["sitemap.xml"] = self.render_sitemap()

    # ---------------------------------------------------------------- validations des sorties
    def validate_outputs(self, with_tidy):
        pages = {p: c for p, c in self.outputs.items() if p.endswith(".html")}
        for p, c in sorted(pages.items()):
            for problem in html_problems(c):
                self.report.error(p, problem)
            self.check_ld(p, c)
        for p in ("sitemap.xml", "feed.xml"):
            if p in self.outputs:
                try:
                    ET.fromstring(self.outputs[p].encode("utf-8"))
                except ET.ParseError as e:
                    self.report.error(p, "XML mal formé : %s" % e)
        self.check_site_links(pages)
        self.check_orphans(pages)
        self.check_sitemap_urls()
        if with_tidy and pages:
            self.run_tidy(pages)

    def check_site_links(self, pages):
        by = self.by_slug()
        for p, c in sorted(pages.items()):
            for href in sorted(set(re.findall(r'(?:href|src)="(/[^"#?]*)', c))):
                if href.startswith("//"):
                    continue
                problem = self.resolve_path(href, by)
                if problem:
                    self.report.error(p, "lien ou ressource « %s » : %s" % (href, problem))

    def check_orphans(self, pages):
        inbound = {a.slug: set() for a in self.articles}
        for p, c in pages.items():
            for slug in re.findall(r'href="/blog/([a-z0-9-]+)/"', c):
                if slug in inbound and p != "blog/%s/index.html" % slug:
                    inbound[slug].add(p)
        for a in self.articles:
            if not inbound[a.slug]:
                self.report.error(a.rel, "article orphelin : aucune page du site ne pointe vers /blog/%s/" % a.slug)
        if len(self.articles) > 1:
            editorial = {a.slug: set() for a in self.articles}
            for a in self.articles:
                for href, _ in a.links:
                    m = re.match(r"^/blog/([a-z0-9-]+)/", href)
                    if m and m.group(1) in editorial and m.group(1) != a.slug:
                        editorial[m.group(1)].add(a.slug)
                for r in a.related:
                    if r in editorial:
                        editorial[r].add(a.slug)
            for a in self.articles:
                if not editorial[a.slug]:
                    self.report.warn(a.rel, "aucun autre article ne pointe vers celui-ci (lien dans le texte ou champ related d'un autre article)")

    def check_sitemap_urls(self):
        sm = self.outputs.get("sitemap.xml")
        if not sm:
            return
        locs = re.findall(r"<loc>([^<]+)</loc>", sm)
        if len(locs) != len(set(locs)):
            self.report.error("sitemap.xml", "URL en double")
        for a in self.published:
            if a.url not in locs:
                self.report.error("sitemap.xml", "article absent du sitemap : %s" % a.url)
        for loc in locs:
            if loc.endswith(".html") or "/index" in loc:
                self.report.error("sitemap.xml", "URL avec extension : %s" % loc)

    def check_ld(self, page, content):
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', content, re.S)
        if not blocks:
            self.report.error(page, "JSON-LD absent")
        for raw in blocks:
            try:
                data = json.loads(raw)
            except ValueError as e:
                self.report.error(page, "JSON-LD invalide : %s" % e)
                continue
            graph = data.get("@graph", [data])
            ids = {n.get("@id") for n in graph if isinstance(n, dict)}
            for ref in re.findall(r'\{"@id":\s*"([^"]+)"\}', json.dumps(data)):
                if ref not in ids:
                    self.report.error(page, "JSON-LD : référence @id « %s » non définie dans la page" % ref)
            for node in graph:
                for problem in ld_node_problems(node):
                    self.report.error(page, "JSON-LD %s : %s" % (node.get("@type"), problem))

    def run_tidy(self, pages):
        try:
            subprocess.run(["tidy", "-v"], capture_output=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            self.report.warn("tidy", "outil « tidy » introuvable : contrôle HTML par tidy ignoré (contrôle de structure interne effectué)")
            return
        for p, c in sorted(pages.items()):
            res = subprocess.run(["tidy", "-q", "-e", "-utf8"], input=c.encode("utf-8"), capture_output=True)
            for line in res.stderr.decode("utf-8", "replace").splitlines():
                if TIDY_FATAL.search(line):
                    self.report.error(p, "tidy : %s" % line.strip())

    # ---------------------------------------------------------------- écriture
    def write(self):
        """Écrit les sorties (seulement si le contenu change) et supprime les fichiers générés périmés."""
        written, unchanged, removed = [], [], []
        for rel, content in sorted(self.outputs.items()):
            target = self.root / rel
            data = content.encode("utf-8")
            if target.exists() and target.read_bytes() == data:
                unchanged.append(rel)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written.append(rel)
        for old in self.stale:
            (self.root / old).unlink()
            removed.append(old)
        self.prune_empty_dirs()
        return written, unchanged, removed

    def stale_files(self):
        """Fichiers déjà générés par ce script mais qui ne le sont plus (ex. article repassé en brouillon)."""
        stale = []
        blog = self.root / "blog"
        candidates = [p for p in blog.rglob("index.html")] if blog.is_dir() else []
        candidates.append(self.root / "feed.xml")
        for p in candidates:
            rel = rel_posix(p, self.root) if p.exists() else None
            if rel and rel not in self.outputs:
                text = p.read_text(encoding="utf-8", errors="replace")
                if ('content="%s"' % GENERATOR) in text or ("<generator>%s</generator>" % GENERATOR) in text:
                    stale.append(rel)
                else:
                    self.report.warn(rel, "fichier inconnu du générateur : laissé en place")
        return stale

    def prune_empty_dirs(self):
        blog = self.root / "blog"
        if not blog.is_dir():
            return
        for d in sorted((p for p in blog.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
        if not any(blog.iterdir()):
            blog.rmdir()


# =====================================================================================
# 9. CONTRÔLES DE SORTIE (HTML, JSON-LD)
# =====================================================================================

# Messages de tidy qui signalent un HTML réellement mal formé. Les autres avertissements (attributs
# HTML5 comme aria-current/fetchpriority, <span> vides du bouton burger, lien WhatsApp du gabarit...)
# sont du bruit connu de tidy 5.8 et ne bloquent pas.
TIDY_FATAL = re.compile(r"Error:|missing </|discarding unexpected|inserting implicit|unexpected </|isn't allowed in|"
                        r"missing <!DOCTYPE|duplicate attribute|end of file while parsing|missing '>'|lacks \"")

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class _Balance(HTMLParser):
    """Vérifie l'équilibre des balises, l'unicité des id, l'unique H1 et les attributs des images."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.problems, self.ids, self.h1 = [], [], set(), 0

    def where(self):
        return "ligne %d" % self.getpos()[0]

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if "id" in d:
            if d["id"] in self.ids:
                self.problems.append("id en double « %s » (%s)" % (d["id"], self.where()))
            self.ids.add(d["id"])
        if tag == "img":
            if "alt" not in d:
                self.problems.append("<img> sans attribut alt (%s)" % self.where())
            if not d.get("width") or not d.get("height"):
                self.problems.append("<img> sans width/height : %s (%s)" % (d.get("src"), self.where()))
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            self.problems.append("balise </%s> inattendue (%s)%s" % (
                tag, self.where(), ", attendue </%s>" % self.stack[-1][0] if self.stack else ""))


def html_problems(content):
    p = _Balance()
    p.feed(content)
    p.close()
    out = list(p.problems)
    out += ["balise <%s> ouverte ligne %d jamais fermée" % (t, ln) for t, ln in p.stack]
    if p.h1 != 1:
        out.append("%d balise(s) <h1> (il en faut exactement une)" % p.h1)
    return out[:12]


def ld_node_problems(node):
    t = node.get("@type")
    need = {"BlogPosting": ("headline", "description", "image", "datePublished", "dateModified", "author", "publisher", "mainEntityOfPage"),
            "BreadcrumbList": ("itemListElement",), "FAQPage": ("mainEntity",), "CollectionPage": ("name", "url"),
            "Organization": ("name",), "WebSite": ("url",)}.get(t, ())
    out = ["champ « %s » manquant" % k for k in need if not node.get(k)]
    if t == "BreadcrumbList":
        for k, item in enumerate(node.get("itemListElement", []), 1):
            if item.get("position") != k or not item.get("name"):
                out.append("élément %d mal formé" % k)
    if t == "FAQPage":
        for q in node.get("mainEntity", []):
            if not q.get("name") or not (q.get("acceptedAnswer") or {}).get("text"):
                out.append("question ou réponse vide")
    if t == "BlogPosting":
        for k in ("datePublished", "dateModified"):
            if node.get(k) and parse_date(node[k]) is None:
                out.append("%s invalide" % k)
    return out


# =====================================================================================
# 10. PROGRAMME PRINCIPAL
# =====================================================================================

def digest(root):
    """Empreinte globale des fichiers générés (pour vérifier l'idempotence : deux builds de suite = même valeur)."""
    files = ["sitemap.xml", "feed.xml"]
    if (root / "blog").is_dir():
        files += sorted(rel_posix(p, root) for p in (root / "blog").rglob("*") if p.is_file())
    h = hashlib.sha256()
    for rel in files:
        if (root / rel).exists():
            h.update(rel.encode() + b"\0" + (root / rel).read_bytes())
    return h.hexdigest()[:16]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Génère le blog statique (blog/, feed.xml, sitemap.xml).")
    ap.add_argument("--check", action="store_true", help="contrôle uniquement : n'écrit rien, code retour != 0 en cas d'erreur")
    ap.add_argument("--include-drafts", action="store_true", help="inclut brouillons et fichiers « _ » (aperçu, pages en noindex)")
    ap.add_argument("--strict", action="store_true", help="les avertissements font aussi échouer")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="racine du site (défaut : dossier parent de tools/)")
    ap.add_argument("-q", "--quiet", action="store_true", help="n'affiche que les erreurs et le résumé")
    args = ap.parse_args(argv)

    b = Builder(args.root, include_drafts=args.include_drafts)
    b.load()
    b.validate_meta()
    b.build_outputs()
    if not b.report.errors:
        b.validate_outputs(with_tidy=args.check)
        b.stale = b.stale_files()

    print("build_blog : %d article(s) publié(s)%s, %d ignoré(s)" % (
        len(b.published), ", %d brouillon(s) inclus" % (len(b.articles) - len(b.published)) if len(b.articles) > len(b.published) else "",
        len(b.ignored)))
    if not args.quiet:
        for rel, why in b.ignored:
            print("  ignoré : %s (%s)" % (rel, why))
    if args.include_drafts:
        print("  ATTENTION : --include-drafts actif ; pages de brouillon en noindex, absentes du sitemap et du flux. Ne pas publier ainsi.")
    b.report.show(args.strict)
    if b.report.failed(args.strict):
        print("ÉCHEC : %d erreur(s), %d avertissement(s)%s. Rien n'a été écrit." % (
            len(b.report.errors), len(b.report.warnings), " (--strict)" if args.strict and not b.report.errors else ""))
        return 1
    if not b.articles:
        print("  Aucun article publié : blog/ et feed.xml ne sont PAS générés (pas de page « blog » vide).")
        print("  Rappel : le lien « Blog » du menu pointe vers /blog/, qui répondra 404 tant qu'aucun article n'est publié.")
    if args.check:
        for rel in b.stale:
            print("  à supprimer au prochain build (périmé) : %s" % rel)
        print("OK (contrôle seul, rien écrit) : %d avertissement(s)." % len(b.report.warnings))
        return 0
    written, unchanged, removed = b.write()
    for rel in written:
        print("  écrit : %s" % rel)
    for rel in removed:
        print("  supprimé (périmé) : %s" % rel)
    print("OK : %d fichier(s) écrit(s), %d inchangé(s), %d supprimé(s). Empreinte : %s" % (
        len(written), len(unchanged), len(removed), digest(b.root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
