/* ============================================================
   LE CLOS DES ZINNIAS — main.js
   Navigation · Navbar auto-hide · Scroll progress · Page transitions
   Lightbox · Accordion · Flip tap · Form · Active link
   ============================================================ */
(function () {
  "use strict";

  /* ----------------------------------------------------------
     NAVBAR — scroll behaviour (threshold 80px)
     ---------------------------------------------------------- */
  function initNavbar() {
    const nav = document.querySelector(".nav");
    if (!nav) return;
    let last = window.scrollY;
    let ticking = false;

    function update() {
      const y = window.scrollY;
      nav.classList.toggle("scrolled", y > 80);

      // Auto-hide hospitality : masque au défilement descendant, révèle au remontant.
      // Jamais masqué près du haut, ni quand le menu mobile est ouvert.
      const menuOpen = document.body.classList.contains("menu-open");
      if (!menuOpen && y > 260 && y > last + 6) {
        nav.classList.add("nav--hidden");
      } else if (y < last - 6 || y < 260) {
        nav.classList.remove("nav--hidden");
      }
      last = y;
      ticking = false;
    }

    window.addEventListener("scroll", () => {
      if (!ticking) { requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    update();
  }

  /* ----------------------------------------------------------
     SCROLL PROGRESS — fine barre dorée de lecture
     ---------------------------------------------------------- */
  function initScrollProgress() {
    const bar = document.createElement("div");
    bar.className = "scroll-progress";
    document.body.appendChild(bar);
    let ticking = false;

    function update() {
      const h = document.documentElement;
      const max = h.scrollHeight - h.clientHeight;
      const p = max > 0 ? h.scrollTop / max : 0;
      bar.style.transform = `scaleX(${p})`;
      bar.classList.toggle("visible", h.scrollTop > 120);
      ticking = false;
    }
    window.addEventListener("scroll", () => {
      if (!ticking) { requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    update();
  }

  /* ----------------------------------------------------------
     MOBILE HAMBURGER MENU
     ---------------------------------------------------------- */
  function initBurger() {
    const burger = document.querySelector(".nav__burger");
    const menu = document.querySelector(".mobile-menu");
    if (!burger || !menu) return;

    const toggle = (open) => {
      const willOpen = open ?? !menu.classList.contains("open");
      menu.classList.toggle("open", willOpen);
      burger.classList.toggle("open", willOpen);
      burger.setAttribute("aria-expanded", willOpen ? "true" : "false"); // synchronise l'état a11y
      document.body.classList.toggle("menu-open", willOpen);
      document.body.style.overflow = willOpen ? "hidden" : "";
    };

    burger.addEventListener("click", () => toggle());
    menu.querySelectorAll("a").forEach((a) =>
      a.addEventListener("click", () => toggle(false))
    );
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") toggle(false);
    });
  }

  /* ----------------------------------------------------------
     ACTIVE LINK based on current page
     ---------------------------------------------------------- */
  function initActiveLink() {
    let page = location.pathname.split("/").pop();
    if (!page || page === "") page = "index.html";
    document.querySelectorAll(".nav__links a, .mobile-menu a").forEach((a) => {
      const href = a.getAttribute("href");
      if (href === page) a.classList.add("active");
    });
  }

  /* ----------------------------------------------------------
     PAGE TRANSITIONS (fade out → navigate)
     ---------------------------------------------------------- */
  function initPageTransitions() {
    // Pas de fondu de transition (ni de délai) si l'utilisateur préfère moins d'animation
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    // Un seul listener délégué pour toute la page (au lieu d'un par lien)
    document.addEventListener("click", (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;
      const a = e.target.closest("a[href]");
      if (!a || e.defaultPrevented) return;
      const href = a.getAttribute("href");
      const isInternal =
        href &&
        /\.html$/.test(href) &&
        !a.target &&
        !href.startsWith("http") &&
        !a.hasAttribute("data-no-transition");
      if (!isInternal) return;
      e.preventDefault();
      document.body.classList.add("page-leaving");
      setTimeout(() => { window.location.href = href; }, 150);
    });
  }

  /* ----------------------------------------------------------
     SMOOTH ANCHOR SCROLL
     ---------------------------------------------------------- */
  function initSmoothAnchors() {
    // Un seul listener délégué pour tous les liens d'ancre
    document.addEventListener("click", (e) => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const id = a.getAttribute("href");
      if (id === "#" || id.length < 2) return;
      let target = null;
      try { target = document.querySelector(id); } catch (_) { return; }
      if (!target) return;
      e.preventDefault();
      // Décalage de la hauteur de navbar pour ne pas masquer le titre de section
      const nav = document.querySelector(".nav");
      const offset = (nav ? nav.offsetHeight : 0) + 16;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: "smooth" });
    });
  }

  /* ----------------------------------------------------------
     FLIP CARDS — fallback tactile (pas de :hover au doigt)
     ---------------------------------------------------------- */
  function initFlipTap() {
    if (!window.matchMedia("(pointer: coarse)").matches) return;
    document.querySelectorAll(".flip").forEach((flip) => {
      flip.addEventListener("click", (e) => {
        // un lien sur la face arrière reste cliquable une fois retournée
        if (e.target.closest("a") && flip.classList.contains("is-flipped")) return;
        if (e.target.closest("a") && !flip.classList.contains("is-flipped")) {
          e.preventDefault();
        }
        flip.classList.toggle("is-flipped");
      });
    });
  }

  /* ----------------------------------------------------------
     ACCORDION
     ---------------------------------------------------------- */
  function initAccordion() {
    document.querySelectorAll(".acc-head").forEach((head) => {
      // état initial annoncé aux lecteurs d'écran
      if (!head.hasAttribute("aria-expanded")) head.setAttribute("aria-expanded", "false");
      head.addEventListener("click", () => {
        const item = head.closest(".acc-item");
        const body = item.querySelector(".acc-body");
        const open = item.classList.toggle("open");
        body.style.maxHeight = open ? body.scrollHeight + "px" : "0";
        head.setAttribute("aria-expanded", open ? "true" : "false"); // synchronise l'état a11y
      });
    });
    window.addEventListener("resize", () => {
      // Batch : toutes les lectures de layout d'abord, puis toutes les écritures
      const bodies = [...document.querySelectorAll(".acc-item.open .acc-body")];
      const heights = bodies.map((body) => body.scrollHeight);
      bodies.forEach((body, i) => { body.style.maxHeight = heights[i] + "px"; });
    });
  }

  /* ----------------------------------------------------------
     LIGHTBOX (gallery) — keyboard, arrows, swipe
     ---------------------------------------------------------- */
  function initLightbox() {
    const triggers = Array.from(document.querySelectorAll("[data-lightbox]"));
    if (!triggers.length) return;

    const items = triggers.map((t) => ({
      src: t.getAttribute("data-lightbox"),
      cap: t.getAttribute("data-caption") || "",
    }));

    const box = document.createElement("div");
    box.className = "lightbox";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Visionneuse d'images");
    let lastFocused = null;
    const multiple = items.length > 1;
    box.innerHTML = `
      <button class="lightbox__close" aria-label="Fermer">&times;</button>
      ${multiple ? '<div class="lightbox__count"></div>' : ""}
      ${multiple ? '<button class="lightbox__nav lightbox__nav--prev" aria-label="Précédent">&#8249;</button>' : ""}
      <img alt="">
      ${multiple ? '<button class="lightbox__nav lightbox__nav--next" aria-label="Suivant">&#8250;</button>' : ""}
      <div class="lightbox__hint">Cliquez pour zoomer · glissez pour déplacer</div>
      <div class="lightbox__cap"></div>`;
    document.body.appendChild(box);

    const imgEl = box.querySelector("img");
    const capEl = box.querySelector(".lightbox__cap");
    const countEl = box.querySelector(".lightbox__count");
    let idx = 0;

    /* ----- ZOOM / PAN / PINCH (molette, clic, double-tap, pincée) ----- */
    let s = 1, tx = 0, ty = 0;
    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
    const cx = () => window.innerWidth / 2;
    const cy = () => window.innerHeight / 2;
    function applyZoom() {
      imgEl.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
      imgEl.classList.toggle("is-zoomed", s > 1);
      box.classList.toggle("zoomed", s > 1);
    }
    function resetZoom() {
      s = 1; tx = 0; ty = 0;
      imgEl.classList.remove("panning");
      applyZoom();
    }
    function zoomAt(clientX, clientY, ns) {
      ns = clamp(ns, 1, 5);
      const ux = clientX - cx(), uy = clientY - cy();
      tx = ux - (ns / s) * (ux - tx);
      ty = uy - (ns / s) * (uy - ty);
      s = ns;
      if (s === 1) { tx = 0; ty = 0; }
      applyZoom();
    }

    imgEl.addEventListener("wheel", (e) => {
      e.preventDefault();
      zoomAt(e.clientX, e.clientY, s * (e.deltaY < 0 ? 1.22 : 1 / 1.22));
    }, { passive: false });
    imgEl.addEventListener("click", (e) => e.stopPropagation());

    const pointers = new Map();
    let panStart = null, startTx = 0, startTy = 0, moved = 0, pinchDist = 0, pinchS = 1;
    const dist = (a, b) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);

    imgEl.addEventListener("pointerdown", (e) => {
      imgEl.setPointerCapture(e.pointerId);
      pointers.set(e.pointerId, e);
      moved = 0;
      if (pointers.size === 1) {
        panStart = { x: e.clientX, y: e.clientY, dx: 0 };
        startTx = tx; startTy = ty;
        if (s > 1) imgEl.classList.add("panning");
      } else if (pointers.size === 2) {
        const p = [...pointers.values()];
        pinchDist = dist(p[0], p[1]); pinchS = s;
        imgEl.classList.add("panning");
      }
    });
    imgEl.addEventListener("pointermove", (e) => {
      if (!pointers.has(e.pointerId)) return;
      pointers.set(e.pointerId, e);
      if (pointers.size === 2) {
        const p = [...pointers.values()];
        const mid = { x: (p[0].clientX + p[1].clientX) / 2, y: (p[0].clientY + p[1].clientY) / 2 };
        const d = dist(p[0], p[1]);
        if (pinchDist) zoomAt(mid.x, mid.y, pinchS * (d / pinchDist));
        moved = 999;
      } else if (pointers.size === 1 && panStart) {
        const dx = e.clientX - panStart.x, dy = e.clientY - panStart.y;
        moved = Math.hypot(dx, dy);
        panStart.dx = dx;
        if (s > 1) { tx = startTx + dx; ty = startTy + dy; applyZoom(); }
      }
    });
    function endPointer(e) {
      const wasSingle = pointers.size === 1;
      const dx = panStart ? panStart.dx : 0;
      pointers.delete(e.pointerId);
      if (pointers.size < 2) pinchDist = 0;
      if (pointers.size === 0) imgEl.classList.remove("panning");
      if (wasSingle && panStart) {
        if (s === 1) {
          if (multiple && Math.abs(dx) > 50) { show(idx + (dx < 0 ? 1 : -1)); }
          else if (moved < 10) { zoomAt(e.clientX, e.clientY, 2.5); }
        } else if (moved < 10) {
          resetZoom();
        }
      }
      panStart = null;
    }
    imgEl.addEventListener("pointerup", endPointer);
    imgEl.addEventListener("pointercancel", endPointer);

    const pad = (n) => String(n).padStart(2, "0");

    // Précharge une image voisine pour une navigation fluide
    function preload(i) {
      const it = items[(i + items.length) % items.length];
      if (it) { const im = new Image(); im.src = it.src; }
    }

    function show(i) {
      idx = (i + items.length) % items.length;
      imgEl.src = items[idx].src;
      imgEl.alt = items[idx].cap;
      capEl.textContent = items[idx].cap;
      if (countEl) countEl.innerHTML = `<b>${pad(idx + 1)}</b> / ${pad(items.length)}`;
      resetZoom();
      preload(idx + 1);
      preload(idx - 1);
    }
    function open(i) {
      lastFocused = document.activeElement;
      show(i);
      box.classList.add("open");
      document.body.style.overflow = "hidden";
      // déplace le focus dans la visionneuse (accessibilité clavier)
      box.querySelector(".lightbox__close").focus();
    }
    function close() {
      box.classList.remove("open");
      document.body.style.overflow = "";
      // rend le focus à l'élément qui a ouvert la visionneuse
      if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus();
    }

    triggers.forEach((t, i) => {
      t.addEventListener("click", (e) => { e.preventDefault(); open(i); });
      // déclencheurs non natifs (role="button") : activation clavier Entrée / Espace
      t.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(i); }
      });
    });
    box.querySelector(".lightbox__close").addEventListener("click", close);
    box.querySelector(".lightbox__nav--prev")?.addEventListener("click", () => show(idx - 1));
    box.querySelector(".lightbox__nav--next")?.addEventListener("click", () => show(idx + 1));
    box.addEventListener("click", (e) => { if (e.target === box) close(); });

    document.addEventListener("keydown", (e) => {
      if (!box.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(idx - 1);
      if (e.key === "ArrowRight") show(idx + 1);
      // piège à focus : Tab/Shift+Tab bouclent à l'intérieur de la visionneuse
      if (e.key === "Tab") {
        const f = [...box.querySelectorAll("button")].filter((b) => b.offsetParent !== null);
        if (!f.length) return;
        const first = f[0], lastEl = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastEl.focus(); }
        else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); first.focus(); }
      }
    });

  }

  /* ----------------------------------------------------------
     PRÉ-REMPLISSAGE DU LOT (deep-link ?lot=N)
     Les liens « Être recontacté(e) — lot N » arrivent sur le
     formulaire avec le bon lot déjà présélectionné.
     ---------------------------------------------------------- */
  function initLotPrefill() {
    const lot = new URLSearchParams(location.search).get("lot");
    if (!lot) return;
    const select = document.querySelector("#lot");
    if (select && [...select.options].some((o) => o.value === lot)) select.value = lot;
    const objet = document.querySelector("#objet");
    if (objet && [...objet.options].some((o) => o.value === "reservation")) objet.value = "reservation";
    const msg = document.querySelector("#message");
    if (msg && !msg.value) {
      msg.value = `Bonjour, je souhaite en savoir plus sur le lot ${lot} du Clos des Zinnias. Merci de me recontacter.`;
    }
  }

  /* ----------------------------------------------------------
     LOT COMPARISON TABLE — tri par surface / prix / prix·m²
     ---------------------------------------------------------- */
  function initLotSort() {
    const table = document.querySelector("[data-sortable]");
    if (!table) return;
    const tbody = table.querySelector("tbody");
    const btns = Array.from(document.querySelectorAll(".sort-btn[data-sort]"));
    if (!tbody || !btns.length) return;

    // Ordre d'origine, pour pouvoir revenir à l'état initial (3e clic)
    const original = Array.from(tbody.querySelectorAll("tr"));

    // Région live : annonce le changement de tri aux lecteurs d'écran
    let live = document.getElementById("sort-live");
    if (!live) {
      live = document.createElement("div");
      live.id = "sort-live";
      live.className = "lots-sr-only";
      live.setAttribute("aria-live", "polite");
      table.parentNode.insertBefore(live, table);
    }
    const sortLabels = { surface: "surface", price: "prix", ppm: "prix au mètre carré" };

    // état initial : aucun tri actif
    btns.forEach((b) => { if (!b.hasAttribute("aria-pressed")) b.setAttribute("aria-pressed", "false"); });

    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.sort; // surface | price | ppm
        const dir = btn.dataset.dir || "none";
        // cycle : none → asc → desc → none
        const next = dir === "none" ? "asc" : dir === "asc" ? "desc" : "none";

        // reset des autres boutons
        btns.forEach((b) => {
          b.classList.remove("active");
          b.dataset.dir = "none";
          b.setAttribute("aria-pressed", "false");
          const d = b.querySelector(".dir");
          if (d) d.textContent = "↕";
        });

        btn.dataset.dir = next;
        const arrow = btn.querySelector(".dir");

        let rows;
        if (next === "none") {
          rows = original;
          if (arrow) arrow.textContent = "↕";
        } else {
          btn.classList.add("active");
          btn.setAttribute("aria-pressed", "true");
          if (arrow) arrow.textContent = next === "asc" ? "↑" : "↓";
          rows = original.slice().sort((a, b) => {
            const va = parseFloat(a.dataset[key]) || 0;
            const vb = parseFloat(b.dataset[key]) || 0;
            return next === "asc" ? va - vb : vb - va;
          });
        }
        rows.forEach((r) => tbody.appendChild(r));

        // annonce a11y du nouvel ordre
        live.textContent = next === "none"
          ? "Tableau remis dans l'ordre d'origine."
          : `Tableau trié par ${sortLabels[key] || key} ${next === "asc" ? "croissant" : "décroissant"}.`;
      });
    });
  }

  /* ----------------------------------------------------------
     VALIDATION E-MAIL EN TEMPS RÉEL (feedback discret)
     Pose .is-valid / .is-invalid sur le .field parent et affiche
     un indice sous le champ. Ne « crie » qu'après le premier blur.
     ---------------------------------------------------------- */
  function initFieldValidation() {
    const email = document.querySelector("#email");
    if (!email) return;
    const field = email.closest(".field");
    if (!field) return;

    let hint = field.querySelector(".field__hint");
    if (!hint) {
      hint = document.createElement("span");
      hint.className = "field__hint";
      hint.setAttribute("aria-live", "polite");
      field.appendChild(hint);
    }

    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    let touched = false;

    function validate() {
      const v = email.value.trim();
      if (!v) {
        field.classList.remove("is-valid", "is-invalid");
        hint.textContent = "";
        return;
      }
      if (re.test(v)) {
        field.classList.add("is-valid");
        field.classList.remove("is-invalid");
        hint.textContent = "";
      } else {
        field.classList.add("is-invalid");
        field.classList.remove("is-valid");
        hint.textContent = "Format d'e-mail invalide — exemple : prenom@email.com";
      }
    }

    email.addEventListener("blur", () => { touched = true; validate(); });
    email.addEventListener("input", () => { if (touched) validate(); });
  }

  /* ----------------------------------------------------------
     FAÇADE GOOGLE MAPS — l'iframe (cookies tiers) n'est chargée
     qu'au clic de l'utilisateur (conformité CNIL).
     ---------------------------------------------------------- */
  function initMapFacade() {
    document.querySelectorAll(".map-facade").forEach((facade) => {
      const btn = facade.querySelector("[data-map-load]");
      if (!btn) return;
      btn.addEventListener("click", () => {
        const iframe = document.createElement("iframe");
        iframe.src = facade.dataset.mapSrc;
        iframe.title = facade.dataset.mapTitle || "Carte";
        iframe.setAttribute("referrerpolicy", "no-referrer-when-downgrade");
        facade.replaceWith(iframe);
      });
    });
  }

  /* ----------------------------------------------------------
     CONTACT FORM
     ---------------------------------------------------------- */
  function initForm() {
    const form = document.querySelector("#contact-form");
    if (!form) return;
    const success = form.querySelector(".form-success");
    const btn = form.querySelector('button[type="submit"]');

    function showSuccess() {
      if (success) success.classList.add("show");
      form.querySelectorAll("input, select, textarea").forEach((el) => {
        if (el.type !== "submit") el.disabled = true;
      });
      if (btn) { btn.textContent = "Message envoyé"; btn.disabled = true; }
      success?.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function showError(msg) {
      let errEl = form.querySelector(".form-error");
      if (!errEl) {
        errEl = document.createElement("div");
        errEl.className = "form-error";
        errEl.setAttribute("role", "alert"); // annonce immédiate aux lecteurs d'écran
        (success || form).after(errEl);
      }
      errEl.textContent = msg;
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }

      // Recopie l'email saisi dans _replyto (reply-to Formspree)
      const email = form.querySelector('[name="email"]');
      const replyto = form.querySelector('[name="_replyto"]');
      if (email && replyto) replyto.value = email.value;

      const action = form.getAttribute("action") || "";

      // Mode démo : tant que l'ID Formspree n'est pas renseigné, on simule
      // un court envoi (état « Envoi en cours… ») puis on affiche le succès.
      if (!/formspree\.io\/f\/(?!xxxx)\w+/.test(action)) {
        if (btn) { btn.textContent = "Envoi en cours…"; btn.disabled = true; }
        setTimeout(showSuccess, 750);
        return;
      }

      const original = btn ? btn.textContent : "";
      if (btn) { btn.textContent = "Envoi en cours…"; btn.disabled = true; }
      try {
        const res = await fetch(action, {
          method: "POST",
          body: new FormData(form),
          headers: { Accept: "application/json" },
        });
        if (res.ok) {
          // Redirige vers la page de remerciement : URL de conversion mesurable
          // (Pixel Lead, objectifs GA/Meta) et confirmation claire pour l'utilisateur.
          const lot = form.querySelector('[name="lot"]');
          const q = lot && lot.value && lot.value !== "tous" ? "?lot=" + encodeURIComponent(lot.value) : "";
          window.location.href = "merci.html" + q;
        } else {
          if (btn) { btn.textContent = original; btn.disabled = false; }
          showError("Une erreur est survenue lors de l'envoi. Merci de réessayer ou de nous appeler au 06 09 20 45 90.");
        }
      } catch (err) {
        if (btn) { btn.textContent = original; btn.disabled = false; }
        showError("Connexion impossible. Merci de réessayer ou de nous appeler au 06 09 20 45 90.");
      }
    });
  }

  /* ----------------------------------------------------------
     CONTACT INTENT CARDS — pré-remplit l'objet + défile au form
     ---------------------------------------------------------- */
  function initContactIntent() {
    const cards = document.querySelectorAll("[data-intent]");
    if (!cards.length) return;
    const select = document.querySelector("#objet");
    const form = document.querySelector("#contact-form");
    const firstField = document.querySelector("#prenom");

    cards.forEach((card) => {
      card.addEventListener("click", () => {
        const val = card.getAttribute("data-intent");
        cards.forEach((c) => c.classList.toggle("is-active", c === card));
        if (select && [...select.options].some((o) => o.value === val)) {
          select.value = val;
        }
        (form || document.body).scrollIntoView({ behavior: "smooth", block: "start" });
        setTimeout(() => firstField?.focus({ preventScroll: true }), 550);
      });
    });
  }

  /* ----------------------------------------------------------
     RETOUR EN HAUT — bouton discret qui apparaît au défilement
     Injecté dynamiquement (pas de markup dans les pages).
     ---------------------------------------------------------- */
  function initBackToTop() {
    const btn = document.createElement("button");
    btn.className = "to-top";
    btn.type = "button";
    btn.setAttribute("aria-label", "Revenir en haut de la page");
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    document.body.appendChild(btn);

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    btn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    });

    let ticking = false;
    function update() {
      btn.classList.toggle("visible", window.scrollY > 600);
      ticking = false;
    }
    window.addEventListener("scroll", () => {
      if (!ticking) { requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    update();
  }

  /* ---------- INIT ----------
     Deux phases pour réduire le Total Blocking Time :
     - immédiat : ce qui est visible/interactif dès le premier écran
     - différé (requestIdleCallback) : le reste, quand le thread est libre */
  function init() {
    initNavbar();
    initBurger();
    initActiveLink();
    initSmoothAnchors();
    initPageTransitions();

    const later = () => {
      initScrollProgress();
      initBackToTop();
      initFlipTap();
      initAccordion();
      initLightbox();
      initLotSort();
      initLotPrefill();
      initFieldValidation();
      initMapFacade();
      initForm();
      initContactIntent();
    };
    if ("requestIdleCallback" in window) {
      requestIdleCallback(later, { timeout: 1500 });
    } else {
      setTimeout(later, 200);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
