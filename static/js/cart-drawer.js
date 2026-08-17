(function () {
    const drawer = document.getElementById('cart-drawer');
    const body = document.getElementById('cart-drawer-body');
    const totalEl = document.getElementById('cart-drawer-total');
    const countEl = document.getElementById('cart-count');
    const bottomCountEl = document.getElementById('bottom-cart-count');
    if (!drawer || !body) return;

    const resumoUrl = '/carrinho/resumo/';
    const removerUrl = '/carrinho/remover/';

    function getCsrf() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    function formatMoney(value) {
        const n = parseFloat(value);
        if (Number.isNaN(n)) return value;
        return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function renderCart(data) {
        if (countEl) countEl.textContent = data.total_itens;
        if (bottomCountEl) bottomCountEl.textContent = data.total_itens;
        if (totalEl) totalEl.textContent = formatMoney(data.total);

        if (!data.itens.length) {
            body.innerHTML = '<p class="cart-drawer-empty">Seu carrinho está vazio.</p>';
            return;
        }

        body.innerHTML = data.itens.map((item) => `
            <article class="cart-drawer-item">
                ${item.imagem_url ? `<img src="${item.imagem_url}" alt="">` : '<div class="cart-drawer-item-ph"></div>'}
                <div>
                    <strong>${item.titulo}</strong>
                    <span class="mono">${item.modalidade_label} · ${item.quantidade}x · ${formatMoney(item.subtotal)}</span>
                </div>
                <button type="button" class="cart-drawer-remove" data-cart-remove="${item.key}" aria-label="Remover">×</button>
            </article>
        `).join('');

        body.querySelectorAll('[data-cart-remove]').forEach((btn) => {
            btn.addEventListener('click', () => removeItem(btn.getAttribute('data-cart-remove')));
        });
    }

    function loadCart() {
        body.innerHTML = '<p class="cart-drawer-loading">Carregando…</p>';
        fetch(resumoUrl, { credentials: 'same-origin' })
            .then((r) => r.json())
            .then(renderCart)
            .catch(() => {
                body.innerHTML = '<p class="cart-drawer-empty">Não foi possível carregar o carrinho.</p>';
            });
    }

    function openDrawer() {
        drawer.hidden = false;
        document.body.classList.add('cart-drawer-open');
        loadCart();
    }

    function closeDrawer() {
        drawer.hidden = true;
        document.body.classList.remove('cart-drawer-open');
    }

    function removeItem(key) {
        const params = new URLSearchParams();
        params.set('key', key);
        fetch(removerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrf(),
            },
            body: params.toString(),
            credentials: 'same-origin',
        })
            .then((r) => r.json())
            .then((data) => {
                if (data.ok) renderCart(data);
            });
    }

    document.querySelectorAll('[data-cart-open]').forEach((btn) => {
        btn.addEventListener('click', openDrawer);
    });

    drawer.querySelectorAll('[data-cart-close]').forEach((el) => {
        el.addEventListener('click', closeDrawer);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
    });

    document.querySelectorAll('.js-add-cart').forEach((form) => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrf(),
                },
                body: formData,
                credentials: 'same-origin',
            })
                .then((r) => r.json())
                .then((data) => {
                    if (data.ok) {
                        renderCart(data);
                        openDrawer();
                    } else {
                        alert(data.detail || 'Não foi possível adicionar ao carrinho.');
                    }
                })
                .catch(() => alert('Erro ao adicionar ao carrinho.'));
        });
    });

    document.querySelectorAll('[data-favorito-toggle]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const id = btn.getAttribute('data-favorito-toggle');
            const params = new URLSearchParams();
            fetch(`/favoritos/toggle/${id}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrf(),
                },
                body: params.toString(),
                credentials: 'same-origin',
            })
                .then((r) => r.json())
                .then((data) => {
                    if (!data.ok) return;
                    btn.classList.toggle('is-active', data.favoritado);
                    btn.setAttribute('aria-label', data.favoritado ? 'Remover dos favoritos' : 'Salvar para depois');
                });
        });
    });
})();
