# tools/ — outils de développement (non utilisés par le site)

Rien ici n'est chargé par les pages. Python 3.9 suffit (macOS), sans Node.

## Régénérer les fichiers `.min.js`

`main.min.js`, `consent.min.js` et `animations.min.js` sont les versions allégées de
`main.js`, `consent.js` et `animations.js`. **Toute modification d'un `.js` doit être suivie
de cette commande**, sinon le site (qui charge les `.min.js`) ne change pas.

```sh
python3 -m venv ~/.venv-clos-min          # une seule fois, HORS du dépôt
~/.venv-clos-min/bin/pip install rjsmin    # (testé avec rjsmin 1.2.5)

~/.venv-clos-min/bin/python tools/minify.py          # main + consent
~/.venv-clos-min/bin/python tools/minify.py animations   # un fichier précis
~/.venv-clos-min/bin/python tools/minify.py --all    # les trois
~/.venv-clos-min/bin/python tools/minify.py --check  # ne modifie rien : « à jour » ou « PÉRIMÉ »
```

- Idempotent : relancé sans changement de source, il répond « inchangé » (mêmes octets).
- `rjsmin` ne retire que les espaces et les commentaires (aucun renommage de variable) : le
  fichier est plus gros que l'ancien (≈ 17 Ko contre 13 Ko pour `main`), mais sans risque.
- Avant d'écrire, le script vérifie que chaînes, gabarits et expressions régulières sont
  identiques à la source et que le code ne diffère que par les espaces ; après écriture, il
  fait un test de syntaxe avec JavaScriptCore (`osascript`, macOS).
- `animations.min.js` n'est PAS régénéré par défaut : il date de l'ancienne chaîne et
  `animations.js` n'a pas changé. Ne le relancer que si `animations.js` est modifié.

## Ce qui n'est PAS régénérable (chaîne d'origine perdue)

Le code des pages cite `scripts/build-critical.mjs` et `npm run build:min`. Ils n'existent
pas dans le dépôt (ni `package.json`, ni dossier `scripts/`), et Node n'est pas installé.
Conséquences :

- `style.min.css` ne peut pas être reproduit : `rcssmin` donne un résultat équivalent mais
  différent (69 095 octets contre 67 581), donc il n'est ni utilisé ni écrit par `minify.py`.
  Après une modification de `style.css`, `style.min.css` doit être mis à jour à la main
  (ou avec `rcssmin` après essai visuel de toutes les pages).
- Le CSS critique (≈ 22 Ko) recopié dans le `<head>` de chaque page ne se régénère pas non
  plus : toute modification du haut de page se fait à la main, page par page.

## Contrôler les dates du sitemap

`sitemap.xml` est tenu à la main (le futur générateur du blog en reprendra la main).
`python3 tools/lastmod_check.py` compare chaque `<lastmod>` à la date réelle du fichier
(dernier commit, ou date de modification si le fichier est modifié et pas encore commité).
Il n'écrit rien ; code retour 1 en cas d'écart.

## Blog : couvertures allégées (srcset), polices et CSS critique

`python3 tools/build_blog.py` fabrique les pages du blog (voir son en-tête) ; `--check` ne modifie rien.

- **Couvertures** : dès que des variantes `<nom>-640.avif` et `<nom>-1024.avif` existent à côté de l'image (ex.
  `images-optimized/blog/<slug>/couverture-640.avif`), la page déclare un `srcset` + `sizes` ; sans variantes, l'image
  est servie seule. Fabrication d'une variante (macOS, `avifenc` de Homebrew), à partir de la couverture 1600 x 900 :
  `avifdec couverture.avif /tmp/c.png && sips --resampleWidth 640 /tmp/c.png --out /tmp/c640.png &&
  avifenc -q 38 -s 3 -y 420 -j all /tmp/c640.png couverture-640.avif` (idem en 1024).
- **Polices préchargées** par le blog : constante `BLOG_FONT_PRELOADS` de `build_blog.py` (indépendante de l'accueil).
- **CSS critique** : le blog reprend celui d'`index.html` (`<style data-critical>`) à chaque génération ; après une
  modification à la main du CSS critique des 11 pages, relancer `python3 tools/build_blog.py`.

## Système de design : guide de style, sprite de pictogrammes, CSS des composants (refonte visuelle)

Catalogue complet pour les pages : `phase3/03-design-system.md` (hors dépôt). Ici, seulement l'outillage.

- **`tools/styleguide.html`** : tous les composants et variantes, avec le marquage HTML à copier. Non déployé (`tools` est dans `.assetsignore`).
  Voir le rendu : `phase3/qa/serve.sh start 8765`, puis `http://localhost:8765/tools/styleguide.html`.
- **`icons.svg`** (racine, déployé) : sprite de pictogrammes Lucide (ISC ; quelques dessins dérivés de Feather, MIT) et WhatsApp (Simple Icons, CC0).
  Licences en commentaire du fichier. Appel : `<svg class="ico" width="24" height="24" aria-hidden="true" focusable="false"><use href="/icons.svg#nom"/></svg>`.
  Ajouter un pictogramme : prendre `https://cdn.jsdelivr.net/npm/lucide-static@1.52.0/icons/<nom>.svg`, en garder les balises internes
  (`<path>`, `<circle>`…) sans `fill`, `stroke` ni `stroke-width`, les mettre dans un `<symbol id="<nom>" viewBox="0 0 24 24">` du sprite. Le trait
  (1,5 px) vient de la classe `.ico`. Cache de 1 jour (`_headers`) : un pictogramme ajouté apparaît chez un visiteur au plus tard le lendemain.
- **Élaguer le sprite en fin de refonte** (garder les seuls pictogrammes utilisés) : lister les `/icons.svg#nom` des `*.html` et `blog/**/*.html`, puis
  recopier dans un nouveau fichier l'en-tête de licences et les `<symbol>` correspondants (un alias comme `bus-front` renvoie à `#bus` : garder `bus`).
  Le sprite complet pèse 21,7 Ko (7,2 Ko en gzip, dont 1,6 Ko de licences).
- **CSS** : les composants forment un bloc à la fin de `style.css` (à partir du commentaire « SYSTÈME DE DESIGN »), recopié minifié à la fin de
  `style.min.css`. Après une modification du bloc dans `style.css`, remplacer la fin de `style.min.css` (le reste du fichier ne change pas) :

```sh
~/.venv-clos-qa/bin/python - <<'PY'
import rcssmin
css = open('style.css', encoding='utf-8').read()
block = rcssmin.cssmin(css[css.index('/* ============================================================\n   SYSTÈME DE DESIGN'):])
mini = open('style.min.css', encoding='utf-8').read()
open('style.min.css', 'w', encoding='utf-8').write(mini[:mini.index(':root{--cb-h')] + block)
PY
```

  (`rcssmin` : `~/.venv-clos-qa/bin/pip install rcssmin`, testé avec 1.2.2 ; relancée sans modification, la commande redonne exactement le même fichier.)
  Le CSS critique en ligne des pages n'est pas concerné : aucun composant n'est au-dessus de la ligne de flottaison, sauf la barre d'appel `call-bar`
  (voir `phase3/03-design-system.md`).

## Règle de déploiement

Ce dossier ne doit pas être publié : l'ajouter à `.assetsignore` (ligne `tools`).
