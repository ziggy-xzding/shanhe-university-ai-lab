# 学生成长 Agent 与权限模块设计文档

> 本文档整合了需求、数据表、接口和实施计划四份设计文档；它们是学生成长 Agent 与分角色登录功能的统一设计入口。
>
> 整理日期：2026-07-24

## 文档组成

- 需求文档
- 表设计文档
- 接口设计文档
- 实施计划

---

## 需求文档

## 学生成长 Agent 与分角色登录需求文档

- 项目名称：沃林学生管理系统
- 文档版本：V1.0
- 编写日期：2026-07-23
- 适用范围：教培公司学生管理系统的学生、教师职员、管理员职员

### 1. 项目背景

现有系统已经具备学生、班级、教师、成绩、就业等基础管理能力，以及《三国演义》RAG 问答能力；但尚未区分学生与职员的访问边界，也无法让学生以自己的成绩为依据获得成长建议。

本次新增“易老师·三国成长伙伴”：它以通俗的三国讲坛式表达，基于学生本人阶段成绩、班级对比和《三国演义》典故，提供成绩解读、个性化评语、学习建议与温和的情绪陪伴。

> 易老师为原创的“讲坛学者”虚拟角色，不使用真实人物肖像，不宣称为任何真实人物本人。

### 2. 建设目标

1. 建立学生、教师职员、管理员职员三类身份及后端强制授权机制。
2. 让学生仅凭“学号 + 姓名”验证后，查看自己的成绩、趋势、评语和 Agent 对话。
3. 让教师职员仅查看所负责或授课班级的数据并完成成绩维护与班级分析。
4. 让管理员职员管理全量业务数据、职员账户和全局统计。
5. 通过可重复执行的种子脚本，为所有现有表和新增表写入真实感的虚构演示数据。
6. 提供一个比原有 Bootstrap 列表页更具展示效果的学生成长页面。

### 3. 用户与权限

| 用户 | 身份确认 | 可访问内容 | 明确禁止 |
| --- | --- | --- | --- |
| 学生 | 学号 + 姓名，获得短期学生会话 | 个人成长页、本人六次阶段考核、趋势、个人评语、自己的会话历史 | 其他学生数据、职员管理页面、班级完整名单 |
| 教师职员 | 职员账号/工号 + 密码 | 所负责或授课班级的学生名单、成绩录入/修改、班级统计、班级风险汇总 | 非本人班级、部门/顾问/职员账户管理、学生原始私密聊天内容 |
| 管理员职员 | 职员账号/工号 + 密码 | 全量业务管理、全局统计、职员账户、Agent 汇总统计 | 默认不展示学生原始聊天内容；如未来需要，必须另设审计流程 |
| 未登录用户 | 无 | 统一登录页 | 任何业务 API 与页面 |

权限必须由后端依赖项校验，前端隐藏菜单仅用于改善体验，不能作为安全控制手段。

### 4. 功能需求

#### 4.1 统一登录与跳转

1. 新增 `/pages/login` 页面，提供“职员登录”和“学生入口”两个清晰入口。
2. 职员以账号/工号和密码登录；系统根据 `admin` 或 `teacher` 角色跳转到对应工作台。
3. 学生以学号和姓名验证；成功后跳转到学生成长页。
4. 会话过期、退出登录或身份状态失效时，跳转回登录页并显示友好提示。
5. 根路径改为跳转至登录页；现有业务页面在无有效会话时不可直接访问。

#### 4.2 学生成长 Agent

学生验证后可使用以下能力：

1. **个人成绩查询**：查看本人全部阶段考核成绩、均分、及格率、班级排名和与班均差值。
2. **趋势分析**：以现有 `scores.exam_seq` 的 1~6 次阶段考核为横轴，展示变化趋势、近两次变化和关注等级。
3. **班级对比**：只返回学生自己的相对位置、班均和排名，不向学生暴露其他同学身份及成绩。
4. **特色评语**：根据确定性指标生成“优势、待改进点、下周可执行目标”，再由 Agent 转为有三国典故的自然语言表达。
5. **情绪陪伴**：先表达理解，再用恰当三国典故解释，再给出具体小步骤；不做医学诊断或夸大承诺。
6. **三国依据**：在适合的回答中复用已有 RAG 检索，展示简短的原著来源信息。
7. **安全处理**：识别到自伤、伤人或紧急危险表述时，停止用典故式安慰，建议立即联系可信成年人、学校心理老师或当地紧急服务。

#### 4.3 教师工作台

1. 展示本人关联班级、学生数、班级均分、及格率和需关注人数。
2. 查看自己班级的成绩趋势、优秀/波动/需关注人数分布。
3. 使用现有成绩录入、修改能力，但必须限制到自己负责或授课的班级。
4. 仅查看班级粒度的 Agent 风险统计，不显示学生私密聊天的原始文本。

#### 4.4 管理员工作台

1. 保留并保护学生、教师、班级、顾问、部门、成绩、就业等全量管理页面。
2. 新增职员账户管理：创建、停用、重置演示密码、关联教师档案、分配角色。
3. 查看全局成绩、就业、登录和 Agent 使用汇总统计。

#### 4.5 前端体验

