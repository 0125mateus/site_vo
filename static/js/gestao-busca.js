(function () {
    const input = document.getElementById('gestao-busca');
    const panel = document.getElementById('gestao-busca-resultados');
    if (!input || !panel) return;

    let timer = null;

    function grupo(titulo, itens, campo) {
        if (!itens.length) return '';
        const lis = itens.map((item) => {
            const texto = item[campo] || '';
            const url = item.url || '#';
            return '<li><a href="' + url + '">' + texto.replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])) + '</a></li>';
        }).join('');
        return '<p>' + titulo + '</p><ul>' + lis + '</ul>';
    }

    function render(data) {
        const html = [
            grupo('Produtos', data.produtos || [], 'titulo'),
            grupo('Clientes', data.clientes || [], 'nome'),
            grupo('Pedidos', data.pedidos || [], 'rotulo'),
            grupo('Aluguéis', data.alugueis || [], 'rotulo'),
        ].join('');
        panel.innerHTML = html || '<p>Nenhum resultado.</p>';
        panel.hidden = false;
    }

    input.addEventListener('input', function () {
        window.clearTimeout(timer);
        const q = input.value.trim();
        if (q.length < 2) {
            panel.hidden = true;
            panel.innerHTML = '';
            return;
        }
        timer = window.setTimeout(function () {
            const url = input.getAttribute('data-busca-url') + '?formato=json&q=' + encodeURIComponent(q);
            fetch(url, { headers: { 'X-Requested-With': 'fetch' } })
                .then((res) => res.ok ? res.json() : null)
                .then((data) => { if (data) render(data); })
                .catch(function () { panel.hidden = true; });
        }, 250);
    });

    document.addEventListener('click', function (event) {
        if (!input.parentElement.contains(event.target)) panel.hidden = true;
    });
})();
