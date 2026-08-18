const serviceKind = window.shanheServiceModule;
const rows = document.getElementById('serviceRows');
const heading = document.getElementById('serviceHeading');
const icon = document.getElementById('serviceIcon');

const configs = {
    'campus-life': {url: '/api/v1/campus/activities', heading: '校园活动与生活服务', icon: 'bi-house-heart', fields: item => [item.title, item.category, item.location || '校园服务']},
    library: {url: '/api/v1/library/loans', heading: '当前借阅', icon: 'bi-book', fields: item => [`《${item.book_title}》`, item.author || '作者信息待同步', item.due_at ? `归还：${String(item.due_at).slice(0, 10)}` : '待确认归还日期']},
    career: {url: '/api/v1/career/opportunities', heading: '推荐岗位与实习机会', icon: 'bi-briefcase', fields: item => [item.title, item.organization, `${item.city} · ${item.job_type}`]},
    'mental-health': {url: '/api/v1/mental/checkins', heading: '我的情绪记录', icon: 'bi-heart-pulse', fields: item => [`心情 ${item.mood_score}/10`, item.risk_level === 'normal' ? '状态平稳' : '建议关注', (item.tags || []).join('、') || '今日记录']},
};

function showItems(items, config) {
    heading.textContent = config.heading;
    icon.className = `bi ${config.icon}`;
    rows.innerHTML = '';
    (items || []).slice(0, 3).forEach(item => {
        const card = document.createElement('article');
        card.className = 'sh-service-row';
        const values = config.fields(item);
        card.innerHTML = '<i class="bi bi-check2-circle"></i><span><strong></strong><small></small></span><b></b>';
        card.querySelector('strong').textContent = values[0];
        card.querySelector('small').textContent = values[1];
        card.querySelector('b').textContent = values[2];
        rows.appendChild(card);
    });
    if (!rows.children.length) rows.innerHTML = '<div class="sh-empty-panel">暂无演示数据</div>';
}

async function loadService() {
    const config = configs[serviceKind];
    const response = await fetch(config.url);
    const data = await response.json();
    if (!response.ok) { rows.textContent = data.detail || '数据暂不可用'; return; }
    showItems(data.items, config);
    if (serviceKind === 'library' && data.integration_note) {
        document.querySelector('.sh-service-note').textContent = data.integration_note;
    }
}

document.getElementById('moodForm')?.addEventListener('submit', async event => {
    event.preventDefault();
    const response = await fetch('/api/v1/mental/checkins', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mood_score: Number(document.getElementById('moodScore').value), note: document.getElementById('moodNote').value})});
    const data = await response.json();
    if (response.ok) { document.getElementById('moodNote').value = ''; await loadService(); }
    else alert(data.detail || '保存失败');
});

loadService();
