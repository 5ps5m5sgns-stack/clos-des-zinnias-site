#!/usr/bin/env python3
"""Photos libres de droits pour le blog : recherche sur Wikimedia Commons, contrôle de licence, optimisation.

Pourquoi seulement Wikimedia Commons : chaque fichier y porte sa licence, lisible par machine. On n'accepte que
CC0, domaine public, CC BY et CC BY-SA (usage commercial permis, à condition de créditer l'auteur). Tout le reste
(NC, ND, « fair use », licence inconnue, restrictions signalées) est refusé par le script.

Commandes (à lancer depuis la racine du dépôt) :

  python3 tools/blog_photos.py search "requête" [--n 12] [--dir DOSSIER]
      Liste les fichiers candidats (titre, dimensions, licence) et enregistre leurs vignettes dans DOSSIER
      (un dossier NEUF) pour les regarder avec l'outil de lecture d'images.

  python3 tools/blog_photos.py get "File:Nom du fichier.jpg" --dir DOSSIER
      Contrôle la licence, télécharge l'image (2000 px de large au plus) dans DOSSIER (un dossier NEUF)
      et imprime le crédit prêt à coller (Markdown) + la fiche de provenance.

  python3 tools/blog_photos.py cover  FICHIER SLUG [--focus X,Y] [--name couverture] --from "File:..."
      Fabrique la couverture : <name>.avif (1600x900), <name>-1024.avif, <name>-640.avif et partage.jpg (1200x630)
      dans images-optimized/blog/SLUG/.

  python3 tools/blog_photos.py inline FICHIER SLUG NOM [--ratio 3:2] [--focus X,Y] [--width 1200] --from "File:..."
      Fabrique une image d'illustration NOM.avif (largeur 1200 px au plus, 150 Ko au plus).

--focus X,Y : point d'intérêt de la photo, en fractions de 0 à 1 (0.5,0.5 = centre) pour le recadrage.
Un fichier existant n'est jamais écrasé (le navigateur garde les images un an) : choisissez un autre nom.
Chaque image fabriquée est inscrite dans content/blog/credits/SLUG.json (fichier hors déploiement).
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
API = "https://commons.wikimedia.org/w/api.php"
UA = "ClosDesCypresSite/1.0 (https://clos-des-cypres.fr; recherche de photos libres) python-urllib"
ALLOWED = re.compile(r"^(CC0.*|Public domain.*|PD[- ].*|CC[- ]BY([- ]SA)?[- ]\d(\.\d)?.*|Attribution.*)$", re.I)
REFUSED = re.compile(r"\bNC\b|-NC|\bND\b|-ND|GFDL(?! *or)|fair use|non-free|copyrighted|all rights", re.I)
SITE_MAX_WIDTH = 2000


def http(url, binary=False, tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and k < tries - 1:
                time.sleep(4 * (k + 1))
                continue
            raise
        except urllib.error.URLError:
            if k < tries - 1:
                time.sleep(3)
                continue
            raise


def api(**params):
    params.update(format="json", formatversion="2")
    time.sleep(0.6)
    return json.loads(http(API + "?" + urllib.parse.urlencode(params)))


def plain(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def info_of(page):
    ii = (page.get("imageinfo") or [{}])[0]
    md = ii.get("extmetadata") or {}
    g = lambda k: (md.get(k) or {}).get("value", "")
    lic = plain(g("LicenseShortName"))
    artist_html = g("Artist")
    am = re.search(r'href="([^"]+)"', artist_html or "")
    artist_url = am.group(1) if am else ""
    artist_url = html.unescape(artist_url)
    if artist_url.startswith("//"):
        artist_url = "https:" + artist_url
    elif artist_url.startswith("/"):
        artist_url = "https://commons.wikimedia.org" + artist_url
    if "redlink=1" in artist_url or not artist_url.startswith("https://"):
        artist_url = ""          # page d'utilisateur inexistante : on crédite le nom seul
    return {
        "title": page.get("title", ""),
        "page_url": ii.get("descriptionurl", ""),
        "width": ii.get("width", 0), "height": ii.get("height", 0), "mime": ii.get("mime", ""),
        "thumb": ii.get("thumburl", ""), "url": ii.get("url", ""),
        "license": lic, "license_url": plain(g("LicenseUrl")),
        "artist": plain(artist_html) or "auteur non indiqué", "artist_url": artist_url,
        "credit": plain(g("Credit")), "description": plain(g("ImageDescription"))[:200],
        "restrictions": plain(g("Restrictions")), "nonfree": plain(g("NonFree")),
        "attribution_required": plain(g("AttributionRequired")),
    }


def license_problem(i):
    if not i["license"]:
        return "licence illisible"
    if REFUSED.search(i["license"]) or not ALLOWED.match(i["license"]):
        return "licence refusée : %s" % i["license"]
    if i["nonfree"].lower() in ("true", "1", "yes"):
        return "fichier marqué non libre"
    if i["restrictions"]:
        return "restrictions signalées : %s" % i["restrictions"]
    if not i["mime"].startswith("image/") or "svg" in i["mime"] or "gif" in i["mime"]:
        return "format non retenu : %s" % i["mime"]
    return ""


def fetch_infos(titles_or_search, search=False, n=12, width=800):
    base = dict(action="query", prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth=width,
                iiextmetadatafilter="LicenseShortName|LicenseUrl|Artist|Credit|ImageDescription|Restrictions|NonFree|AttributionRequired")
    if search:
        data = api(generator="search", gsrsearch=titles_or_search + " filetype:bitmap", gsrnamespace=6, gsrlimit=n, **base)
    else:
        data = api(titles=titles_or_search, **base)
    pages = (data.get("query") or {}).get("pages") or []
    return sorted(pages, key=lambda p: p.get("index", 0))


def fresh_dir(path):
    d = Path(path)
    if d.exists() and any(d.iterdir()):
        sys.exit("Le dossier %s n'est pas vide : donnez un dossier neuf (fichiers téléchargés = non fiables)." % d)
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_name(title):
    base = re.sub(r"^File:", "", title)
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:90]


def cmd_search(a):
    d = fresh_dir(a.dir) if a.dir else None
    for p in fetch_infos(a.query, search=True, n=a.n):
        i = info_of(p)
        bad = license_problem(i)
        print("%s%s | %dx%d | %s | %s" % ("[REFUSÉ] " if bad else "", i["title"], i["width"], i["height"], i["license"] or "?", i["description"][:90]))
        if bad:
            print("    -> %s" % bad)
        elif d and i["thumb"]:
            f = d / safe_name(i["title"])
            f.write_bytes(http(i["thumb"], binary=True))
            time.sleep(0.5)
            print("    vignette : %s" % f)


def credit_markdown(i, modified=False):
    who = "[%s](%s)" % (i["artist"], i["artist_url"]) if i["artist_url"] else i["artist"]
    lic = "[%s](%s)" % (i["license"], i["license_url"]) if i["license_url"] else i["license"]
    if re.match(r"^(public domain|pd)", i["license"], re.I):
        lic = "domaine public" if not i["license_url"] else "[%s](%s)" % (i["license"], i["license_url"])
    out = "Photo : %s, %s, [Wikimedia Commons](%s)" % (who, lic, i["page_url"].replace("(", "%28").replace(")", "%29"))
    if modified:
        out += ", recadrée"
    return out


def cmd_get(a):
    title = a.title if a.title.startswith("File:") else "File:" + a.title
    pages = fetch_infos(title, width=SITE_MAX_WIDTH)
    if not pages or pages[0].get("missing"):
        sys.exit("Fichier introuvable : %s" % title)
    i = info_of(pages[0])
    bad = license_problem(i)
    if bad:
        sys.exit("REFUSÉ : %s (%s)" % (bad, i["title"]))
    d = fresh_dir(a.dir)
    src = i["thumb"] if i["width"] > SITE_MAX_WIDTH and i["thumb"] else i["url"]
    f = d / safe_name(i["title"])
    f.write_bytes(http(src, binary=True))
    i["local"] = str(f)
    print(json.dumps({k: i[k] for k in ("title", "page_url", "width", "height", "license", "license_url", "artist", "artist_url", "local")}, ensure_ascii=False, indent=1))
    print("\nCrédit (Markdown) :\n" + credit_markdown(i))
    print("\nAvec « recadrée » :\n" + credit_markdown(i, modified=True))


def need_pil():
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("Pillow est absent : lancez ce script avec le python3 du système (python3 -c 'import PIL').")
    return Image, ImageOps


def crop_to(img, ratio, focus):
    w, h = img.size
    target = ratio[0] / ratio[1]
    if w / h > target:
        nw, nh = int(round(h * target)), h
    else:
        nw, nh = w, int(round(w / target))
    fx, fy = focus
    x = min(max(int(round(fx * w - nw / 2)), 0), w - nw)
    y = min(max(int(round(fy * h - nh / 2)), 0), h - nh)
    return img.crop((x, y, x + nw, y + nh))


def avif(img, out, max_bytes, q_start=62):
    """Encode en AVIF ; baisse la qualité jusqu'à passer sous max_bytes."""
    if out.exists():
        sys.exit("Fichier déjà présent, jamais écrasé : %s (choisissez un autre nom)" % out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "in.png"
        img.save(tmp)
        q = q_start
        while True:
            tmp_out = Path(td) / "out.avif"
            subprocess.run(["avifenc", "-q", str(q), "-s", "6", "-j", "all", str(tmp), str(tmp_out)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if tmp_out.stat().st_size <= max_bytes or q <= 30:
                out.write_bytes(tmp_out.read_bytes())
                return q, out.stat().st_size
            q -= 4


def load_image(path):
    Image, ImageOps = need_pil()
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return img


def log_credit(slug, rel, a, kind):
    if not a.source:
        sys.exit("Option --from \"File:...\" obligatoire (provenance de chaque image).")
    title = a.source if a.source.startswith("File:") else "File:" + a.source
    pages = fetch_infos(title, width=200)
    i = info_of(pages[0]) if pages and not pages[0].get("missing") else None
    if not i:
        sys.exit("Provenance introuvable sur Commons : %s" % title)
    bad = license_problem(i)
    if bad:
        sys.exit("REFUSÉ : %s (%s)" % (bad, i["title"]))
    f = ROOT / "content" / "blog" / "credits" / (slug + ".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    rows = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    rows.append({"file": rel, "kind": kind, "source": i["page_url"], "title": i["title"], "author": i["artist"],
                 "author_url": i["artist_url"], "license": i["license"], "license_url": i["license_url"],
                 "checked": datetime.date.today().isoformat(), "credit_markdown": credit_markdown(i, modified=True)})
    f.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return credit_markdown(i, modified=True)


def parse_focus(v):
    try:
        x, y = [float(t) for t in v.split(",")]
        return min(max(x, 0), 1), min(max(y, 0), 1)
    except Exception:
        sys.exit("--focus attend « X,Y » entre 0 et 1, par exemple 0.5,0.4")


def cmd_cover(a):
    Image, _ = need_pil()
    img = load_image(a.file)
    if img.size[0] < 1600:
        sys.exit("Photo trop petite pour une couverture (%dpx de large, 1600 minimum) : choisissez-en une plus grande." % img.size[0])
    focus = parse_focus(a.focus)
    wide = crop_to(img, (16, 9), focus).resize((1600, 900), Image.LANCZOS)
    base = ROOT / "images-optimized" / "blog" / a.slug
    results = []
    q, size = avif(wide, base / (a.name + ".avif"), 150_000)
    results.append((a.name + ".avif", 1600, 900, size))
    for w in (1024, 640):
        im = wide.resize((w, int(round(w * 9 / 16))), Image.LANCZOS)
        q, size = avif(im, base / ("%s-%d.avif" % (a.name, w)), 90_000 if w == 1024 else 45_000)
        results.append(("%s-%d.avif" % (a.name, w), w, im.size[1], size))
    share = crop_to(img, (1200, 630), focus).resize((1200, 630), Image.LANCZOS)
    pj = base / "partage.jpg"
    if pj.exists():
        sys.exit("partage.jpg existe déjà dans %s" % base)
    share.save(pj, "JPEG", quality=78, optimize=True, progressive=True)
    results.append(("partage.jpg", 1200, 630, pj.stat().st_size))
    credit = log_credit(a.slug, "/images-optimized/blog/%s/%s.avif" % (a.slug, a.name), a, "cover")
    for n, w, h, s in results:
        print("%s  %dx%d  %d Ko" % (n, w, h, s // 1000))
    print("\nFront matter :")
    print("image: /images-optimized/blog/%s/%s.avif" % (a.slug, a.name))
    print("image_width: 1600\nimage_height: 900")
    print("og_image: /images-optimized/blog/%s/partage.jpg" % a.slug)
    print("image_credit: " + credit)


def cmd_inline(a):
    Image, _ = need_pil()
    img = load_image(a.file)
    if img.size[0] < 900:
        sys.exit("Photo trop petite (%dpx de large, 900 minimum)." % img.size[0])
    focus = parse_focus(a.focus)
    if a.ratio:
        m = re.match(r"^(\d+):(\d+)$", a.ratio)
        if not m:
            sys.exit("--ratio attend « L:H », par exemple 3:2")
        img = crop_to(img, (int(m.group(1)), int(m.group(2))), focus)
    width = min(a.width, img.size[0])
    img = img.resize((width, int(round(img.size[1] * width / img.size[0]))), Image.LANCZOS)
    out = ROOT / "images-optimized" / "blog" / a.slug / (a.name + ".avif")
    q, size = avif(img, out, 150_000)
    credit = log_credit(a.slug, "/images-optimized/blog/%s/%s.avif" % (a.slug, a.name), a, "inline")
    print("%s  %dx%d  %d Ko (q=%d)" % (out.relative_to(ROOT), img.size[0], img.size[1], size // 1000, q))
    print("\nMarkdown (légende puis § puis crédit ; 3 à 4 mots utiles dans le texte alternatif, rien d'artificiel) :")
    print('![Texte alternatif décrivant la photo](/images-optimized/blog/%s/%s.avif "Légende. § %s"){%dx%d}' % (
        a.slug, a.name, credit, img.size[0], img.size[1]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--n", type=int, default=12); s.add_argument("--dir")
    g = sub.add_parser("get"); g.add_argument("title"); g.add_argument("--dir", required=True)
    for name in ("cover", "inline"):
        c = sub.add_parser(name)
        c.add_argument("file"); c.add_argument("slug")
        if name == "inline":
            c.add_argument("name"); c.add_argument("--ratio"); c.add_argument("--width", type=int, default=1200)
        else:
            c.add_argument("--name", default="couverture")
        c.add_argument("--focus", default="0.5,0.5"); c.add_argument("--from", dest="source", required=True)
    a = ap.parse_args()
    {"search": cmd_search, "get": cmd_get, "cover": cmd_cover, "inline": cmd_inline}[a.cmd](a)


if __name__ == "__main__":
    main()
