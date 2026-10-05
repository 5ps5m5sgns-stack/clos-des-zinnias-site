#!/bin/sh
# =====================================================================================
# verify_migration.sh : contrôle de la migration clos-des-zinnias.fr -> clos-des-cypres.fr
# =====================================================================================
#
# LECTURE SEULE. Le script n'écrit rien nulle part (hors un dossier temporaire effacé à la
# fin) : uniquement des requêtes GET ou HEAD avec curl, des lectures DNS avec dig (si
# disponible) et, sur demande (WHOIS=1), une lecture WHOIS. Aucun POST, aucun envoi de
# formulaire, aucune écriture chez Cloudflare, GitHub, Google ou Formspree.
#
# USAGE (depuis n'importe quel dossier ; sh, bash et zsh conviennent)
#
#   sh tools/verify_migration.sh
#   sh tools/verify_migration.sh NEW=clos-des-cypres.fr OLD=clos-des-zinnias.fr
#   NEW=clos-des-cypres.fr OLD=clos-des-zinnias.fr sh tools/verify_migration.sh
#   sh tools/verify_migration.sh | tee verification-$(date +%Y-%m-%d).txt
#
# Les paramètres peuvent être passés en NOM=valeur (arguments) ou en variables d'environnement.
#
#   NEW        nouveau domaine, sans https:// ni barre finale   (défaut clos-des-cypres.fr)
#   OLD        ancien domaine ; vide = on saute la section « ancien domaine » (défaut clos-des-zinnias.fr)
#   BLOG       auto (défaut) : le blog est contrôlé s'il répond 200 sur /blog/ ; yes : il doit exister ;
#              no : ignoré
#   TIMEOUT    délai maximum par requête, en secondes           (défaut 20)
#   DNSCHECK   1 (défaut) : contrôle DNS (NS, MX, SPF, www) ; 0 : ignoré
#   MX_EXPECT  texte qui doit figurer dans les MX de NEW         (défaut ovh.net : courrier OVH)
#   SPF_EXPECT texte qui doit figurer dans le SPF de NEW         (défaut include:mx.ovh.com)
#   EMAIL_OK   adresse qui doit être affichée                    (défaut cypres@ponthieu.fr : l'adresse UNIQUE du site, D48 bis)
#   EMAIL_OLD  adresse qui ne doit plus apparaître               (défaut zinnias@ponthieu.fr)
#   WA_EXPECT  numéro du lien WhatsApp (wa.me/NUMERO)            (défaut 33609204590 : le numéro affiché, D48)
#   EXPECT_URLS nombre d'URLs attendu dans sitemap.xml           (défaut 18 : 9 pages + 3 pages d'atterrissage + /blog/ + 5 articles)
#   OLDWORD    ancien nom de marque cherché dans les pages       (défaut zinnias)
#   PDF_PATH   chemin d'une plaquette PDF encore déployée        (défaut : vide ; la plaquette n'est plus déployée,
#              dossier docs/ dans .assetsignore : le script contrôle alors qu'elle répond 404)
#   WHOIS      1 : affiche l'échéance de OLD et NEW (AFNIC, nécessite whois) ; défaut 0
#   EXT_LINKS  adresses externes dont le certificat TLS est testé (section H) ; défaut : les 2 pages de la mairie de Gardanne
#              citées par le blog (PLUi, dépôt des demandes d'urbanisme)
#   UA         User-Agent à envoyer (défaut : celui de curl)
#   NO_COLOR   défini : pas de couleurs
#
#   Réservés aux essais en local (voir plus bas) : SCHEME (défaut https), CANON (défaut = NEW),
#   OLD_SCHEME (défaut = SCHEME).
#
# SORTIE : un tableau « RÉS. | CONTRÔLE | DÉTAIL ».
#   PASS  conforme            FAIL  non conforme (à corriger)
#   WARN  à regarder          SKIP/INFO  non évalué ou simple information
#   Code de sortie : 0 s'il n'y a aucun FAIL, 1 s'il y en a au moins un, 2 en cas d'erreur d'usage.
#
# CE QUE LE SCRIPT VÉRIFIE
#   A. Ancien domaine : https://OLD/ et https://OLD/lots?x=1 -> 301 vers NEW avec chemin et paramètres
#      conservés ; chemin profond (et PDF si PDF_PATH est renseigné) ; http://OLD aboutit sur https://NEW (nombre de sauts) ; www.OLD.
#   B. Nouveau domaine : http -> https ; www -> apex (chemin et paramètres conservés) ;
#      200 sur /, /lots, /contact, /terrain-a-batir-gardanne, /terrain-a-batir-aix-en-provence,
#      /terrain-a-batir-marseille, /terrain-a-batir-provence, /projet, /environnement, /galerie,
#      /mentions-legales, /confidentialite, /blog/ (si publié) ; /lots.html -> /lots ; /index.html -> / ;
#      URL inconnue -> 404 avec un corps HTML non vide (page 404 stylée, chemins absolus).
#   C. Balises : canonical = URL propre sur NEW (sans .html, barre finale seulement pour /blog/...) ;
#      og:url identique ; aucune trace de OLD dans canonical, og:*, twitter:*, JSON-LD ;
#      aucun noindex sur les pages indexables ; e-mail affiché (cypres@ponthieu.fr) ; ancien e-mail absent ;
#      aucune trace de « ownimmobilier », « jessica@ » ni de l'ancien numéro WhatsApp 33630073601 ;
#      liens WhatsApp = wa.me/33609204590 sur chaque page ; lien tel:+33609204590 sur chaque page ;
#      mention résiduelle de l'ancien nom.
#   D. robots.txt (ligne Sitemap: de NEW, pas de Disallow: /) et sitemap.xml (XML valide avec xmllint,
#      URLs toutes sur NEW, toutes en 200 sans redirection, images comprises ; EXPECT_URLS URLs (18) dont les 3 pages
#      d'atterrissage ; ni /merci ni /404) ; ni « 20 min » ni « 23 min » (trajets périmés, décision D14) ni « ownimmobilier »,
#      « jessica@ », « 33630073601 » dans site.webmanifest, feed.xml et sitemap.xml : FAIL s'ils réapparaissent.
#   E. En-têtes : HSTS, X-Content-Type-Options, Referrer-Policy, X-Frame-Options, Permissions-Policy
#      (browsing-topics), cache CSS/JS (revalidation), cache immuable des polices et images ;
#      la plaquette PDF n'est plus servie (404), ou, si PDF_PATH est renseigné, X-Robots-Tag: noindex.
#   F. DNS (si dig) : NS Cloudflare, MX et SPF du courrier toujours présents, www existe, jeton
#      google-site-verification de OLD toujours présent.
#   H. Liens externes cités par le blog (mairie de Gardanne : PLUi, dépôt des demandes d'urbanisme) : WARN si le
#      certificat TLS est invalide ou expiré (constaté le 05/10/2026 sur www.ville-gardanne.fr) ou si le site ne répond pas.
#
# ESSAI EN LOCAL (sans toucher à la production), pour tester le script lui-même
#   Un petit serveur local qui imite Cloudflare (307 sur .html, 404 avec 404.html, _headers,
#   301 par nom d'hôte) permet de vérifier que le script sait répondre PASS :
#     NEW=127.0.0.1:8788 OLD=localhost:8788 SCHEME=http CANON=clos-des-cypres.fr \
#       DNSCHECK=0 sh tools/verify_migration.sh
#   En mode SCHEME=http, les contrôles qui n'ont de sens qu'en https (http -> https, www, HSTS, DNS)
#   sont marqués SKIP.
#
# LIMITES : le script ne voit pas les réglages Cloudflare (il en constate seulement l'effet), ne sait
# pas si Google a indexé quoi que ce soit (c'est le travail de la Search Console), et ne remplace pas
# un regard humain sur la page 404 ou sur le rendu des pages.
# =====================================================================================

