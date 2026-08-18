const drawer = document.getElementById('agentDrawer');
const launcher = document.getElementById('teacherLauncher');
const chatMessages = document.getElementById('chatMessages');

function notice(message) {
    const box = document.getElementById('growthNotice');
    if (!box) return;
    box.textContent = message;
    box.classList.remove('d-none');
}

function renderBars(scores) {
    const bars = document.getElementById('trendBars');
    if (!bars) return;
    bars.innerHTML = '';
    scores.forEach((item, index) => {
        const bar = document.createElement('div');
        bar.className = 'sh-trend-bar';
        bar.style.height = `${Math.max(10, Number(item.score) || 0)}%`;
        bar.setAttribute('aria-label', `第 ${index + 1} 次，${item.score} 分`);
        bar.innerHTML = `<span>${item.score}</span>`;
        bars.appendChild(bar);
    });
}

function renderRows(targetId, items, emptyText, buildRow) {
    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = '';
    (items || []).forEach(item => target.appendChild(buildRow(item)));
    if (!target.children.length) target.innerHTML = `<div class="sh-empty-panel">${emptyText}</div>`;
}

function createServiceRow(title, detail, badge, icon = 'bi-check2-circle') {
    const row = document.createElement('article');
    row.className = 'sh-service-row';
    row.innerHTML = `<i class="bi ${icon}"></i><span><strong></strong><small></small></span><b></b>`;
    row.querySelector('strong').textContent = title;
    row.querySelector('small').textContent = detail;
    row.querySelector('b').textContent = badge;
    return row;
}

async function archiveTodo(id) {
    const response = await fetch(`/api/student-agent/todos/${id}/read`, {method: 'PATCH'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '待办归档失败');
    await loadOverview();
}

function renderDevelopment(data) {
    document.getElementById('insightTitle').textContent = data.student_group || '学习阶段';
    renderRows('todoRows', data.todos, '当前没有待办事项', item => {
        const row = createServiceRow(item.title, item.description, item.priority === 'high' ? '优先处理' : '待查看', item.todo_type === 'library' ? 'bi-book' : 'bi-check2-circle');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-sm btn-outline-secondary ms-2';
        button.textContent = '已阅';
        button.title = '标记为已阅并归档';
        button.addEventListener('click', event => { event.stopPropagation(); archiveTodo(item.id).catch(error => notice(error.message)); });
        row.appendChild(button);
        if (item.href) {
            row.classList.add('js-clickable');
            row.title = '打开相关功能';
            row.addEventListener('click', event => { if (!event.target.closest('button')) location.assign(item.href); });
        }
        return row;
    });
    renderRows('announcementRows', data.announcements, '暂无学校推送', item => createServiceRow(item.title, item.content, item.published_at ? String(item.published_at).slice(0, 10) : '学校通知', 'bi-megaphone'));
    renderRows('recommendationRows', data.recommendations, '暂无新的推荐', item => {
        const row = createServiceRow(item.title, item.description, item.type === 'career' ? '就业推荐' : '持续学习', item.type === 'career' ? 'bi-briefcase' : 'bi-lightbulb');
        if (item.href) { row.classList.add('js-clickable'); row.addEventListener('click', () => location.assign(item.href)); }
        return row;
    });
}

function renderChat(role, text) {
    const bubble = document.createElement('div');
    bubble.className = `sh-chat-bubble ${role}`;
    bubble.textContent = text;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadOverview() {
    try {
        const response = await fetch('/api/student-agent/overview');
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || '成绩读取失败');
        const metrics = data.metrics;
        document.getElementById('averageScore').textContent = metrics.average_score ?? '--';
        document.getElementById('classRank').textContent = metrics.class_rank ?? '--';
        document.getElementById('classSize').textContent = `/ ${metrics.class_size ?? '--'} 名`;
        document.getElementById('scoreHint').textContent = metrics.latest_change == null ? '暂无趋势数据' : `近两次变化 ${metrics.latest_change >= 0 ? '+' : ''}${metrics.latest_change} 分`;
        document.getElementById('attentionBadge').textContent = metrics.attention_level || '状态良好';
        renderDevelopment(data);
    } catch (error) {
        notice(error.message);
    }
}

async function generateReport() {
    const button = document.getElementById('reportButton');
    button.disabled = true;
    button.innerHTML = '正在生成 <i class="bi bi-arrow-repeat"></i>';
    try {
        const response = await fetch('/api/student-agent/reports', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({report_type: 'latest_score'})});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || '建议生成失败');
        document.getElementById('reportText').textContent = data.comment;
    } catch (error) {
        notice(error.message);
    } finally {
        button.disabled = false;
        button.innerHTML = '生成学习建议 <i class="bi bi-arrow-up-right"></i>';
    }
}

document.getElementById('teacherLauncher').addEventListener('click', () => {
    drawer.classList.add('is-open');
    document.getElementById('chatInput').focus();
});
document.getElementById('closeDrawer').addEventListener('click', () => drawer.classList.remove('is-open'));
document.getElementById('reportButton').addEventListener('click', generateReport);
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
chatInput.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});
chatForm.addEventListener('submit', async event => {
    event.preventDefault();
    const input = chatInput;
    const message = input.value.trim();
    if (!message) return;
    renderChat('student', message);
    input.value = '';
    try {
        const response = await fetch('/api/student-agent/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message})});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || '对话暂不可用');
        renderChat('teacher', data.answer);
    } catch (error) {
        renderChat('teacher', error.message);
    }
});

loadOverview();
