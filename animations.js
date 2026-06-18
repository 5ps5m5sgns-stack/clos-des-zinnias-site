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
    }, { threshold: 0.12, rootMargin: "0px 0px -10% 0px" });

    els.forEach((el) => io.observe(el));
  }

  /* ----------------------------------------------------------
     PARALLAX ([data-parallax] with data-speed)
     ---------------------------------------------------------- */
  function initParallax() {
    if (reduceMotion || isTouch) return;
    const items = Array.from(document.querySelectorAll("[data-parallax]"));
    if (!items.length) return;

    let ticking = false;
    function update() {
      const vh = window.innerHeight;
      items.forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.bottom < -200 || rect.top > vh + 200) return;
        const speed = parseFloat(el.dataset.speed || "0.5");
        // distance of element center from viewport center
        const offset = (rect.top + rect.height / 2 - vh / 2);
        el.style.transform = `translateY(${offset * speed * -0.18}px)`;
      });
      ticking = false;
    }
    window.addEventListener("scroll", () => {
      if (!ticking) { requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    window.addEventListener("resize", update);
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
