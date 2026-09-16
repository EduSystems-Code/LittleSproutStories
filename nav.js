/* Shared nav behavior for every top-level LittleSprout page: the mobile
   menu toggle and the "For Families" dropdown (Family Resources, Grants
   & Funding, Community Board). One file instead of ~10 pages drifting
   out of sync with each other -- same reasoning as sw.js/manifest.json
   already being shared, not duplicated, across every page. */
(function () {
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function closeDropdowns(except) {
    document.querySelectorAll('.nav-dd.open').forEach(function (dd) {
      if (dd === except) return;
      dd.classList.remove('open');
      var btn = dd.querySelector('.nav-dd-btn');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
  }

  ready(function () {
    var toggle = document.getElementById('navToggle');
    var links = document.getElementById('navLinks');
    if (toggle && links) {
      toggle.addEventListener('click', function () {
        var open = links.classList.toggle('open');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }

    document.querySelectorAll('.nav-dd').forEach(function (dd) {
      var btn = dd.querySelector('.nav-dd-btn');
      if (!btn) return;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var isOpen = dd.classList.contains('open');
        closeDropdowns(dd);
        dd.classList.toggle('open', !isOpen);
        btn.setAttribute('aria-expanded', !isOpen ? 'true' : 'false');
      });
    });

    document.addEventListener('click', function () { closeDropdowns(); });

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      closeDropdowns();
      if (links && links.classList.contains('open') && toggle) {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  });
})();
