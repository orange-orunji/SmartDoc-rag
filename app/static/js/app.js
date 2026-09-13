/* 企业知识库前端逻辑
   功能：登录注册 / 会话管理 / 消息流式渲染 / 文档上传 */

const API_BASE = 'http://127.0.0.1:8000';

const ICONS = {
    edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>',
};

let authMode = 'login';
let token = null;
let username = '';
let currentSessionId = '';
let messages = [];
let isStreaming = false;
let awaitingApproval = false;   // 待审批：中断挂起期间锁定输入

/* ──────────────────────────
   初始化
   ────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    const savedToken = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');
    if (savedToken && savedUser) {
        token = savedToken;
        username = savedUser;
        showChatPage();
    }
});

/* ──────────────────────────
   登录 / 注册
   ────────────────────────── */
function switchAuthTab(mode) {
    authMode = mode;
    document.getElementById('tab-login').classList.toggle('active', mode === 'login');
    document.getElementById('tab-register').classList.toggle('active', mode === 'register');
    document.getElementById('auth-form-title').textContent = mode === 'login' ? '登录' : '注册';
    document.getElementById('auth-submit-btn').textContent = mode === 'login' ? '登录' : '注册';
    document.getElementById('auth-msg').textContent = '';
    document.getElementById('auth-msg').className = 'auth-msg';
}

async function handleAuth(e) {
    e.preventDefault();
    const user = document.getElementById('auth-username').value.trim();
    const pass = document.getElementById('auth-password').value;
    if (!user || !pass) return;

    const btn = document.getElementById('auth-submit-btn');
    btn.disabled = true;
    btn.textContent = '处理中...';
    const msgEl = document.getElementById('auth-msg');
    msgEl.textContent = '';
    msgEl.className = 'auth-msg';

    try {
        const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
        const resp = await fetch(API_BASE + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });

        if (resp.ok) {
            const data = await resp.json();
            if (authMode === 'register') {
                msgEl.className = 'auth-msg success';
                msgEl.textContent = '注册成功，请登录。';
                switchAuthTab('login');
            } else {
                token = data.access_token;
                username = user;
                localStorage.setItem('access_token', token);
                localStorage.setItem('user', username);
                showChatPage();
            }
        } else {
            const err = await resp.json().catch(() => ({}));
            msgEl.className = 'auth-msg error';
            msgEl.textContent = err.detail || '操作失败，请重试';
        }
    } catch (err) {
        msgEl.className = 'auth-msg error';
        msgEl.textContent = '网络错误，请确认后端服务是否运行';
    } finally {
        btn.disabled = false;
        btn.textContent = authMode === 'login' ? '登录' : '注册';
    }
}

function logout() {
    token = null;
    username = '';
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    currentSessionId = '';
    messages = [];
    document.getElementById('chat-page').classList.add('hidden');
    document.getElementById('auth-page').classList.remove('hidden');
    document.getElementById('auth-username').value = '';
    document.getElementById('auth-password').value = '';
}

/* ──────────────────────────
   进入主界面
   ────────────────────────── */
async function showChatPage() {
    document.getElementById('auth-page').classList.add('hidden');
    document.getElementById('chat-page').classList.remove('hidden');
    document.getElementById('display-username').textContent = username;
    document.getElementById('avatar-initial').textContent =
        (username.charAt(0) || '?').toUpperCase();

    if (!currentSessionId) {
        currentSessionId = username + '_' + newSessionSuffix();
    }

    await loadSessions();
    await loadHistory();
    updateHeaderSession();
    await checkPendingInterrupt();
}

function newSessionSuffix() {
    return crypto.randomUUID
        ? crypto.randomUUID().slice(0, 8)
        : Math.random().toString(36).slice(2, 10);
}

/* ──────────────────────────
   会话管理
   ────────────────────────── */
