// Configurações globais e Estado da UI
let activeTenant = 'quantum_corp';
let activeUser = 'visitante_feira';
let currentConversationId = null;
let attachedImageBase64 = null;

// Elementos do DOM
const userIdInput = document.getElementById('user-id-input');
const btnSaveTenant = document.getElementById('btn-save-tenant');
const displayTenantName = document.getElementById('display-tenant-name');
const displayUserId = document.getElementById('display-user-id');

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const btnSend = document.getElementById('btn-send');
const btnAttach = document.getElementById('btn-attach');
const imageInput = document.getElementById('image-input');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreview = document.getElementById('image-preview');
const btnRemoveImage = document.getElementById('btn-remove-image');
const btnClearChat = document.getElementById('btn-clear-chat');

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    updateTenantDisplay();
    setupEventListeners();
});

// Atualiza informações na UI
function updateTenantDisplay() {
    activeTenant = 'quantum_corp';
    activeUser = userIdInput ? (userIdInput.value.trim() || 'visitante_feira') : 'visitante_feira';

    if (displayTenantName) displayTenantName.innerText = 'Nexus ERP';
    if (displayUserId) displayUserId.innerText = `Usuário: ${activeUser}`;

    // Atualiza o chip de usuário no footer da sidebar ou modal
    const footerName = document.getElementById('footer-user-name');
    if (footerName) footerName.textContent = activeUser;
}

// Configuração de Event Listeners
function setupEventListeners() {
    // Salvar Perfil (modal)
    if (btnSaveTenant) {
        btnSaveTenant.addEventListener('click', () => {
            updateTenantDisplay();
            clearChatUI();
            currentConversationId = null;

            // Atualiza nome no header do modal
            const modalUsername = document.getElementById('profile-modal-username');
            if (modalUsername) modalUsername.textContent = activeUser;

            // Feedback visual dentro do modal
            const profileStatus = document.getElementById('profile-status');
            if (profileStatus) {
                profileStatus.textContent = `✔ Perfil salvo como ${activeUser}.`;
                profileStatus.className = 'status-message success';
                setTimeout(() => {
                    profileStatus.textContent = '';
                    profileStatus.className = 'status-message';
                    closeProfileModal();
                }, 1500);
            }
        });
    }

    // Limpar conversa
    if (btnClearChat) {
        btnClearChat.addEventListener('click', () => {
            clearChatUI();
            currentConversationId = null;
            appendSystemMessage('Conversa reiniciada. Nova sessão iniciada.');
        });
    }

    // Anexo de Imagem (Print de Erro)
    if (btnAttach) {
        btnAttach.addEventListener('click', () => imageInput && imageInput.click());
    }
    
    if (imageInput) {
        imageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    // Remove o cabeçalho base64 padrão do dataUrl para mandar puro para o backend
                    attachedImageBase64 = event.target.result.split(',')[1];
                    if (imagePreview) imagePreview.src = event.target.result;
                    if (imagePreviewContainer) imagePreviewContainer.classList.remove('hidden');
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Remover imagem anexada
    if (btnRemoveImage) {
        btnRemoveImage.addEventListener('click', () => {
            attachedImageBase64 = null;
            if (imageInput) imageInput.value = '';
            if (imagePreviewContainer) imagePreviewContainer.classList.add('hidden');
            if (imagePreview) imagePreview.src = '';
        });
    }

    // Enviar mensagem
    if (btnSend) btnSend.addEventListener('click', handleSendMessage);
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });
    }

    // Clique fora para fechar o dropdown
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('fc-dropdown');
        const menuBtn = document.getElementById('btn-header-menu');
        if (dropdown && dropdown.classList.contains('open')) {
            if (!dropdown.contains(e.target) && (!menuBtn || !menuBtn.contains(e.target))) {
                dropdown.classList.remove('open');
            }
        }
    });
}

// Dropdown do menu do topo
window.toggleHeaderMenu = function() {
    const dropdown = document.getElementById('fc-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('open');
    }
};