# Compatibilité zsh : comportement « sh » (découpage des variables non entourées de guillemets).
[ -n "${ZSH_VERSION:-}" ] && emulate -R sh
set -u
set -f

# ---------------------------------------------------------------- paramètres
NEW=${NEW:-clos-des-cypres.fr}
OLD=${OLD-clos-des-zinnias.fr}
SCHEME=${SCHEME:-https}
OLD_SCHEME=${OLD_SCHEME:-$SCHEME}
BLOG=${BLOG:-auto}
TIMEOUT=${TIMEOUT:-20}
DNSCHECK=${DNSCHECK:-1}
MX_EXPECT=${MX_EXPECT:-ovh.net}
SPF_EXPECT=${SPF_EXPECT:-include:mx.ovh.com}
EMAIL_OK=${EMAIL_OK:-cypres@ponthieu.fr}
EMAIL_OLD=${EMAIL_OLD:-zinnias@ponthieu.fr}
WA_EXPECT=${WA_EXPECT:-33609204590}
EXPECT_URLS=${EXPECT_URLS:-18}
OLDWORD=${OLDWORD:-zinnias}
PDF_PATH=${PDF_PATH-}
WHOIS=${WHOIS:-0}
UA=${UA:-}

for _a in "$@"; do
  case "$_a" in
    NEW=*) NEW=${_a#NEW=} ;;
    OLD=*) OLD=${_a#OLD=} ;;
    BLOG=*) BLOG=${_a#BLOG=} ;;
    TIMEOUT=*) TIMEOUT=${_a#TIMEOUT=} ;;
    DNSCHECK=*) DNSCHECK=${_a#DNSCHECK=} ;;
    WHOIS=*) WHOIS=${_a#WHOIS=} ;;
    SCHEME=*) SCHEME=${_a#SCHEME=}; OLD_SCHEME=$SCHEME ;;
    CANON=*) CANON=${_a#CANON=} ;;
    -h|--help)
      awk 'NR >= 2 { print } /^# =+$/ { c++ } c == 3 { exit }' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) printf 'Argument inconnu : %s (voir --help)\n' "$_a" >&2; exit 2 ;;
  esac
done
# Tolérance : on accepte NEW=https://exemple.fr/ et on ramène à « exemple.fr ».
for _v in NEW OLD CANON; do
  eval "_x=\${$_v:-}"
  _x=${_x#http://}; _x=${_x#https://}; _x=${_x%/}
  eval "$_v=\$_x"
done
CANON=${CANON:-$NEW}

command -v curl >/dev/null 2>&1 || { echo "curl est introuvable : installez-le." >&2; exit 2; }

BASE="$SCHEME://$NEW"          # là où l'on envoie les requêtes
TARGET="https://$CANON"        # forme officielle attendue (canonical, Location, sitemap)
LOCAL=0; [ "$SCHEME" = http ] && LOCAL=1

T=$(mktemp -d "${TMPDIR:-/tmp}/verifmig.XXXXXX") || { echo "mktemp a échoué" >&2; exit 2; }
trap 'rm -rf "$T"' EXIT
trap 'exit 130' INT TERM HUP

# ---------------------------------------------------------------- affichage
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_G=$(printf '\033[32m'); C_R=$(printf '\033[31;1m'); C_Y=$(printf '\033[33m')
  C_D=$(printf '\033[2m'); C_B=$(printf '\033[1m'); C_0=$(printf '\033[0m')
else
  C_G=; C_R=; C_Y=; C_D=; C_B=; C_0=
fi
NPASS=0; NFAIL=0; NWARN=0; NSKIP=0

row() { # $1 = PASS|FAIL|WARN|SKIP|INFO   $2 = contrôle   $3 = détail
  case "$1" in
    PASS) NPASS=$((NPASS+1)); _rc=$C_G ;;
    FAIL) NFAIL=$((NFAIL+1)); _rc=$C_R ;;
    WARN) NWARN=$((NWARN+1)); _rc=$C_Y ;;
    SKIP) NSKIP=$((NSKIP+1)); _rc=$C_D ;;
    *)    _rc=$C_D ;;
  esac
  printf '%s%-4s%s | %-52s | %s\n' "$_rc" "$1" "$C_0" "$2" "$3"
}
section() { printf '\n%s%s%s\n' "$C_B" "$1" "$C_0"; }

# ---------------------------------------------------------------- outils HTTP
curlx() { # curl avec les options communes (lecture seule, stdin fermé)
  if [ -n "$UA" ]; then
    curl -sS --max-time "$TIMEOUT" -A "$UA" "$@" </dev/null
  else
    curl -sS --max-time "$TIMEOUT" "$@" </dev/null
  fi
}