async function loadSessions() {
    const listEl = document.getElementById('session-list');
    try {
        const resp = await fetch(API_BASE + '/api/chat/sessions', {
            headers: authHeaders()
        });
        if (resp.status === 401) { logout(); return; }
        if (!resp.ok) throw new Error('Failed to load sessions');
        const data = await resp.json();
        const sessions = data.sessions || [];

        if (currentSessionId && !sessions.includes(currentSessionId)) {
            sessions.unshift(currentSessionId);
        }

        if (sessions.length === 0) {
            listEl.innerHTML = '<div class="session-list-hint">暂无会话，点击上方新建</div>';
            return;
        }
        listEl.innerHTML = sessions.map(s =>
            `<div class="session-item${s === currentSessionId ? ' active' : ''}" onclick="switchSession('${escapeHtml(s)}')">
                <span class="session-name">${escapeHtml(s)}</span>
                <button class="btn-icon" data-sid="${escapeHtml(s)}"
                    onclick="event.stopPropagation();startRename(this)" title="重命名">${ICONS.edit}</button>
                <button class="btn-icon danger" data-sid="${escapeHtml(s)}"
                    onclick="event.stopPropagation();deleteSession(this.dataset.sid)" title="删除">${ICONS.trash}</button>
            </div>`
        ).join('');
    } catch (err) {
        listEl.innerHTML = '<div class="session-list-hint" style="color:#e07a72;">加载失败</div>';
    }
}

function createSession() {
    currentSessionId = username + '_' + newSessionSuffix();
    messages = [];
    awaitingApproval = false;
    unlockInput();
    renderMessages();
    loadSessions();
    updateHeaderSession();
}

async function switchSession(sessionId) {
    if (sessionId === currentSessionId) return;
    currentSessionId = sessionId;
    messages = [];
    awaitingApproval = false;
    unlockInput();
    renderMessages();
    await loadHistory();
    await loadSessions();
    updateHeaderSession();
    await checkPendingInterrupt();
}

async function deleteSession(sessionId) {
    if (!confirm(`确定要删除会话 "${sessionId}" 吗？`)) return;
    try {
        await fetch(API_BASE + '/api/chat/session/' + encodeURIComponent(sessionId), {
            method: 'DELETE',
            headers: authHeaders()
        });
        if (sessionId === currentSessionId) {
            createSession();
        } else {
            await loadSessions();
        }
    } catch (err) {
        alert('删除失败: ' + err.message);
    }
}

function updateHeaderSession() {
    document.getElementById('chat-header-session').textContent =
        currentSessionId ? '会话 · ' + currentSessionId : '新会话';
}

/* ──────────────────────────
   会话重命名
   ────────────────────────── */
function startRename(btn) {
    const sessionId = btn.dataset.sid;
    const item = btn.closest('.session-item');
    const span = item.querySelector('.session-name');
    if (!span) return;
    const oldName = span.textContent;

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'session-rename-input';
    input.value = oldName;
    span.replaceWith(input);
    input.focus();
    input.select();

    let finished = false;
    const finish = async () => {
        if (finished) return;
        finished = true;
        const newName = input.value.trim();
        if (!newName || newName === oldName) { input.replaceWith(span); return; }
        input.disabled = true;
        input.style.opacity = '0.5';
        try {
            const url = API_BASE + '/api/chat/session/' + encodeURIComponent(sessionId) + '/rename';
            const resp = await fetch(url, {
                method: 'PUT',
                headers: { ...authHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: newName })
            });
            if (resp.ok) {
                const data = await resp.json();
                if (sessionId === currentSessionId) {
                    currentSessionId = data.data.new_name;
                    updateHeaderSession();
                }
                await loadSessions();
            } else {
                const err = await resp.json().catch(() => ({}));
                alert('重命名失败: ' + (err.message || 'HTTP ' + resp.status));
                input.replaceWith(span);
            }
        } catch (err) {
            alert('网络错误: ' + err.message);
            input.replaceWith(span);
        }
    };

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); finish(); }
        if (e.key === 'Escape') { finished = true; input.replaceWith(span); }
    });
    input.addEventListener('blur', () => setTimeout(finish, 150));
}

