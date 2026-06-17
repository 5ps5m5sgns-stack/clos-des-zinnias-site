/* ============================================================
   LE CLOS DES ZINNIAS — main.js
   Navigation · Navbar scroll · Page transitions · Lightbox
   Accordion · Ripple · Form · Active link
   ============================================================ */
(function () {
  "use strict";

  /* ----------------------------------------------------------
     NAVBAR — scroll behaviour (threshold 80px)
     ---------------------------------------------------------- */
  function initNavbar() {
    const nav = document.querySelector(".nav");
    if (!nav) return;
    const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 80);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
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
    document.querySelectorAll('a[href]').forEach((a) => {
      const href = a.getAttribute("href");
      if (!href) return;
      const isInternal =
        /\.html$/.test(href) &&
        !a.target &&
        !href.startsWith("http") &&
        !a.hasAttribute("data-no-transition");
      if (!isInternal) return;

      a.addEventListener("click", (e) => {
        // allow same-page anchors and modifier clicks
        if (e.metaKey || e.ctrlKey || e.shiftKey) return;
        e.preventDefault();
        document.body.classList.add("page-leaving");
        setTimeout(() => { window.location.href = href; }, 300);
      });
    });
  }

  /* ----------------------------------------------------------
     SMOOTH ANCHOR SCROLL
     ---------------------------------------------------------- */
  function initSmoothAnchors() {
    document.querySelectorAll('a[href^="#"]').forEach((a) => {
      a.addEventListener("click", (e) => {
        const id = a.getAttribute("href");
        if (id === "#" || id.length < 2) return;
        const target = document.querySelector(id);
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  /* ----------------------------------------------------------
     RIPPLE on buttons
     ---------------------------------------------------------- */
  function initRipple() {
    document.querySelectorAll(".btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const circle = document.createElement("span");
        const d = Math.max(btn.clientWidth, btn.clientHeight);
        const rect = btn.getBoundingClientRect();
        circle.className = "ripple";
        circle.style.width = circle.style.height = d + "px";
        circle.style.left = e.clientX - rect.left - d / 2 + "px";
        circle.style.top = e.clientY - rect.top - d / 2 + "px";
        btn.appendChild(circle);
        setTimeout(() => circle.remove(), 600);
      });
    });
  }

  /* ----------------------------------------------------------
     ACCORDION
     ---------------------------------------------------------- */
  function initAccordion() {
    document.querySelectorAll(".acc-head").forEach((head) => {
      head.addEventListener("click", () => {
        const item = head.closest(".acc-item");
        const body = item.querySelector(".acc-body");
        const open = item.classList.toggle("open");
        body.style.maxHeight = open ? body.scrollHeight + "px" : "0";
      });
    });
    window.addEventListener("resize", () => {
      document.querySelectorAll(".acc-item.open .acc-body").forEach((body) => {
        body.style.maxHeight = body.scrollHeight + "px";
      });
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
    box.innerHTML = `
      <button class="lightbox__close" aria-label="Fermer">&times;</button>
      <button class="lightbox__nav lightbox__nav--prev" aria-label="Précédent">&#8249;</button>
      <img alt="">
      <button class="lightbox__nav lightbox__nav--next" aria-label="Suivant">&#8250;</button>
      <div class="lightbox__cap"></div>`;
    document.body.appendChild(box);

    const imgEl = box.querySelector("img");
    const capEl = box.querySelector(".lightbox__cap");
    let idx = 0;

    function show(i) {
      idx = (i + items.length) % items.length;
      imgEl.src = items[idx].src;
      capEl.textContent = items[idx].cap;
    }
    function open(i) { show(i); box.classList.add("open"); document.body.style.overflow = "hidden"; }
    function close() { box.classList.remove("open"); document.body.style.overflow = ""; }

    triggers.forEach((t, i) =>
      t.addEventListener("click", (e) => { e.preventDefault(); open(i); })
    );
    box.querySelector(".lightbox__close").addEventListener("click", close);
    box.querySelector(".lightbox__nav--prev").addEventListener("click", () => show(idx - 1));
    box.querySelector(".lightbox__nav--next").addEventListener("click", () => show(idx + 1));
    box.addEventListener("click", (e) => { if (e.target === box) close(); });

    document.addEventListener("keydown", (e) => {
      if (!box.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(idx - 1);
      if (e.key === "ArrowRight") show(idx + 1);
    });

    // swipe
    let sx = 0;
    box.addEventListener("touchstart", (e) => { sx = e.touches[0].clientX; }, { passive: true });
    box.addEventListener("touchend", (e) => {
      const dx = e.changedTouches[0].clientX - sx;
      if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
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

      // Mode démo : tant que l'ID Formspree n'est pas renseigné, on affiche
      // simplement le message de succès (aucun envoi réel).
      if (!/formspree\.io\/f\/(?!xxxx)\w+/.test(action)) {
        showSuccess();
        return;
      }

      const original = btn ? btn.textContent : "";
      if (btn) { btn.textContent = "Envoi…"; btn.disabled = true; }
      try {
        const res = await fetch(action, {
          method: "POST",
          body: new FormData(form),
          headers: { Accept: "application/json" },
        });
        if (res.ok) {
          showSuccess();
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

  /* ---------- INIT ---------- */
  function init() {
    initNavbar();
    initBurger();
    initActiveLink();
    initSmoothAnchors();
    initRipple();
    initAccordion();
    initLightbox();
    initForm();
    initPageTransitions();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
