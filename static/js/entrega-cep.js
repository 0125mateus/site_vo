(function () {
    const cepInput = document.querySelector('input[data-cep]');
    if (!cepInput) return;

    const statusEl = document.getElementById('entrega-cep-status');
    const campo = (nome) => document.getElementById(`id_entrega_${nome}`);
    let ultimoCep = '';

    function avisar(texto) {
        if (statusEl) statusEl.textContent = texto;
    }

    function preencher(nome, valor) {
        const el = campo(nome);
        if (el && valor && !el.value.trim()) el.value = valor;
    }

    async function buscarCep() {
        const digitos = cepInput.value.replace(/\D/g, '');
        if (digitos.length === 8) {
            cepInput.value = `${digitos.slice(0, 5)}-${digitos.slice(5)}`;
        }
        if (digitos.length !== 8 || digitos === ultimoCep) return;
        ultimoCep = digitos;
        avisar('Buscando endereço…');
        try {
            const resposta = await fetch(`https://viacep.com.br/ws/${digitos}/json/`);
            const dados = await resposta.json();
            if (dados.erro) {
                avisar('CEP não encontrado. Preencha o endereço abaixo.');
                return;
            }
            preencher('logradouro', dados.logradouro);
            preencher('bairro', dados.bairro);
            preencher('cidade', dados.localidade);
            const uf = campo('uf');
            if (uf && dados.uf && !uf.value) uf.value = dados.uf;
            avisar('');
            const numero = campo('numero');
            if (numero && !numero.value) numero.focus();
        } catch (erro) {
            avisar('Não foi possível buscar o CEP. Preencha o endereço abaixo.');
        }
    }

    cepInput.addEventListener('input', () => {
        if (cepInput.value.replace(/\D/g, '').length === 8) buscarCep();
    });
    cepInput.addEventListener('blur', buscarCep);
})();
