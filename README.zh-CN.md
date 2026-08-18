# 山河大学学生管理系统

[English](README.md)

## 项目目的与定位

本项目的首要目的，是学习 AI Vibecoding 和多智能体工程，而不是直接交付一个已经成熟的商业教务系统。校园管理场景为学习提供了统一载体，可以把认证、权限、教务数据、知识检索、情绪支持和校园服务放在同一套可运行系统中持续实践。

“山河大学”借用了中文互联网中与“山河四省”、教育机会和公共学习愿景相关的想象。项目进一步把它理解为一处面向漂泊者的数字化学习空间：回应那些求学、工作或生活在外、长期在不同地方之间移动的人。“山河无恙”表达对安稳与尊严的愿望，“崇山仰止 · 纳川致远”表达对知识、差异和持续前行的尊重。

这是本项目的个人创作性解释，不是对网络语境的官方定义。完整的学习目标、边界、原则和路线见 [项目定位说明](项目定位说明.md)。

山河大学是本项目中的虚构学校名称，校训为“崇山仰止 · 纳川致远”。本项目是一个面向高校的角色化学生管理系统演示，覆盖学生、教师和校园系统管理者的常见业务，并提供可扩展的多智能体与书籍知识库工作台。

> 本项目包含演示账号、虚构学生数据和本地开发配置。不要把真实学生数据、教材文件、数据库备份、日志、模型索引或 API 密钥提交到公开仓库。

## 项目概览

- 统一登录：根据账号类型自动进入学生、教师或系统管理者界面。
- 学生端：学业概览、成绩与绩点、选课、课表、学生事务、寝室、图书借阅、学生发展和待办事项。
- 教师端：课程与教学班、选课管理、成绩录入、教学事务和学生支持。
- 管理者端：校园系统问题受理、反馈流转、基础数据管理和跨模块查看。
- 多智能体：山河主智能体使用语义路由和模糊意图识别，按需调用七个专业子智能体，并支持多意图拆解、会话记忆和 SSE 流式输出。
- 知识库：支持上传 TXT、PDF、DOCX 书籍，后台解析、切片、使用 Ollama bge-m3 向量化，并在回答中返回书名、版本和片段来源。
- 数据导入：Excel 是学生、班级、课程和教学班等模块的数据导入格式，不是单独的业务模块。
- 权限控制：服务端根据登录会话和角色授权，客户端不能通过传入主体编号越权访问数据。

## 技术栈与架构

~~~text
浏览器
  |  HTML/CSS/JavaScript + SSE
  v
FastAPI 应用
  |-- SQLAlchemy / MySQL 8       业务数据
  |-- 多智能体编排                路由、工具调用、专业回答、综合回答
  |-- DeepSeek API                主智能体和子智能体的自然语言生成
  |-- Ollama + bge-m3             本地知识库向量模型
  |-- FAISS                       默认上传书籍和演示知识库的本地索引
  +-- Milvus                      可选的独立高阶 RAG 模块
~~~

生产或多人联调建议使用 Docker MySQL。默认 Compose 将宿主机端口 3307 映射到容器 3306。本地开发也保留 SQLite 测试路径，测试不需要启动外部数据库。

## 目录说明

| 目录或文件 | 用途 |
| --- | --- |
| main.py | FastAPI 应用入口 |
| Api/ | 认证、学生、教师、管理者、多智能体和 RAG 路由 |
| Service/ | 业务服务、多智能体编排、知识库上传和数据处理 |
| Engine/ | LLM、Ollama embedding、FAISS 索引和底层服务客户端 |
| rag_core/ | 可选的 Milvus 混合检索 RAG 实现 |
| Model/、Schema/、DAO/ | 数据模型、请求响应结构和数据访问代码 |
| templates/、css/、js/、img/ | 前端页面、样式、脚本和图片资源 |
| scripts/ | 演示数据、知识库和 RAG 初始化脚本 |
| data/ | 仅供本地运行的数据目录；大部分内容被 Git 忽略 |
| docker-compose.yml | MySQL + 应用容器 |
| docker-compose.milvus.yml | 可选 Milvus 服务 |
| .env.example | 不含真实密钥的配置模板 |

## 快速开始

### 准备 Python 环境

建议使用 Python 3.10 或更高版本：

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
~~~

编辑 .env，至少设置 AUTH_SECRET、DB_PASSWORD、MYSQL_ROOT_PASSWORD 和自己的 DEEPSEEK_API_KEY。AUTH_SECRET 应不少于 32 个字符；数据库密码应使用强密码。

### 启动 MySQL 和应用

~~~powershell
docker compose up -d db
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3307"
python scripts/seed_demo_data.py
python main.py
~~~

访问 http://127.0.0.1:8801/pages/login。

也可以使用 Docker 启动应用：

~~~powershell
docker compose up -d --build
docker compose ps
~~~

应用容器通过 host.docker.internal:11434 访问宿主机 Ollama。Linux 环境如无法访问该地址，请将 OLLAMA_BASE_URL 改为容器可访问的宿主机地址。

### 启动本地向量模型

~~~powershell
ollama pull bge-m3
ollama list
~~~

默认向量配置：

~~~dotenv
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
~~~

上传书籍后，系统会在后台完成文本提取、切片、向量化、索引和来源登记。

