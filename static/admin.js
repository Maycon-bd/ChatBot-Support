// ─────────────────────────────────────────────────
// ERP Support Assistant — Admin Panel JS
// ─────────────────────────────────────────────────

let adminKey = null;
const TENANT_ID = 'quantum_corp';

// ── Login ──────────────────────────────────────
function doLogin() {
    const input = document.getElementById('admin-password-input');
    const key   = input.value.trim();
    if (!key) return;

    const btn = document.getElementById('btn-login');
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2"></i> Verificando...';
    lucide.createIcons();

    // Testa a chave tentando listar documentos
    fetch('/api/v1/documents/list', {
        headers: { 'X-Admin-Key': key, 'X-Tenant-ID': TENANT_ID }
    }).then(res => {
        if (res.ok) {
            adminKey = key;
            sessionStorage.setItem('adminKey', key);
            showPanel();
        } else {
            showLoginError('Senha incorreta. Tente novamente.');
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="log-in"></i> Acessar Painel';
            lucide.createIcons();
        }
    }).catch(() => {
        showLoginError('Erro de conexão com o servidor.');
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="log-in"></i> Acessar Painel';
        lucide.createIcons();
    });
}

function showLoginError(msg) {
    const el = document.getElementById('login-error');
    document.getElementById('login-error-msg').textContent = msg;
    el.classList.add('show');
    lucide.createIcons();
    setTimeout(() => el.classList.remove('show'), 4000);
}

function showPanel() {
    document.getElementById('login-card').style.display = 'none';
    document.getElementById('admin-panel').classList.add('show');
    loadDocs();
    lucide.createIcons();
}

function doLogout() {
    adminKey = null;
    sessionStorage.removeItem('adminKey');
    document.getElementById('login-card').style.display = '';
    document.getElementById('admin-panel').classList.remove('show');
    document.getElementById('admin-password-input').value = '';
    lucide.createIcons();
}

// ── Carregar lista de documentos ───────────────
async function loadDocs() {
    const list = document.getElementById('doc-list');
    list.innerHTML = `<div class="doc-empty"><i data-lucide="loader-2"></i>Carregando...</div>`;
    lucide.createIcons();

    try {
        const res  = await fetch('/api/v1/documents/list', {
            headers: { 'X-Admin-Key': adminKey, 'X-Tenant-ID': TENANT_ID }
        });
        const docs = await res.json();

        // Atualiza estatísticas
        document.getElementById('stat-docs').textContent   = docs.length;
        document.getElementById('stat-chunks').textContent = docs.reduce((a, d) => a + d.chunks, 0);

        if (docs.length === 0) {
            list.innerHTML = `
                <div class="doc-empty">
                    <i data-lucide="inbox"></i>
                    Nenhum documento indexado ainda.<br>
                    <span style="font-size:11px;">Faça upload de um manual acima.</span>
                </div>`;
            lucide.createIcons();
            return;
        }

        list.innerHTML = docs.map(doc => `
            <div class="doc-item" id="doc-${CSS.escape(doc.source)}">
                <div class="doc-icon"><i data-lucide="file-text"></i></div>
                <div class="doc-info">
                    <p class="doc-name" title="${escapeHtml(doc.source)}">${escapeHtml(doc.source)}</p>
                    <p class="doc-chunks">${doc.chunks} chunks indexados</p>
                </div>
                <button class="btn-delete-doc" title="Remover documento"
                        onclick="deleteDoc('${escapeHtml(doc.source)}')">
                    <i data-lucide="trash-2"></i>
                </button>
            </div>
        `).join('');
        lucide.createIcons();

    } catch (e) {
        list.innerHTML = `<div class="doc-empty" style="color:var(--color-error);">Erro ao carregar documentos.</div>`;
    }
}

// ── Deletar documento ──────────────────────────
async function deleteDoc(source) {
    if (!confirm(`Remover "${source}" da base vetorial?\n\nEsta ação não pode ser desfeita.`)) return;

    try {
        const res = await fetch(`/api/v1/documents/delete?source=${encodeURIComponent(source)}`, {
            method: 'DELETE',
            headers: { 'X-Admin-Key': adminKey, 'X-Tenant-ID': TENANT_ID }
        });

        if (res.ok) {
            // Remove item com animação
            const el = document.querySelector(`[title="${CSS.escape(source)}"]`)?.closest('.doc-item');
            if (el) {
                el.style.transition = 'opacity 0.3s, transform 0.3s';
                el.style.opacity = '0';
                el.style.transform = 'translateX(-10px)';
                setTimeout(() => loadDocs(), 350);
            } else {
                loadDocs();
            }
        } else {
            const data = await res.json();
            alert(`Erro ao remover: ${data.detail || 'Erro desconhecido'}`);
        }
    } catch (e) {
        alert('Erro de conexão ao tentar remover o documento.');
    }
}

// ── Upload de documento ────────────────────────
let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
    const fileInput  = document.getElementById('admin-file-input');
    const dropZone   = document.getElementById('admin-drop-zone');
    const fileNameEl = document.getElementById('admin-file-name');
    const btnUpload  = document.getElementById('btn-admin-upload');

    // Recupera sessão
    const saved = sessionStorage.getItem('adminKey');
    if (saved) { adminKey = saved; showPanel(); }

    fileInput.addEventListener('change', e => {
        handleFileSelect(e.target.files[0]);
    });

    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
    });

    function handleFileSelect(file) {
        if (!file) return;
        const valid = ['.txt', '.md', '.html'];
        const ext   = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
        if (!valid.includes(ext)) {
            showAdminStatus('Formato inválido. Use .txt, .md ou .html.', 'error');
            return;
        }
        selectedFile = file;
        fileNameEl.textContent = file.name;
        btnUpload.disabled = false;
        showAdminStatus('', '');
    }
});

async function adminUpload() {
    if (!selectedFile) return;

    const btn      = document.getElementById('btn-admin-upload');
    const progress = document.getElementById('upload-progress');

    btn.disabled = true;
    progress.classList.add('show');
    showAdminStatus('', '');
    lucide.createIcons();

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const res  = await fetch('/api/v1/documents/upload', {
            method: 'POST',
            headers: {
                'X-Admin-Key': adminKey,
                'X-Tenant-ID': TENANT_ID
            },
            body: formData
        });
        const data = await res.json();

        progress.classList.remove('show');

        if (res.ok) {
            showAdminStatus(`✔ ${data.message} (${data.chunks_count} chunks)`, 'success');
            document.getElementById('admin-file-name').textContent = 'Nenhum arquivo selecionado';
            document.getElementById('admin-file-input').value = '';
            selectedFile = null;
            btn.disabled = true;
            // Atualiza lista após 800ms
            setTimeout(loadDocs, 800);
        } else {
            showAdminStatus(`Erro: ${data.detail || 'Erro desconhecido'}`, 'error');
            btn.disabled = false;
        }
    } catch (e) {
        progress.classList.remove('show');
        showAdminStatus(`Erro de conexão: ${e.message}`, 'error');
        btn.disabled = false;
    }
}

function showAdminStatus(msg, type) {
    const el = document.getElementById('admin-upload-status');
    el.textContent = msg;
    el.className   = `status-message ${type}`;
}

function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
