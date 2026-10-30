// scottduncombe.com prototype — tiny JS: googly eyes, year stamps, monogram replay
(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Footer year stamps
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  // Click the monogram to replay its signature animation
  document.querySelectorAll(".sig").forEach(function (sig) {
    sig.addEventListener("click", function () {
      if (reduce) return;
      sig.classList.add("replay");
      void sig.offsetWidth; // reflow
      sig.classList.remove("replay");
    });
  });

  // 404: pizza slice googly eyes follow the cursor
  if (!reduce) {
    var eyes = document.querySelectorAll(".eye");
    if (eyes.length) {
      var raf = null;
      var track = function (e) {
        if (raf) return;
        raf = requestAnimationFrame(function () {
          raf = null;
          eyes.forEach(function (eye) {
            var pupil = eye.querySelector(".pupil");
            if (!pupil) return;
            var r = eye.getBoundingClientRect();
            var cx = r.left + r.width / 2;
            var cy = r.top + r.height / 2;
            var dx = (e.clientX || cx) - cx;
            var dy = (e.clientY || cy) - cy;
            var d = Math.max(1, Math.hypot(dx, dy));
            var reach = Math.min(d, r.width * 0.18);
            pupil.setAttribute("transform",
              "translate(" + ((dx / d) * reach).toFixed(1) + "," + ((dy / d) * reach).toFixed(1) + ")");
          });
        });
      };
      window.addEventListener("pointermove", track, { passive: true });
      window.addEventListener("touchmove", track, { passive: true });
    }
  }

  // Rail compresses once you scroll past the fold — and ONLY on
  // scroll. Never at load, even when the full rail is taller than the
  // viewport: the sticky rail scrolls internally (max-height +
  // overflow-y), so a short window must still start with the full
  // letterhead. (An earlier "too tall → compress now" rule here is what
  // made the menu load pre-collapsed on short windows.)
  var compact = function () {
    var past = (window.scrollY || 0) > 120;
    document.body.classList.toggle("scrolled", past);
  };
  window.addEventListener("scroll", compact, { passive: true });
  window.addEventListener("resize", compact, { passive: true });
  compact();

  // Mobile menu at the bottom of the page — the rail markup stays the
  // single source of truth; this clones its nav/social/footer into a
  // footer that sits just above the true page footer (Proudly powered…).
  // CSS shows the clone only on narrow screens (and hides the originals
  // there under body.foot-menu); desktop shows the rail sidebar.
  var rail = document.querySelector(".rail");
  if (rail) {
    var sources = [".nav", ".social", ".rail-foot"];
    var clones = sources
      .map(function (s) { return rail.querySelector(s); })
      .filter(function (el) { return el; })
      .map(function (el) { return el.cloneNode(true); });
    if (clones.length) {
      var foot = document.createElement("footer");
      foot.className = "page-foot";
      foot.setAttribute("aria-label", "Site menu");
      clones.forEach(function (c) { foot.appendChild(c); });
      var trueFoot = document.querySelector("main .foot");
      if (trueFoot && trueFoot.parentNode) {
        trueFoot.parentNode.insertBefore(foot, trueFoot);
      } else {
        document.body.appendChild(foot);
      }
      document.body.classList.add("foot-menu");
    }
  }
})();