hget() { # hget FICHIER_ENTETES nom : valeur du dernier en-tête de ce nom (insensible à la casse)
  grep -i "^$2:" "$1" 2>/dev/null | tail -1 | sed -E 's/^[^:]*:[[:space:]]*//' | tr -d '\r'
}
F_CODE=000; F_LOC=
fetch() { # fetch URL TAG : GET sans suivre les redirections ; remplit $T/TAG.h (en-têtes) et .b (corps)
  curlx -o "$T/$2.b" -D "$T/$2.h" -w '%{http_code}' "$1" >"$T/$2.code" 2>"$T/$2.err"
  F_CODE=$(cat "$T/$2.code" 2>/dev/null); [ -n "$F_CODE" ] || F_CODE=000
  [ -f "$T/$2.h" ] || : >"$T/$2.h"
  [ -f "$T/$2.b" ] || : >"$T/$2.b"
  F_LOC=$(hget "$T/$2.h" location)
}
fetchh() { # fetchh URL TAG : HEAD sans suivre les redirections
  curlx -I -o /dev/null -D "$T/$2.h" -w '%{http_code}' "$1" >"$T/$2.code" 2>"$T/$2.err"
  F_CODE=$(cat "$T/$2.code" 2>/dev/null); [ -n "$F_CODE" ] || F_CODE=000
  [ -f "$T/$2.h" ] || : >"$T/$2.h"
  F_LOC=$(hget "$T/$2.h" location)
}
CH_URL=; CH_N=0; CH_CODE=000
chain() { # chain URL TAG : suit les redirections (6 maximum) ; remplit CH_URL CH_N CH_CODE
  _r=$(curlx -L --max-redirs 6 -o /dev/null -w '%{url_effective}|%{num_redirects}|%{http_code}' "$1" 2>"$T/$2.err")
  CH_URL=$(printf '%s' "$_r" | cut -d'|' -f1)
  CH_N=$(printf '%s' "$_r" | cut -d'|' -f2)
  CH_CODE=$(printf '%s' "$_r" | cut -d'|' -f3)
  [ -n "$CH_CODE" ] || CH_CODE=000
  [ -n "$CH_N" ] || CH_N=0
}
abs_loc() { # abs_loc URL_REQUETE LOCATION : rend la Location en forme absolue
  case "$2" in
    /*) printf '%s%s' "$(printf '%s' "$1" | sed -E 's#^([a-z]+://[^/]+).*#\1#')" "$2" ;;
    *)  printf '%s' "$2" ;;
  esac
}
lc() { tr 'A-Z' 'a-z'; }
flat() { tr '\n\r' '  ' <"$1"; }

chk_redirect() { # chk_redirect "nom" URL ATTENDU_ABSOLU [codes acceptés] [ATTENDU_ALTERNATIF]
  _n=$1; _u=$2; _w=$3; _codes=${4:-301 308}; _alt=${5:-}
  fetch "$_u" rd
  if [ "$F_CODE" = 000 ]; then
    row FAIL "$_n" "pas de réponse : $(head -c 100 "$T/rd.err" | tr '\n' ' ')"; return 0
  fi
  _l=$(abs_loc "$_u" "$F_LOC")
  # Essai local : une Location relative est résolue contre BASE ; on la ramène à la forme officielle.
  if [ "$BASE" != "$TARGET" ]; then
    case "$_l" in "$BASE"|"$BASE"/*|"$BASE"\?*) _l="$TARGET${_l#"$BASE"}" ;; esac
  fi
  case " $_codes " in *" $F_CODE "*) _okc=1 ;; *) _okc=0 ;; esac
  _shown=${_l:-(sans Location)}
  if [ "$_okc" = 1 ] && { [ "$_l" = "$_w" ] || { [ -n "$_alt" ] && [ "$_l" = "$_alt" ]; }; }; then
    row PASS "$_n" "$F_CODE -> $_l"
  else
    row FAIL "$_n" "obtenu : HTTP $F_CODE -> $_shown ; attendu : $_codes -> $_w"
  fi
  return 0
}

# ---------------------------------------------------------------- extraction dans le HTML
canon_of() { flat "$1" | grep -o -i -E '<link[^>]*rel="canonical"[^>]*>' | head -1 | sed -E 's/.*href="([^"]*)".*/\1/'; }
meta_of() { # meta_of FICHIER propriete_ou_name : contenu de <meta property|name="..." content="...">
  flat "$1" | grep -o -i -E "<meta[^>]*(property|name)=\"$2\"[^>]*>" | head -1 | sed -E 's/.*content="([^"]*)".*/\1/'
}
jsonld_of() { # tous les blocs <script type="application/ld+json"> du fichier
  awk '
    inld == 0 { p = index(tolower($0), "application/ld+json"); if (p == 0) next
                inld = 1; rest = substr($0, p); q = index(rest, ">"); $0 = substr(rest, q + 1) }
    inld == 1 { e = index(tolower($0), "</script>")
                if (e > 0) { print substr($0, 1, e - 1); inld = 0 } else print $0 }
  ' "$1"
}
noindex_in() { flat "$1" | grep -o -i -E '<meta[^>]*name="robots"[^>]*>' | grep -i -c noindex; }
# D48 / D48 bis : motifs qui ne doivent plus apparaître NULLE PART (texte, mailto, JSON-LD, liens, commentaires)
FORBID_PAT='ownimmobilier|jessica@|33630073601'
scan_forbid() { grep -o -i -E "$FORBID_PAT" "$1" 2>/dev/null | sort -u | tr '\n' ' '; }
scan_wa() { grep -o -E 'wa\.me/[0-9]+' "$1" 2>/dev/null | sort -u | tr '\n' ' '; }

# ================================================================ EN-TÊTE
printf '%sContrôle de migration%s  NEW=%s  OLD=%s  (%s)\n' "$C_B" "$C_0" "$NEW" "${OLD:-(aucun)}" "$(date '+%Y-%m-%d %H:%M')"
[ "$LOCAL" = 1 ] && printf '%sMode essai local (SCHEME=http) : les contrôles propres à https/DNS sont ignorés.%s\n' "$C_D" "$C_0"
printf '%s%-4s | %-52s | %s%s\n' "$C_B" "RÉS." "CONTRÔLE" "DÉTAIL" "$C_0"

# ================================================================ A. ANCIEN DOMAINE
if [ -n "$OLD" ]; then
  section "A. Ancien domaine ($OLD) vers nouveau domaine"
  OB="$OLD_SCHEME://$OLD"
  chk_redirect "OLD / : 301 vers NEW /"                      "$OB/"                         "$TARGET/"
  chk_redirect "OLD /lots?x=1 : 301, chemin + paramètre"     "$OB/lots?x=1"                 "$TARGET/lots?x=1"
  chk_redirect "OLD /terrain-a-batir-gardanne : 301"         "$OB/terrain-a-batir-gardanne" "$TARGET/terrain-a-batir-gardanne"
  chk_redirect "OLD /lots.html : 301 (chemin conservé)"      "$OB/lots.html"                "$TARGET/lots.html" "301 308" "$TARGET/lots"
  if [ -n "$PDF_PATH" ]; then
    chk_redirect "OLD PDF : 301 (lien imprimé ou de portail)"  "$OB$PDF_PATH"                 "$TARGET$PDF_PATH"
  else
    row SKIP "OLD PDF : 301" "plaquette retirée du déploiement (PDF_PATH vide)"
  fi
  if [ "$LOCAL" = 1 ]; then
    row SKIP "OLD http:// et www. vers https://NEW/"         "non applicable en http"
  else
    chain "http://$OLD/lots?x=1" ch1
    if [ "$CH_CODE" = 200 ] && [ "$CH_URL" = "$TARGET/lots?x=1" ]; then
      if [ "$CH_N" -le 2 ]; then row PASS "http://OLD/lots?x=1 aboutit sur https://NEW" "$CH_N saut(s) -> $CH_URL"
      else row WARN "http://OLD/lots?x=1 aboutit sur https://NEW" "$CH_N sauts (2 maximum souhaités)"; fi
    else
      row FAIL "http://OLD/lots?x=1 aboutit sur https://NEW" "arrivée : HTTP $CH_CODE $CH_URL (attendu 200 $TARGET/lots?x=1)"
    fi
    chk_redirect "https://www.OLD/ : 301 vers NEW /"         "https://www.$OLD/"            "$TARGET/"
  fi
else
  section "A. Ancien domaine : ignoré (OLD vide)"
fi

# ================================================================ B. NOUVEAU DOMAINE
section "B. Nouveau domaine ($NEW) : redirections et pages"

if [ "$LOCAL" = 1 ]; then
  row SKIP "http://NEW vers https://NEW"                     "non applicable en http"
  row SKIP "www.NEW vers NEW (chemin + paramètres)"          "non applicable en http"
else
  chk_redirect "http://NEW/ : 301 vers https://NEW/"         "http://$NEW/"                 "$TARGET/"
  chk_redirect "http://NEW/lots?x=1 : https, chemin conservé" "http://$NEW/lots?x=1"        "$TARGET/lots?x=1"
  chk_redirect "https://www.NEW/ : 301 vers NEW/"            "https://www.$NEW/"            "$TARGET/"
  chk_redirect "https://www.NEW/lots?x=1 : vers NEW/lots?x=1" "https://www.$NEW/lots?x=1"  "$TARGET/lots?x=1"
fi
chk_redirect "NEW /lots.html : vers /lots (307 ou 301)"      "$BASE/lots.html"              "$TARGET/lots"      "301 307 308"
chk_redirect "NEW /lots.html?lot=3 : vers /lots?lot=3"       "$BASE/lots.html?lot=3"        "$TARGET/lots?lot=3" "301 307 308"
chk_redirect "NEW /index.html : vers /"                      "$BASE/index.html"             "$TARGET/"          "301 307 308"

# Le blog est-il publié ?
BLOG_PUB=0
fetch "$BASE/blog/" blogidx
case "$BLOG" in
  no)  ;;
  yes) BLOG_PUB=1 ;;
  *)   [ "$F_CODE" = 200 ] && BLOG_PUB=1 ;;
