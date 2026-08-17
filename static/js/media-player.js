(function () {
    const mainAudio = document.getElementById('player-audio');
    const barAudio = document.getElementById('media-bar-audio');
    const bar = document.getElementById('media-bar');
    if (!mainAudio || !barAudio || !bar) return;

    document.body.classList.add('has-media-bar');

    function syncFromMain() {
        if (Math.abs(barAudio.currentTime - mainAudio.currentTime) > 0.3) {
            barAudio.currentTime = mainAudio.currentTime;
        }
        if (mainAudio.paused !== barAudio.paused) {
            if (mainAudio.paused) barAudio.pause();
            else barAudio.play().catch(() => {});
        }
    }

    function syncFromBar() {
        if (Math.abs(mainAudio.currentTime - barAudio.currentTime) > 0.3) {
            mainAudio.currentTime = barAudio.currentTime;
        }
        if (barAudio.paused !== mainAudio.paused) {
            if (barAudio.paused) mainAudio.pause();
            else mainAudio.play().catch(() => {});
        }
    }

    mainAudio.addEventListener('play', () => barAudio.play().catch(() => {}));
    mainAudio.addEventListener('pause', () => barAudio.pause());
    mainAudio.addEventListener('timeupdate', syncFromMain);

    barAudio.addEventListener('play', () => mainAudio.play().catch(() => {}));
    barAudio.addEventListener('pause', () => mainAudio.pause());
    barAudio.addEventListener('timeupdate', syncFromBar);
})();