/* ──────────────────────────
   历史消息
   ────────────────────────── */
async function loadHistory() {
    if (!currentSessionId) return;
    try {
        const resp = await fetch(API_BASE + '/api/chat/history/' + encodeURIComponent(currentSessionId), {
            headers: authHeaders()
        });
        if (resp.status === 401) { logout(); return; }
        if (resp.ok) {
            const data = await resp.json();
            messages = data.messages || [];
            renderMessages();
        }
    } catch (err) {
        /* 历史加载失败不阻断对话 */
    }
}

/* ──────────────────────────
   消息渲染
   ────────────────────────── */
function renderMessages() {
    const container = document.getElementById('chat-messages');
    if (!messages || messages.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>选择或新建一个会话开始对话</p></div>';
        return;
    }
    container.innerHTML = messages.map(m => {
        const role = (m.role === 'human' || m.role === 'user') ? 'user' : 'assistant';
        const label = role === 'user' ? '你' : '助手';
        return `<div class="message ${role}">
            <div class="msg-role">${label}</div>
            <div class="msg-bubble">${formatContent(m.content)}</div>
        </div>`;
    }).join('');
    scrollToBottom();
}

function appendMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const empty = container.querySelector('.empty-state');
    if (empty) empty.remove();

    const label = role === 'user' ? '你' : '助手';
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `<div class="msg-role">${label}</div><div class="msg-bubble">${formatContent(content)}</div>`;
    container.appendChild(div);
    scrollToBottom();
    return div;
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
}

/* GFM 表格贪婪吞行：LLM 流式输出常在两块内容间漏空行，marked 会把
   ① 相邻表格合并；② 表格后的无竖线说明文字吞进表格成为一行；③ 列表项后的表格嵌套进 <li>。
   修复：表格状态机——检测到"新表格开始"（表头行 + 下一行分隔行）且前面紧跟内容时补空行；
   表格内出现无竖线行（说明文字/新块）时强制结束表格。 */
function normalizeTables(text) {
    const lines = text.split('\n');
    const sepRe = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/;
    const headRe = /^\s*\|.*\|/;
    const out = [];
    let inTable = false;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const next = (lines[i + 1] || '').trim();
        if (!inTable) {
            if (headRe.test(line) && sepRe.test(next)) {
                const prev = out.length ? out[out.length - 1].trim() : '';
                if (prev !== '' && !sepRe.test(prev)) {
                    out.push('');
                }
                inTable = true;
            }
        } else {
            if (!line.includes('|')) {
                inTable = false;
                out.push('');
            }
        }
        out.push(line);
    }
    return out.join('\n');
}

function formatContent(text) {
    if (!text) return '';
    // 后端以 JSON 字符串编码 SSE 帧，这里拿到的是原始文本（含真实换行、字面 \n 无损）
    // breaks: true —— LLM 常用单个 \n 分段，默认 breaks:false 会把单换行折叠成空格
    return marked.parse(normalizeTables(text), { breaks: true });
}

/* ──────────────────────────
   发送消息（SSE 流式）
   ────────────────────────── */
function handleInputKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

/* 输入区锁定/解锁（待审批期间禁用） */
function lockInput() {
    document.getElementById('send-btn').disabled = true;
    document.getElementById('chat-input').disabled = true;
}

function unlockInput() {
    document.getElementById('send-btn').disabled = false;
    document.getElementById('chat-input').disabled = false;
    document.getElementById('chat-input').focus();
}

/** 消费 SSE 响应流：文本渲染进 bubble，工具提示独立展示，中断帧捕获返回
 *  返回 { fullResponse, interrupt } —— interrupt 非空表示图已挂起等待审批 */
