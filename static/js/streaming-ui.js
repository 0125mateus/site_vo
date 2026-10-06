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

    if (!window.matchMedia('(hover: hover) and (prefers-reduced-motion: no-preference)').matches) return;

    const pausaTrailerMs = 700;
    const painel = document.createElement('div');
    painel.className = 'hover-preview';
    painel.hidden = true;
    document.body.appendChild(painel);

    let timerAbrir = 0;
    let timerFechar = 0;
    let cardAberto = null;

    const midiaDo = (el) => {
        if (!el) return null;
        const file = el.dataset.trailerFile || '';
        const embed = el.dataset.trailerEmbed || '';
        if (!file && !embed) return null;
        return el;
    };

    const fechar = () => {
        window.clearTimeout(timerAbrir);
        window.clearTimeout(timerFechar);
        cardAberto = null;
        painel.hidden = true;
        painel.replaceChildren();
    };

    const posicionar = (card) => {
        const rect = card.getBoundingClientRect();
        const largura = Math.min(440, window.innerWidth - 24);
        let left = rect.left + (rect.width / 2) - (largura / 2);
        left = Math.max(12, Math.min(left, window.innerWidth - largura - 12));
        painel.style.width = `${largura}px`;
        painel.style.left = `${left}px`;
        const altura = painel.offsetHeight || 360;
        let top = rect.top + (rect.height / 2) - (altura / 2);
        top = Math.max(12, Math.min(top, window.innerHeight - altura - 12));
        painel.style.top = `${top}px`;
    };

    const abrir = (card, layer) => {
        const file = layer.dataset.trailerFile || '';
        const embed = layer.dataset.trailerEmbed || '';
        const titulo = layer.dataset.trailerTitle || '';
        const sub = layer.dataset.trailerSub || (card.querySelector('.item-card-sub') || {}).textContent || '';
        const preco = (card.querySelector('.item-price--sale') || {}).textContent || '';
        const link = card.querySelector('.item-card-cover');

        painel.replaceChildren();
        const media = document.createElement('div');
        media.className = 'hover-preview-media';
        if (file) {
            const video = document.createElement('video');
            video.muted = true;
            video.defaultMuted = true;
            video.autoplay = true;
            video.loop = true;
            video.playsInline = true;
            video.src = file;
            media.appendChild(video);
            video.play().catch(() => {});
        } else if (embed) {
            const iframe = document.createElement('iframe');
            const sep = embed.includes('?') ? '&' : '?';
            iframe.src = `${embed}${sep}autoplay=1&mute=1&controls=0&modestbranding=1`;
            iframe.allow = 'autoplay; encrypted-media';
            iframe.title = titulo || 'Trailer';
            media.appendChild(iframe);
        }
        const corpo = document.createElement('div');
        corpo.className = 'hover-preview-body';
        const h = document.createElement('h3');
        h.className = 'hover-preview-title';
        h.textContent = titulo.trim();
        corpo.appendChild(h);
        const linha = document.createElement('p');
        linha.className = 'hover-preview-sub';
        linha.textContent = sub.trim();
        corpo.appendChild(linha);
        if (preco.trim()) {
            const valor = document.createElement('p');
            valor.className = 'hover-preview-price';
            valor.textContent = preco.trim();
            corpo.appendChild(valor);
        }
        if (link) {
            const detalhes = document.createElement('a');
            detalhes.className = 'btn btn-ghost btn-sm';
            detalhes.href = link.href;
            detalhes.textContent = 'Detalhes';
            corpo.appendChild(detalhes);
        }
        painel.append(media, corpo);
        painel.hidden = false;
        cardAberto = card;
        painel.dataset.abertoEm = String(Date.now());
        posicionar(card);
    };

    document.querySelectorAll('.item-card--midia').forEach((card) => {
        const layer = midiaDo(card.querySelector('.item-card-trailer'));
        if (!layer) return;

        const agendar = () => {
            if (cardAberto === card) return;
            window.clearTimeout(timerAbrir);
            window.clearTimeout(timerFechar);
            timerAbrir = window.setTimeout(() => abrir(card, layer), pausaTrailerMs);
        };

        card.addEventListener('mouseenter', agendar);
        card.addEventListener('mousemove', agendar);
        card.addEventListener('mouseleave', (event) => {
            window.clearTimeout(timerAbrir);
            if (painel.contains(event.relatedTarget)) return;
            const abertoEm = Number(painel.dataset.abertoEm || 0);
            if (cardAberto === card && Date.now() - abertoEm < 400) return;
            timerFechar = window.setTimeout(fechar, 220);
        });
    });

    painel.addEventListener('mouseenter', () => {
        window.clearTimeout(timerFechar);
    });
    painel.addEventListener('mouseleave', () => {
        timerFechar = window.setTimeout(fechar, 180);
    });
    window.addEventListener('scroll', () => {
        if (!painel.hidden) fechar();
    }, true);
    window.addEventListener('resize', () => {
        if (cardAberto && !painel.hidden) posicionar(cardAberto);
    });
})();