window.startNewChat = function() {
    clearChatUI();
    currentConversationId = null;
    
    // Close dropdown
    const dropdown = document.getElementById('fc-dropdown');
    if (dropdown) dropdown.classList.remove('open');
};

// Preenche input de chat via sugestões rápidas
function fillInput(text) {
    chatInput.value = text;
    chatInput.focus();
}

// Limpa chat
function clearChatUI() {
    // Remove all message wrappers
    const wrappers = chatMessages.querySelectorAll('.msg-wrapper');
    wrappers.forEach(w => w.remove());
    
    // Show welcome screen
    const welcomeCard = document.getElementById('fc-welcome');
    if (welcomeCard) {
        welcomeCard.classList.remove('hidden');
    }
    
    // Esconde o widget de tokens ao reiniciar a conversa
    const widget = document.getElementById('token-widget');
    if (widget) widget.classList.add('hidden');
    
    // Reseta alertas de tokens
    if (typeof notifiedThresholds !== 'undefined') {
        notifiedThresholds = { 100: false, 80: false, 50: false, 30: false, 10: false, 0: false };
    }
}

// Envia Mensagem de chat
async function handleSendMessage() {
    const text = chatInput.value.trim();
    const hasImage = attachedImageBase64 !== null;

    if (!text && !hasImage) return;

    // Desabilita botões temporariamente
    chatInput.value = '';
    chatInput.disabled = true;
    btnSend.disabled = true;

    // Remove/esconde welcome card se existir
    const welcomeCard = document.getElementById('fc-welcome');
    if (welcomeCard) {
        welcomeCard.classList.add('hidden');
    }

    // Adiciona a mensagem do Usuário na tela
    appendUserMessage(text, hasImage ? imagePreview.src : null);

    // Reseta visualizador de imagem
    const tempImageBase64 = attachedImageBase64;
    attachedImageBase64 = null;
    if (imagePreviewContainer) imagePreviewContainer.classList.add('hidden');
    if (imagePreview) imagePreview.src = '';
    if (imageInput) imageInput.value = '';

    // Adiciona indicador de digitação (Typing Indicator)
    const typingIndicator = appendTypingIndicator();

    try {
        const response = await fetch('/api/v1/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Tenant-ID': activeTenant
            },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                user_id: activeUser,
                content: text,
                image_base64: tempImageBase64
            })
        });

        // Remove indicador de digitação
        typingIndicator.remove();

        const data = await response.json();

        if (response.ok) {
            currentConversationId = data.conversation_id;
            
            // Adiciona resposta do Assistente
            appendAssistantResponse(data);
        } else {
            appendSystemMessage(`Erro na API: ${data.detail || 'Erro desconhecido'}`);
        }
    } catch (err) {
        typingIndicator.remove();
        appendSystemMessage(`Erro de conexão: ${err.message}`);
    } finally {
        chatInput.disabled = false;
        btnSend.disabled = false;
        chatInput.focus();
        scrollToBottom();
    }
}

// Renderiza mensagem do Usuário
function appendUserMessage(text, imageSrc) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper user';
    
    let imageHtml = '';
    if (imageSrc) {
        imageHtml = `<img src="${imageSrc}" class="msg-image" alt="Print anexado">`;
    }

    wrapper.innerHTML = `
        <div class="msg-bubble">
            ${imageHtml}
            <div>${formatMessageText(text)}</div>
        </div>
        <span class="msg-meta">Você • ${getCurrentTime()}</span>
    `;

    chatMessages.appendChild(wrapper);
    scrollToBottom();
}