学生成长页参考 [21st.dev Community Components](https://21st.dev/community/components) 的深色组件化和 Bento 卡片层级，不直接复制第三方代码或素材。

页面组成：

```text
顶部：学生身份状态、退出登录
主体左侧：综合均分、班级排名、趋势折线
主体右侧：易老师观察、评语和本周建议
主体下方：易老师对话区、快捷提问
右下角：可拖拽的原创“易”头像按钮，短按打开对话抽屉
```

头像按钮要求：拖动距离超过阈值时不触发点击；释放后吸附左/右边缘；位置保存到浏览器 `localStorage`；移动端可用且不遮挡输入框。

### 5. 非功能需求

| 类别 | 要求 |
| --- | --- |
| 安全 | 密码仅保存强哈希；会话凭证不保存明文；所有接口按角色和数据归属鉴权；错误消息不泄露密码和数据库细节。 |
| 隐私 | 学生只看本人；教师仅看所管班级；学生聊天内容不进入教师列表和管理员常规视图。 |
| 可用性 | RAG 或大模型不可用时，仍返回本地规则生成的成绩总结与重试提示。 |
| 性能 | 成绩统计使用聚合查询；列表接口分页或限制返回量；不在页面首次加载时调用模型。 |
| 可维护性 | 授权、成绩分析、Agent 编排、数据访问、模板和种子脚本职责分离。 |
| 数据 | 演示数据为虚构数据；种子脚本可重复运行且不删除已有业务数据。 |

### 6. 验收标准

1. 未登录请求受保护页面或接口时被拒绝并跳转/返回 401。
2. 学生 A 无法通过修改请求参数读取学生 B 的任何成绩或报告。
3. 教师无法查看不属于自己班级的学生成绩；管理员能看到全量业务统计。
4. 任意有成绩的学生可看到均分、排名、趋势、评语和可用的 Agent 对话。
5. RAG/LLM 服务不可用时，成长页仍可显示确定性成绩分析。
6. 易老师头像可拖拽、短按可打开对话，并能在刷新后恢复位置。
7. 执行种子脚本后，所有现有表和新增表均有可用于演示的数据；重复执行不产生重复记录。

---

## 表设计文档

## 学生成长 Agent 与权限模块表设计文档

- 项目名称：沃林学生管理系统
- 文档版本：V1.0
- 编写日期：2026-07-23

### 1. 设计原则

1. 复用既有 `students`、`classes`、`scores`、`teacher_table` 等业务表，不为 Agent 复制成绩数据。
2. 职员账户独立于教师档案：管理员没有教师档案，教师账户可关联 `teacher_table.tid`。
3. 会话凭证只保存哈希；学生身份、权限和会话均在服务端验证。
4. Agent 报告保存生成时的指标快照，保证后续成绩变化后仍能解释历史报告。
5. 现有 ORM 中部分关联未建数据库外键；新增表优先在应用层保证关联一致性，并在可迁移时建立外键。

### 2. 既有业务表

| 表名 | 用途 | 与本次功能的关系 |
| --- | --- | --- |
| `departments` | 部门信息 | 管理员维护、顾问/职员归属展示。 |
| `consultant` | 顾问信息 | 管理员维护，学生资料中的 `advisor_id` 可关联展示。 |
| `teacher_table` | 教师档案 | 教师职员账户通过 `teacher_id` 关联；班级分配教师。 |
| `classes` | 班级信息 | 教师的数据范围与学生班级对比依据。 |
| `students` | 学生主数据 | 学生身份校验与 Agent 数据主体。 |
| `scores` | 阶段考核成绩 | 六次趋势、均分、及格率、排名和报告的原始来源。 |
| `employment` | 就业信息 | 管理员全局管理；不进入学生学习 Agent 的默认提示词。 |

### 3. 新增表

#### 3.1 `staff_accounts`：职员账户表

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | INT | PK, AUTO_INCREMENT | 主键。 |
| `staff_no` | VARCHAR(20) | NOT NULL, UNIQUE | 职员工号。 |
| `username` | VARCHAR(50) | NOT NULL, UNIQUE | 登录账号。 |
| `password_hash` | VARCHAR(255) | NOT NULL | 强哈希后的密码，不保存明文。 |
| `display_name` | VARCHAR(50) | NOT NULL | 职员显示名称。 |
| `role` | VARCHAR(20) | NOT NULL | 仅允许 `admin`、`teacher`。 |
| `teacher_id` | INT | NULL, INDEX | 教师角色关联 `teacher_table.tid`；管理员为空。 |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT `active` | `active`、`disabled`。 |
| `last_login_at` | DATETIME | NULL | 最近登录时间。 |
| `created_at` | DATETIME | NOT NULL | 创建时间。 |
| `updated_at` | DATETIME | NOT NULL | 最后更新时间。 |

索引：`uk_staff_no(staff_no)`、`uk_username(username)`、`ix_staff_role_status(role,status)`、`ix_staff_teacher_id(teacher_id)`。

#### 3.2 `auth_login_logs`：登录审计表

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | BIGINT | PK, AUTO_INCREMENT | 主键。 |
| `account_type` | VARCHAR(20) | NOT NULL | `student` 或 `staff`。 |
| `account_id` | VARCHAR(50) | NOT NULL, INDEX | 学号或职员账户标识。 |
| `role` | VARCHAR(20) | NULL | 成功时记录角色。 |
| `success` | BOOLEAN | NOT NULL | 是否登录成功。 |
| `failure_reason` | VARCHAR(100) | NULL | 仅记录通用失败原因。 |
| `ip_hash` | CHAR(64) | NULL | 可选的客户端地址哈希，不保存明文地址。 |
| `user_agent` | VARCHAR(255) | NULL | 客户端标识。 |
| `created_at` | DATETIME | NOT NULL | 发生时间。 |

索引：`ix_login_account_time(account_type,account_id,created_at)`、`ix_login_success_time(success,created_at)`。

#### 3.3 `agent_sessions`：学生 Agent 会话表

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | CHAR(36) | PK | UUID 会话标识。 |
| `student_no` | VARCHAR(20) | NOT NULL, INDEX | 已验证学生学号。 |
| `token_hash` | CHAR(64) | NOT NULL, UNIQUE | 会话凭证 SHA-256 哈希。 |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT `active` | `active`、`expired`、`revoked`。 |
| `expires_at` | DATETIME | NOT NULL, INDEX | 到期时间。 |
| `last_active_at` | DATETIME | NOT NULL | 最近访问时间。 |
| `created_at` | DATETIME | NOT NULL | 创建时间。 |

索引：`ix_agent_session_student_status(student_no,status)`、`ix_agent_session_expiry(expires_at)`。

#### 3.4 `agent_messages`：Agent 消息表

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | BIGINT | PK, AUTO_INCREMENT | 主键。 |
| `session_id` | CHAR(36) | NOT NULL, INDEX | 关联 `agent_sessions.id`。 |
| `role` | VARCHAR(20) | NOT NULL | `user`、`assistant`、`system`。 |
| `intent` | VARCHAR(30) | NULL | `grade_query`、`analysis`、`report`、`comfort`、`general`。 |
| `content` | TEXT | NOT NULL | 消息正文。 |
| `source_refs` | JSON | NULL | 三国来源或成绩指标引用。 |
| `risk_level` | VARCHAR(20) | NOT NULL, DEFAULT `normal` | `normal`、`attention`、`urgent`。 |
| `created_at` | DATETIME | NOT NULL | 创建时间。 |

索引：`ix_agent_message_session_time(session_id,created_at)`、`ix_agent_message_risk_time(risk_level,created_at)`。

#### 3.5 `agent_reports`：成长报告表

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | BIGINT | PK, AUTO_INCREMENT | 主键。 |
| `student_no` | VARCHAR(20) | NOT NULL, INDEX | 报告归属学生。 |
| `report_type` | VARCHAR(30) | NOT NULL | `latest_score`、`weekly`、`manual`。 |
| `metrics_snapshot` | JSON | NOT NULL | 均分、排名、班均、及格率、趋势等快照。 |
| `attention_level` | VARCHAR(20) | NOT NULL | `excellent`、`stable`、`attention`、`urgent`。 |
| `strengths` | TEXT | NULL | 优势摘要。 |
| `improvements` | TEXT | NULL | 待改进点。 |
| `action_plan` | TEXT | NULL | 可执行计划。 |
| `comment` | TEXT | NOT NULL | 易老师特色评语。 |
| `generated_by` | VARCHAR(30) | NOT NULL | `rule`、`llm`、`fallback`。 |
| `created_at` | DATETIME | NOT NULL | 生成时间。 |

索引：`ix_agent_report_student_time(student_no,created_at)`、`ix_agent_report_level_time(attention_level,created_at)`。

### 4. 关系说明

```text
teacher_table 1 ── 0..1 staff_accounts（教师职员账户）
classes       N ── 1    teacher_table（班主任/授课教师）
students      N ── 1    classes
scores        N ── 1    students
agent_sessions N ── 1   students
agent_messages N ── 1   agent_sessions
agent_reports  N ── 1   students
```

`staff_accounts.teacher_id`、`agent_sessions.student_no`、`agent_reports.student_no` 的关联在服务层校验；数据库迁移条件具备时可追加外键约束。

### 5. 成绩指标口径

| 指标 | 计算方式 |
| --- | --- |
| 综合均分 | 本人全部未删除成绩的平均值。 |
| 最近变化 | 最后一次成绩减倒数第二次成绩；不足两次则为 `null`。 |
| 班级均分 | 本人所在班级全部未删除成绩的平均值。 |
| 班级排名 | 按同班学生综合均分降序排名；并列使用相同排名规则。 |
| 及格率 | 本人成绩中 `score >= 60` 的记录数 / 总记录数。 |
| 关注等级 | 均分、最近变化、连续不及格次数组合判定；仅用于建议，不作为学业处分依据。 |

### 6. 演示种子数据设计

种子脚本为 `scripts/seed_demo_data.py`，使用事务、唯一键和业务键查询保证幂等。数据均为虚构的教学场景样例：

| 表 | 预计数量 | 覆盖场景 |
| --- | ---: | --- |
| `departments` | 4 | 教学、就业、教务、运营部门。 |
| `consultant` | 10 | 多地区、多职级顾问。 |
| `teacher_table` | 12 | 班主任与授课教师。 |
| `classes` | 6 | 六个在读班级。 |
| `students` | 72 | 性别、籍贯、学历、专业、顾问分布真实感。 |
| `scores` | 432 | 每人六次考核，含优秀、回升、波动、需关注四类趋势。 |
| `employment` | 22 | 已就业学生的公司、薪资、Offer 时间。 |
| `staff_accounts` | 14 | 2 名管理员、12 名教师职员。 |
| `auth_login_logs` | 20+ | 成功与失败登录演示。 |
| `agent_sessions` | 12 | 已验证学生会话。 |
| `agent_messages` | 60+ | 查成绩、求评语、情绪陪伴等对话。 |
| `agent_reports` | 18 | 四类趋势对应的成长报告。 |

演示密码仅用于本地测试；脚本执行后会输出账号摘要，生产环境必须改为管理员设置的强密码。

---

## 接口设计文档

## 学生成长 Agent 与权限模块接口设计文档

- 项目名称：沃林学生管理系统
- 文档版本：V1.0
- 编写日期：2026-07-23
- 基础路径：`/api`

### 1. 通用约定

1. 新增接口使用 JSON，字符集 UTF-8。
2. 登录成功后由服务端设置短期、`HttpOnly` 的会话 Cookie；请求无须提交其他人的学号或角色。
3. 所有响应错误使用 FastAPI `detail` 字段；业务响应的对象字段保持明确命名。
4. 现有未带 `/api` 前缀的业务接口保留兼容，但必须补充认证与角色依赖项。
5. 成绩金额/分数等 `Decimal` 字段在 JSON 中输出为数值或格式化字符串，前后端统一测试。

### 2. 认证接口

#### 2.1 职员登录

`POST /api/auth/staff/login`

请求：

```json
{
  "account": "T20260701",
  "password": "Teacher@123"
}
```

成功响应：

```json
{
  "role": "teacher",
  "display_name": "陈晓宁",
  "redirect_to": "/pages/teacher-dashboard"
}
```

处理规则：验证 `staff_accounts.status=active`、校验密码哈希、写入成功/失败登录日志；不在响应中返回密码、哈希或内部账户主键。

#### 2.2 学生身份验证

`POST /api/auth/student/verify`

请求：

```json
{
  "student_no": "ST2401001",
  "name": "李欣妍"
}
```

成功响应：

```json
{
  "role": "student",
  "student": {
    "student_no": "ST2401001",
    "name": "李欣妍",
    "class_name": "AI 应用开发 2401 班"
  },
  "redirect_to": "/pages/student-agent"
}
```

处理规则：仅匹配未逻辑删除的学生；创建或更新 `agent_sessions`；账号不存在与姓名不匹配均返回统一的 401，避免枚举学生资料。

#### 2.3 获取当前身份

`GET /api/auth/me`

成功响应示例：

```json
{
  "role": "student",
  "subject_id": "ST2401001",
  "display_name": "李欣妍",
  "permissions": ["student_agent:read", "student_agent:chat"]
}
```

#### 2.4 退出登录

`POST /api/auth/logout`

清除客户端 Cookie，并将当前学生会话置为 `revoked`（职员会话仅失效 Cookie/令牌）。响应：

```json
{"message": "已安全退出登录"}
```

### 3. 学生成长 Agent 接口

所有本节接口仅允许 `student` 会话访问，且后端从会话中确定 `student_no`。

#### 3.1 成长总览

`GET /api/student-agent/overview`

响应：

```json
{
  "student": {"student_no": "ST2401001", "name": "李欣妍", "class_name": "AI 应用开发 2401 班"},
  "metrics": {
    "average_score": 82.6,
    "class_average": 78.4,
    "class_rank": 12,
    "class_size": 36,
    "pass_rate": 1.0,
    "latest_change": 6.8,
    "attention_level": "stable"
  },
  "scores": [
    {"exam_seq": 1, "score": 72.0},
    {"exam_seq": 2, "score": 76.0}
  ]
}
```

#### 3.2 成绩与趋势

`GET /api/student-agent/grades`

返回本人阶段成绩、班级均分序列、趋势标签；不得返回其他学生姓名、学号和单次成绩。

#### 3.3 获取最新成长报告

`GET /api/student-agent/reports/latest`

无历史报告时返回 404，前端显示“生成第一份评语”状态。

#### 3.4 生成成长报告

`POST /api/student-agent/reports`

请求：

```json
{"report_type": "latest_score"}
```

流程：先计算指标快照，再调用大模型生成自然语言评语；模型失败时使用规则模板生成并将 `generated_by` 标为 `fallback`。

#### 3.5 与易老师对话

`POST /api/student-agent/chat`

请求：

```json
{
  "message": "我这次成绩进步了，但还是很焦虑，该怎么做？"
}
```

响应：

```json
{
  "message_id": 101,
  "intent": "comfort",
  "answer": "能看见进步却仍觉得不踏实，这很常见。先把这 6.8 分当作一次找到方法的证据……",
  "sources": [
    {"book_name": "三国演义", "chapter": "第三十八回", "content": "……"}
  ],
  "risk_level": "normal",
  "fallback_used": false
}
```

服务端按 `grade_query`、`analysis`、`report`、`comfort`、`general` 识别意图。模型只能接收已计算的本人指标及已检索的资料，不能生成或执行 SQL。

#### 3.6 获取个人会话历史

`GET /api/student-agent/messages?limit=30`

仅返回当前学生、当前有效会话的消息，最大 `limit=50`。

### 4. 教师职员接口

以下接口要求 `teacher` 角色，服务端根据登录账户关联的 `teacher_id` 筛选班级；管理员可复用这些查询并查看全量。

| 方法与路径 | 功能 |
| --- | --- |
| `GET /api/teacher/workbench/overview` | 本人班级、学生数、班级均分、及格率、关注人数。 |
| `GET /api/teacher/classes` | 获取本人可管理班级。 |
| `GET /api/teacher/classes/{class_id}/students` | 获取一个授权班级的学生列表。 |
| `GET /api/teacher/classes/{class_id}/score-analysis` | 班级成绩趋势、分段分布、风险汇总。 |
| `POST /score/` | 录入成绩，追加教师班级范围校验。 |
| `PUT /score/` | 修改成绩，追加教师班级范围校验。 |

教师访问非授权 `class_id` 时返回 403；不提供查询学生私密 Agent 消息的接口。

### 5. 管理员接口

管理员拥有现有管理 API 的完整权限，并新增职员账户管理：

| 方法与路径 | 功能 |
| --- | --- |
| `GET /api/admin/staff-accounts` | 查询职员账户。 |
| `POST /api/admin/staff-accounts` | 新建职员账户。 |
| `PUT /api/admin/staff-accounts/{id}` | 修改显示名、角色、教师关联、状态。 |
| `POST /api/admin/staff-accounts/{id}/reset-password` | 重置演示或管理员指定的密码。 |
| `GET /api/admin/agent-statistics` | Agent 使用量、关注等级分布、报告数量等脱敏汇总。 |

### 6. 页面路由与守卫

| 页面 | 允许角色 |
| --- | --- |
| `/pages/login` | 全部用户。 |
| `/pages/student-agent` | 学生。 |
| `/pages/teacher-dashboard` | 教师、管理员。 |
| `/pages/dashboard`、`/pages/students` 等现有后台页 | 管理员；教师只暴露其工作台和受授权成绩页。 |

无身份访问受保护页面时返回登录页；身份存在但角色不匹配时返回 403 页面，不进行静默降权。

### 7. 错误码

| 状态码 | 使用场景 | 示例 `detail` |
| --- | --- | --- |
| 400 | 参数格式、报告类型非法 | `请求参数不合法` |
| 401 | 未登录、会话过期、学生验证失败 | `身份验证失败或已过期` |
| 403 | 角色或班级范围越权 | `当前身份无权访问该资源` |
| 404 | 已验证学生暂无成绩、报告不存在 | `当前暂无可用成绩数据` |
| 409 | 成绩唯一约束冲突 | `该学生本次考核成绩已存在` |
| 422 | Pydantic 字段校验失败 | FastAPI 默认校验响应。 |
| 503 | LLM/RAG 不可用 | `智能服务暂不可用，已为你提供基础分析` |

---

## 实施计划

## Student Growth Agent and Role Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为沃林学生管理系统增加学生成长 Agent、学生/职员统一登录、教师与管理员角色权限、可拖拽易老师入口及可重复演示数据。

**Architecture:** 新认证服务签发 JWT Cookie，并通过 FastAPI 依赖项将“谁在访问、能够访问什么”放在后端控制。学生 Agent 先由成绩分析服务计算确定性指标，再选择性检索现有三国 RAG，最后通过已有百炼客户端生成自然语言；模型不可直接执行数据库查询。

**Tech Stack:** Python 3.10、FastAPI 0.128、SQLAlchemy 2.0、MySQL/PyMySQL、Pydantic 2、PyJWT、bcrypt、Jinja2、原生 JavaScript、Bootstrap 5、pytest。

### Global Constraints

- 学生以“学号 + 姓名”验证，只能读取会话中学生本人的数据。
- 职员角色只允许 `admin` 和 `teacher`；教师只能访问本人负责或授课的班级。
- 既有成绩表以 `scores.exam_seq` 的 1~6 次阶段考核作为趋势维度，不新增科目维度。
- 密码仅保存 bcrypt 哈希，学生会话令牌仅保存 SHA-256 哈希。
- 易老师是原创讲坛学者角色；使用原创头像，不使用或暗示真实人物肖像。
- RAG/LLM 不可用时，必须返回本地规则生成的基础分析，不能把服务异常暴露成 500。
- 种子数据全部虚构，可重复运行，不删除、不覆盖既有业务数据。
- 本次仅借鉴 21st.dev 的深色 Bento 层级，不复制第三方组件代码或素材。

---

### 1. 实施范围

### 1. 实施范围

本计划覆盖统一登录、角色权限、学生成长 Agent、教师/管理员工作台、深色 Bento 前端、可拖拽易老师头像、演示数据和自动化测试。已有四大名著 RAG、原有业务 API 与现有数据模型保持兼容。

### 2. 实施顺序

| 阶段 | 任务 | 主要产物 | 完成标准 |
| --- | --- | --- | --- |
| 0. 基线确认 | 检查依赖、数据库连接、现有测试与工作区变更。 | 基线记录。 | 不修改无关文件；原有测试基线明确。 |
| 1. 数据与认证 | 新增 ORM、Schema、迁移/建表逻辑、认证服务与登录路由。 | 职员账户、审计、会话与 Agent 三张业务表；认证 API。 | 未登录/越权均被拒绝；密码不以明文存储。 |
| 2. 成绩分析 | 编写成绩聚合 DAO 与指标服务。 | 学生个人指标、教师班级统计。 | 指标口径固定，空成绩与异常趋势可测。 |
| 3. Agent 编排 | 实现意图识别、成绩上下文、RAG 复用、报告与聊天持久化、降级回复。 | 学生 Agent API。 | 仅能读取当前学生；模型失败仍有基础报告。 |
| 4. 职员工作台 | 增加教师与管理员页面路由、菜单过滤、班级范围保护。 | 教师工作台、职员账户入口。 | 教师仅看所属班级；管理员可管理全量。 |
| 5. 学生前端 | 实现登录页、学生成长 Bento 看板、趋势图、聊天抽屉与拖拽头像。 | `student_agent.html`、前端脚本/CSS。 | 桌面和移动端可用，拖拽不误触发点击。 |
| 6. 种子与测试 | 编写幂等种子脚本和单元/API/页面测试。 | `seed_demo_data.py`、测试用例。 | 全表有数据；重复运行无重复；测试通过。 |
| 7. 验收与文档 | 执行测试、关键流程冒烟、更新 README。 | 验收记录、启动与演示说明。 | 三种角色流程均可演示。 |

### 3. 代码组织计划

```text
Model/
  staff_account_table.py
  auth_login_log_table.py
  agent_session_table.py
  agent_message_table.py
  agent_report_table.py
Schema/
  auth_schema.py
  student_agent_schema.py
  staff_schema.py
DAO/
  staff_account_dao.py
  student_agent_dao.py
  score_analysis_dao.py
Service/ 或 Engine/
  auth_service.py
  score_analysis_service.py
  student_agent_service.py
  authorization.py
Api/
  auth_api.py
  student_agent_api.py
  teacher_workbench_api.py
  admin_staff_api.py
templates/
  login.html
  student_agent.html
  teacher_dashboard.html
css/
  student_agent.css
js/
  student_agent.js
scripts/
  seed_demo_data.py
tests/
  test_auth_api.py
  test_authorization.py
  test_score_analysis.py
  test_student_agent_api.py
```

实际目录命名以现有项目约定为准；不做与本需求无关的全仓库重构。

### 4. 测试计划

#### 4.1 单元测试

1. 密码哈希与校验：正确密码可登录，错误密码不可登录，停用职员不可登录。
2. 成绩指标：均分、班均、排名、及格率、趋势和关注等级覆盖正常、并列、无成绩、单次成绩情况。
3. 授权：学生身份忽略伪造的其他学号；教师班级范围校验；管理员全量访问。
4. Agent：不同意图组合正确；高风险词进入安全回复；模型异常返回 `fallback`。

#### 4.2 API 测试

1. 未登录访问 `/api/student-agent/overview` 返回 401。
2. 学生 A 登录后传入学生 B 学号仍只能得到 A 的数据，或参数被拒绝。
3. 教师访问非关联班级返回 403。
4. 管理员可获取全局 Agent 脱敏汇总。
5. 空成绩学生获得可读空状态，不产生 500。

#### 4.3 前端与冒烟测试

1. 职员/学生入口切换、表单校验、登录跳转正确。
2. 学生页显示指标、趋势、报告和降级提示。
3. 头像拖动超过阈值不打开抽屉，短按可打开；刷新后位置恢复。
4. 以管理员、教师、学生三个账号分别登录，检查菜单和直链访问均符合权限矩阵。

### 5. 演示数据与验收流程

1. 启动 MySQL 后执行 `python scripts/seed_demo_data.py`。
2. 使用脚本输出的管理员、教师和学生演示账号进入对应流程。
3. 学生演示：查看趋势 → 生成评语 → 询问学习焦虑 → 查看三国来源。
4. 教师演示：进入教师工作台 → 查看授权班级 → 查看成绩分析 → 修改一条本班成绩。
5. 管理员演示：管理后台 → 查看全局统计 → 查看职员账户与脱敏 Agent 汇总。

### 6. 风险与应对

| 风险 | 应对策略 |
| --- | --- |
| 现有项目没有登录体系 | 将认证与授权独立成服务和依赖项，逐步挂载到现有路由。 |
| 部分既有模型未建立外键 | 先在 DAO/服务层做归属校验，必要时通过迁移补齐约束。 |
| LLM/RAG 依赖本地服务或密钥 | 使用依赖注入和 fallback，测试不调用真实模型。 |
| 种子脚本重复写入 | 按业务唯一键预检查，并用事务提交。 |
| 教师误读学生私密对话 | 教师工作台仅返回人数和等级聚合，不提供消息明细接口。 |
| 前端组件过度依赖外部资源 | 仅借鉴布局和层级，使用项目现有 Bootstrap/原生 CSS/JS 实现。 |

### 7. 交付清单

- [ ] 需求文档、表设计文档、接口设计文档、开发计划文档
- [ ] 职员/学生统一登录页
- [ ] 角色权限与后端接口守卫
- [ ] 学生成长 Agent 页面与服务
- [ ] 教师工作台与管理员职员账户管理
- [ ] 易老师可拖拽头像按钮
- [ ] 全表虚构演示数据种子脚本
- [ ] 自动化测试和启动/演示说明

### 8. 逐任务实施清单

#### Task 1: 新增认证与 Agent 持久化模型

**Files:**

- Create: `Model/staff_account_table.py`
- Create: `Model/auth_login_log_table.py`
- Create: `Model/agent_session_table.py`
- Create: `Model/agent_message_table.py`
- Create: `Model/agent_report_table.py`
- Create: `Schema/auth_schema.py`
- Create: `Service/auth_service.py`
- Create: `tests/conftest.py`
- Create: `tests/test_auth_service.py`
- Modify: `main.py`
- Modify: `.env.example`

**Interfaces:**

```python
@dataclass(frozen=True)
class AuthPrincipal:
    role: Literal["student", "teacher", "admin"]
    subject_id: str
    display_name: str
    teacher_id: int | None = None

def hash_password(password: str) -> str: ...
def verify_password(password: str, password_hash: str) -> bool: ...
def create_access_token(principal: AuthPrincipal, expires_minutes: int) -> str: ...
def token_digest(token: str) -> str: ...
```

- [ ] **Step 1: 建立隔离测试数据库，并编写失败的密码与令牌测试。**

`tests/conftest.py` 必须用内存 SQLite 覆盖应用数据库依赖和 lifespan 使用的引擎，避免测试读取本机 MySQL：

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main as main_module
from DAO.db import Base, get_db


@pytest.fixture
def test_session(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(main_module, "engine", engine)
    yield session_factory()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_session):
    def override_get_db():
        try:
            yield test_session
        finally:
            pass
    main_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main_module.app) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(test_session):
    from datetime import datetime
    from Model.class_table import Class
    from Model.student_table import Student
    from Model.Student_score_table import Score
    from Model.teacher_table import teacher_table
    from Model.staff_account_table import StaffAccount
    from Service.auth_service import hash_password

    teacher_one = teacher_table(tname="陈晓宁", tphone="13800000001", tsubject="Python", t_code="在职")
    teacher_two = teacher_table(tname="周明远", tphone="13800000002", tsubject="数据库", t_code="在职")
    test_session.add_all([teacher_one, teacher_two])
    test_session.flush()
    class_one = Class(class_no="AI2401", name="AI 应用开发 2401 班", start_date=datetime(2026, 3, 1), head_teacher_id=teacher_one.tid, instructor_id=teacher_one.tid)
    class_two = Class(class_no="AI2402", name="AI 应用开发 2402 班", start_date=datetime(2026, 3, 1), head_teacher_id=teacher_two.tid, instructor_id=teacher_two.tid)
    test_session.add_all([class_one, class_two])
    test_session.flush()
    test_session.add_all([
        Student(student_no="ST2401001", name="李欣妍", class_id=class_one.id, age=22, gender="女"),
        Student(student_no="ST2401002", name="王子轩", class_id=class_two.id, age=22, gender="男"),
    ])
    test_session.add_all([Score(student_no="ST2401001", exam_seq=index, score=score) for index, score in enumerate([72, 76, 74, 81, 79, 86], 1)])
    test_session.add_all([
        StaffAccount(staff_no="T20260701", username="teacher01", password_hash=hash_password("Teacher@123"), display_name="陈晓宁", role="teacher", teacher_id=teacher_one.tid, status="active"),
        StaffAccount(staff_no="A20260701", username="admin01", password_hash=hash_password("Admin@123"), display_name="系统管理员", role="admin", status="active"),
    ])
    test_session.commit()
    return test_session


