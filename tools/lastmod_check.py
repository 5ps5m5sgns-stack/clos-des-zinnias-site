#!/usr/bin/env python3
"""Contrôle (lecture seule) des <lastmod> de sitemap.xml.

N'ÉCRIT RIEN : ni sitemap.xml, ni aucun autre fichier. Le sitemap est tenu à la main
tant que le générateur du blog n'en a pas repris la main.

Règle appliquée : pour chaque page du sitemap, la date attendue est
  - la date du dernier commit qui a touché le fichier source (git log -1 --format=%cs) ;
  - ou, si le fichier est modifié mais pas encore commité, la date de sa dernière
    modification sur disque.
Les URLs propres (sans .html) correspondent aux fichiers x.html du dépôt ; "/" = index.html.

Usage (depuis la racine du dépôt) :
    python3 tools/lastmod_check.py          # affiche le tableau, code retour 1 si écart
"""
import datetime
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def source_file(loc):
    path = re.sub(r"^https?://[^/]+", "", loc).strip("/")
    return "index.html" if path == "" else path + ".html"


def expected_date(rel):
    full = os.path.join(ROOT, rel)
    if not os.path.exists(full):
        return None
    def git(*a):
        return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True).stdout.strip()
    if git("status", "--porcelain", "--", rel):
        return datetime.date.fromtimestamp(os.path.getmtime(full)).isoformat()
    return git("log", "-1", "--format=%cs", "--", rel) or None


def main():
    tree = ET.parse(os.path.join(ROOT, "sitemap.xml"))
    bad = 0
    for url in tree.getroot().findall("s:url", NS):
        loc = url.find("s:loc", NS).text
        lm = url.find("s:lastmod", NS)
        have = lm.text if lm is not None else None
        rel = source_file(loc)
        want = expected_date(rel)
        flag = "ok " if have == want else "ECART"
        bad += have != want
        print("%-5s %-58s sitemap=%s attendu=%s (%s)" % (flag, loc, have, want, rel))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
