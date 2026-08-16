(function () {
    const widget = document.getElementById('assistant-widget');
    const fab = document.getElementById('assistant-fab');
    const panel = document.getElementById('assistant-panel');
    const closeBtn = document.getElementById('assistant-close');
    const messagesEl = document.getElementById('assistant-messages');
    const suggestionsEl = document.getElementById('assistant-suggestions');
    const form = document.getElementById('assistant-form');
    const input = document.getElementById('assistant-input');
    const sendBtn = document.getElementById('assistant-send');
    const modeEl = document.getElementById('assistant-mode');

    if (!widget || !fab || !panel) return;

    const audience = widget.dataset.audience || 'cliente';
    let history = [];
    let isLoading = false;

    function getCsrfToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        if (el) return el.value;
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function formatReply(text) {
        let html = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/_(.+?)_/g, '<em>$1</em>');

        const lines = html.split('\n');
        const parts = [];
        let inList = false;

        lines.forEach((line) => {
            const trimmed = line.trim();
            if (trimmed.startsWith('• ') || trimmed.startsWith('- ')) {
                if (!inList) { parts.push('<ul>'); inList = true; }
                parts.push(`<li>${trimmed.slice(2)}</li>`);
            } else {
                if (inList) { parts.push('</ul>'); inList = false; }
                if (trimmed) parts.push(`<p>${trimmed}</p>`);
            }
        });
        if (inList) parts.push('</ul>');
        return parts.join('') || `<p>${html}</p>`;
    }

    function appendMessage(role, content, extraClass) {
        const div = document.createElement('div');
        div.className = `assistant-msg ${role} ${extraClass || ''}`.trim();
        if (role === 'bot') {
            div.innerHTML = formatReply(content);
        } else {
            div.textContent = content;
        }
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    }

    function renderSuggestions(items) {
        suggestionsEl.innerHTML = '';
        (items || []).forEach((text) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'assistant-chip';
            btn.textContent = text;
            btn.addEventListener('click', () => {
                input.value = text;
                form.dispatchEvent(new Event('submit'));
            });
            suggestionsEl.appendChild(btn);
        });
    }

    function openPanel() {
        panel.hidden = false;
        fab.classList.add('is-open');
        input.focus();
    }

    function closePanel() {
        panel.hidden = true;
        fab.classList.remove('is-open');
    }

    async function initAssistant() {
        try {
            const res = await fetch(`/api/assistente/init/?audience=${encodeURIComponent(audience)}`);
            const data = await res.json();
            if (!res.ok) return;
            appendMessage('bot', data.greeting);
            renderSuggestions(data.suggestions);
            if (data.ai_enabled) {
                modeEl.textContent = 'IA generativa';
                modeEl.classList.add('is-ai');
            } else {
                modeEl.textContent = 'Modo guiado';
            }
        } catch {
            appendMessage('bot', 'Olá! Como posso ajudar?');
        }
    }

    async function sendMessage(text) {
        if (!text.trim() || isLoading) return;

        isLoading = true;
        sendBtn.disabled = true;
        input.disabled = true;

        appendMessage('user', text.trim());
        history.push({ role: 'user', content: text.trim() });

        const typingEl = appendMessage('bot', 'Pensando...', 'typing');

        try {
            const res = await fetch('/api/assistente/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                credentials: 'same-origin',
                body: JSON.stringify({ message: text.trim(), history, audience }),
            });

            const data = await res.json();
            typingEl.remove();

            if (!res.ok) {
                appendMessage('bot', data.error || 'Não foi possível obter resposta.');
                return;
            }

            appendMessage('bot', data.reply);
            history.push({ role: 'assistant', content: data.reply });
            if (history.length > 20) history = history.slice(-20);
        } catch {
            typingEl.remove();
            appendMessage('bot', 'Erro de conexão. Verifique se o servidor está rodando.');
        } finally {
            isLoading = false;
            sendBtn.disabled = false;
            input.disabled = false;
            input.value = '';
            input.focus();
        }
    }

    fab.addEventListener('click', openPanel);
    closeBtn.addEventListener('click', closePanel);
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage(input.value);
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !panel.hidden) closePanel();
    });

    initAssistant();
})();
