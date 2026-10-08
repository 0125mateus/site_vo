/* Capa de filme: ao escolher a imagem, vira pôster vertical 2:3 (1000 x 1500), com a foto inteira ou preenchendo o card. */
(function () {
    const input = document.querySelector('input[type="file"][data-capa-vertical]');
    if (!input) return;

    const LARGURA = 1000;
    const ALTURA = 1500;
    const PROPORCAO = LARGURA / ALTURA;
    const TOLERANCIA = 0.04;

    const preview = document.createElement('div');
    preview.className = 'gestao-image-preview gestao-image-preview--vertical';
    preview.hidden = true;
    const previewImg = document.createElement('img');
    previewImg.alt = 'Prévia da capa';
    const previewTexto = document.createElement('p');
    previewTexto.className = 'mono';
    const modos = document.createElement('div');
    modos.className = 'gestao-capa-modos';
    const btnInteira = document.createElement('button');
    btnInteira.type = 'button';
    btnInteira.textContent = 'Foto inteira';
    const btnPreencher = document.createElement('button');
    btnPreencher.type = 'button';
    btnPreencher.textContent = 'Preencher o card';
    modos.append(btnInteira, btnPreencher);
    preview.append(previewImg, modos, previewTexto);
    input.insertAdjacentElement('afterend', preview);

    let original = null;

    const carregar = (arquivo) => new Promise((resolve, reject) => {
        const url = URL.createObjectURL(arquivo);
        const img = new Image();
        img.onload = () => resolve({ img, url });
        img.onerror = () => {
            URL.revokeObjectURL(url);
            reject(new Error('imagem inválida'));
        };
        img.src = url;
    });

    const desenharCobrindo = (ctx, origem, largura, altura, margem) => {
        const ow = origem.naturalWidth || origem.width;
        const oh = origem.naturalHeight || origem.height;
        const escala = Math.max((largura + margem * 2) / ow, (altura + margem * 2) / oh);
        const w = ow * escala;
        const h = oh * escala;
        ctx.drawImage(origem, (largura - w) / 2, (altura - h) / 2, w, h);
    };

    const fundoDesfocado = (ctx, img) => {
        if (typeof ctx.filter === 'string') {
            ctx.filter = 'blur(48px)';
            desenharCobrindo(ctx, img, LARGURA, ALTURA, 120);
            ctx.filter = 'none';
        } else {
            // Sem ctx.filter: reduzir em etapas e ampliar de volta também desfoca, sem quadriculado forte.
            let atual = img;
            [250, 125, 64].forEach((largura) => {
                const etapa = document.createElement('canvas');
                etapa.width = largura;
                etapa.height = Math.round(largura / PROPORCAO);
                const c = etapa.getContext('2d');
                c.imageSmoothingEnabled = true;
                c.imageSmoothingQuality = 'high';
                desenharCobrindo(c, atual, etapa.width, etapa.height, 0);
                atual = etapa;
            });
            ctx.drawImage(atual, 0, 0, LARGURA, ALTURA);
        }
        ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
        ctx.fillRect(0, 0, LARGURA, ALTURA);
    };

    const montarPoster = (img, modo) => {
        const canvas = document.createElement('canvas');
        canvas.width = LARGURA;
        canvas.height = ALTURA;
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        if (modo === 'preencher') {
            desenharCobrindo(ctx, img, LARGURA, ALTURA, 0);
        } else {
            fundoDesfocado(ctx, img);
            const escala = Math.min(LARGURA / img.naturalWidth, ALTURA / img.naturalHeight);
            const w = img.naturalWidth * escala;
            const h = img.naturalHeight * escala;
            ctx.shadowColor = 'rgba(0, 0, 0, 0.55)';
            ctx.shadowBlur = 40;
            ctx.drawImage(img, (LARGURA - w) / 2, (ALTURA - h) / 2, w, h);
        }
        return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
    };

    const nomeJpg = (nome) => `${(nome || 'capa').replace(/\.[^.]+$/, '')}-capa.jpg`;

    const mostrar = (arquivo, texto) => {
        if (previewImg.dataset.url) URL.revokeObjectURL(previewImg.dataset.url);
        const url = URL.createObjectURL(arquivo);
        previewImg.dataset.url = url;
        previewImg.src = url;
        previewTexto.textContent = texto;
        preview.hidden = false;
    };

    const marcarModo = (modo) => {
        btnInteira.className = `btn btn-sm ${modo === 'inteira' ? 'btn-primary' : 'btn-ghost'}`;
        btnPreencher.className = `btn btn-sm ${modo === 'preencher' ? 'btn-primary' : 'btn-ghost'}`;
    };

    const aplicar = async (modo) => {
        if (!original) return;
        const blob = await montarPoster(original.img, modo);
        if (!blob || typeof DataTransfer === 'undefined') {
            modos.hidden = true;
            mostrar(original.arquivo, 'Não deu para ajustar neste navegador. A capa vai como foi escolhida.');
            return;
        }
        const ajustado = new File([blob], nomeJpg(original.arquivo.name), { type: 'image/jpeg' });
        const lista = new DataTransfer();
        lista.items.add(ajustado);
        input.dataset.ajustando = '1';
        input.files = lista.files;
        delete input.dataset.ajustando;
        marcarModo(modo);
        mostrar(
            ajustado,
            modo === 'preencher'
                ? 'Capa 1000 x 1500 preenchendo o card. As bordas que sobram da foto são cortadas.'
                : 'Capa 1000 x 1500 com a foto inteira. O espaço que sobra ganha um fundo desfocado.',
        );
    };

    btnInteira.addEventListener('click', () => aplicar('inteira'));
    btnPreencher.addEventListener('click', () => aplicar('preencher'));

    input.addEventListener('change', async () => {
        if (input.dataset.ajustando === '1') return;
        const arquivo = input.files && input.files[0];
        if (!arquivo || !arquivo.type.startsWith('image/')) return;
        let carregada;
        try {
            carregada = await carregar(arquivo);
        } catch (erro) {
            return;
        }
        if (original) URL.revokeObjectURL(original.url);
        original = { arquivo, img: carregada.img, url: carregada.url };
        modos.hidden = false;
        const proporcao = carregada.img.naturalWidth / carregada.img.naturalHeight;
        await aplicar(Math.abs(proporcao - PROPORCAO) <= TOLERANCIA ? 'preencher' : 'inteira');
    });
})();