esac

# Pages : 200 sans redirection
PAGES="/ /lots /contact /terrain-a-batir-gardanne /terrain-a-batir-aix-en-provence /terrain-a-batir-marseille /terrain-a-batir-provence /projet /environnement /galerie /mentions-legales /confidentialite"
: >"$T/pages.lst"
_i=0
for _p in $PAGES; do
  _i=$((_i+1))
  fetch "$BASE$_p" "pg$_i"
  echo "$_i $_p" >>"$T/pages.lst"
  if [ "$F_CODE" = 200 ] && [ -z "$F_LOC" ]; then
    _ct=$(hget "$T/pg$_i.h" content-type)
    case "$_ct" in
      *html*) row PASS "NEW $_p : 200" "HTML, $(wc -c <"$T/pg$_i.b" | tr -d ' ') octets, sans redirection" ;;
      *)      row WARN "NEW $_p : 200" "type inattendu : $_ct" ;;
    esac
  else
    row FAIL "NEW $_p : 200" "obtenu HTTP $F_CODE${F_LOC:+ -> $F_LOC}"
  fi
done

# /merci : 200 et noindex (page de conversion, ne doit pas être indexée)
fetch "$BASE/merci" merci
if [ "$F_CODE" = 200 ] && [ "$(noindex_in "$T/merci.b")" -ge 1 ]; then row PASS "NEW /merci : 200 et noindex" "page de conversion non indexable"
elif [ "$F_CODE" = 200 ]; then row WARN "NEW /merci : 200 et noindex" "200 mais sans noindex"
else row FAIL "NEW /merci : 200 et noindex" "obtenu HTTP $F_CODE"; fi

# Blog
if [ "$BLOG" = no ]; then
  row SKIP "NEW /blog/" "ignoré (BLOG=no)"
elif [ "$BLOG_PUB" = 1 ]; then
  fetch "$BASE/blog/" blogidx
  if [ "$F_CODE" = 200 ]; then row PASS "NEW /blog/ : 200" "index du blog publié"
  else row FAIL "NEW /blog/ : 200" "obtenu HTTP $F_CODE (BLOG=yes : le blog doit exister)"; fi
  chk_redirect "NEW /blog : vers /blog/ (une seule étape)" "$BASE/blog" "$TARGET/blog/" "301 307 308"
else
  row SKIP "NEW /blog/" "blog non publié (404) : contrôle ignoré (BLOG=yes pour l'exiger)"
fi

# URL inconnue : 404 avec corps HTML non vide
_unk="/zz-verif-$$"
fetch "$BASE$_unk" unk
_sz=$(wc -c <"$T/unk.b" | tr -d ' ')
if [ "$F_CODE" = 404 ] && [ "$_sz" -gt 0 ] && grep -q -i '<html' "$T/unk.b"; then
  row PASS "NEW URL inconnue : 404 + page" "HTTP 404, corps HTML de $_sz octets"
elif [ "$F_CODE" = 404 ]; then
  row FAIL "NEW URL inconnue : 404 + page" "404 mais corps vide ou non HTML ($_sz octet) : not_found_handling pas encore actif ?"
else
  row FAIL "NEW URL inconnue : 404 + page" "obtenu HTTP $F_CODE (attendu 404)"
fi
fetch "$BASE/blog/zz-verif-$$/x/" unk2
if [ "$F_CODE" = 404 ] && grep -q 'href="/style.min.css"' "$T/unk2.b"; then
  row PASS "NEW 404 profonde : CSS en chemin absolu" "la page 404 reste stylée sous /blog/.../"
elif [ "$F_CODE" = 404 ]; then
  row WARN "NEW 404 profonde : CSS en chemin absolu" "404 sans href=\"/style.min.css\" : page non stylée dans un sous-dossier"
else
  row FAIL "NEW 404 profonde : CSS en chemin absolu" "obtenu HTTP $F_CODE (attendu 404)"
fi

# ================================================================ C. BALISES
section "C. Balises (canonical, og, JSON-LD), e-mail, ancien nom"

PYOK=0; command -v python3 >/dev/null 2>&1 && PYOK=1
NOIDX_BAD=; OLDMAIL_BAD=; OLDWORD_BAD=; HOME_MAIL=0; CONTACT_MAIL=0; JSON_BAD=; FORBID_BAD=; WA_BAD=; TEL_BAD=