// Renderiza resposta do Assistente
function appendAssistantResponse(data) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper assistant';
    
    // Constrói HTML do balão de resposta
    let contentHtml = `<div class="msg-bubble">${formatMessageText(data.response)}`;
    
    // Adiciona Card do Ticket se o Gemini tiver escalado para suporte humano
    if (data.is_action && data.ticket_id) {
        contentHtml += `
            <div class="ticket-card">
                <div class="ticket-icon-box">
                    <i data-lucide="ticket"></i>
                </div>
                <div class="ticket-details">
                    <h4>Chamado Técnico Aberto</h4>
                    <span class="ticket-id-badge">${data.ticket_id}</span>
                </div>
            </div>
        `;
    }

    // Adiciona Contexto do RAG expandível se houver trechos de manuais recuperados
    if (data.retrieved_context && data.retrieved_context.length > 0) {
        const uniqueId = 'rag-' + Math.random().toString(36).substr(2, 9);
        
        let contextChunksHtml = '';
        data.retrieved_context.forEach((chunk, i) => {
            contextChunksHtml += `
                <div class="rag-chunk">
                    <strong>Trecho ${i + 1}:</strong>
                    <p>${escapeHTML(chunk)}</p>
                </div>
            `;
        });

        contentHtml += `
            <div class="rag-context-box">
                <div class="rag-header" onclick="toggleContextVisibility('${uniqueId}')">
                    <span><i data-lucide="info" style="width:12px;height:12px;vertical-align:middle;margin-right:4px;"></i> Ver Contexto Recuperado (RAG)</span>
                    <i data-lucide="chevron-down" id="chevron-${uniqueId}"></i>
                </div>
                <div id="${uniqueId}" class="rag-content hidden">
                    ${contextChunksHtml}
                </div>
            </div>
        `;
    }
    
    contentHtml += `</div><span class="msg-meta">Support • ${getCurrentTime()}</span>`;
    wrapper.innerHTML = contentHtml;
    
    chatMessages.appendChild(wrapper);
    
    // Inicializa novos ícones Lucide gerados
    lucide.createIcons();

    // Atualiza o widget de tokens se o backend retornou usage
    if (data.token_usage) {
        updateTokenWidget(data.token_usage);
    }

    scrollToBottom();
}

// Adiciona mensagem informativa do sistema
function appendSystemMessage(text) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper assistant';
    wrapper.innerHTML = `
        <div class="msg-bubble" style="background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.2);">
            <i data-lucide="alert-triangle" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; color: var(--color-error); margin-right: 6px;"></i>
            <span>${text}</span>
        </div>
    `;
    chatMessages.appendChild(wrapper);
    lucide.createIcons();
    scrollToBottom();
}

// Animação de digitação
function appendTypingIndicator() {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper assistant';
    wrapper.innerHTML = `
        <div class="msg-bubble">
            <div class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
}

// Alternar visibilidade de contexto RAG
window.toggleContextVisibility = function(id) {
    const content = document.getElementById(id);
    const chevron = document.getElementById('chevron-' + id);
    
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        chevron.style.transform = 'rotate(180deg)';
    } else {
        content.classList.add('hidden');
        chevron.style.transform = 'rotate(0deg)';
    }
};

// Utilitários de Formatação
function formatMessageText(text) {
    if (!text) return '';
    // Converte quebras de linha simples
    let formatted = escapeHTML(text).replace(/\n/g, '<br>');
    // Converte negrito em markdown simples (**texto** -> <strong>texto</strong>)
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Converte código em linha (`código` -> <code>código</code>)
    formatted = formatted.replace(/`(.*?)`/g, '<code>$1</code>');
    return formatted;
}

function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Modal de Perfil — abre/fecha o popover no canto inferior esquerdo
window.openProfileModal = function() {
    const overlay = document.getElementById('profile-modal-overlay');
    const trigger = document.getElementById('btn-profile-trigger');
    if (!overlay) return;
    overlay.classList.add('open');
    trigger?.classList.add('open');
    lucide.createIcons();
};

window.closeProfileModal = function(event) {
    // Fecha ao clicar no overlay (fundo), mas não no modal em si
    if (event && event.target !== document.getElementById('profile-modal-overlay')) return;
    const overlay = document.getElementById('profile-modal-overlay');
    const trigger = document.getElementById('btn-profile-trigger');
    overlay?.classList.remove('open');
    trigger?.classList.remove('open');
};

// Fecha modal com Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const overlay = document.getElementById('profile-modal-overlay');
        const trigger = document.getElementById('btn-profile-trigger');
        overlay?.classList.remove('open');
        trigger?.classList.remove('open');
    }
});

// Estado global para alertas interativos de tokens
let notifiedThresholds = {
    100: false,
    80: false,
    50: false,
    30: false,
    10: false,
    0: false
};

// Exibe uma Notificação Flutuante (Toast)
function showTokenToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `token-toast ${type}`;
    
    let iconName = 'info';
    if (type === 'warning') iconName = 'alert-circle';
    if (type === 'critical') iconName = 'alert-triangle';

    toast.innerHTML = `
        <div class="toast-icon">
            <i data-lucide="${iconName}" style="width: 20px; height: 20px;"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;

    container.appendChild(toast);
    lucide.createIcons();

    // Animação de entrada
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    // Remove após 5 segundos
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400); // aguarda animação css
    }, 5000);
}