## 演示账号

先运行 python scripts/seed_demo_data.py。

| 类型 | 账号 | 密码 |
| --- | --- | --- |
| 系统管理者 | admin01 | Admin@123 |
| 教师 | teacher01 | Teacher@123 |
| 新生示例 | ST240001 | 123456 |
| 丁小朱示例 | ST2401001 | 123456 |

以上账号仅用于本地演示，部署到共享或生产环境前必须修改。学生使用学号和密码登录。

## 多智能体

多智能体入口位于各角色界面左侧导航的最下方。用户可以使用自然语言提问，不需要精确匹配固定关键词。

主智能体结合用户角色、会话上下文、规则和 DeepSeek 语义路由判断是否调用子智能体。一条消息包含多个事项时，会先拆解为子任务，再综合回答。

| 子智能体 | 主要职责 |
| --- | --- |
| 教务助手 | 课程、课表、选课、成绩、学期和绩点 |
| 学习教练 | 学习计划、复习方法和知识检索 |
| 心理伙伴 | 情绪陪伴、压力疏导和风险转介 |
| 安全卫士 | 诈骗识别、账户安全和紧急安全建议 |
| 就业导师 | 实习、招聘、简历和面试建议 |
| 辅导员助手 | 请假、困难帮扶、预警和学生事务 |
| 生活管家 | 寝室、校园活动、报修和校园生活 |

流式接口为 /api/multi-agent/chat/stream，返回状态、路由元数据、回答 token 和完成事件，响应类型为 text/event-stream。

## 书籍知识库

知识检索智能体支持从知识库检索学习和图书内容，上传权限默认给予系统管理者、教务管理者、教师和档案管理者。学生可以检索已发布内容，但不能上传管理资料。

支持格式：.txt、.pdf、.docx。

~~~text
上传 -> 校验 -> 创建版本 -> 提取文本 -> 文本切片
     -> Ollama bge-m3 -> FAISS 索引 -> 检索来源 -> DeepSeek 回答
~~~

回答应先说明证据来自哪一本书或哪些书，再给出相关来源信息和大模型整理后的回答。当前演示以《三国演义》为例。上传教材和图书馆书籍前，应确认版权和访问授权。

### 可选 Milvus 模式

rag_core/ 和 docker-compose.milvus.yml 提供可选的 Milvus 2.6 混合检索模式：

~~~powershell
docker compose -f docker-compose.milvus.yml up -d
python scripts/init_rag.py
python scripts/ingest_novels.py
~~~

在 .env 中配置 MILVUS_URI、MILVUS_DATABASE 和 NOVEL_SOURCE_DIR。源文件和 Milvus 数据卷均会被忽略。

## 主要 API

OpenAPI 文档仅供开发者使用，不作为客户端功能展示。

| 路径 | 说明 |
| --- | --- |
| /api/auth/* | 登录、登出和当前会话 |
| /api/multi-agent/agents | 智能体信息 |
| /api/multi-agent/chat/stream | 多智能体 SSE 问答 |
| /api/multi-agent/knowledge/books | 书籍列表和上传 |
| /api/student-agent/* | 学生发展、待办和学生画像 |
| /api/university/* | 学校、学院、专业、课程和教学数据 |
| /api/teacher/* | 教师课程、教学班和成绩 |
| /api/archives/* | 电子档案和审计 |
| /api/rag/* | 可选 Milvus RAG 接口 |

## Excel 导入

Excel 只是业务模块上传数据时支持的文件格式，不是单独的业务模块。

| Sheet | 用途 | 字段示例 |
| --- | --- | --- |
| students | 学生档案 | student_no, name, college_code, major_code, class_no, grade |
| classes | 班级 | class_no, name, start_date, head_teacher_id |
| courses | 课程 | code, name, credits, hours |
| teaching_sections | 教学班 | course_code, term_code, teacher_id, capacity, timetable_json |

推荐流程：下载模板、上传预校验、修复错误、确认入库。

## 测试

~~~powershell
$runTemp = Join-Path (Get-Location) "pytest-run"
python -m pytest -q -p no:cacheprovider --basetemp $runTemp
python -m compileall -q Service Api Engine rag_core
~~~

自动化测试不应依赖真实 DeepSeek、Ollama、Milvus 或外部网络。

## GitHub 发布前检查

- 不提交 .env、数据库、日志、截图、书籍、学生数据和模型索引。
- 检查 git diff 和 git status。
- 任何曾在聊天、截图、提交记录或远程仓库中出现过的真实 Key，都应立即撤销并重新生成。
- 生产环境使用随机 AUTH_SECRET、强数据库密码、HTTPS、安全 Cookie 和受限 CORS。
- 上传教材、图书和档案前确认版权、隐私和访问权限。

## 后续路线

1. 将知识库登记表和异步任务迁移到 MySQL 与持久化任务队列。
2. 按规模将 FAISS 迁移到 Milvus 或其他向量服务。
3. 增加文档审核、删除、权限标签、页码引用和版本回滚。
4. 增加智能体可观测性、提示词版本、离线评测和人工转接。
5. 对接真实教务系统和图书馆系统。

## License

本仓库暂未声明开源许可证。公开发布前请根据校徽、图片、数据、书籍和第三方依赖的授权情况补充 LICENSE 文件。
