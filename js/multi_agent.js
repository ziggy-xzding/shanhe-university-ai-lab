const messages = document.getElementById('multiAgentMessages');
const agentList = document.getElementById('subAgentList');
const bookList = document.getElementById('bookList');
const uploadBox = document.getElementById('bookUploadBox');
let selectedAgentType = null;
let sessionId = null;

function addMessage(role, text, meta = '') {
    const item = document.createElement('article');
    item.className = `sh-agent-message ${role}`;
    const label = document.createElement('strong');
    label.textContent = role === 'user' ? '你' : '山河主智能体';
    const body = document.createElement('p');
    body.textContent = text;
    item.append(label, body);
    if (meta) { const note = document.createElement('small'); note.textContent = meta; item.append(note); }
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
}

function createStreamingMessage() {
    const item = document.createElement('article');
    item.className = 'sh-agent-message assistant';
    const label = document.createElement('strong');
    label.textContent = '山河主智能体';
    const body = document.createElement('p');
    body.textContent = '正在理解你的问题…';
    const note = document.createElement('small');
    note.textContent = '正在分配专业智能体';
    item.append(label, body, note);
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
    return {item, label, body, note};
}

function parseSseBlock(block) {
    let event = 'message';
    let data = '';
    block.split(/\r?\n/).forEach(line => {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        if (line.startsWith('data:')) data += line.slice(5).trim();
    });
    try { return {event, data: JSON.parse(data)}; } catch { return {event, data: {}}; }
}

function renderAgents(items) {
    agentList.innerHTML = '';
    items.forEach(agent => {
        const item = document.createElement('div');
        item.className = 'sh-sub-agent';
        item.dataset.agentType = agent.key;
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');
        item.setAttribute('aria-pressed', 'false');
        item.title = `指定由${agent.name}回答，点击可取消指定`;
        item.innerHTML = `<span class="sh-sub-agent-icon"><i class="bi ${agent.icon}"></i></span><span><strong></strong><small></small></span><b>待命</b>`;
        item.querySelector('strong').textContent = agent.name;
        item.querySelector('small').textContent = agent.hint;
        const select = () => {
            selectedAgentType = selectedAgentType === agent.key ? null : agent.key;
            agentList.querySelectorAll('.sh-sub-agent').forEach(node => {
                const active = node.dataset.agentType === selectedAgentType;
                node.classList.toggle('is-selected', active);
                node.setAttribute('aria-pressed', String(active));
                node.querySelector('b').textContent = active ? '已指定' : '待命';
            });
            multiAgentInput.placeholder = selectedAgentType ? `已指定${agent.name}，也可以直接描述问题` : '例如：桃园三结义是哪三个人？或查询我的成绩';
        };
        item.addEventListener('click', select);
        item.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); } });
        agentList.appendChild(item);
    });
}

function renderBooks(items, canUpload) {
    bookList.innerHTML = '';
    items.slice(0, 3).forEach(book => {
        const item = document.createElement('div');
        item.className = 'sh-book-item';
        item.innerHTML = `<i class="bi bi-book"></i><span><strong></strong><small></small></span><b></b>`;
        item.querySelector('strong').textContent = book.book_name;
        const version = book.version ? `v${book.version}` : '';
        const progress = Number.isFinite(book.progress) ? ` ${book.progress}%` : '';
        item.querySelector('small').textContent = `${version} · ${book.source || '内置知识库'} · ${book.chunks || 0} 个片段${progress}`;
        const labels = {ready: '可检索', queued: '排队中', processing: '处理中', failed: '处理失败', archived: '历史版本'};
        item.querySelector('b').textContent = labels[book.status] || '待处理';
        if (book.status === 'failed' && book.error) item.title = book.error;
        bookList.appendChild(item);
    });
    uploadBox.classList.toggle('d-none', !canUpload);
}

let bookPolling = null;
async function loadBooks() {
    const response = await fetch('/api/multi-agent/knowledge/books');
    if (!response.ok) return;
    const data = await response.json();
    const items = data.items || [];
    renderBooks(items, data.can_upload);
    const active = items.some(book => ['queued', 'processing'].includes(book.status));
    if (active && !bookPolling) bookPolling = setTimeout(() => { bookPolling = null; loadBooks(); }, 2000);
}

async function loadWorkspace() {
    const [agentsResponse] = await Promise.all([fetch('/api/multi-agent/agents'), loadBooks()]);
    if (agentsResponse.ok) renderAgents((await agentsResponse.json()).sub_agents || []);
    addMessage('assistant', '你好，我是山河主智能体。你可以查询校务数据，也可以从知识库检索学习和图书内容。');
}