async function consumeStream(resp, assistantDiv, bubble) {
    let fullResponse = '';
    let interrupt = null;
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const handleFrame = (raw) => {
        if (!raw || raw === '[DONE]') return;
        let data;
        try { data = JSON.parse(raw); } catch { data = raw; }

        // 中断帧（JSON object）：捕获，交给上层渲染审批卡片，不并入文本
        if (typeof data === 'object' && data !== null) {
            if (data.type === 'interrupt') interrupt = data;
            return;
        }

        // 工具调用提示：渲染为独立提示条，不并入回答文本
        if (data.startsWith('[调用工具')) {
            const tip = document.createElement('div');
            tip.className = 'tool-call-tip';
            tip.textContent = data;
            assistantDiv.insertBefore(tip, bubble);
            scrollToBottom();
            return;
        }

        fullResponse += data;
        bubble.innerHTML = formatContent(fullResponse);
        scrollToBottom();
    };

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data: ')) continue;
            handleFrame(trimmed.slice(6));
        }
    }
    if (buffer.trim().startsWith('data: ')) {
        handleFrame(buffer.trim().slice(6));
    }
    return { fullResponse, interrupt };
}

/** 审批卡片：展示中断 payload，用户确认/取消后走 resume 恢复流 */
function renderApprovalCard(interrupt, assistantDiv, bubble) {
    const p = interrupt.payload || {};
    awaitingApproval = true;
    lockInput();

    const card = document.createElement('div');
    card.className = 'approval-card';

    const title = document.createElement('div');
    title.className = 'approval-card-title';
    title.textContent = (p.to || p.subject) ? '📋 待确认操作 · 发送邮件' : '📋 待确认操作';
    card.appendChild(title);

    const addRow = (k, v) => {
        if (v === undefined || v === null || v === '') return;
        const row = document.createElement('div');
        row.className = 'approval-card-row';
        const kEl = document.createElement('span');
        kEl.className = 'k';
        kEl.textContent = k;
        const vEl = document.createElement('span');
        vEl.className = 'v';
        vEl.textContent = v;
        row.appendChild(kEl);
        row.appendChild(vEl);
        card.appendChild(row);
    };
    addRow('收件人', p.to);
    addRow('主　题', p.subject);
    addRow('正　文', p.body);
    if (Array.isArray(p.attachment) && p.attachment.length) {
        addRow('附　件', p.attachment.join('、'));
    }

    const actions = document.createElement('div');
    actions.className = 'approval-card-actions';
    const btnConfirm = document.createElement('button');
    btnConfirm.className = 'approval-btn approval-btn-confirm';
    btnConfirm.textContent = '确认发送';
    const btnCancel = document.createElement('button');
    btnCancel.className = 'approval-btn approval-btn-cancel';
    btnCancel.textContent = '取消';
    actions.appendChild(btnConfirm);
    actions.appendChild(btnCancel);
    card.appendChild(actions);

    const status = document.createElement('div');
    status.className = 'approval-card-status';
    card.appendChild(status);

    btnConfirm.onclick = () => sendResume(true, status, btnConfirm, btnCancel, assistantDiv, bubble);
    btnCancel.onclick = () => sendResume(false, status, btnConfirm, btnCancel, assistantDiv, bubble);

    assistantDiv.appendChild(card);
    scrollToBottom();
}

/** 查询当前会话是否有待审批中断；有则重建审批卡片（覆盖切会话/刷新页面/换设备场景） */
async function checkPendingInterrupt() {
    if (!currentSessionId || !token) return;
    try {
        const resp = await fetch(API_BASE + '/api/chat/pending/' + encodeURIComponent(currentSessionId), {
            method: 'POST',
            headers: authHeaders()
        });
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.interrupt) return;   // 无待审批 → 不做事（输入保持解锁）

        const container = document.getElementById('chat-messages');
        const empty = container.querySelector('.empty-state');
        if (empty) empty.remove();

        // 重建一个助手气泡容器（占位文案会被恢复流的文本覆盖）+ 卡片
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = '<div class="msg-role">助手</div><div class="msg-bubble">⏳ 等待您的审批确认…</div>';
        container.appendChild(div);
        const bubble = div.querySelector('.msg-bubble');

        renderApprovalCard(data.interrupt, div, bubble);   // 内部会锁定输入
        scrollToBottom();
    } catch (err) {
        // 查询失败不阻断会话加载；用户发消息时后端防呆仍会兜底拦截
        console.warn('pending 查询失败:', err);
    }
}

