(function () {
    const btn = document.getElementById('btn-gerar-descricao');
    const statusEl = document.getElementById('gerar-descricao-status');
    const descricaoEl = document.getElementById('id_descricao');
    if (!btn || !descricaoEl) return;

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function getExtra() {
        const artista = document.getElementById('id_artista');
        const autor = document.getElementById('id_autor');
        const diretor = document.getElementById('id_diretor');
        if (artista && artista.value) return 'Artista: ' + artista.value;
        if (autor && autor.value) return 'Autor: ' + autor.value;
        if (diretor && diretor.value) return 'Diretor: ' + diretor.value;
        return '';
    }

    btn.addEventListener('click', async function () {
        const titulo = (document.getElementById('id_titulo') || {}).value || '';
        if (!titulo.trim()) {
            statusEl.hidden = false;
            statusEl.textContent = 'Preencha o título antes de gerar.';
            return;
        }

        btn.disabled = true;
        statusEl.hidden = false;
        statusEl.textContent = 'Gerando descrição…';

        try {
            const body = new FormData();
            body.append('titulo', titulo.trim());
            body.append('tipo', btn.dataset.tipo || 'livro');
            body.append('extra', getExtra());

            const response = await fetch('/gestao/api/gerar-descricao/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                credentials: 'same-origin',
                body,
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                throw new Error(data.detail || 'Não foi possível gerar.');
            }
            descricaoEl.value = data.descricao;
            statusEl.textContent = 'Descrição gerada — revise antes de salvar.';
        } catch (err) {
            statusEl.textContent = err.message || 'Erro ao gerar descrição.';
        } finally {
            btn.disabled = false;
        }
    });
})();
