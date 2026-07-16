/* ============================================================
   LE CLOS DES ZINNIAS — animations.js
   Reveal on scroll · Parallax · Compteurs animés
   Chargé en defer, autonome.
   ============================================================ */
(function () {
  "use strict";

  const isTouch = window.matchMedia("(pointer: coarse)").matches;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ----------------------------------------------------------
     REVEAL ON SCROLL (IntersectionObserver, staggered)
     ---------------------------------------------------------- */
  function initReveal() {
    const SEL = ".reveal, .reveal-left, .reveal-right, .reveal-img";
    const els = [...document.querySelectorAll(SEL)];
    if (reduceMotion) {
      els.forEach((el) => el.classList.add("in"));
      return;
    }

    // auto-stagger des groupes [data-stagger] — calculé avant l'observation
    document.querySelectorAll("[data-stagger]").forEach((group) => {
      const kids = group.querySelectorAll(SEL);
      kids.forEach((k, i) => { if (!k.dataset.delay) k.dataset.delay = i * 90; });
    });

    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const delay = el.dataset.delay ? parseInt(el.dataset.delay, 10) : 0;
          setTimeout(() => el.classList.add("in"), delay);
          io.unobserve(el);
        }
      });
    }, { threshold: 0, rootMargin: "400px 0px 400px 0px" });

    els.forEach((el) => io.observe(el));

    // Filet de sécurité : un scroll très rapide (molette/trackpad flingué,
    // clic sur la piste de la scrollbar) peut faire passer un élément par la
    // zone d'observation entre deux frames sans déclencher l'IntersectionObserver.
    // On force la révélation de tout ce qui reste au repos après le scroll.
    let idleTimer;
    window.addEventListener("scroll", () => {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        // révèle tout ce qui a été atteint ou dépassé par le scroll,
        // pas seulement ce qui est actuellement dans le viewport.
        // Batch : toutes les lectures de layout d'abord, puis les écritures.
        const vh = window.innerHeight;
        const pending = [...document.querySelectorAll(SEL + ":not(.in)")]
          .filter((el) => el.getBoundingClientRect().top < vh);
        pending.forEach((el) => el.classList.add("in"));
      }, 250);
    }, { passive: true });
  }

  /* ----------------------------------------------------------
     PARALLAX ([data-parallax] with data-speed)
     ---------------------------------------------------------- */
  function initParallax() {
    if (reduceMotion || isTouch) return;
    const els = Array.from(document.querySelectorAll("[data-parallax]"));
    if (!els.length) return;

    // Positions de layout mises en cache (recalculées au resize) : évite de
    // lire getBoundingClientRect à chaque frame de scroll (reflow forcé).
    let items = [];
    let firstMeasure = true;
    function measure() {
      const y = window.scrollY;
      const vh = window.innerHeight;
      items = els.map((el) => {
        const rect = el.getBoundingClientRect();
        // soustrait le translateY déjà appliqué pour retrouver la position d'origine
        const applied = el._plxY || 0;
        const top = rect.top + y - applied;
        const it = {
          el,
          top,
          height: rect.height,
          speed: parseFloat(el.dataset.speed || "0.5"),
          zero: el._plxZero || 0,
        };
        // Élément visible au chargement (typiquement le hero) : le parallax
        // démarre à zéro — aucun transform appliqué au premier rendu, donc
        // aucun décalage compté au CLS. Le mouvement reste identique au scroll.
        if (firstMeasure) {
          const vTop = top - y;
          if (vTop < vh && vTop + rect.height > 0) {
            it.zero = vTop + rect.height / 2 - vh / 2;
          }
          el._plxZero = it.zero;
        }
        return it;
      });
      firstMeasure = false;
    }

    let ticking = false;
    function update() {
      const vh = window.innerHeight;
      const y = window.scrollY;
      items.forEach((it) => {
        const top = it.top - y; // position viewport, sans lecture du DOM
        if (top + it.height < -200 || top > vh + 200) return;
        // distance of element center from viewport center
        const offset = top + it.height / 2 - vh / 2;
        const ty = (offset - it.zero) * it.speed * -0.18;
        it.el._plxY = ty;
        it.el.style.transform = `translateY(${ty}px)`;
      });
      ticking = false;
    }
    window.addEventListener("scroll", () => {
      if (!ticking) { requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    window.addEventListener("resize", () => { measure(); update(); });
    measure();
    update();
  }

  /* ----------------------------------------------------------
     ANIMATED COUNTERS ([data-count], easeOutExpo)
     ---------------------------------------------------------- */
  function initCounters() {
    const els = document.querySelectorAll("[data-count]");
    if (!els.length) return;

    const easeOutExpo = (t) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));

    function run(el) {
      const target = parseFloat(el.dataset.count);
      const decimals = (el.dataset.count.split(".")[1] || "").length;
      const duration = 2000;
      const start = performance.now();
      function frame(now) {
        const p = Math.min((now - start) / duration, 1);
        const val = target * easeOutExpo(p);
        el.textContent = formatNum(val, decimals);
        if (p < 1) requestAnimationFrame(frame);
        else el.textContent = formatNum(target, decimals);
      }
      requestAnimationFrame(frame);
    }

    function formatNum(n, decimals) {
      const fixed = n.toFixed(decimals);
      const parts = fixed.split(".");
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " "); // thin space
      return parts.join(",");
    }

    if (reduceMotion) {
      els.forEach((el) => {
        const decimals = (el.dataset.count.split(".")[1] || "").length;
        el.textContent = formatNum(parseFloat(el.dataset.count), decimals);
      });
      return;
    }

    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { run(entry.target); io.unobserve(entry.target); }
      });
    }, { threshold: 0.5 });
    els.forEach((el) => io.observe(el));
  }

  /* ---------- INIT ---------- */
  function init() {
    initReveal();
    initParallax();
    initCounters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