/** 提交审批决定 → 消费恢复流（可能再次中断，链式支持） */
async function sendResume(decision, statusEl, btnConfirm, btnCancel, assistantDiv, bubble) {
    btnConfirm.disabled = true;
    btnCancel.disabled = true;
    statusEl.textContent = decision ? '已确认，正在执行…' : '已取消，正在通知助手…';
    isStreaming = true;

    let interruptData = null;
    try {
        const resp = await fetch(API_BASE + '/api/chat/resume', {
            method: 'POST',
            headers: { ...authHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, decision })
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || '请求失败');
        }
        const result = await consumeStream(resp, assistantDiv, bubble);
        interruptData = result.interrupt;
        if (result.fullResponse) {
            messages.push({ role: 'assistant', content: result.fullResponse });
        }
        statusEl.textContent = decision ? '✓ 已确认发送' : '✓ 已取消发送';
        statusEl.classList.add('done');
    } catch (err) {
        statusEl.textContent = '【错误】' + err.message;
    } finally {
        isStreaming = false;
        scrollToBottom();
    }

    // 恢复流再次中断（未来多审批点）→ 继续渲染新卡片；否则解锁输入
    awaitingApproval = false;
    if (interruptData) {
        renderApprovalCard(interruptData, assistantDiv, bubble);
    } else {
        unlockInput();
    }
}

async function sendMessage() {
    if (isStreaming || awaitingApproval) return;
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question || !currentSessionId) return;

    input.value = '';
    input.style.height = 'auto';

    messages.push({ role: 'user', content: question });
    appendMessage('user', question);

    const assistantDiv = appendMessage('assistant', '');
    const bubble = assistantDiv.querySelector('.msg-bubble');

    isStreaming = true;
    lockInput();

    let interruptData = null;
    try {
        const resp = await fetch(API_BASE + '/api/chat/stream', {
            method: 'POST',
            headers: { ...authHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, session_id: currentSessionId })
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || '请求失败');
        }

        const result = await consumeStream(resp, assistantDiv, bubble);
        interruptData = result.interrupt;
        if (result.fullResponse) {
            messages.push({ role: 'assistant', content: result.fullResponse });
        }
    } catch (err) {
        bubble.textContent = '【错误】' + err.message;
        bubble.style.color = 'var(--danger)';
    } finally {
        isStreaming = false;
        bubble.style.color = '';
        scrollToBottom();
    }

    // 流结束后若遇到审批中断 → 渲染卡片并锁定输入（等用户决定）
    if (interruptData) {
        renderApprovalCard(interruptData, assistantDiv, bubble);
    } else {
        unlockInput();
    }
}

/* ──────────────────────────
   文档上传
   ────────────────────────── */
async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const statusEl = document.getElementById('upload-status');
    statusEl.textContent = '上传中...';
    statusEl.style.color = 'var(--sidebar-text-dim)';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch(API_BASE + '/api/document/upload', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            body: formData
        });

        if (resp.ok) {
            const data = await resp.json();
            statusEl.textContent = data.message || '上传成功';
            statusEl.style.color = '#7fd19a';
        } else {
            const err = await resp.json().catch(() => ({}));
            statusEl.textContent = err.detail || '上传失败';
            statusEl.style.color = '#f2a5a0';
        }
    } catch (err) {
        statusEl.textContent = '网络错误';
        statusEl.style.color = '#f2a5a0';
    }

    e.target.value = '';
    setTimeout(() => { statusEl.textContent = ''; }, 4000);
}

/* ──────────────────────────
   工具函数
   ────────────────────────── */
function authHeaders() {
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* 输入框自适应高度 */
document.addEventListener('input', function (e) {
    if (e.target.id === 'chat-input') {
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 130) + 'px';
    }
});
