(function () {
    const layout = document.getElementById('gestao-layout');
    const openBtn = document.getElementById('gestao-menu-open');
    const backdrop = document.getElementById('gestao-sidebar-backdrop');
    if (!layout || !openBtn) return;

    function openNav() {
        layout.classList.add('gestao-nav-open');
        if (backdrop) backdrop.hidden = false;
        document.body.classList.add('gestao-nav-open');
    }

    function closeNav() {
        layout.classList.remove('gestao-nav-open');
        if (backdrop) backdrop.hidden = true;
        document.body.classList.remove('gestao-nav-open');
    }

    openBtn.addEventListener('click', openNav);
    document.querySelectorAll('[data-gestao-nav-close]').forEach((el) => {
        el.addEventListener('click', closeNav);
    });

    layout.querySelectorAll('.gestao-side-link').forEach((link) => {
        link.addEventListener('click', () => {
            if (window.matchMedia('(max-width: 900px)').matches) closeNav();
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeNav();
    });
})();
