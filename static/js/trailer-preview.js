(function () {
    const modal = document.getElementById('trailer-modal');
    if (!modal) return;

    const titleEl = document.getElementById('trailer-modal-title');
    const videoEl = document.getElementById('trailer-video');
    const iframeEl = document.getElementById('trailer-iframe');

    function stopPlayback() {
        if (videoEl) {
            videoEl.pause();
            videoEl.removeAttribute('src');
            videoEl.load();
            videoEl.hidden = true;
        }
        if (iframeEl) {
            iframeEl.src = '';
            iframeEl.hidden = true;
        }
    }

    function closeModal() {
        modal.hidden = true;
        document.body.classList.remove('trailer-open');
        stopPlayback();
    }

    function openModal(btn) {
        const title = btn.getAttribute('data-trailer-title') || 'Trailer';
        const fileUrl = btn.getAttribute('data-trailer-file') || '';
        const embedUrl = btn.getAttribute('data-trailer-embed') || '';

        titleEl.textContent = title;
        stopPlayback();

        if (fileUrl) {
            videoEl.hidden = false;
            videoEl.src = fileUrl;
            videoEl.play().catch(() => {});
        } else if (embedUrl) {
            iframeEl.hidden = false;
            iframeEl.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
            const sep = embedUrl.includes('?') ? '&' : '?';
            iframeEl.src = `${embedUrl}${sep}autoplay=1`;
        } else {
            return;
        }

        modal.hidden = false;
        document.body.classList.add('trailer-open');
    }

    document.querySelectorAll('.btn-trailer').forEach((btn) => {
        btn.addEventListener('click', () => openModal(btn));
    });

    modal.querySelectorAll('[data-trailer-close]').forEach((el) => {
        el.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.hidden) closeModal();
    });
})();