check_meta() { # check_meta ETIQUETTE URL_ATTENDUE FICHIER
  _mc=$(canon_of "$3"); _mo=$(meta_of "$3" og:url)
  _mp=
  [ "$_mc" = "$2" ] || _mp="canonical=${_mc:-(absent)}"
  [ "$_mo" = "$2" ] || _mp="$_mp og:url=${_mo:-(absent)}"
  _mhit=
  if [ -n "$OLD" ]; then
    _mimg=$(meta_of "$3" og:image); _mtw=$(meta_of "$3" twitter:image)
    _mld=$(jsonld_of "$3" | lc)
    case "$(printf '%s' "$_mc" | lc)" in *"$OLD"*) _mhit="$_mhit canonical" ;; esac
    case "$(printf '%s%s%s' "$_mo" "$_mimg" "$_mtw" | lc)" in *"$OLD"*) _mhit="$_mhit og/twitter" ;; esac
    case "$_mld" in *"$OLD"*) _mhit="$_mhit JSON-LD" ;; esac
  fi
  if [ -z "$_mp" ] && [ -z "$_mhit" ]; then
    row PASS "balises $1" "canonical = og:url = $2 ; JSON-LD et og sans l'ancien domaine"
  else
    row FAIL "balises $1" "attendu $2 ; obtenu :$_mp${_mhit:+ ; ancien domaine présent dans :$_mhit}"
  fi
  if [ "$PYOK" = 1 ]; then
    if ! python3 - "$3" <<'PY' >/dev/null 2>&1
import re, sys, json
t = open(sys.argv[1], encoding="utf-8", errors="replace").read()
for b in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t, re.S | re.I):
    json.loads(b)
PY
    then JSON_BAD="$JSON_BAD $1"; fi
  fi
  return 0
}

while read -r _idx _p; do
  _f="$T/pg$_idx.b"
  [ -s "$_f" ] || continue
  if [ "$_p" = "/" ]; then _exp="$TARGET/"; else _exp="$TARGET$_p"; fi
  check_meta "$_p" "$_exp" "$_f"
  [ "$(noindex_in "$_f")" -ge 1 ] && NOIDX_BAD="$NOIDX_BAD $_p"
  case "$(hget "$T/pg$_idx.h" x-robots-tag | lc)" in *noindex*) NOIDX_BAD="$NOIDX_BAD $_p(en-tête)" ;; esac
  grep -q -i -F "$EMAIL_OLD" "$_f" && OLDMAIL_BAD="$OLDMAIL_BAD $_p"
  _fb=$(scan_forbid "$_f"); [ -n "$_fb" ] && FORBID_BAD="$FORBID_BAD $_p($_fb)"
  _wa=$(scan_wa "$_f")
  case "$_wa" in
    "wa.me/$WA_EXPECT ") ;;
    "") WA_BAD="$WA_BAD $_p(aucun lien)" ;;
    *)  WA_BAD="$WA_BAD $_p($_wa)" ;;
  esac
  grep -q -F 'href="tel:+33609204590"' "$_f" || TEL_BAD="$TEL_BAD $_p"
  _cnt=$(lc <"$_f" | sed 's/plaquette-clos-des-[a-z]*\.pdf//g' | grep -o -i "$OLDWORD" | wc -l | tr -d ' ')
  [ "$_cnt" -gt 0 ] && OLDWORD_BAD="$OLDWORD_BAD $_p($_cnt)"
  if grep -q -i -F "$EMAIL_OK" "$_f"; then
    [ "$_p" = "/" ] && HOME_MAIL=1
    [ "$_p" = "/contact" ] && CONTACT_MAIL=1
  fi
done <"$T/pages.lst"

if [ -n "$NOIDX_BAD" ]; then row FAIL "aucun noindex sur les pages indexables" "noindex trouvé sur :$NOIDX_BAD"
else row PASS "aucun noindex sur les pages indexables" "balise robots et X-Robots-Tag corrects"; fi
if [ "$PYOK" = 1 ]; then
  if [ -n "$JSON_BAD" ]; then row WARN "JSON-LD syntaxiquement valide" "JSON invalide sur :$JSON_BAD"
  else row PASS "JSON-LD syntaxiquement valide" "tous les blocs s'analysent (python3)"; fi
else row SKIP "JSON-LD syntaxiquement valide" "python3 absent"; fi
if [ "$HOME_MAIL" = 1 ] && [ "$CONTACT_MAIL" = 1 ]; then row PASS "e-mail affiché = $EMAIL_OK" "présent sur / et /contact"
else row FAIL "e-mail affiché = $EMAIL_OK" "absent de :$([ "$HOME_MAIL" = 1 ] || printf ' /')$([ "$CONTACT_MAIL" = 1 ] || printf ' /contact')"; fi
if [ -n "$OLDMAIL_BAD" ]; then row FAIL "absence de $EMAIL_OLD" "encore présent sur :$OLDMAIL_BAD"
else row PASS "absence de $EMAIL_OLD" "absent des $(wc -l <"$T/pages.lst" | tr -d ' ') pages contrôlées"; fi
_np=$(wc -l <"$T/pages.lst" | tr -d ' ')
if [ -n "$FORBID_BAD" ]; then row FAIL "aucune trace de ownimmobilier / jessica@ / 33630073601" "présent sur :$FORBID_BAD"
else row PASS "aucune trace de ownimmobilier / jessica@ / 33630073601" "absents des $_np pages contrôlées"; fi
if [ -n "$WA_BAD" ]; then row FAIL "WhatsApp : wa.me/$WA_EXPECT sur chaque page" "écart sur :$WA_BAD"
else row PASS "WhatsApp : wa.me/$WA_EXPECT sur chaque page" "bulle WhatsApp présente et unique numéro sur les $_np pages"; fi
if [ -n "$TEL_BAD" ]; then row FAIL "lien tel:+33609204590 sur chaque page" "absent de :$TEL_BAD"
else row PASS "lien tel:+33609204590 sur chaque page" "présent sur les $_np pages"; fi
if [ -n "$OLDWORD_BAD" ]; then row WARN "ancien nom « $OLDWORD » (hors nom du PDF)" "occurrences :$OLDWORD_BAD"
else row PASS "ancien nom « $OLDWORD » (hors nom du PDF)" "aucune mention résiduelle"; fi

# ================================================================ D. robots.txt et sitemap
section "D. robots.txt et sitemap.xml"

