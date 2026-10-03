/* Visual apenas: header no scroll e setas das prateleiras. Não mexe no carrinho. */
(function () {
    const header = document.querySelector('header.site-header');
    if (header) {
        const onScroll = () => {
            header.classList.toggle('is-scrolled', window.scrollY > 8);
        };
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
    }

    document.querySelectorAll('.shelf-arrow').forEach((btn) => {
        btn.addEventListener('click', () => {
            const shelf = btn.parentElement && btn.parentElement.querySelector('.shelf');
            if (!shelf) return;
            const dir = Number(btn.dataset.shelfDir) || 1;
            const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            shelf.scrollBy({
                left: dir * Math.max(shelf.clientWidth * 0.75, 220),
                behavior: reduce ? 'auto' : 'smooth',
            });
        });
    });
})();
