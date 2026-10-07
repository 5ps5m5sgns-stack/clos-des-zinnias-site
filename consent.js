/* ============================================================
   LE CLOS DES CYPRÈS — consent.js
   Bandeau de consentement (CNIL) + Meta Pixel conditionnel.
   Le Pixel ne se charge JAMAIS avant un consentement explicite.
   Tant qu'aucun Pixel n'est configuré (PIXEL_ID ci-dessous), le site n'utilise
   AUCUN traceur : le bandeau n'est PAS affiché et le lien « Cookies » du pied
   de page est retiré. Dès qu'un identifiant valide est renseigné, le bandeau
   et le lien réapparaissent d'eux-mêmes (rien d'autre à modifier dans les pages).
   ============================================================ */
(function () {
  "use strict";

  /* ⚠️ CONFIGURATION — remplacer par l'ID du Pixel Meta
     (Gestionnaire d'événements Meta → Sources de données).
     Valeur valide = uniquement des chiffres (6 au moins). Toute autre valeur =
     pas de Pixel : ni bandeau, ni traceur. Si vous activez le Pixel, vérifiez que
     la politique de confidentialité et le registre des traitements sont à jour. */
  var PIXEL_ID = "REMPLACER_PAR_PIXEL_ID";

  function pixelConfigured() { return /^\d{6,}$/.test(PIXEL_ID); }

  var KEY = "cypres-consent";
  var TTL = 180 * 24 * 3600 * 1000; // le choix expire après 6 mois (recommandation CNIL)

  function readChoice() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return null;
      var c = JSON.parse(raw);
      if (!c.t || Date.now() - c.t > TTL) { localStorage.removeItem(KEY); return null; }
      return c.v === "granted" || c.v === "denied" ? c.v : null;
    } catch (e) { return null; }
  }

  function saveChoice(v) {
    try { localStorage.setItem(KEY, JSON.stringify({ v: v, t: Date.now() })); } catch (e) {}
  }

  /* ----------------------------------------------------------
     META PIXEL — chargé uniquement après consentement.
     ---------------------------------------------------------- */
  var pixelLoaded = false;
  function loadPixel() {
    if (pixelLoaded || !pixelConfigured()) return;   // sans ID valide : aucun traceur, jamais
    pixelLoaded = true;

    /* Snippet officiel Meta Pixel */
    !(function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0";
      n.queue = []; t = b.createElement(e); t.async = !0; t.src = v;
      s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    })(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");

    window.fbq("init", PIXEL_ID);
    window.fbq("track", "PageView");

    // Conversion : l'arrivée sur la page de remerciement signifie qu'un formulaire a été envoyé.
    // URL propre « /merci » ; « /merci/ » et l'ancienne forme « /merci.html » restent acceptées.
    if (/(^|\/)merci(\.html)?\/?$/i.test(location.pathname)) {
      window.fbq("track", "Lead");
    }

    // Intention forte : clic sur un lien téléphone.
    document.querySelectorAll('a[href^="tel:"], a[href*="wa.me/"]').forEach(function (a) {
      a.addEventListener("click", function () { window.fbq("track", "Contact"); });
    });
  }

  /* ----------------------------------------------------------
     BANDEAU — accepter et refuser avec la même facilité (CNIL).
     ---------------------------------------------------------- */
  var banner = null;
  function showBanner() {
    if (banner) { banner.removeAttribute("inert"); banner.classList.add("show"); return; }
    banner = document.createElement("div");
    banner.className = "consent-banner";
    banner.setAttribute("role", "region");
    banner.setAttribute("aria-label", "Gestion des cookies");
    banner.innerHTML =
      '<p class="consent-banner__txt">Avec votre accord, nous utilisons le <strong>Pixel Meta</strong> pour mesurer l\'efficacité de nos annonces et en optimiser la diffusion. La carte Google Maps de la page L\'Environnement ne se charge qu\'à votre demande. Aucun autre traceur n\'est utilisé ; votre choix est simplement mémorisé dans votre navigateur. <a href="/confidentialite">En savoir plus</a></p>' +
      '<div class="consent-banner__btns">' +
      '<button type="button" class="btn btn-gold consent-accept">Accepter</button>' +
      '<button type="button" class="btn btn-outline-gold consent-deny">Refuser</button>' +
      "</div>";
    document.body.appendChild(banner);
    requestAnimationFrame(function () { banner.classList.add("show"); });

    banner.querySelector(".consent-accept").addEventListener("click", function () {
      saveChoice("granted"); hideBanner(); loadPixel();
    });
    banner.querySelector(".consent-deny").addEventListener("click", function () {
      saveChoice("denied"); hideBanner();
    });
  }
  function hideBanner() { if (banner) { banner.classList.remove("show"); banner.setAttribute("inert", ""); } }

  function init() {
    var links = document.querySelectorAll("[data-consent-open]");

    // Aucun Pixel configuré = aucun traceur : pas de bandeau, et le lien « Cookies » du pied
    // de page serait sans objet (il est retiré avec son séparateur « · »).
    if (!pixelConfigured()) {
      links.forEach(function (a) {
        var prev = a.previousSibling;
        if (prev && prev.nodeType === 3) prev.nodeValue = prev.nodeValue.replace(/\s*·\s*$/, " ");
        if (a.parentNode) a.parentNode.removeChild(a);
      });
      return;
    }

    // lien « Cookies » du pied de page : permet de retirer/changer son choix à tout moment
    links.forEach(function (a) {
      a.addEventListener("click", function (e) { e.preventDefault(); showBanner(); });
    });

    var choice = readChoice();
    if (choice === "granted") loadPixel();
    else if (choice === null) showBanner();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
