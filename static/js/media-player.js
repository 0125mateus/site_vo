(function () {
    const stage = document.getElementById('player-stage');
    const mainMedia = document.getElementById('player-main');
    if (!stage || !mainMedia) return;

    const saveUrl = stage.getAttribute('data-save-url');
    const progressoInicial = parseInt(stage.getAttribute('data-progresso') || '0', 10);
    let lastSaved = 0;

    function restoreProgress() {
        if (progressoInicial > 0) {
            mainMedia.addEventListener('loadedmetadata', () => {
                if (mainMedia.duration && progressoInicial < mainMedia.duration - 5) {
                    mainMedia.currentTime = progressoInicial;
                }
            }, { once: true });
        }
    }

    function saveProgress() {
        if (!saveUrl || mainMedia.paused) return;
        const segundos = Math.floor(mainMedia.currentTime || 0);
        if (Math.abs(segundos - lastSaved) < 5) return;
        lastSaved = segundos;

        const body = new URLSearchParams();
        body.set('segundos', String(segundos));
        if (mainMedia.duration && isFinite(mainMedia.duration)) {
            body.set('duracao', String(Math.floor(mainMedia.duration)));
        }

        const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
        fetch(saveUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrf ? csrf.value : '',
            },
            body: body.toString(),
            credentials: 'same-origin',
        }).catch(() => {});
    }

    restoreProgress();
    mainMedia.addEventListener('timeupdate', saveProgress);
    mainMedia.addEventListener('pause', saveProgress);

    /* Barra fixa para áudio */
    const barAudio = document.getElementById('media-bar-audio');
    const bar = document.getElementById('media-bar');
    if (mainMedia.tagName === 'AUDIO' && barAudio && bar) {
        document.body.classList.add('has-media-bar');
        barAudio.src = mainMedia.src;

        mainMedia.addEventListener('play', () => barAudio.play().catch(() => {}));
        mainMedia.addEventListener('pause', () => barAudio.pause());
        barAudio.addEventListener('play', () => mainMedia.play().catch(() => {}));
        barAudio.addEventListener('pause', () => mainMedia.pause());
    }
})();