@pytest.fixture
def student_client(client, seeded_db):
    assert client.post("/api/auth/student/verify", json={"student_no": "ST2401001", "name": "李欣妍"}).status_code == 200
    return client


@pytest.fixture
def teacher_client(client, seeded_db):
    assert client.post("/api/auth/staff/login", json={"account": "T20260701", "password": "Teacher@123"}).status_code == 200
    return client


@pytest.fixture
def admin_client(client, seeded_db):
    assert client.post("/api/auth/staff/login", json={"account": "A20260701", "password": "Admin@123"}).status_code == 200
    return client
```

```python
## tests/test_auth_service.py
from Service.auth_service import AuthPrincipal, create_access_token, hash_password, token_digest, verify_password


def test_password_hash_cannot_be_reused_as_plaintext():
    password_hash = hash_password("Teacher@123")
    assert password_hash != "Teacher@123"
    assert verify_password("Teacher@123", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_same_token_has_stable_digest_and_contains_role():
    principal = AuthPrincipal(role="student", subject_id="ST2401001", display_name="李欣妍")
    token = create_access_token(principal, expires_minutes=30)
    assert token_digest(token) == token_digest(token)
    assert len(token_digest(token)) == 64
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `python -m pytest tests/test_auth_service.py -q`

Expected: FAIL，提示 `Service.auth_service` 或对应函数尚不存在。

- [ ] **Step 3: 实现模型和认证原语。**

`Service/auth_service.py` 使用以下核心实现，密钥从 `AUTH_SECRET` 读取：

```python
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt

AUTH_ALGORITHM = "HS256"

@dataclass(frozen=True)
class AuthPrincipal:
    role: Literal["student", "teacher", "admin"]
    subject_id: str
    display_name: str
    teacher_id: int | None = None

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_access_token(principal: AuthPrincipal, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": principal.subject_id, "role": principal.role, "name": principal.display_name,
               "teacher_id": principal.teacher_id, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, os.environ["AUTH_SECRET"], algorithm=AUTH_ALGORITHM)
```

各模型按《表设计文档》的字段定义 `__tablename__`、主键、唯一索引和创建/更新时间；`main.py` 必须显式导入新增模型，确保 `Base.metadata.create_all()` 能创建它们。`.env.example` 新增 `AUTH_SECRET=replace-with-a-long-random-secret`。

- [ ] **Step 4: 运行单元测试确认通过。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_auth_service.py -q`

Expected: `2 passed`。

- [ ] **Step 5: 提交本任务涉及的模型、认证原语和测试。**

```powershell
git add Model Schema Service/auth_service.py main.py .env.example tests/test_auth_service.py
git commit -m "feat: add auth and agent persistence models"
```

#### Task 2: 认证路由、角色依赖项与现有路由守卫

**Files:**

- Create: `Api/auth_api.py`
- Create: `Service/authorization.py`
- Create: `tests/test_auth_api.py`
- Modify: `main.py`
- Modify: `Api/frontend_api.py`
- Modify: `Api/student_api.py`
- Modify: `Api/student_score.py`

**Interfaces:**

```python
def get_current_principal(request: Request, db: Session = Depends(get_db)) -> AuthPrincipal: ...
def require_roles(*roles: str) -> Callable[..., AuthPrincipal]: ...
def require_admin(principal: AuthPrincipal = Depends(require_roles("admin"))) -> AuthPrincipal: ...
def require_teacher_or_admin(principal: AuthPrincipal = Depends(require_roles("teacher", "admin"))) -> AuthPrincipal: ...
```

- [ ] **Step 1: 编写失败的认证和越权 API 测试。**

```python
## tests/test_auth_api.py
def test_student_verification_sets_cookie_and_me_returns_student(student_client):
    response = student_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "student"
    assert response.json()["subject_id"] == "ST2401001"

def test_student_cannot_open_teacher_workbench(student_client):
    response = student_client.get("/api/teacher/workbench/overview")
    assert response.status_code == 403
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_auth_api.py -q`

Expected: FAIL，提示 `/api/auth/student/verify`、`require_roles` 或教师工作台尚未实现。

- [ ] **Step 3: 实现 Cookie 认证和授权依赖项。**

在 `Api/auth_api.py` 中实现四个端点：`POST /api/auth/staff/login`、`POST /api/auth/student/verify`、`GET /api/auth/me`、`POST /api/auth/logout`。登录成功后使用：

```python
response.set_cookie(
    key="wolink_auth",
    value=token,
    httponly=True,
    samesite="lax",
    secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    max_age=expires_minutes * 60,
)
```

`Service/authorization.py` 解码 Cookie 中 JWT，student 角色额外查询 `agent_sessions`，要求 `token_hash`、状态和到期时间均有效。`require_roles` 对已登录但角色不匹配的请求抛出 `HTTPException(403, "当前身份无权访问该资源")`，无会话或失效会话抛出 401。

将 `auth_router` 注册到 `main.py`。`frontend_api.py` 新增 `/pages/login`，并为后台页面添加相应的角色依赖；`student_api.py` 的学生 CRUD 仅管理员可用；`student_score.py` 的写操作改为教师或管理员可用，班级范围检查在 Task 6 接入。

- [ ] **Step 4: 运行认证、旧接口回归测试。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_auth_api.py tests/test_file_utils.py tests/test_text_splitter.py -q`

Expected: 全部 PASS；无 Cookie 请求返回 401，学生角色请求教师接口返回 403。

- [ ] **Step 5: 提交认证路由和授权守卫。**

```powershell
git add Api/auth_api.py Service/authorization.py Api/frontend_api.py Api/student_api.py Api/student_score.py main.py tests/test_auth_api.py
git commit -m "feat: add role based login and route guards"
```

#### Task 3: 成绩分析查询与规则化报告指标

**Files:**

- Create: `DAO/score_analysis_dao.py`
- Create: `Service/score_analysis_service.py`
- Create: `Schema/student_agent_schema.py`
- Create: `tests/test_score_analysis.py`

**Interfaces:**

```python
class ScoreOverview(BaseModel):
    average_score: float | None
    class_average: float | None
    class_rank: int | None
    class_size: int
    pass_rate: float | None
    latest_change: float | None
    attention_level: Literal["excellent", "stable", "attention", "urgent"]

def build_student_overview(db: Session, student_no: str) -> ScoreOverview: ...
def build_class_analysis(db: Session, class_id: int) -> ClassScoreAnalysis: ...
```

- [ ] **Step 1: 编写趋势、排名、空成绩的失败测试。**

```python
## tests/test_score_analysis.py
from Service.score_analysis_service import classify_attention, summarize_scores

def test_summarize_scores_calculates_average_pass_rate_and_change():
    summary = summarize_scores([72, 76, 74, 81, 79, 86])
    assert summary.average_score == 78.0
    assert summary.pass_rate == 1.0
    assert summary.latest_change == 7.0

def test_attention_level_is_urgent_for_two_recent_failures():
    assert classify_attention([70, 68, 58, 55]) == "urgent"

def test_empty_scores_return_empty_metrics_not_exception():
    summary = summarize_scores([])
    assert summary.average_score is None
    assert summary.attention_level == "attention"
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `python -m pytest tests/test_score_analysis.py -q`

Expected: FAIL，提示 `score_analysis_service` 或指标函数尚不存在。

- [ ] **Step 3: 实现纯计算逻辑和参数化聚合 DAO。**

`Service/score_analysis_service.py` 先实现不依赖数据库的计算函数，保证 `round(sum(scores) / len(scores), 1)`、`score >= 60`、最后两次差值与空列表处理具有稳定行为。`DAO/score_analysis_dao.py` 仅使用 `sqlalchemy.text()` 的命名参数：

```python
rows = db.execute(
    text("SELECT exam_seq, score FROM scores WHERE student_no=:student_no AND is_deleted=0 ORDER BY exam_seq"),
    {"student_no": student_no},
).mappings().all()
```

班级排名以每位学生 `AVG(score)` 降序计算；学生 API 仅返回当前学生自己的排名、班均和班级人数，不返回同学明细。

- [ ] **Step 4: 运行单元测试与现有成绩测试。**

Run: `python -m pytest tests/test_score_analysis.py tests/test_rag_service.py -q`

Expected: 全部 PASS。

- [ ] **Step 5: 提交成绩分析组件。**

```powershell
git add DAO/score_analysis_dao.py Service/score_analysis_service.py Schema/student_agent_schema.py tests/test_score_analysis.py
git commit -m "feat: add student score analysis service"
```

#### Task 4: 实现学生成长 Agent API 与降级回复

**Files:**

- Create: `DAO/student_agent_dao.py`
- Create: `Service/student_agent_service.py`
- Create: `Api/student_agent_api.py`
- Create: `tests/test_student_agent_api.py`
- Modify: `rag_core/clients/llm_client.py`
- Modify: `main.py`

**Interfaces:**

```python
def generate_report(db: Session, student_no: str, report_type: Literal["latest_score", "weekly", "manual"]) -> AgentReport: ...
def chat_with_student(db: Session, principal: AuthPrincipal, message: str) -> AgentChatResponse: ...
def compose_growth_reply(intent: str, message: str, overview: ScoreOverview, sources: list[dict]) -> str: ...
def build_fallback_reply(intent: str, overview: ScoreOverview) -> str: ...
```

- [ ] **Step 1: 编写 Agent 隔离与降级的失败测试。**

```python
## tests/test_student_agent_api.py
import pytest

@pytest.fixture
def unavailable_llm(monkeypatch):
    import Service.student_agent_service as agent_module
    def raise_service_unavailable(*args, **kwargs):
        raise RuntimeError("LLM unavailable")
    monkeypatch.setattr(agent_module, "compose_growth_reply", raise_service_unavailable)

def test_student_overview_uses_session_subject_not_query_parameter(student_client):
    response = student_client.get("/api/student-agent/overview?student_no=ST2401002")
    assert response.status_code == 200
    assert response.json()["student"]["student_no"] == "ST2401001"

def test_chat_returns_rule_fallback_when_llm_is_unavailable(student_client, unavailable_llm):
    response = student_client.post("/api/student-agent/chat", json={"message": "我担心这次成绩"})
    assert response.status_code == 200
    assert response.json()["fallback_used"] is True
    assert response.json()["answer"]
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_student_agent_api.py -q`

Expected: FAIL，提示学生 Agent 路由尚不存在。

- [ ] **Step 3: 实现 Agent 服务和 API。**

新增 `/api/student-agent/overview`、`/grades`、`/reports/latest`、`POST /reports`、`POST /chat`、`/messages`。所有端点首先调用 `require_roles("student")` 并只使用 `principal.subject_id`。

意图判定采用可测试的关键词优先规则：含“成绩/分数/排名”优先 `grade_query`，含“评语/总结/报告”优先 `report`，含“焦虑/难过/压力/委屈”优先 `comfort`，其余为 `general`。高风险词触发固定安全回复，不调用模型。

在 `rag_core/clients/llm_client.py` 新增 `generate_growth_reply(system_prompt: str, user_prompt: str) -> str`，复用同一个 OpenAI 客户端。`student_agent_service.compose_growth_reply()` 负责构造受控提示词并调用该方法；调用异常必须被 `chat_with_student()` 和 `generate_report()` 捕获，改为 `build_fallback_reply()`；将 `generated_by` 写为 `fallback`。聊天和报告均通过 `student_agent_dao` 事务保存，消息中的 `source_refs` 只保存必要来源摘要。

- [ ] **Step 4: 运行 Agent 与 RAG 回归测试。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_student_agent_api.py tests/test_rag_api.py tests/test_rag_service.py -q`

Expected: 全部 PASS；真实模型不参与测试。

- [ ] **Step 5: 提交 Agent 服务与接口。**

```powershell
git add DAO/student_agent_dao.py Service/student_agent_service.py Api/student_agent_api.py Schema/student_agent_schema.py rag_core/clients/llm_client.py main.py tests/test_student_agent_api.py
git commit -m "feat: add student growth agent"
```

#### Task 5: 学生登录页、成长 Bento 看板与头像交互

**Files:**

- Create: `templates/login.html`
- Create: `templates/student_agent.html`
- Create: `css/student_agent.css`
- Create: `js/student_agent.js`
- Modify: `templates/base.html`
- Modify: `Api/frontend_api.py`

**Interfaces:**

```javascript
async function verifyStudent(studentNo, name) { /* POST /api/auth/student/verify */ }
async function loadGrowthOverview() { /* GET /api/student-agent/overview */ }
function mountTeacherLauncher() { /* Pointer drag/click behavior */ }
function openAgentDrawer() { /* opens #agentDrawer */ }
```

- [ ] **Step 1: 编写可验证的页面交互测试。**

```python
## tests/test_student_pages.py
def test_login_page_is_public(client):
    response = client.get("/pages/login")
    assert response.status_code == 200
    assert "职员登录" in response.text
    assert "学生入口" in response.text

def test_student_agent_page_redirects_without_student_cookie(client):
    response = client.get("/pages/student-agent", follow_redirects=False)
    assert response.status_code in {302, 303, 307}
    assert response.headers["location"] == "/pages/login"
```

- [ ] **Step 2: 运行页面测试确认失败。**

Run: `python -m pytest tests/test_student_pages.py -q`

Expected: FAIL，提示模板或学生页面路由尚不存在。

- [ ] **Step 3: 实现模板、样式和前端脚本。**

`login.html` 使用两个可切换表单：职员提交 `/api/auth/staff/login`，学生提交 `/api/auth/student/verify`。成功后使用响应的 `redirect_to` 跳转。

`student_agent.html` 使用深色 Bento 布局：身份栏、均分卡、排名卡、Canvas 或 SVG 趋势折线、观察/报告卡、对话抽屉。`student_agent.js` 使用 Pointer Events 实现头像：

```javascript
let dragging = false;
let startX = 0;
let startY = 0;

launcher.addEventListener("pointerdown", (event) => {
  dragging = false;
  startX = event.clientX;
  startY = event.clientY;
  launcher.setPointerCapture(event.pointerId);
});
launcher.addEventListener("pointermove", (event) => {
  if (Math.hypot(event.clientX - startX, event.clientY - startY) > 8) dragging = true;
  if (dragging) moveLauncherWithinViewport(event.clientX, event.clientY);
});
launcher.addEventListener("pointerup", () => {
  if (dragging) snapAndPersistLauncher(); else openAgentDrawer();
});
```

`base.html` 根据服务端传入的 `principal.role` 渲染对应导航；学生 Agent 头像仅在 student 页面/学生会话内出现。所有 API 错误使用页面内可读提示，不弹出原始堆栈。

- [ ] **Step 4: 运行页面测试和浏览器手工冒烟。**

Run: `python -m pytest tests/test_student_pages.py tests/test_auth_api.py -q`

Expected: PASS。

手工检查：打开 `/pages/login`，用学生验证进入成长页；拖动头像后刷新页面，确认位置恢复；短按头像，确认对话抽屉打开。

- [ ] **Step 5: 提交学生体验页面。**

```powershell
git add templates/login.html templates/student_agent.html css/student_agent.css js/student_agent.js templates/base.html Api/frontend_api.py tests/test_student_pages.py
git commit -m "feat: add student agent experience"
```

#### Task 6: 教师工作台、管理员职员账户与班级范围控制

**Files:**

- Create: `DAO/staff_account_dao.py`
- Create: `DAO/teacher_workbench_dao.py`
- Create: `Api/teacher_workbench_api.py`
- Create: `Api/admin_staff_api.py`
- Create: `templates/teacher_dashboard.html`
- Create: `Schema/staff_schema.py`
- Create: `tests/test_teacher_authorization.py`
- Modify: `Api/student_score.py`
- Modify: `Api/frontend_api.py`
- Modify: `main.py`

**Interfaces:**

```python
def teacher_class_ids(db: Session, teacher_id: int) -> set[int]: ...
def ensure_teacher_can_access_class(db: Session, principal: AuthPrincipal, class_id: int) -> None: ...
def teacher_workbench_overview(db: Session, teacher_id: int) -> TeacherWorkbenchOverview: ...
```

- [ ] **Step 1: 编写教师范围与管理员全量权限的失败测试。**

```python
## tests/test_teacher_authorization.py
def test_teacher_can_read_only_assigned_class(teacher_client):
    assert teacher_client.get("/api/teacher/classes/1/students").status_code == 200
    assert teacher_client.get("/api/teacher/classes/2/students").status_code == 403

def test_admin_can_read_staff_accounts(admin_client):
    response = admin_client.get("/api/admin/staff-accounts")
    assert response.status_code == 200
    assert response.json()[0]["role"] in {"teacher", "admin"}
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_teacher_authorization.py -q`

Expected: FAIL，提示教师工作台、管理员职员接口或范围校验尚不存在。

- [ ] **Step 3: 实现工作台与权限检查。**

`teacher_class_ids()` 查询 `classes.head_teacher_id` 或 `classes.instructor_id` 等于 `principal.teacher_id` 的未删除班级。教师接口在每次按班级访问之前调用：

```python
if principal.role == "teacher" and class_id not in teacher_class_ids(db, principal.teacher_id):
    raise HTTPException(status_code=403, detail="当前身份无权访问该班级")
```

`Api/teacher_workbench_api.py` 提供工作台总览、授权班级、学生列表、班级成绩分析；仅返回 Agent `attention_level` 聚合数量。`Api/admin_staff_api.py` 提供职员查询、创建、修改状态/关联/角色及重置密码，所有端点要求 `admin`。将对应页面路由注册到 `main.py` 与 `frontend_api.py`。

- [ ] **Step 4: 运行授权与现有成绩接口测试。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_teacher_authorization.py tests/test_auth_api.py -q`

Expected: PASS；教师跨班查询返回 403，管理员访问职员账户返回 200。

- [ ] **Step 5: 提交职员工作台。**

```powershell
git add DAO/staff_account_dao.py DAO/teacher_workbench_dao.py Api/teacher_workbench_api.py Api/admin_staff_api.py Api/student_score.py Api/frontend_api.py templates/teacher_dashboard.html Schema/staff_schema.py main.py tests/test_teacher_authorization.py
git commit -m "feat: add teacher workbench and staff admin"
```

#### Task 7: 实现全表演示数据种子脚本

**Files:**

- Create: `scripts/seed_demo_data.py`
- Create: `tests/test_seed_demo_data.py`
- Modify: `README.md`

**Interfaces:**

```python
def seed_demo_data(db: Session) -> dict[str, int]: ...
def get_or_create(db: Session, model: type[Base], lookup: dict, defaults: dict) -> tuple[Base, bool]: ...
```

- [ ] **Step 1: 编写幂等与数量覆盖的失败测试。**

```python
## tests/test_seed_demo_data.py
from scripts.seed_demo_data import seed_demo_data

def test_seed_is_idempotent_and_creates_cross_table_data(test_db):
    first = seed_demo_data(test_db)
    second = seed_demo_data(test_db)
    assert first["students"] == 72
    assert second["students"] == 72
    assert first["scores"] == 432
    assert second["staff_accounts"] == 14
```

- [ ] **Step 2: 运行种子测试确认失败。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_seed_demo_data.py -q`

Expected: FAIL，提示种子脚本尚不存在。

- [ ] **Step 3: 实现事务化、幂等种子。**

脚本按部门编号、顾问编号、教师手机号/姓名组合、班级编号、学生学号、成绩 `(student_no, exam_seq)`、职员工号和会话 UUID 查询后插入。必须使用：

```python
try:
    summary = seed_demo_data(db)
    db.commit()
except Exception:
    db.rollback()
    raise
finally:
    db.close()
```

构造 4 部门、10 顾问、12 教师、6 班、72 学生、每人 6 次成绩、22 就业记录、2 管理员 + 12 教师账户、20 条登录日志、12 会话、60 条消息、18 份报告。种子中 `T20260701` 必须关联第一个班级、不得关联第二个班级，以覆盖教师跨班拒绝测试。学生成绩必须包含优秀稳定、持续回升、波动、两次近期不及格四类趋势。账户密码使用 `hash_password()`，脚本只在控制台输出演示账户，不将明文写入数据库。

- [ ] **Step 4: 运行两次种子和测试。**

Run: `$env:AUTH_SECRET='local-demo-secret'; python scripts/seed_demo_data.py`

Expected: 输出每张表总数，第二次输出相同总数且没有唯一键冲突。

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest tests/test_seed_demo_data.py -q`

Expected: PASS。

- [ ] **Step 5: 提交种子脚本与演示说明。**

```powershell
git add scripts/seed_demo_data.py tests/test_seed_demo_data.py README.md
git commit -m "feat: add idempotent demo data seed"
```

#### Task 8: 全量验证、文档同步与交付检查

**Files:**

- Modify: `README.md`
- Modify: `codex文档/需求文档.md`
- Modify: `codex文档/表设计文档.md`
- Modify: `codex文档/接口设计文档.md`
- Modify: `codex文档/开发计划文档.md`

**Interfaces:** 本任务不新增运行时接口；验证此前定义的认证、成绩分析、学生 Agent、教师工作台、管理员管理和种子脚本接口。

- [ ] **Step 1: 运行所有自动化测试。**

Run: `$env:AUTH_SECRET='test-secret'; python -m pytest -q`

Expected: 所有测试 PASS；测试不会调用真实百炼、Milvus 或外部网络。

- [ ] **Step 2: 启动本地服务并进行三角色冒烟。**

Run: `$env:AUTH_SECRET='local-demo-secret'; uvicorn main:app --host 0.0.0.0 --port 8801 --reload`

Expected: 可访问 `http://localhost:8801/pages/login`。

依次验证：学生身份验证→成长页→报告→对话；教师登录→本班分析→跨班拒绝；管理员登录→职员账户→全局汇总。

- [ ] **Step 3: 检查 API 文档与越权响应。**

Run: `Invoke-WebRequest http://localhost:8801/openapi.json -UseBasicParsing | Select-Object -ExpandProperty StatusCode`

Expected: `200`，Swagger 中包含认证、学生 Agent、教师工作台和管理员接口。

- [ ] **Step 4: 自检文档和工作区变更。**

Run: `Get-ChildItem codex文档 -Filter *.md | Select-Object Name,Length`

Expected: 四份文档存在且非空；每份文档中的接口、表名、角色和测试账号与代码一致。

- [ ] **Step 5: 提交最终验证与文档同步。**

```powershell
git add README.md codex文档
git commit -m "docs: finalize student growth agent delivery"
```
