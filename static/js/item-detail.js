(function () {
    const form = document.getElementById('item-detail-form');
    if (!form) return;

    const modalidadeInput = document.getElementById('item-modalidade');
    const cta = document.getElementById('item-detail-cta');
    const hint = document.getElementById('item-detail-hint');
    const toggleBtns = document.querySelectorAll('.modalidade-toggle-btn');

    const labels = {
        venda: {
            cta: 'Adicionar compra ao carrinho',
            hint: 'Compra: o item é seu após o pagamento.',
        },
        aluguel: {
            cta: 'Adicionar aluguel ao carrinho',
            hint: 'Aluguel: acesso por alguns dias após pagamento. Veja prazo na opção acima.',
        },
    };

    toggleBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
            const modalidade = btn.getAttribute('data-modalidade');
            if (!modalidade || !modalidadeInput) return;

            toggleBtns.forEach((b) => b.classList.remove('is-active'));
            btn.classList.add('is-active');
            modalidadeInput.value = modalidade;

            if (cta && labels[modalidade]) {
                cta.textContent = labels[modalidade].cta;
            }
            if (hint && labels[modalidade]) {
                hint.textContent = labels[modalidade].hint;
            }
        });
    });
})();
