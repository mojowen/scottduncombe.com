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

  // Rail compresses once you scroll past the fold, or right away if the
  // full rail can't fit the viewport (desktop grid layout only — the
  // .scrolled styles are scoped to min-width: 1080px).
  var compact = function () {
    var rail = document.querySelector(".rail");
    var tooTall = rail && rail.scrollHeight > document.documentElement.clientHeight;
    var past = (window.scrollY || 0) > 120;
    document.body.classList.toggle("scrolled", past || !!tooTall);
  };
  window.addEventListener("scroll", compact, { passive: true });
  window.addEventListener("resize", compact, { passive: true });
  compact();
})();