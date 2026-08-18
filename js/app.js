/**
 * 可复用前端 — 通用 CRUD 引擎
 * ================================
 * 本文件不硬编码任何业务字段，全部从 config.js 读取。
 * 换项目只需改 config.js，本文件不用动。
 */
(function () {
  'use strict';

  // ─── 状态 ──────────────────────────────────────────
  let currentModule = null;
  let currentData = [];

  // ─── DOM 快捷 ──────────────────────────────────────
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  // ─── API 请求封装 ──────────────────────────────────
  async function api(path, opts) {
    opts = opts || {};
    const headers = opts.headers || {};
    if (!(opts.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(API_BASE + path, {
      ...opts,
      headers,
      body: opts.body instanceof FormData
        ? opts.body
        : opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error(data?.detail || `请求失败 (${res.status})`);
    return data;
  }

  // ─── Toast 提示 ────────────────────────────────────
  function toast(msg, type) {
    type = type || 'info';
    const el = $('#toast');
    el.textContent = msg;
    el.className = 'toast toast-' + type + ' show';
    setTimeout(() => el.classList.remove('show'), 2500);
  }

  // ─── 工具：把日期字符串转成 input[type=date] 的 value ─
  function toDateInputVal(v) {
    if (!v) return '';
    if (v.includes('T')) return v.split('T')[0];
    return v.slice(0, 10);
  }
  function toDateTimeInputVal(v) {
    if (!v) return '';
    return v.slice(0, 16);
  }

  // ─── 渲染侧边栏 ────────────────────────────────────
  function renderSidebar() {
    const nav = $('#sidebar-nav');
    nav.innerHTML = '';
    Object.entries(MODULES).forEach(([key, mod]) => {
      const btn = document.createElement('button');
      btn.className = 'nav-item' + (key === Object.keys(MODULES)[0] ? ' active' : '');
      btn.dataset.module = key;
      btn.innerHTML = `<span class="nav-icon">${mod.icon || '📋'}</span><span>${mod.label}</span>`;
      btn.addEventListener('click', () => switchModule(key));
      nav.appendChild(btn);
    });
  }

  // ─── 切换模块 ──────────────────────────────────────
  function switchModule(key) {
    currentModule = key;
    $$('.nav-item').forEach(el => el.classList.remove('active'));
    $(`.nav-item[data-module="${key}"]`).classList.add('active');
    $('#page-title').textContent = MODULES[key].label;
    $('#page-subtitle').textContent = `管理 ${MODULES[key].label} 信息`;

    const main = $('#main-content');
    main.innerHTML = '';

    const mod = MODULES[key];

    // 自定义模块（如成绩管理）
    if (mod.isCustom && mod.customRenderer) {
      renderCustomModule(key, mod, main);
      return;
    }

    // 标准 CRUD 模块
    renderCrudModule(key, mod, main);
  }

  // ─── 渲染标准 CRUD 模块 ────────────────────────────
  function renderCrudModule(key, mod, container) {
    const listFields = (mod.fields || []).filter(f => f.isList !== false);
    const searchable = (mod.endpoints.list || '').includes('keyword');

    let html = '';

    // 工具栏
    html += `<div class="toolbar">`;
    if (searchable) {
      html += `<input id="search-input" class="search-input" placeholder="搜索…" />`;
    }
    html += `<button id="btn-add" class="btn btn-primary">＋ 新增</button>`;
    if (mod.endpoints.batchCreate) {
      html += `<button id="btn-batch" class="btn btn-outline">批量录入</button>`;
    }
    html += `</div>`;

    // 表格
    html += `<div class="card"><div class="table-wrap"><table>
      <thead><tr>`;
    listFields.forEach(f => { html += `<th>${f.label}</th>`; });
    html += `<th>操作</th>`;
    html += `</tr></thead>
      <tbody id="table-body">
        <tr><td colspan="${listFields.length + 1}" class="empty-state">加载中…</td></tr>
      </tbody>
    </table></div></div>`;

    container.innerHTML = html;

    // 事件
    if (searchable) {
      $('#search-input').addEventListener('input', () => {
        const kw = $('#search-input').value.toLowerCase();
        renderTableRows(key, mod, currentData.filter(row =>
          listFields.some(f => String(row[f.key] ?? '').toLowerCase().includes(kw))
        ));
      });
    }
    $('#btn-add').addEventListener('click', () => openForm(key, mod, null));
    if (mod.endpoints.batchCreate) {
      $('#btn-batch').addEventListener('click', () => openBatchCreate(key, mod));
    }

    // 加载数据
    loadList(key, mod);
  }

  // ─── 加载列表数据 ──────────────────────────────────
  async function loadList(key, mod) {
    try {
      let url = mod.endpoints.list;
      // 顾问模块 list 接口需要无参数 GET（已支持）
      // 学生/就业模块 list 接口直接 GET
      const data = await api(url);
      // 兼容返回数组或 { data: [...] } 的情况
      currentData = Array.isArray(data) ? data : (data.data || data.list || []);
      renderTableRows(key, mod, currentData);
    } catch (e) {
      $('#table-body').innerHTML =
        `<tr><td colspan="999" class="empty-state" style="color:var(--danger)">加载失败: ${e.message}</td></tr>`;
    }
  }

  // ─── 渲染表格行 ────────────────────────────────────
  function renderTableRows(key, mod, data) {
    const listFields = (mod.fields || []).filter(f => f.isList !== false);
    const tbody = $('#table-body');
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="${listFields.length + 1}" class="empty-state">暂无数据</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(row => {
      const id = row.id ?? row.tid ?? row.consultant_id ?? row.student_id ?? '';
      let tr = '<tr>';
      listFields.forEach(f => {
        let val = row[f.key];
        if (val === null || val === undefined) val = '-';
        if (f.type === 'date' && val !== '-') val = toDateInputVal(val);
        if (f.type === 'datetime' && val !== '-') val = toDateTimeInputVal(val);
        tr += `<td>${val}</td>`;
      });
      let extraBtns = '';
      if (mod.extraActions) {
        mod.extraActions.forEach(action => {
          const actionId = row[action.idField] ?? id;
          extraBtns += `<button class="btn ${action.style || 'btn-outline'} btn-sm" onclick="window.__extraAction('${key}','${action.handler}','${actionId}')">${action.label}</button>`;
        });
      }
      tr += `<td class="td-actions">
        <button class="btn btn-outline btn-sm" onclick="window.__editItem('${key}',${id})">编辑</button>
        <button class="btn btn-danger btn-sm" onclick="window.__deleteItem('${key}',${id},'${row.name || row.tname || row.dept_name || row.student_no || id}')">删除</button>
        ${extraBtns}
      </td>`;
      tr += '</tr>';
      return tr;
    }).join('');
  }

  // ─── 打开新增/编辑表单弹窗 ────────────────────────
  function openForm(key, mod, row) {
    const fields = mod.formFields || mod.fields.filter(f => f.isForm !== false);
    const isEdit = !!row;
    const title = isEdit ? `编辑 - ${mod.label}` : `新增 - ${mod.label}`;

    let html = `<div class="form-grid">`;
    fields.forEach(f => {
      const val = row ? (row[f.key] ?? '') : '';
      html += `<div class="form-group">`;
      html += `<label>${f.label}${f.isRequired ? ' <span style="color:var(--danger)">*</span>' : ''}</label>`;
      if (f.type === 'select' && f.options) {
        html += `<select id="form-${f.key}" ${isEdit && f.key === 'id' ? 'disabled' : ''}>`;
        if (!f.isRequired) html += `<option value="">-- 请选择 --</option>`;
        f.options.forEach(o => {
          const sel = (val === o.value || String(val) === String(o.value)) ? 'selected' : '';
          html += `<option value="${o.value}" ${sel}>${o.label}</option>`;
        });
        html += `</select>`;
      } else if (f.type === 'textarea') {
        html += `<textarea id="form-${f.key}">${val}</textarea>`;
      } else {
        const inputType = f.type === 'date' ? 'date'
                        : f.type === 'datetime' ? 'datetime-local'
                        : f.type === 'number' ? 'number' : 'text';
        const inputVal = f.type === 'date' ? toDateInputVal(val)
                       : f.type === 'datetime' ? toDateTimeInputVal(val)
                       : val;
        html += `<input type="${inputType}" id="form-${f.key}" value="${inputVal !== null && inputVal !== undefined ? inputVal : ''}" />`;
      }
      html += `</div>`;
    });
    html += `</div>`;
    html += `<div class="modal-actions">
      <button class="btn btn-outline" onclick="window.__closeModal()">取消</button>
      <button class="btn btn-primary" onclick="window.__saveItem('${key}',${isEdit})">保存</button>
    </div>`;

    $('#modal-title').textContent = title;
    $('#modal-body').innerHTML = html;
    showModal();

    // 存储当前编辑行的 id
    window.__currentEditId = isEdit ? (row.id ?? row.tid ?? row.consultant_id ?? row.student_id ?? null) : null;
  }

  // ─── 保存（新增/更新）─────────────────────────────
  window.__saveItem = async function (key, isEdit) {
    const mod = MODULES[key];
    const fields = mod.formFields || mod.fields.filter(f => f.isForm !== false);
    const body = {};

    // 特殊处理：教师模块更新时只提交 tname/tphone/tsubject
    const isTeacherUpdate = key === 'teachers' && isEdit;

    for (const f of fields) {
      if (isTeacherUpdate && !['tname', 'tphone', 'tsubject'].includes(f.key)) continue;

      const el = document.getElementById('form-' + f.key);
      if (!el) continue;
      let val = el.value;
      if (f.type === 'number') val = val === '' ? null : Number(val);
      if (f.isRequired && (val === '' || val === null || val === undefined)) {
        toast(`请填写「${f.label}」`, 'error');
        el.focus();
        return;
      }
      if (val === '' || val === null || val === undefined) continue;
      body[f.key] = val;
    }

    try {
      if (isEdit && window.__currentEditId != null) {
        // 更新
        let url;
        if (typeof mod.endpoints.update === 'function') {
          url = mod.endpoints.update(window.__currentEditId);
        } else {
          url = mod.endpoints.update + '/' + window.__currentEditId;
        }
        await api(url, { method: 'PUT', body });
        toast('更新成功', 'success');
      } else {
        // 新增
        await api(mod.endpoints.create, { method: 'POST', body });
        toast('新增成功', 'success');
      }
      closeModal();
      loadList(key, mod);
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  // ─── 编辑 ──────────────────────────────────────────
  window.__editItem = function (key, id) {
    const mod = MODULES[key];
    const row = currentData.find(r => (r.id ?? r.tid ?? r.consultant_id ?? r.student_id) == id);
    if (row) openForm(key, mod, row);
  };

  // ─── 删除 ──────────────────────────────────────────
  window.__deleteItem = function (key, id, name) {
    if (!confirm(`确定删除「${name}」？`)) return;
    const mod = MODULES[key];
    let url;
    if (typeof mod.endpoints.delete === 'function') {
      url = mod.endpoints.delete(id);
    } else {
      url = mod.endpoints.delete.replace('{id}', id);
    }
    api(url, { method: 'DELETE' })
      .then(() => { toast('删除成功', 'success'); loadList(key, mod); })
      .catch(e => toast(e.message, 'error'));
  };

  // ─── 弹窗控制 ──────────────────────────────────────
  function showModal()  { $('#modal-overlay').classList.add('show'); }
  window.__closeModal = closeModal;
  function closeModal() { $('#modal-overlay').classList.remove('show'); }

  // ─── 自定义模块：成绩管理 ──────────────────────────
  function renderCustomModule(key, mod, container) {
    if (key === 'scores') {
      container.innerHTML = `
        <div class="card">
          <div class="card-header">成绩查询</div>
          <div class="card-body">
            <div class="toolbar">
              <input id="score-search-no" class="search-input" placeholder="输入学号查询成绩…" />
              <button class="btn btn-primary" onclick="window.__searchScores()">查询</button>
              <button class="btn btn-outline" onclick="window.__showScoreForm(null)">＋ 录入成绩</button>
            </div>
            <div id="score-result"><p class="empty-state">输入学号查询成绩</p></div>
          </div>
        </div>`;
      return;
    }
  }

  window.__searchScores = async function () {
    const no = $('#score-search-no').value.trim();
    if (!no) return toast('请输入学号', 'error');
    try {
      const data = await api('/score/' + no);
      const result = $('#score-result');
      if (!data || !data.length) {
        result.innerHTML = '<p class="empty-state">该学生暂无成绩记录</p>';
        return;
      }
      const mod = MODULES.scores;
      const fields = mod.fields.filter(f => f.isList !== false);
      let html = '<table><thead><tr>';
      fields.forEach(f => { html += `<th>${f.label}</th>`; });
      html += '<th>操作</th></tr></thead><tbody>';
      data.forEach(row => {
        html += '<tr>';
        fields.forEach(f => { html += `<td>${row[f.key] ?? '-'}</td>`; });
        html += `<td>
          <button class="btn btn-outline btn-sm" onclick="window.__editScore('${no}',${row.exam_seq})">编辑</button>
          <button class="btn btn-danger btn-sm" onclick="window.__deleteScore('${no}',${row.exam_seq})">删除</button>
        </td>`;
        html += '</tr>';
      });
      html += '</tbody></table>';
      result.innerHTML = html;
    } catch (e) { toast(e.message, 'error'); }
  };

  window.__showScoreForm = function (studentNo) {
    const mod = MODULES.scores;
    const fields = mod.fields.filter(f => f.isForm !== false);
    let html = '<div class="form-grid">';
    fields.forEach(f => {
      html += `<div class="form-group"><label>${f.label}</label>`;
      html += `<input type="${f.type === 'number' ? 'number' : 'text'}" id="form-${f.key}" value="${f.key === 'student_no' && studentNo ? studentNo : ''}" /></div>`;
    });
    html += '</div>';
    html += `<div class="modal-actions">
      <button class="btn btn-outline" onclick="window.__closeModal()">取消</button>
      <button class="btn btn-primary" onclick="window.__saveScore()">保存</button>
    </div>`;
    $('#modal-title').textContent = studentNo ? '编辑成绩' : '录入成绩';
    $('#modal-body').innerHTML = html;
    showModal();
  };

  window.__editScore = function (studentNo, examSeq) {
    // 成绩模块编辑：先查询再填表
    api('/score/' + studentNo + '?exam_seq=' + examSeq).then(data => {
      if (data && data.length) window.__showScoreForm(studentNo);
    }).catch(e => toast(e.message, 'error'));
  };

  window.__saveScore = async function () {
    const mod = MODULES.scores;
    const fields = mod.fields.filter(f => f.isForm !== false);
    const body = {};
    fields.forEach(f => {
      const el = document.getElementById('form-' + f.key);
      if (el) body[f.key] = f.type === 'number' ? Number(el.value) : el.value;
    });
    try {
      // 先尝试 POST（新增），若已存在则 PUT（更新）
      try {
        await api(mod.endpoints.create, { method: 'POST', body });
        toast('录入成功', 'success');
      } catch {
        await api(mod.endpoints.update, { method: 'PUT', body });
        toast('更新成功', 'success');
      }
      closeModal();
      if ($('#score-search-no')?.value) window.__searchScores();
    } catch (e) { toast(e.message, 'error'); }
  };

  window.__deleteScore = function (studentNo, examSeq) {
    if (!confirm('确定删除该成绩记录？')) return;
    api(MODULES.scores.endpoints.delete(studentNo, examSeq), { method: 'DELETE' })
      .then(() => { toast('删除成功', 'success'); window.__searchScores(); })
      .catch(e => toast(e.message, 'error'));
  };

  // ─── 额外操作分发 ──────────────────────────────────
  window.__extraAction = function (key, handler, actionId) {
    const mod = MODULES[key];
    if (handler === 'showManager') {
      showConsultantManager(mod, actionId);
    }
  };

  // 查询顾问直属领导弹窗
  async function showConsultantManager(mod, consultantNo) {
    try {
      const data = await api(mod.endpoints.manager(consultantNo));
      const html = `
        <div class="form-grid">
          <div class="form-group"><label>顾问编号</label><input type="text" disabled value="${data.consultant_no || '-'}" /></div>
          <div class="form-group"><label>顾问姓名</label><input type="text" disabled value="${data.consultant_name || '-'}" /></div>
          <div class="form-group"><label>顾问职称</label><input type="text" disabled value="${data.consultant_title || '-'}" /></div>
          <div class="form-group"><label>所属部门</label><input type="text" disabled value="${data.dept_name || '-'}" /></div>
          <div class="form-group"><label>直属领导</label><input type="text" disabled value="${data.manager_name || '-'}" /></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" onclick="window.__closeModal()">关闭</button>
        </div>`;
      $('#modal-title').textContent = '直属领导信息';
      $('#modal-body').innerHTML = html;
      showModal();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  // 批量录入弹窗
  function openBatchCreate(key, mod) {
    const example = JSON.stringify([{
      consultant_no: 'CON005', name: '姓名', gender: '男',
      phone: '13900000001', dept_no: 'DEPT001', title: '顾问'
    }], null, 2);
    const html = `
      <p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:8px">
        输入 JSON 数组，每个对象为一条记录：
      </p>
      <textarea id="batch-input" style="width:100%;height:200px;font-family:monospace;font-size:12px;padding:8px;border:1px solid var(--border);border-radius:6px;resize:vertical" placeholder="${example.replace(/"/g, '&quot;')}"></textarea>
      <div class="modal-actions">
        <button class="btn btn-outline" onclick="window.__closeModal()">取消</button>
        <button class="btn btn-primary" onclick="window.__saveBatch('${key}')">提交</button>
      </div>`;
    $('#modal-title').textContent = `批量录入 - ${mod.label}`;
    $('#modal-body').innerHTML = html;
    showModal();
  }

  window.__saveBatch = async function (key) {
    const mod = MODULES[key];
    const text = ($('#batch-input') || {}).value || '';
    if (!text.trim()) return toast('请输入数据', 'error');
    let body;
    try {
      body = JSON.parse(text);
      if (!Array.isArray(body)) throw new Error('必须是 JSON 数组 [...]');
    } catch (e) {
      return toast('JSON 格式错误: ' + e.message, 'error');
    }
    try {
      await api(mod.endpoints.batchCreate, { method: 'POST', body });
      toast(`批量录入成功，共 ${body.length} 条`, 'success');
      closeModal();
      loadList(key, mod);
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  // ─── 启动 ──────────────────────────────────────────
  function init() {
    renderSidebar();
    const firstKey = Object.keys(MODULES)[0];
    if (firstKey) switchModule(firstKey);
  }

  // DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
