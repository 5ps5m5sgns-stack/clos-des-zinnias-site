/* ============================================================
   LE CLOS DES ZINNIAS — consent.js
   Bandeau de consentement (CNIL) + Meta Pixel conditionnel.
   Le Pixel ne se charge JAMAIS avant un consentement explicite.
   ============================================================ */
(function () {
  "use strict";

  /* ⚠️ CONFIGURATION — remplacer par l'ID du Pixel Meta
     (Gestionnaire d'événements Meta → Sources de données). */
  var PIXEL_ID = "REMPLACER_PAR_PIXEL_ID";

  var KEY = "zinnias-consent";
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
    if (pixelLoaded) return;
    if (!/^\d{6,}$/.test(PIXEL_ID)) {
      // ID non configuré : le consentement est enregistré mais aucun traceur n'est posé.
      console.info("[consent] Meta Pixel non configuré (PIXEL_ID placeholder) — aucun traceur chargé.");
      return;
    }
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

    // Conversion : l'arrivée sur merci.html signifie qu'un formulaire a été envoyé.
    if (/(^|\/)merci\.html/.test(location.pathname)) {
      window.fbq("track", "Lead");
    }

    // Intention forte : clic sur un lien téléphone.
    document.querySelectorAll('a[href^="tel:"]').forEach(function (a) {
      a.addEventListener("click", function () { window.fbq("track", "Contact"); });
    });
  }

  /* ----------------------------------------------------------
     BANDEAU — accepter et refuser avec la même facilité (CNIL).
     ---------------------------------------------------------- */
  var banner = null;
  function showBanner() {
    if (banner) { banner.classList.add("show"); return; }
    banner = document.createElement("div");
    banner.className = "consent-banner";
    banner.setAttribute("role", "region");
    banner.setAttribute("aria-label", "Gestion des cookies");
    banner.innerHTML =
      '<p class="consent-banner__txt">Avec votre accord, nous utilisons le <strong>Pixel Meta</strong> pour mesurer l\'efficacité de nos annonces. Aucun autre traceur n\'est utilisé. <a href="confidentialite.html">En savoir plus</a></p>' +
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
  function hideBanner() { if (banner) banner.classList.remove("show"); }

  function init() {
    // lien « Cookies » du pied de page : permet de retirer/changer son choix à tout moment
    document.querySelectorAll("[data-consent-open]").forEach(function (a) {
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