const multiAgentForm = document.getElementById('multiAgentForm');
const multiAgentInput = document.getElementById('multiAgentInput');

multiAgentInput.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        multiAgentForm.requestSubmit();
    }
});

multiAgentForm.addEventListener('submit', async event => {
    event.preventDefault();
    const input = multiAgentInput;
    const question = input.value.trim();
    if (!question) return;
    addMessage('user', question);
    input.value = '';
    const submitButton = multiAgentForm.querySelector('button[type="submit"]');
    const streamMessage = createStreamingMessage();
    input.disabled = true;
    submitButton.disabled = true;
    try {
        const requestBody = {message: question};
        if (selectedAgentType) requestBody.agent_type = selectedAgentType;
        if (sessionId) requestBody.session_id = sessionId;
        const response = await fetch('/api/multi-agent/chat/stream', {method: 'POST', headers: {'Content-Type': 'application/json', 'Accept': 'text/event-stream'}, body: JSON.stringify(requestBody)});
        if (!response.ok || !response.body) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || '智能体暂时不可用');
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let agentMeta = {};
        const consume = block => {
            if (!block.trim()) return;
            const eventData = parseSseBlock(block);
            if (eventData.event === 'status') streamMessage.note.textContent = eventData.data.message || '正在处理';
            if (eventData.event === 'meta') {
                agentMeta = eventData.data;
                streamMessage.label.textContent = agentMeta.agent_name || '山河主智能体';
                const trace = (agentMeta.agent_trace || []).map(item => item.name).join(' → ');
                const confidence = agentMeta.routing?.confidence;
                streamMessage.note.textContent = `${trace || '山河主智能体'} · ${confidence != null ? `路由置信度 ${(confidence * 100).toFixed(0)}%` : '正在生成回答'}`;
                streamMessage.body.textContent = '';
            }
            if (eventData.event === 'token') {
                streamMessage.body.textContent += eventData.data.text || '';
                messages.scrollTop = messages.scrollHeight;
            }
            if (eventData.event === 'done') {
                const data = eventData.data;
                if (data.session_id) sessionId = data.session_id;
                const sourceNames = (data.sources || []).map(source => source.book_name).filter(Boolean);
                streamMessage.label.textContent = data.agent_name || agentMeta.agent_name || '山河主智能体';
                const trace = (data.agent_trace || agentMeta.agent_trace || []).map(item => item.name).join(' → ');
                const toolNames = (data.tool_calls || []).filter(tool => tool.status === 'completed').map(tool => tool.name || tool.tool_name);
                const taskDetail = data.sub_tasks?.length ? `已拆解 ${data.sub_tasks.length} 个子任务` : '';
                const detail = taskDetail || (toolNames.length ? `工具：${[...new Set(toolNames)].join('、')}` : (sourceNames.length ? `来源：${[...new Set(sourceNames)].join('、')}` : '校园数据范围内回答'));
                const memory = data.memory_turns ? `已关联 ${data.memory_turns} 轮对话` : '新会话';
                streamMessage.note.textContent = `${trace || data.agent_name || '山河主智能体'} · ${detail} · ${memory}`;
            }
            if (eventData.event === 'error') throw new Error(eventData.data.message || '智能体流式输出中断');
        };
        while (true) {
            const {value, done} = await reader.read();
            buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
            const blocks = buffer.split(/\r?\n\r?\n/);
            buffer = blocks.pop() || '';
            blocks.forEach(consume);
            if (done) break;
        }
        if (buffer.trim()) consume(buffer);
    } catch (error) {
        streamMessage.body.textContent = error.message;
        streamMessage.note.textContent = '请求未完成';
    } finally {
        input.disabled = false;
        submitButton.disabled = false;
        input.focus();
    }
});

document.getElementById('bookUploadButton').addEventListener('click', async () => {
    const file = document.getElementById('bookFile').files[0];
    if (!file) return;
    const form = new FormData();
    form.append('book_name', document.getElementById('bookName').value.trim() || '新教材');
    form.append('file', file);
    const response = await fetch('/api/multi-agent/knowledge/books', {method: 'POST', body: form});
    const data = await response.json();
    addMessage('assistant', response.ok ? data.message : (data.detail || '书籍上传失败'));
    if (response.ok) await loadBooks();
});

loadWorkspace();