fetch "$BASE/robots.txt" rb
if [ "$F_CODE" != 200 ]; then row FAIL "robots.txt : 200" "obtenu HTTP $F_CODE"
else
  _sm=$(grep -i '^Sitemap:' "$T/rb.b" | head -1 | tr -d '\r' | sed -E 's/^[Ss]itemap:[[:space:]]*//')
  if [ "$_sm" = "$TARGET/sitemap.xml" ]; then row PASS "robots.txt : ligne Sitemap: de NEW" "$_sm"
  else row FAIL "robots.txt : ligne Sitemap: de NEW" "obtenu « ${_sm:-(aucune)} » ; attendu $TARGET/sitemap.xml"; fi
  if grep -q -E '^Disallow:[[:space:]]*/[[:space:]]*$' "$T/rb.b"; then row FAIL "robots.txt : site non bloqué" "« Disallow: / » trouvé : site interdit aux robots"
  else row PASS "robots.txt : site non bloqué" "pas de « Disallow: / »"; fi
  if [ -n "$OLD" ] && grep -q -i -F "$OLD" "$T/rb.b"; then row FAIL "robots.txt : sans ancien domaine" "$OLD présent"
  else row PASS "robots.txt : sans ancien domaine" "propre"; fi
fi

fetch "$BASE/sitemap.xml" sm
if [ "$F_CODE" != 200 ]; then
  row FAIL "sitemap.xml : 200" "obtenu HTTP $F_CODE"
else
  _ct=$(hget "$T/sm.h" content-type)
  case "$_ct" in *xml*) row PASS "sitemap.xml : 200, type XML" "$_ct" ;; *) row WARN "sitemap.xml : 200, type XML" "Content-Type : $_ct" ;; esac
  if command -v xmllint >/dev/null 2>&1; then
    if xmllint --noout "$T/sm.b" 2>"$T/xml.err"; then row PASS "sitemap.xml : XML valide (xmllint)" "document bien formé"
    else row FAIL "sitemap.xml : XML valide (xmllint)" "$(head -c 150 "$T/xml.err" | tr '\n' ' ')"; fi
  else row SKIP "sitemap.xml : XML valide" "xmllint absent"; fi

  flat "$T/sm.b" | grep -o '<loc>[^<]*</loc>' | sed -E 's#</?loc>##g; s/^[[:space:]]+//; s/[[:space:]]+$//' >"$T/locs.lst"
  flat "$T/sm.b" | grep -o '<image:loc>[^<]*</image:loc>' | sed -E 's#</?image:loc>##g; s/^[[:space:]]+//; s/[[:space:]]+$//' >"$T/imgs.lst"
  _nl=$(wc -l <"$T/locs.lst" | tr -d ' ')
  if [ "$_nl" -eq 0 ]; then row FAIL "sitemap.xml : contient des URLs" "aucune balise <loc>"
  else
    _bad=; _ok=0; _nbad=0
    while IFS= read -r _u; do
      [ -n "$_u" ] || continue
      case "$_u" in
        "$TARGET"|"$TARGET"/*) ;;
        *) _nbad=$((_nbad+1)); [ "$_nbad" -le 4 ] && _bad="$_bad [hors domaine : $_u]"; continue ;;
      esac
      case "$_u" in *.html*|*index*) _nbad=$((_nbad+1)); [ "$_nbad" -le 4 ] && _bad="$_bad [forme non propre : $_u]" ;; esac
      _fu="$BASE${_u#"$TARGET"}"
      fetch "$_fu" smu
      if [ "$F_CODE" = 200 ] && [ -z "$F_LOC" ]; then
        _ok=$((_ok+1))
        case "$_u" in "$TARGET/blog/"*) check_meta "$_u" "$_u" "$T/smu.b" ;; esac
      else
        _nbad=$((_nbad+1)); [ "$_nbad" -le 4 ] && _bad="$_bad [$_u : HTTP $F_CODE${F_LOC:+ -> $F_LOC}]"
      fi
    done <"$T/locs.lst"
    if [ "$_nbad" -eq 0 ]; then row PASS "sitemap.xml : $_nl URLs, toutes en 200 sans redirection" "toutes sur $CANON, formes propres"
    else row FAIL "sitemap.xml : $_ok/$_nl URLs conformes" "$_nbad problème(s) dont :$_bad"; fi
    if [ "$BLOG_PUB" = 1 ] && ! grep -q -x "$TARGET/blog/" "$T/locs.lst"; then
      row WARN "sitemap.xml : contient /blog/" "le blog est publié mais /blog/ n'est pas dans le sitemap"
    fi
    _miss=
    for _lp in terrain-a-batir-aix-en-provence terrain-a-batir-marseille terrain-a-batir-provence; do
      grep -q -x "$TARGET/$_lp" "$T/locs.lst" || _miss="$_miss /$_lp"
    done
    if [ -z "$_miss" ]; then row PASS "sitemap.xml : les 3 pages d'atterrissage" "/terrain-a-batir-aix-en-provence, -marseille, -provence présentes"
    else row FAIL "sitemap.xml : les 3 pages d'atterrissage" "absentes du sitemap :$_miss"; fi
    if [ "$_nl" -eq "$EXPECT_URLS" ]; then row PASS "sitemap.xml : $EXPECT_URLS URLs attendues" "$_nl URLs (9 pages + 3 atterrissage + /blog/ + 5 articles)"
    else row FAIL "sitemap.xml : $EXPECT_URLS URLs attendues" "obtenu $_nl URL(s)"; fi
    if grep -q -E "/(merci|404)([/?]|$)" "$T/locs.lst"; then row FAIL "sitemap.xml : ni /merci ni /404" "page non indexable listée dans le sitemap"
    else row PASS "sitemap.xml : ni /merci ni /404" "pages non indexables absentes"; fi
    _ni=$(wc -l <"$T/imgs.lst" | tr -d ' ')
    if [ "$_ni" -gt 0 ]; then
      _ibad=
      while IFS= read -r _u; do
        [ -n "$_u" ] || continue
        case "$_u" in
          "$TARGET"/*) _fu="$BASE${_u#"$TARGET"}" ;;
          *) _ibad="$_ibad $_u(hors domaine)"; continue ;;
        esac
        fetchh "$_fu" smi
        [ "$F_CODE" = 200 ] || _ibad="$_ibad $_u(HTTP $F_CODE)"
      done <"$T/imgs.lst"
      if [ -z "$_ibad" ]; then row PASS "sitemap.xml : $_ni image(s) en 200" "toutes accessibles sur $CANON"
      else row FAIL "sitemap.xml : images" "en défaut :$_ibad"; fi
    fi
  fi
fi

# --- Trajets périmés (« 20 min d'Aix », « 23 min de Marseille » : décision D14) et anciennes coordonnées dans les fichiers publics hors pages
_nb=$(printf '\302\240')   # espace insécable (UTF-8)
for _f in site.webmanifest feed.xml sitemap.xml; do
  fetch "$BASE/$_f" trj
  _fb=
  [ "$F_CODE" = 200 ] && _fb=$(scan_forbid "$T/trj.b")
  if [ -n "$_fb" ]; then
    row FAIL "$_f : sans ownimmobilier / jessica@ / 33630073601" "trouvé : $_fb"
  elif [ "$F_CODE" != 200 ]; then
    row WARN "$_f : sans « 20 min » ni « 23 min »" "HTTP $F_CODE : fichier non contrôlé"
  elif LC_ALL=C grep -q -E "(^|[^0-9])(20|23)( |$_nb)*min" "$T/trj.b"; then
    _hit=$(LC_ALL=C grep -o -E "(^|[^0-9])(20|23)( |$_nb)*min[a-z]*" "$T/trj.b" | head -1 | sed -E 's/^[^0-9]+//' | tr -d '\n')
    row FAIL "$_f : sans « 20 min » ni « 23 min »" "formulation périmée trouvée (« ${_hit} ») : écrire « à 25 minutes d'Aix-en-Provence » / « à 30 minutes de Marseille » (hors heures de pointe)"
  else
    row PASS "$_f : sans « 20 min » ni « 23 min »" "aucune formulation périmée ; ni ownimmobilier, ni jessica@, ni 33630073601"
  fi
done

# ================================================================ E. EN-TÊTES
section "E. En-têtes HTTP"

H="$T/pg1.h"   # page d'accueil
if [ "$LOCAL" = 1 ]; then row SKIP "HSTS" "non applicable en http"
else
  _v=$(hget "$H" strict-transport-security)
  _age=$(printf '%s' "$_v" | sed -n -E 's/.*max-age=([0-9]+).*/\1/p')
  if [ -n "$_age" ] && [ "$_age" -ge 31536000 ]; then row PASS "HSTS (1 an minimum)" "$_v"
  else row FAIL "HSTS (1 an minimum)" "obtenu « ${_v:-(absent)} »"; fi
