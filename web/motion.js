// Progressive enhancement: content and links remain usable without this script.
(() => {
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const root = document.documentElement;
  const running = new Map();
  const seen = new WeakSet();
  let navigationTimer;
  let recoveryTimer;
  let destination;
  const easing = 'cubic-bezier(.22,1,.36,1)';

  function animate(element, frames, options = {}) {
    if (!element?.animate || preference.matches) return;
    running.get(element)?.cancel();
    const animation = element.animate(frames, { duration: 650, easing, fill: 'backwards', ...options });
    running.set(element, animation);
    const cleanup = () => { if (running.get(element) === animation) running.delete(element); };
    animation.finished.then(cleanup, cleanup);
    return animation;
  }

  function reveal(element, delay = 0) {
    if (!element) return;
    if (seen.has(element)) return;
    seen.add(element);
    if (element.contains(document.activeElement)) return;
    animate(element, [{ opacity: 0, translate: '0 24px' }, { opacity: 1, translate: '0 0' }], { delay });
  }

  function resetNavigation() {
    clearTimeout(navigationTimer);
    clearTimeout(recoveryTimer);
    destination = undefined;
    root.classList.remove('page-departing');
  }

  function syncPreference() {
    root.dataset.motion = preference.matches ? 'off' : 'on';
    if (preference.matches) {
      running.forEach(animation => animation.cancel());
      running.clear();
      // Finish a user-requested navigation immediately when motion is disabled.
      if (destination) {
        const url = destination;
        resetNavigation();
        window.location.assign(url);
      }
    }
  }
  syncPreference();
  preference.addEventListener('change', syncPreference);

  // Entry rhythm. Individual translate preserves the floating header's centering transform.
  const hero = document.querySelector('.hero');
  if (hero) {
    reveal(document.querySelector('.navigation'));
    document.querySelectorAll('.hero-content > *').forEach((element, index) => reveal(element, 80 + index * 85));
    reveal(document.querySelector('.scroll-cue'), 450);
  } else {
    document.querySelectorAll('.workspace-header, .workspace-main > .section-label, .workspace-main > h1, .workspace-intro').forEach((element, index) => reveal(element, index * 60));
  }

  const targets = document.querySelectorAll('.section > .section-label, .section-heading, .about-grid > *, .feature-list > article, .steps > article, .inspiration-grid > figure, .closing, .intake-left > section, .property-panel');
  document.querySelectorAll('.feature-list, .steps, .inspiration-grid, .about-grid').forEach(group => {
    [...group.children].forEach((child, index) => { child.dataset.revealDelay = String(index * 85); });
  });
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        reveal(entry.target, Number(entry.target.dataset.revealDelay || 0));
        observer.unobserve(entry.target);
      }
    }, { threshold: 0.06, rootMargin: '0px 0px -24px 0px' });
    targets.forEach(element => observer.observe(element));
  }

  // Never leave keyboard focus inside an invisible entrance animation.
  document.addEventListener('focusin', event => {
    running.forEach((animation, element) => {
      if (element.contains(event.target)) animation.cancel();
    });
  });

  // A brief spring-like press response, including controls created by the chat UI.
  document.addEventListener('click', event => {
    const control = event.target.closest('button, a.button');
    if (!control || control.disabled || control.getAttribute('aria-disabled') === 'true') return;
    animate(control, [{ scale: '0.96' }, { scale: '1.025', offset: 0.6 }, { scale: '1' }], { duration: 260 });
  });

  // Same-origin, ordinary navigation only. Hash, modified, download and new-tab links stay native.
  document.addEventListener('click', event => {
    if (preference.matches || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest('a[href]');
    if (!link || link.hasAttribute('download') || (link.target && link.target !== '_self') || link.hasAttribute('data-no-transition')) return;
    const url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin || !['http:', 'https:'].includes(url.protocol)) return;
    const directory = window.location.pathname.replace(/[^/]*$/, '');
    const allowed = [directory, `${directory}index.html`, `${directory}experience.html`];
    if (!allowed.includes(url.pathname)) return;
    const currentPage = window.location.pathname.replace(/index\.html$/, '');
    if (url.pathname.replace(/index\.html$/, '') === currentPage && url.search === window.location.search) return;
    event.preventDefault();
    if (destination) return;
    destination = url.href;
    root.classList.add('page-departing');
    navigationTimer = setTimeout(() => {
      window.location.assign(destination);
      // Recover the current page if a navigation is canceled or fails before unloading.
      recoveryTimer = setTimeout(resetNavigation, 1400);
    }, 160);
  });

  // Restored pages must never retain their exit curtain or stale timers.
  window.addEventListener('pageshow', resetNavigation);
  window.addEventListener('pagehide', resetNavigation);
})();
