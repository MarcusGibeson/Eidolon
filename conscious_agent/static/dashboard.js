(function () {
  const search = document.querySelector('[data-nav-search]');
  const toggle = document.querySelector('.nav-mobile-toggle');
  const content = document.querySelector('.nav-content');
  const mobile = window.matchMedia('(max-width: 980px)');
  function setNavigation(open) {
    if (!toggle || !content) return;
    const expanded = !mobile.matches || !!open;
    content.dataset.mobileCollapsed = mobile.matches && !expanded ? 'true' : 'false';
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }
  function syncNavigation() { setNavigation(!mobile.matches); }
  if (toggle) toggle.addEventListener('click', function () { setNavigation(toggle.getAttribute('aria-expanded') !== 'true'); });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && mobile.matches && toggle && toggle.getAttribute('aria-expanded') === 'true') {
      setNavigation(false);
      toggle.focus();
    }
  });
  if (mobile.addEventListener) mobile.addEventListener('change', syncNavigation); else mobile.addListener(syncNavigation);
  syncNavigation();
  if (!search) return;
  function normalize(value) { return String(value || '').toLowerCase(); }
  function applyFilter() {
    const q = normalize(search.value).trim();
    document.querySelectorAll('.nav-section').forEach(function (section) {
      let visibleCount = 0;
      section.querySelectorAll('a.nav-link').forEach(function (link) {
        const haystack = normalize((link.dataset.routeTitle || '') + ' ' + (link.dataset.routeGroup || '') + ' ' + (link.dataset.tip || '') + ' ' + link.textContent);
        const visible = !q || haystack.includes(q);
        link.classList.toggle('nav-hidden', !visible);
        if (visible) visibleCount += 1;
      });
      section.classList.toggle('nav-hidden', !!q && visibleCount === 0);
      if (q && visibleCount > 0) section.open = true;
    });
  }
  search.addEventListener('input', applyFilter);
  document.querySelectorAll('a.nav-link').forEach(function (link) {
    link.addEventListener('click', function () { if (mobile.matches) setNavigation(false); });
  });
})();
