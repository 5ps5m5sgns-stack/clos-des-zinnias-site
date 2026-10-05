#!/usr/bin/env python3
"""Régénère les fichiers JavaScript minifiés du site (main, consent, animations).

Outil de développement : il n'est JAMAIS déployé ni chargé par le site.
Dépendance : rjsmin (voir tools/README.md, à installer dans un venv).

Usage (depuis la racine du dépôt) :
    python3 tools/minify.py                 # main.js et consent.js -> .min.js
    python3 tools/minify.py animations      # un fichier précis (main, consent, animations)
    python3 tools/minify.py --all           # les trois fichiers
    python3 tools/minify.py --check         # n'écrit rien : vérifie que les .min sont à jour

Garanties :
  - idempotent : deux exécutions de suite donnent exactement les mêmes octets ;
  - rjsmin ne retire que les espaces et les commentaires (pas de renommage de
    variables) ; le résultat est vérifié avant écriture (voir verify()) ;
  - le script n'écrit que <nom>.min.js : jamais le HTML, le CSS ni sitemap.xml.
"""
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = ["main", "consent"]
ALL = ["main", "consent", "animations"]

KEYWORDS_BEFORE_REGEX = {
    "return", "typeof", "case", "do", "else", "in", "of", "void", "delete",
    "throw", "new", "instanceof", "yield", "await",
}
PUNCT_BEFORE_REGEX = set("(,=:[!&|?{};+-*%<>~^")


def tokenize(src):
    """Découpe un source JS en jetons ('lit', texte) et ('code', texte).

    Les littéraux (chaînes, gabarits `...`, expressions régulières) sont gardés
    tels quels ; les commentaires sont supprimés. Sert uniquement à la vérification.
    """
    tokens, code = [], []
    i, n = 0, len(src)
    prev_sig = ""  # dernier caractère significatif rencontré (hors espaces)
    last_word = ""  # dernier mot (identifiant ou mot-clé) rencontré
    after_space = False

    def flush():
        if code:
            tokens.append(("code", "".join(code)))
            code.clear()

    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while src[j] != c:
                j += 2 if src[j] == "\\" else 1
            flush(); tokens.append(("lit", src[i:j + 1]))
            i, prev_sig, last_word, after_space = j + 1, c, "", False
        elif c == "`":
            j, depth = i + 1, 0
            while True:
                ch = src[j]
                if ch == "\\":
                    j += 2; continue
                if ch == "`" and depth == 0:
                    break
                if ch == "$" and src[j + 1] == "{":
                    depth += 1; j += 2; continue
                if ch == "}" and depth > 0:
                    depth -= 1
                j += 1
            flush(); tokens.append(("lit", src[i:j + 1]))
            i, prev_sig, last_word, after_space = j + 1, "`", "", False
        elif c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and src.startswith("/*", i):
            i = src.index("*/", i + 2) + 2
            code.append(" ")
            after_space = True
        elif c == "/" and (prev_sig == "" or prev_sig in PUNCT_BEFORE_REGEX
                           or last_word in KEYWORDS_BEFORE_REGEX):
            j, in_class = i + 1, False
            while True:
                ch = src[j]
                if ch == "\\":
                    j += 2; continue
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    break
                j += 1
            j += 1
            while j < n and src[j].isalpha():
                j += 1
            flush(); tokens.append(("lit", src[i:j]))
            i, prev_sig, last_word, after_space = j, ")", "", False
        else:
            code.append(c)
            if c.isspace():
                after_space = True
            else:
                prev_sig = c
                if c.isalnum() or c in "_$":
                    last_word = ("" if after_space else last_word) + c
                else:
                    last_word = ""
                after_space = False
            i += 1
    flush()
    return tokens


def skeleton(src):
    toks = tokenize(src)
    lits = [t for k, t in toks if k == "lit"]
    code = "".join(re.sub(r"\s+", "", t) if k == "code" else "\0" for k, t in toks)
    return lits, code


def js_syntax_ok(path):
    """Test de syntaxe avec JavaScriptCore (macOS) ; None si indisponible."""
    if not os.path.exists("/usr/bin/osascript"):
        return None
    jxa = ("ObjC.import('Foundation');"
           "var p=$.NSProcessInfo.processInfo.environment.objectForKey('JSFILE').js;"
           "var s=$.NSString.stringWithContentsOfFileEncodingError(p,4,null).js;"
           "new Function(s);'ok'")
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", jxa],
                       env=dict(os.environ, JSFILE=path),
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "ok"


def verify(src, out):
    """Le .min ne doit différer de la source que par les espaces et les commentaires."""
    lits_a, code_a = skeleton(src)
    lits_b, code_b = skeleton(out)
    if lits_a != lits_b:
        return "littéraux (chaînes, gabarits, regex) modifiés"
    if code_a != code_b:
        return "le code diffère autrement que par les espaces/commentaires"
    return None


def main(argv):
    try:
        import rjsmin
    except ImportError:
        sys.exit("rjsmin manquant. Une fois : python3 -m venv ~/.venv-clos-min && "
                 "~/.venv-clos-min/bin/pip install rjsmin ; puis lancer ce script avec "
                 "~/.venv-clos-min/bin/python (voir tools/README.md)")
    args = [a for a in argv if not a.startswith("--")]
    check_only = "--check" in argv
    names = ALL if "--all" in argv else (args or DEFAULT)
    bad = [a for a in names if a not in ALL]
    if bad:
        sys.exit("fichier inconnu : %s (choix : %s)" % (", ".join(bad), ", ".join(ALL)))

    failed = False
    for name in names:
        src_path = os.path.join(ROOT, name + ".js")
        min_path = os.path.join(ROOT, name + ".min.js")
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
        out = rjsmin.jsmin(src).strip() + "\n"

        problem = verify(src, out)
        if problem:
            print("ECHEC  %s.js : %s" % (name, problem))
            failed = True
            continue
        current = None
        if os.path.exists(min_path):
            with open(min_path, encoding="utf-8") as f:
                current = f.read()

        if check_only:
            state = "à jour" if current == out else "PÉRIMÉ (relancer tools/minify.py)"
            if current != out:
                failed = True
            print("%-18s %s" % (name + ".min.js", state))
            continue

        if current == out:
            print("inchangé   %s.min.js (%d octets)" % (name, len(out.encode("utf-8"))))
        else:
            with open(min_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(out)
            print("écrit      %s.min.js (%d -> %d octets)"
                  % (name, len(src.encode("utf-8")), len(out.encode("utf-8"))))
        ok = js_syntax_ok(min_path)
        if ok is False:
            print("ECHEC  %s.min.js : erreur de syntaxe (JavaScriptCore)" % name)
            failed = True
        elif ok is None:
            print("           (test de syntaxe JavaScriptCore indisponible ici)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
