/* Capa de filme: ao escolher a imagem, vira pôster vertical 2:3 sem cortar nada da foto. */
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
    preview.append(previewImg, previewTexto);
    input.insertAdjacentElement('afterend', preview);

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
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
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

    const montarPoster = (img) => {
        const canvas = document.createElement('canvas');
        canvas.width = LARGURA;
        canvas.height = ALTURA;
        const ctx = canvas.getContext('2d');
        fundoDesfocado(ctx, img);
        const escala = Math.min(LARGURA / img.naturalWidth, ALTURA / img.naturalHeight);
        const w = img.naturalWidth * escala;
        const h = img.naturalHeight * escala;
        ctx.shadowColor = 'rgba(0, 0, 0, 0.55)';
        ctx.shadowBlur = 40;
        ctx.drawImage(img, (LARGURA - w) / 2, (ALTURA - h) / 2, w, h);
        return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
    };

    const nomeJpg = (nome) => `${(nome || 'capa').replace(/\.[^.]+$/, '')}-vertical.jpg`;

    const mostrar = (arquivo, texto) => {
        if (previewImg.dataset.url) URL.revokeObjectURL(previewImg.dataset.url);
        const url = URL.createObjectURL(arquivo);
        previewImg.dataset.url = url;
        previewImg.src = url;
        previewTexto.textContent = texto;
        preview.hidden = false;
    };

    input.addEventListener('change', async () => {
        const arquivo = input.files && input.files[0];
        if (!arquivo || !arquivo.type.startsWith('image/') || input.dataset.ajustando === '1') return;
        let carregada;
        try {
            carregada = await carregar(arquivo);
        } catch (erro) {
            return;
        }
        const { img, url } = carregada;
        const proporcao = img.naturalWidth / img.naturalHeight;
        if (Math.abs(proporcao - PROPORCAO) <= TOLERANCIA) {
            URL.revokeObjectURL(url);
            mostrar(arquivo, 'A capa já está na vertical. Ela vai assim mesmo.');
            return;
        }
        const blob = await montarPoster(img);
        URL.revokeObjectURL(url);
        if (!blob || typeof DataTransfer === 'undefined') {
            mostrar(arquivo, 'Não deu para ajustar neste navegador. A capa vai como foi escolhida.');
            return;
        }
        const ajustado = new File([blob], nomeJpg(arquivo.name), { type: 'image/jpeg' });
        const lista = new DataTransfer();
        lista.items.add(ajustado);
        input.dataset.ajustando = '1';
        input.files = lista.files;
        delete input.dataset.ajustando;
        mostrar(ajustado, 'Capa ajustada para a vertical, com a foto inteira. É assim que vai aparecer na loja.');
    });
})();