// Atualiza o widget de monitoramento de tokens da LLM
function updateTokenWidget(usage) {
    const widget       = document.getElementById('token-widget');
    const barFill      = document.getElementById('token-bar-fill');
    const countText    = document.getElementById('token-count-text');
    const alertBadge   = document.getElementById('token-alert-badge');

    if (!widget || !usage) return;

    const inputTokens  = usage.input_tokens  || 0;
    const outputTokens = usage.output_tokens || 0;
    const totalTokens  = usage.total_tokens  || (inputTokens + outputTokens);
    const contextWindow = usage.context_window || 1048576;
    
    // Porcentagem Restante!
    const ratio        = usage.usage_ratio   || (inputTokens / contextWindow);
    const remainingRatio = Math.max(0, 1 - ratio);
    const pctRemaining = (remainingRatio * 100).toFixed(1);

    // Mostra o widget
    widget.classList.remove('hidden');

    // Atualiza barra de progresso (encolhe conforme os tokens são consumidos)
    barFill.style.width = pctRemaining + '%';
    
    const isAlert = remainingRatio <= 0.20; // 20% restantes ou menos
    barFill.classList.toggle('warning', isAlert);

    // Texto de contagem
    countText.textContent = `Restante: ${pctRemaining}%`;

    // Badge de alerta visual
    if (isAlert) {
        alertBadge.classList.remove('hidden');
    } else {
        alertBadge.classList.add('hidden');
    }

    // Lógica de Notificações Interativas
    checkTokenThresholds(remainingRatio * 100);

    // Re-renderiza ícones do Lucide dentro do widget
    lucide.createIcons();
}

function checkTokenThresholds(pct) {
    if (pct >= 99 && !notifiedThresholds[100]) {
        showTokenToast('Cotas de Tokens a 100%', 'A sessão foi zerada! Você tem toda a janela de contexto disponível.', 'info');
        notifiedThresholds[100] = true;
    } else if (pct <= 80 && pct > 50 && !notifiedThresholds[80]) {
        showTokenToast('Consumo de Tokens', 'O histórico ativo consumiu 20%. Restam 80% das cotas.', 'info');
        notifiedThresholds[80] = true;
    } else if (pct <= 50 && pct > 30 && !notifiedThresholds[50]) {
        showTokenToast('Atenção: 50% Consumidos', 'Metade da sua cota de contexto já foi utilizada nesta sessão.', 'warning');
        notifiedThresholds[50] = true;
    } else if (pct <= 30 && pct > 10 && !notifiedThresholds[30]) {
        showTokenToast('Alerta de Limite: 30%', 'Restam apenas 30% do limite de tokens nesta sessão!', 'warning');
        notifiedThresholds[30] = true;
    } else if (pct <= 10 && pct > 0 && !notifiedThresholds[10]) {
        showTokenToast('Nível Crítico: 10%', 'Restam menos de 10% de tokens! O sistema poderá truncar ou sumarizar as próximas mensagens.', 'critical');
        notifiedThresholds[10] = true;
    } else if (pct <= 0 && !notifiedThresholds[0]) {
        showTokenToast('Limite Esgotado: 0%', 'Você atingiu 0% de cotas restantes.', 'critical');
        notifiedThresholds[0] = true;
    }
}