fi
_v=$(hget "$H" x-content-type-options | lc)
if [ "$_v" = nosniff ]; then row PASS "X-Content-Type-Options: nosniff" "nosniff"; else row FAIL "X-Content-Type-Options: nosniff" "obtenu « ${_v:-(absent)} »"; fi
_v=$(hget "$H" referrer-policy)
if [ "$_v" = "strict-origin-when-cross-origin" ]; then row PASS "Referrer-Policy" "$_v"; else row FAIL "Referrer-Policy" "obtenu « ${_v:-(absent)} » ; attendu strict-origin-when-cross-origin"; fi
_v=$(hget "$H" x-frame-options | lc)
if [ "$_v" = sameorigin ]; then row PASS "X-Frame-Options: SAMEORIGIN" "sameorigin"; else row FAIL "X-Frame-Options: SAMEORIGIN" "obtenu « ${_v:-(absent)} »"; fi
_v=$(hget "$H" permissions-policy)
case "$_v" in
  *browsing-topics*) row PASS "Permissions-Policy (nouveau _headers en ligne)" "browsing-topics présent" ;;
  *interest-cohort*) row FAIL "Permissions-Policy (nouveau _headers en ligne)" "ancienne valeur (interest-cohort) : le _headers corrigé n'est pas déployé" ;;
  "")                row FAIL "Permissions-Policy (nouveau _headers en ligne)" "absent" ;;
  *)                 row WARN "Permissions-Policy (nouveau _headers en ligne)" "valeur inattendue : $_v" ;;
esac

chk_cache() { # chk_cache ETIQUETTE URL MOTIF_REGEX ATTENDU_TEXTE
  fetchh "$2" ca
  _cc=$(hget "$T/ca.h" cache-control)
  if [ "$F_CODE" != 200 ]; then row FAIL "$1" "HTTP $F_CODE sur $2"
  elif printf '%s' "$_cc" | grep -q -E "$3"; then row PASS "$1" "$_cc"
  else row FAIL "$1" "obtenu « ${_cc:-(absent)} » ; attendu : $4"; fi
  return 0
}
chk_cache "cache CSS : revalidation, pas de cache long" "$BASE/style.min.css" 'max-age=0.*must-revalidate|must-revalidate.*max-age=0' "max-age=0, must-revalidate"
chk_cache "cache JS : revalidation, pas de cache long"  "$BASE/main.min.js"  'max-age=0.*must-revalidate|must-revalidate.*max-age=0' "max-age=0, must-revalidate"

_font=$(grep -o -E 'fonts/[^"'"'"') ]+\.woff2' "$T/pg1.b" | head -1); [ -n "$_font" ] && _font="/${_font#/}"
_img=$(grep -o -E 'images-optimized/[^"'"'"') ]+\.(webp|jpg)' "$T/pg1.b" | head -1); [ -n "$_img" ] && _img="/${_img#/}"
if [ -n "$_font" ]; then chk_cache "cache polices : 1 an, immutable" "$BASE$_font" 'max-age=31536000.*immutable' "max-age=31536000, immutable"
else row SKIP "cache polices" "aucune police trouvée dans l'accueil"; fi
if [ -n "$_img" ]; then chk_cache "cache images : 1 an, immutable" "$BASE$_img" 'max-age=31536000.*immutable' "max-age=31536000, immutable"
else row SKIP "cache images" "aucune image trouvée dans l'accueil"; fi

if [ -n "$PDF_PATH" ]; then
  fetchh "$BASE$PDF_PATH" pdf
  _xr=$(hget "$T/pdf.h" x-robots-tag | lc)
  if [ "$F_CODE" != 200 ]; then row FAIL "X-Robots-Tag: noindex sur /docs/" "PDF introuvable : HTTP $F_CODE sur $PDF_PATH"
  else
    case "$_xr" in
      *noindex*) row PASS "X-Robots-Tag: noindex sur /docs/" "$_xr" ;;
      *)         row FAIL "X-Robots-Tag: noindex sur /docs/" "obtenu « ${_xr:-(absent)} » : le PDF reste indexable" ;;
    esac
  fi
elif [ "$LOCAL" = 1 ]; then
  row SKIP "plaquette PDF non déployée" "non applicable avec le serveur local (il ignore .assetsignore)"
else
  fetchh "$BASE/docs/plaquette-clos-des-zinnias.pdf" pdf
  case "$F_CODE" in
    404) row PASS "plaquette PDF non déployée" "HTTP 404 sur /docs/plaquette-clos-des-zinnias.pdf (dossier docs dans .assetsignore)" ;;
    302|301|307|308)
      case "$F_LOC" in
        */contact*) row PASS "plaquette PDF non déployée" "HTTP $F_CODE vers /contact (_redirects : ancien lien imprimé redirigé)" ;;
        *)          row WARN "plaquette PDF non déployée" "redirigée vers « $F_LOC » (attendu : /contact)" ;;
      esac ;;
    200) row FAIL "plaquette PDF non déployée" "le PDF (ancienne marque) est encore servi : vérifier .assetsignore (ligne « docs »)" ;;
    *)   row WARN "plaquette PDF non déployée" "réponse inattendue : HTTP $F_CODE" ;;
  esac
