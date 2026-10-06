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

    const pausaTrailerMs = 700;
    document.querySelectorAll('.item-card--midia').forEach((card) => {
        const layer = card.querySelector('.item-card-trailer');
        if (!layer) return;
        if (!window.matchMedia('(hover: hover) and (prefers-reduced-motion: no-preference)').matches) return;
        let timer = 0;

        const parar = () => {
            window.clearTimeout(timer);
            layer.hidden = true;
            layer.replaceChildren();
        };

        const tocar = () => {
            const file = layer.dataset.trailerFile || '';
            const embed = layer.dataset.trailerEmbed || '';
            layer.replaceChildren();
            if (file) {
                const video = document.createElement('video');
                video.muted = true;
                video.defaultMuted = true;
                video.autoplay = true;
                video.loop = true;
                video.playsInline = true;
                video.src = file;
                layer.appendChild(video);
                video.play().catch(() => {});
            } else if (embed) {
                const iframe = document.createElement('iframe');
                const sep = embed.includes('?') ? '&' : '?';
                iframe.src = `${embed}${sep}autoplay=1&mute=1&controls=0&modestbranding=1`;
                iframe.allow = 'autoplay; encrypted-media';
                iframe.title = layer.dataset.trailerTitle || 'Trailer';
                layer.appendChild(iframe);
            } else {
                return;
            }
            layer.hidden = false;
        };

        const agendar = () => {
            if (!layer.hidden) return;
            window.clearTimeout(timer);
            timer = window.setTimeout(tocar, pausaTrailerMs);
        };

        card.addEventListener('mouseenter', agendar);
        card.addEventListener('mousemove', agendar);
        card.addEventListener('mouseleave', parar);
    });
})();
