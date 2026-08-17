(function () {
    const tabs = document.querySelectorAll('[data-auth-tab]');
    const panels = document.querySelectorAll('[data-auth-panel]');

    function activateTab(name) {
        tabs.forEach((tab) => {
            const active = tab.getAttribute('data-auth-tab') === name;
            tab.classList.toggle('is-active', active);
            tab.setAttribute('aria-selected', active ? 'true' : 'false');
        });

        panels.forEach((panel) => {
            const active = panel.getAttribute('data-auth-panel') === name;
            panel.classList.toggle('is-active', active);
            panel.hidden = !active;
        });
    }

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            activateTab(tab.getAttribute('data-auth-tab'));
        });
    });

    document.querySelectorAll('.auth-back-login[data-auth-tab]').forEach((btn) => {
        btn.addEventListener('click', () => {
            activateTab(btn.getAttribute('data-auth-tab'));
        });
    });

    document.querySelectorAll('[data-password-toggle]').forEach((btn) => {
        const inputId = btn.getAttribute('data-password-toggle');
        const input = document.getElementById(inputId);
        if (!input) return;

        btn.addEventListener('click', () => {
            const showing = input.type === 'text';
            input.type = showing ? 'password' : 'text';
            btn.setAttribute('aria-label', showing ? 'Mostrar senha' : 'Ocultar senha');
        });
    });

    const params = new URLSearchParams(window.location.search);
    if (params.get('tab') === 'register') {
        activateTab('register');
    }
})();