fi

# ================================================================ F. DNS
section "F. DNS et courrier"
if [ "$LOCAL" = 1 ] || [ "$DNSCHECK" != 1 ]; then
  row SKIP "DNS" "ignoré (mode local ou DNSCHECK=0)"
elif ! command -v dig >/dev/null 2>&1; then
  row SKIP "DNS" "dig absent"
else
  _ns=$(dig +short NS "$NEW" 2>/dev/null | tr '\n' ' ' | lc)
  case "$_ns" in *ns.cloudflare.com*) row PASS "NS de NEW chez Cloudflare" "$_ns" ;; *) row WARN "NS de NEW chez Cloudflare" "obtenu « ${_ns:-(aucun)} »" ;; esac
  _mx=$(dig +short MX "$NEW" 2>/dev/null | tr '\n' ' ' | lc)
  case "$_mx" in
    *"$MX_EXPECT"*) row PASS "MX de NEW toujours présents (courrier)" "$_mx" ;;
    *) row FAIL "MX de NEW toujours présents (courrier)" "obtenu « ${_mx:-(aucun)} » ; attendu un MX contenant $MX_EXPECT. Courrier en danger : rétablir les MX" ;;
  esac
  _spf=$(dig +short TXT "$NEW" 2>/dev/null | grep -i 'v=spf1' | tr '\n' ' ' | lc)
  case "$_spf" in
    *"$SPF_EXPECT"*) row PASS "SPF de NEW toujours présent (courrier)" "$_spf" ;;
    *) row FAIL "SPF de NEW toujours présent (courrier)" "obtenu « ${_spf:-(aucun)} » ; attendu $SPF_EXPECT" ;;
  esac
  _www=$(dig +short "www.$NEW" 2>/dev/null | head -1)
  if [ -n "$_www" ]; then row PASS "www.NEW existe dans le DNS" "$_www"
  else row FAIL "www.NEW existe dans le DNS" "aucun enregistrement : créer www (proxifié) pour que la redirection fonctionne"; fi
  if [ -n "$OLD" ]; then
    _ov=$(dig +short TXT "$OLD" 2>/dev/null | grep -i 'google-site-verification' | head -1)
    if [ -n "$_ov" ]; then row PASS "OLD : jeton google-site-verification conservé" "présent (ne pas le supprimer)"
    else row WARN "OLD : jeton google-site-verification conservé" "absent : la propriété Search Console de OLD risque de perdre sa validation"; fi
    _owww=$(dig +short "www.$OLD" 2>/dev/null | head -1)
    if [ -n "$_owww" ]; then row PASS "www.OLD existe dans le DNS" "$_owww"
    else row WARN "www.OLD existe dans le DNS" "aucun enregistrement : https://www.$OLD/ ne répond pas"; fi
  fi
fi

if [ "$WHOIS" = 1 ] && [ "$LOCAL" = 0 ]; then
  section "G. Échéances des noms de domaine (WHOIS AFNIC)"
  if ! command -v whois >/dev/null 2>&1; then row SKIP "échéances" "whois absent"
  else
    for _d in $OLD $NEW; do
      _e=$(whois -h whois.nic.fr "$_d" 2>/dev/null | grep -i '^Expiry Date:' | head -1 | sed -E 's/^[^:]*:[[:space:]]*//' | cut -c1-10)
      if [ -z "$_e" ]; then row WARN "échéance $_d" "illisible (WHOIS indisponible ?)"
      elif [ "$PYOK" = 1 ]; then
        _days=$(python3 -c 'import sys,datetime; print((datetime.date.fromisoformat(sys.argv[1])-datetime.date.today()).days)' "$_e" 2>/dev/null)
        if [ -n "$_days" ] && [ "$_days" -lt 90 ]; then row WARN "échéance $_d" "$_e (dans $_days jours : RENOUVELER)"
        else row PASS "échéance $_d" "$_e (dans ${_days:-?} jours)"; fi
      else row INFO "échéance $_d" "$_e"; fi
    done
  fi
fi

# ================================================================ H. LIENS EXTERNES SENSIBLES
section "H. Liens externes cités par le blog (certificat TLS valide)"
# Le site de la mairie de Gardanne avait un certificat expiré le 04/10/2026 (6 liens du blog en dépendent). Ce contrôle ne
# bloque jamais (WARN seulement) : le blog reste en ligne, mais le lien affiche une alerte de sécurité aux lecteurs.
EXT_LINKS=${EXT_LINKS:-"https://www.ville-gardanne.fr/vivre-a-gardanne/urbanisme/plan-local-durbanisme/ https://www.ville-gardanne.fr/vivre-a-gardanne/urbanisme/depot-des-demandes-durbanisme-en-ligne/"}
for _u in $EXT_LINKS; do
  _code=$(curlx -I -o /dev/null -w '%{http_code}' "$_u" 2>"$T/ext.err"); _rc=$?
  _short=${_u#https://}
  if [ "$_rc" -eq 0 ] && [ "$_code" -ge 200 ] && [ "$_code" -lt 400 ]; then
    row PASS "lien externe : $_short" "HTTP $_code, certificat valide"
  elif [ "$_rc" -eq 60 ] || [ "$_rc" -eq 35 ] || [ "$_rc" -eq 51 ] || [ "$_rc" -eq 58 ] || [ "$_rc" -eq 83 ]; then
    row WARN "lien externe : $_short" "certificat TLS invalide ou expiré (curl $_rc) : les lecteurs voient une alerte. Reprendre l'adresse à la source ou la remplacer par une page officielle équivalente"
  elif [ "$_rc" -ne 0 ]; then
    row WARN "lien externe : $_short" "injoignable depuis ici (curl $_rc : $(head -c 90 "$T/ext.err" | tr '\n' ' '))"
  else
    row WARN "lien externe : $_short" "réponse HTTP $_code (certificat valide) : à regarder à la main"
  fi
done

# ================================================================ BILAN
printf '\n%sBilan%s : %s%d PASS%s, %s%d FAIL%s, %s%d WARN%s, %d SKIP\n' "$C_B" "$C_0" "$C_G" "$NPASS" "$C_0" "$C_R" "$NFAIL" "$C_0" "$C_Y" "$NWARN" "$C_0" "$NSKIP"
if [ "$NFAIL" -eq 0 ]; then
  printf 'Aucun FAIL : la migration est conforme à ce que ce script sait contrôler.\n'
  exit 0
else
  printf "Au moins un FAIL : corriger puis relancer. Les FAIL de la section A signifient que la redirection de OLD vers NEW n'est pas (encore) en place.\n"
  exit 1
fi
