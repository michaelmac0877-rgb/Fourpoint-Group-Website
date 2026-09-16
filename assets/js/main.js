/* ============================================================================
   Four Points Group — interaction layer
   ----------------------------------------------------------------------------
   Everything scroll-linked runs through ONE requestAnimationFrame loop and only
   ever writes `transform` / `opacity`, so the browser can keep the work on the
   compositor and never re-layouts mid-scroll.

   Three tiers, chosen at runtime:
     full    desktop, motion allowed  -> scroll-driven 3D rotation (CSS 3D)
     simple  small screens / weak GPU -> slow CSS idle spin, no scroll work
     still   prefers-reduced-motion   -> no animation at all
   ========================================================================== */

(function () {
  "use strict";

  var docEl = document.documentElement;
  var stage = document.querySelector(".logo-stage");
  var pivot = document.getElementById("logoPivot");
  var nav = document.getElementById("nav");
  var parallaxEls = Array.prototype.slice.call(
    document.querySelectorAll("[data-parallax]")
  );

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var smallScreen = window.matchMedia("(max-width: 62rem)");

  /* ── Tier selection ────────────────────────────────────────────────────── */

  function pickTier() {
    if (reduceMotion.matches) return "still";
    if (smallScreen.matches) return "simple";
    // Very low core counts are a decent proxy for a GPU that will struggle.
    if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) {
      return "simple";
    }
    return "full";
  }

  var tier = pickTier();

  function applyTier() {
    if (!stage) return;
    stage.classList.toggle("logo-stage--simple", tier === "simple");
    if (tier !== "full" && pivot) {
      // Hand the element back to CSS (or leave it at rest).
      pivot.style.transform = "";
      pivot.style.willChange = "auto";
    }
    if (tier === "still" && stage) {
      stage.classList.remove("logo-stage--simple");
    }
  }
  applyTier();

  /* ── Scroll state ──────────────────────────────────────────────────────── */

  var scrollY = window.pageYOffset || 0;
  var maxScroll = 1;
  var ticking = false;

  // Smoothed rotation values. Lerping toward the target stops the mark from
  // snapping when the user flicks a trackpad or jumps with an anchor link.
  var cur = { x: 0, y: 0, z: 0, s: 1 };
  var tgt = { x: 0, y: 0, z: 0, s: 1 };
  var primed = false;

  function measure() {
    maxScroll = Math.max(
      1,
      (document.body.scrollHeight || 0) - window.innerHeight
    );
  }

  function computeTargets() {
    var p = Math.min(1, Math.max(0, scrollY / maxScroll));
    // rotateZ carries the "keeps turning as you scroll" reading -- a compass
    // mark spinning in plane never degenerates to an invisible edge, which a
    // full rotateY sweep would do every 90 degrees.
    tgt.z = p * 400;
    tgt.y = -38 + p * 76;
    tgt.x = 16 - p * 34;
    tgt.s = 1 + p * 0.18;
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  function render() {
    ticking = false;

    if (nav) nav.classList.toggle("nav--stuck", scrollY > 20);

    if (tier === "full" && pivot) {
      computeTargets();
      var k = primed ? 0.09 : 1; // first frame snaps, afterwards it eases
      primed = true;
      cur.x = lerp(cur.x, tgt.x, k);
      cur.y = lerp(cur.y, tgt.y, k);
      cur.z = lerp(cur.z, tgt.z, k);
      cur.s = lerp(cur.s, tgt.s, k);

      pivot.style.transform =
        "rotateX(" + cur.x.toFixed(2) + "deg) " +
        "rotateY(" + cur.y.toFixed(2) + "deg) " +
        "rotateZ(" + cur.z.toFixed(2) + "deg) " +
        "scale(" + cur.s.toFixed(4) + ")";

      // Keep easing until we have essentially arrived.
      if (Math.abs(cur.z - tgt.z) > 0.05 || Math.abs(cur.y - tgt.y) > 0.05) {
        request();
      }
    }

    if (tier !== "still") {
      for (var i = 0; i < parallaxEls.length; i++) {
        var el = parallaxEls[i];
        var factor = parseFloat(el.getAttribute("data-parallax")) || 0;
        var shift = Math.min(scrollY, window.innerHeight) * factor;
        el.style.transform = "translate3d(0," + shift.toFixed(1) + "px,0)";
      }
    }
  }

  function request() {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(render);
    }
  }

  function onScroll() {
    scrollY = window.pageYOffset || docEl.scrollTop || 0;
    request();
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener(
    "resize",
    function () {
      measure();
      var next = pickTier();
      if (next !== tier) {
        tier = next;
        primed = false;
        applyTier();
      }
      request();
    },
    { passive: true }
  );

  measure();
  onScroll();

  // Late-loading images change page height; re-measure once everything settles.
  window.addEventListener("load", function () { measure(); request(); });

  /* ── Frame-rate watchdog ───────────────────────────────────────────────── */
  /* If the 3D tier cannot hold a reasonable frame rate on this machine, drop to
     the simple tier rather than shipping a janky scroll.                      */

  if (tier === "full") {
    var samples = [];
    var last = 0;
    var strikes = 0;

    function watch(now) {
      if (last) {
        var dt = now - last;
        // Ignore idle gaps -- we only care about frames during active work.
        if (dt < 200) samples.push(dt);
      }
      last = now;

      if (samples.length >= 90) {
        samples.sort(function (a, b) { return a - b; });
        var median = samples[Math.floor(samples.length / 2)];
        samples.length = 0;
        if (median > 22) {          // worse than ~45fps
          if (++strikes >= 2) {
            tier = "simple";
            primed = false;
            applyTier();
            return;                 // stop watching
          }
        } else {
          strikes = 0;
        }
      }
      window.requestAnimationFrame(watch);
    }
    window.requestAnimationFrame(watch);
  }

  /* ── Reveal on scroll ──────────────────────────────────────────────────── */

  var reveals = document.querySelectorAll(".reveal");

  if (tier === "still" || !("IntersectionObserver" in window)) {
    for (var r = 0; r < reveals.length; r++) reveals[r].classList.add("is-visible");
  } else {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 }
    );
    for (var j = 0; j < reveals.length; j++) io.observe(reveals[j]);
  }

  /* ── Active section in the nav ─────────────────────────────────────────── */

  var sections = document.querySelectorAll("main section[id]");
  var navLinks = {};
  Array.prototype.forEach.call(
    document.querySelectorAll('.nav__menu a[href^="#"]'),
    function (a) { navLinks[a.getAttribute("href").slice(1)] = a; }
  );

  if ("IntersectionObserver" in window && sections.length) {
    var spy = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var link = navLinks[entry.target.id];
          if (!link) return;
          if (entry.isIntersecting) {
            for (var key in navLinks) navLinks[key].removeAttribute("aria-current");
            link.setAttribute("aria-current", "true");
          }
        });
      },
      { rootMargin: "-45% 0px -50% 0px" }
    );
    Array.prototype.forEach.call(sections, function (s) { spy.observe(s); });
  }

  /* ── Mobile navigation ─────────────────────────────────────────────────── */

  var toggle = document.getElementById("navToggle");
  var menu = document.getElementById("navMenu");

  function closeMenu() {
    if (!nav || !toggle) return;
    nav.classList.remove("nav--open");
    toggle.setAttribute("aria-expanded", "false");
  }

  if (toggle && nav && menu) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("nav--open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });

    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A") closeMenu();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMenu();
    });

    document.addEventListener("click", function (e) {
      if (!nav.classList.contains("nav--open")) return;
      if (!nav.contains(e.target)) closeMenu();
    });
  }

  /* ── Contact form ──────────────────────────────────────────────────────── */
  /* No backend here, so we compose a pre-filled email and hand it to the user's
     mail client. To switch to a real endpoint (Formspree, Netlify Forms, a
     serverless function), give the <form> an action/method and delete this
     handler -- nothing else depends on it.                                    */

  var form = document.getElementById("contactForm");
  var note = document.getElementById("formNote");
  var TO = "michael@fourpointsflooring.com";

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      var data = new FormData(form);
      var name = (data.get("name") || "").toString().trim();
      var phone = (data.get("phone") || "").toString().trim();

      var missing = [];
      [["name", name], ["phone", phone]].forEach(function (pair) {
        var input = form.elements[pair[0]];
        if (!pair[1]) {
          missing.push(input);
          input.setAttribute("aria-invalid", "true");
        } else {
          input.removeAttribute("aria-invalid");
        }
      });

      if (missing.length) {
        if (note) {
          note.textContent = "Please add your name and a phone number so we can reach you.";
          note.classList.add("form__note--error");
        }
        missing[0].focus();
        return;
      }

      if (note) {
        note.textContent =
          "This opens your email app with the details filled in — nothing is sent until you hit send there.";
        note.classList.remove("form__note--error");
      }

      var property = (data.get("property") || "").toString();
      var service = (data.get("service") || "").toString();
      var email = (data.get("email") || "").toString().trim();
      var message = (data.get("message") || "").toString().trim();

      var subject = "Website enquiry — " + property + " — " + service;
      var body = [
        "Name: " + name,
        "Phone: " + phone,
        "Email: " + (email || "(not given)"),
        "Property type: " + property,
        "Interested in: " + service,
        "",
        "Details:",
        message || "(none)",
        "",
        "— Sent from the Four Points Group website"
      ].join("\n");

      window.location.href =
        "mailto:" + TO +
        "?subject=" + encodeURIComponent(subject) +
        "&body=" + encodeURIComponent(body);
    });
  }

  /* ── Footer year ───────────────────────────────────────────────────────── */

  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
})();
