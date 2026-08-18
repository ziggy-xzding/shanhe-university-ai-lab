/**
 * 可复用前端 — 配置文件
 * ========================
 * 换项目只需修改本文件。
 *
 * 修改步骤：
 *   1. 修改 API_BASE 为你的后端地址
 *   2. 修改 MODULES 中各模块的 endpoints 和 fields
 *   3. 打开 index.html 即可使用
 */
const API_BASE = 'http://127.0.0.1:8000';

// ── 字段类型 ──────────────────────────────────────────
// text / number / date / datetime / select / textarea
// isRequired: true  → 新增表单必填
// isList:   false   → 列表页不显示该列
// isForm:   false   → 新增/编辑表单不显示该字段（如 id、自动生成的时间）
// options:  select 类型时提供的选项列表，格式 [{value,label}]
// ──────────────────────────────────────────────────────

const FIELD_TYPES = {
  text:     'text',
  number:   'number',
  date:     'date',
  datetime: 'datetime-local',
  select:   'select',
  textarea: 'textarea',
};

// ── 模块配置 ──────────────────────────────────────────
// endpoints:
//   list   → GET 获取列表（支持 ?skip= &limit= &keyword=）
//   create → POST 新增
//   update → PUT  更新（URL 拼 id，如 '/students/{id}'）
//   delete → DELETE 删除（URL 拼 id）
//   detail → GET 获取单个（可选，默认用 list + id 过滤）
//
// fields: 数组，每项 { key, label, type, isRequired, isList, isForm, options }
//   key       → 对应 API 返回 JSON 的字段名
//   label    → 列表表头和表单标签的显示文字
//   type     → 表单 input 类型（text/number/date/select/textarea）
//   isRequired → 新增时是否必填（默认 false）
//   isList   → 是否在列表页显示（默认 true）
//   isForm   → 是否在新增/编辑表单显示（默认 true）
//   options  → type=select 时的选项，格式 [{value, label}]
//   width    → 列表列宽（可选，如 '120px'）
// ──────────────────────────────────────────────────────

