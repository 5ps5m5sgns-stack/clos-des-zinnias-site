/* ============================================================
   LE CLOS DES ZINNIAS — animations.js
   Cursor · Reveal on scroll · Parallax · Compteurs · Before/After
   Chargé en defer, autonome.
   ============================================================ */
(function () {
  "use strict";

  const isTouch = window.matchMedia("(pointer: coarse)").matches;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ----------------------------------------------------------
     1. CUSTOM CURSOR (dot + ring with lerp lag)
     ---------------------------------------------------------- */
  function initCursor() {
    if (isTouch) return;

    const dot = document.createElement("div");
    const ring = document.createElement("div");
    dot.className = "cursor-dot";
    ring.className = "cursor-ring";
    document.body.append(dot, ring);

    let mx = window.innerWidth / 2, my = window.innerHeight / 2;
    let rx = mx, ry = my;

    window.addEventListener("mousemove", (e) => {
      mx = e.clientX; my = e.clientY;
      dot.style.transform = `translate(${mx}px, ${my}px) translate(-50%, -50%)`;
    });

    function loop() {
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      ring.style.transform = `translate(${rx}px, ${ry}px) translate(-50%, -50%)`;
      requestAnimationFrame(loop);
    }
    loop();

    // hover targets
    const hoverSel = "a, button, .flip, .btn, [data-cursor='hover']";
    const imgSel = "img, .masonry__item, .figure, .split__media, .img-hover";

    document.addEventListener("mouseover", (e) => {
      if (e.target.closest(hoverSel)) ring.classList.add("is-hover");
      else if (e.target.closest(imgSel)) ring.classList.add("is-image");
    });
    document.addEventListener("mouseout", (e) => {
      if (e.target.closest(hoverSel)) ring.classList.remove("is-hover");
      if (e.target.closest(imgSel)) ring.classList.remove("is-image");
    });

    document.addEventListener("mouseleave", () => {
      dot.style.opacity = "0"; ring.style.opacity = "0";
    });
    document.addEventListener("mouseenter", () => {
      dot.style.opacity = "1"; ring.style.opacity = "1";
    });
  }

  /* ----------------------------------------------------------
     2. REVEAL ON SCROLL (IntersectionObserver, staggered)
     ---------------------------------------------------------- */
  function initReveal() {
    const els = document.querySelectorAll(".reveal, .reveal-left, .reveal-right");
    if (reduceMotion) {
      els.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const delay = el.dataset.delay ? parseInt(el.dataset.delay, 10) : 0;
          setTimeout(() => el.classList.add("in"), delay);
          io.unobserve(el);
        }
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -8% 0px" });

    els.forEach((el) => io.observe(el));

    // auto-stagger for groups marked [data-stagger]
    document.querySelectorAll("[data-stagger]").forEach((group) => {
      const kids = group.querySelectorAll(".reveal, .reveal-left, .reveal-right");
      kids.forEach((k, i) => { if (!k.dataset.delay) k.dataset.delay = i * 100; });
    });
  }

  /* ----------------------------------------------------------
     3. PARALLAX ([data-parallax] with data-speed)
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
     4. ANIMATED COUNTERS ([data-count], easeOutExpo)
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

  /* ----------------------------------------------------------
     5. BEFORE / AFTER SLIDER (drag mouse + touch)
     ---------------------------------------------------------- */
  function initBeforeAfter() {
    document.querySelectorAll(".ba").forEach((ba) => {
      const after = ba.querySelector(".ba__after");
      const handle = ba.querySelector(".ba__handle");
      if (!after || !handle) return;
      let dragging = false;

      function setPos(clientX) {
        const rect = ba.getBoundingClientRect();
        let pct = ((clientX - rect.left) / rect.width) * 100;
        pct = Math.max(0, Math.min(100, pct));
        after.style.width = pct + "%";
        handle.style.left = pct + "%";
      }

      const start = () => { dragging = true; };
      const end = () => { dragging = false; };
      const move = (e) => {
        if (!dragging) return;
        const x = e.touches ? e.touches[0].clientX : e.clientX;
        setPos(x);
      };

      handle.addEventListener("mousedown", start);
      ba.addEventListener("mousedown", (e) => { start(); setPos(e.clientX); });
      window.addEventListener("mouseup", end);
      window.addEventListener("mousemove", move);

      handle.addEventListener("touchstart", start, { passive: true });
      ba.addEventListener("touchstart", (e) => { start(); setPos(e.touches[0].clientX); }, { passive: true });
      window.addEventListener("touchend", end);
      window.addEventListener("touchmove", move, { passive: true });
    });
  }

  /* ---------- INIT ---------- */
  function init() {
    initReveal();
    initParallax();
    initCounters();
    initBeforeAfter();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