const MODULES = {

  // ── 学生管理 ────────────────────────────────────────
  students: {
    label: '学生管理',
    icon: '👨🎓',
    endpoints: {
      list:   '/students',
      create: '/students',
      update: (id) => `/students/${id}`,
      delete: (id) => `/students/${id}`,
    },
    fields: [
      { key: 'id',            label: 'ID',       type: 'number',  isList: false, isForm: false },
      { key: 'student_no',    label: '学号',     type: 'text',    isRequired: true },
      { key: 'name',          label: '姓名',     type: 'text',    isRequired: true },
      { key: 'gender',        label: '性别',     type: 'select',  isRequired: true,
        options: [{ value: '男', label: '男' }, { value: '女', label: '女' }] },
      { key: 'age',           label: '年龄',     type: 'number' },
      { key: 'class_id',      label: '班级ID',   type: 'number' },
      { key: 'major',         label: '专业',     type: 'text' },
      { key: 'hometown',      label: '籍贯',     type: 'text' },
      { key: 'graduate_school', label: '毕业院校', type: 'text' },
      { key: 'education',     label: '学历',     type: 'text' },
      { key: 'enrollment_time',  label: '入学时间', type: 'date' },
      { key: 'graduation_time',  label: '毕业时间', type: 'date' },
      { key: 'advisor_id',    label: '导师ID',   type: 'number' },
    ],
  },

  // ── 教师管理 ────────────────────────────────────────
  teachers: {
    label: '教师管理',
    icon: '👩🏫',
    endpoints: {
      list:   '/teacher/teachers',
      create: '/teacher/teachercrate',
      update: (id) => `/teacher/teacher/${id}`,
      delete: (id) => `/teacher/teacher/${id}`,
    },
    // 注意：教师模块创建时后端会忽略 tid（自增），但更新时需要 tid
    fields: [
      { key: 'tid',           label: '教师ID',   type: 'number',  isForm: false },
      { key: 'tname',         label: '姓名',     type: 'text',    isRequired: true },
      { key: 'tphone',        label: '电话',     type: 'text',    isRequired: true },
      { key: 'tsubject',      label: '科目',     type: 'text',    isRequired: true },
      { key: 't_code',        label: '状态',     type: 'select',
        options: [
          { value: '在职', label: '在职' },
          { value: '离职', label: '离职' },
          { value: '停用', label: '停用' },
        ] },
      { key: 't_is_delete',   label: '已删除',   type: 'number',  isList: false, isForm: false },
      { key: 'create_date',   label: '创建日期', type: 'date',    isList: false, isForm: false },
      { key: 'update_date',   label: '更新日期', type: 'date',    isList: false, isForm: false },
    ],
  },

  // ── 班级管理 ────────────────────────────────────────
  classes: {
    label: '班级管理',
    icon: '📚',
    endpoints: {
      list:   '/classes',
      create: '/classes',
      update: (id) => `/classes/${id}`,
      delete: (id) => `/classes/${id}`,
    },
    fields: [
      { key: 'id',            label: 'ID',       type: 'number',  isList: false, isForm: false },
      { key: 'class_no',      label: '班级编号', type: 'text',    isRequired: true },
      { key: 'name',          label: '班级名称', type: 'text',    isRequired: true },
      { key: 'start_date',    label: '开班日期', type: 'date' },
      { key: 'head_teacher_id',  label: '班主任ID', type: 'number' },
      { key: 'instructor_id', label: '辅导员ID', type: 'number' },
    ],
  },

  // ── 部门管理 ────────────────────────────────────────
  departments: {
    label: '部门管理',
    icon: '🏢',
    endpoints: {
      list:   '/departments',
      create: '/departments',   // 后端接受数组，前端逐条 POST
      update: (id) => `/departments/${id}`,
      delete: (id) => `/departments/${id}`,
    },
    // 注意：部门创建接口接受数组，这里前端逐条提交
    fields: [
      { key: 'id',            label: 'ID',       type: 'number',  isList: false, isForm: false },
      { key: 'dept_no',       label: '部门编号', type: 'text',    isRequired: true },
      { key: 'dept_name',     label: '部门名称', type: 'text',    isRequired: true },
      { key: 'dept_manager',  label: '负责人',   type: 'text',    isRequired: true },
      { key: 'dept_location', label: '位置',     type: 'text',    isRequired: true },
      { key: 'dept_phone',    label: '电话',     type: 'text' },
    ],
  },

  // ── 顾问管理 ────────────────────────────────────────
  consultants: {
    label: '顾问管理',
    icon: '💼',
    endpoints: {
      list:        '/consultant/list',
      create:      '/consultant/create',
      batchCreate: '/consultant/batch-create',
      update:      (id) => `/consultant/update/${id}`,
      delete:      (id) => `/consultant/delete/${id}`,
      manager:     (consultant_no) => `/consultant/${consultant_no}/manager`,
    },
    // 每行额外操作按钮：handler 对应 app.js 中注册的处理函数名
    extraActions: [
      { label: '查领导', handler: 'showManager', idField: 'consultant_no', style: 'btn-outline' },
    ],
    fields: [
      { key: 'consultant_id',  label: 'ID',       type: 'number', isList: false, isForm: false },
      { key: 'consultant_no',  label: '顾问编号', type: 'text',   isRequired: true },
      { key: 'name',           label: '姓名',     type: 'text',   isRequired: true },
      { key: 'gender',         label: '性别',     type: 'select',
        options: [{ value: '男', label: '男' }, { value: '女', label: '女' }] },
      { key: 'phone',          label: '电话',     type: 'text',   isRequired: true },
      { key: 'email',          label: '邮箱',     type: 'text' },
      { key: 'dept_no',        label: '部门编号', type: 'text',   isRequired: true },
      { key: 'title',          label: '职位',     type: 'text',   isRequired: true },
      { key: 'region',         label: '区域',     type: 'text' },
    ],
  },

  // ── 就业管理 ────────────────────────────────────────
  employment: {
    label: '就业管理',
    icon: '💵',
    endpoints: {
      list:   '/employment',
      // 就业模块用 upsert：POST /employment/students/{student_no}
      // 为简化，前端用 list 展示，新增/更新统一走 upsert 接口
      upsert: (student_no) => `/employment/students/${student_no}`,
      delete: (id) => `/employment/${id}`,
    },
    // 就业列表字段（GET /employment 返回）
    fields: [
      { key: 'id',            label: 'ID',       type: 'number',  isList: false, isForm: false },
      { key: 'student_id',    label: '学生ID',   type: 'number',  isForm: false },
      { key: 'student_name',  label: '学生姓名', type: 'text',    isRequired: true, isForm: false },
      { key: 'class_name',    label: '班级',     type: 'text',    isForm: false },
      { key: 'company',       label: '公司',     type: 'text',    isRequired: true },
      { key: 'salary',        label: '薪资',     type: 'number',  isRequired: true },
      { key: 'offer_time',    label: 'Offer时间', type: 'date' },
      { key: 'open_time',     label: '开班时间', type: 'date' },
    ],
    // 就业新增/编辑表单字段（upsert 接口需要的字段）
    formFields: [
      { key: 'student_no',    label: '学号',     type: 'text',    isRequired: true },
      { key: 'student_name',  label: '学生姓名', type: 'text' },
      { key: 'class_name',    label: '班级名称', type: 'text' },
      { key: 'company',       label: '公司',     type: 'text',    isRequired: true },
      { key: 'salary',        label: '薪资',     type: 'number',  isRequired: true },
      { key: 'offer_time',    label: 'Offer时间', type: 'date' },
      { key: 'open_time',     label: '开班时间', type: 'date' },
    ],
  },

  // ── 成绩管理 ────────────────────────────────────────
  scores: {
    label: '成绩管理',
    icon: '📊',
    // 成绩按学号查询：GET /score/{student_no}
    // 录入：POST /score/
    // 修改：PUT  /score/
    // 删除：DELETE /score/{student_no}/{exam_seq}
    endpoints: {
      // 列表需要按学号查询，不走标准 list 接口
      queryByStudent: (student_no) => `/score/${student_no}`,
      create: '/score/',
      update: '/score/',
      delete: (student_no, exam_seq) => `/score/${student_no}/${exam_seq}`,
    },
    fields: [
      { key: 'student_no',    label: '学号',     type: 'text',    isRequired: true },
      { key: 'exam_seq',      label: '考试序次', type: 'number',  isRequired: true },
      { key: 'score',         label: '成绩',     type: 'number',  isRequired: true },
      { key: 'created_at',    label: '录入时间', type: 'datetime', isList: false, isForm: false },
      { key: 'updated_at',    label: '更新时间', type: 'datetime', isList: false, isForm: false },
    ],
    // 成绩模块是"按学号查询"模式，不是标准 CRUD
    isCustom: true,
    customRenderer: 'scores',
  },

};
