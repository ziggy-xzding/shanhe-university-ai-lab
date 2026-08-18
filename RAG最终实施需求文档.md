# 书籍知识库 RAG 实施说明

本文档描述山河大学学生管理系统中的可选书籍知识库 RAG 模块。它服务于知识检索智能体，目标是让学生从教材、课程资料和经授权的图书中检索学习内容。

## 1. 目标与边界

1. 支持 TXT、PDF、DOCX 文档的解析、切片、向量化和检索。
2. 回答先说明证据来自哪一本书或哪些书，再由大模型生成面向学生的解释。
3. 默认使用本地 Ollama bge-m3 作为向量模型，向量维度为 1024。
4. 默认上传知识库使用应用内的 FAISS 持久化索引。
5. rag_core/ 提供可选的 Milvus 混合检索实现，适用于更大规模的书籍集合。
6. 当前演示语料以《三国演义》为例；教材和图书馆书籍必须在获得授权后上传。
7. 不在客户端展示接口文档，知识库上传和管理能力由服务端角色授权。

## 2. 数据目录

默认源目录：

~~~text
./data/novels/
~~~

可通过 NOVEL_SOURCE_DIR 指定其他本地目录。单本书的兼容重建脚本可以通过 NOVEL_SOURCE_FILE 指定文件。个人电脑绝对路径不得写入源码、文档或提交记录。

以下内容属于本地运行数据，默认被 .gitignore 忽略：

- data/knowledge_books/：上传原文件、处理登记表和切片。
- data/faiss/：FAISS 索引和文档元数据。
- data/novels/：本地教材或小说源文件。
- volumes/：Milvus Docker 数据卷。

## 3. 推荐配置

在项目根目录复制 .env.example 为 .env，并按环境修改：

~~~dotenv
DEEPSEEK_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024

MILVUS_URI=http://localhost:19530
MILVUS_TOKEN=
MILVUS_DATABASE=ai0522
MILVUS_TIMEOUT_SECONDS=3

NOVEL_SOURCE_DIR=./data/novels
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=80
RAG_BATCH_SIZE=10
RAG_DEFAULT_TOP_K=5
RAG_RRF_K=60
~~~

API Key、Milvus Token、数据库密码和认证密钥只能从环境变量读取，不得写入源码、日志、前端响应或 Git 历史。

## 4. 默认上传流程

默认知识库接口位于 /api/multi-agent/knowledge/books：

~~~text
上传文件
  -> 扩展名和文件名校验
  -> 生成书籍版本记录
  -> 后台提取 TXT/PDF/DOCX 文本
  -> 按窗口和重叠长度切片
  -> Ollama bge-m3 批量编码
  -> 写入 FAISS 索引和来源元数据
  -> 标记 ready，允许知识检索智能体使用
~~~

处理状态包括 queued、processing、ready 和 failed。失败记录保留错误信息，并可以通过 retry 接口重新处理。再次上传同名书籍会生成新版本，旧版本不会被覆盖。

知识检索回答至少应包含：

- 书名或书名列表。
- 版本和章节/片段信息。
- 与问题相关的证据内容。
- 基于证据由 DeepSeek 生成的自然语言回答。
- 无足够证据时的明确说明，不应凭空补充事实。

## 5. Milvus 可选模式

Milvus 模式由 rag_core/、db/vdb_init_milvus.py 和 docker-compose.milvus.yml 组成。它不影响 MySQL 应用的默认启动。

启动服务：

~~~powershell
ollama pull bge-m3
docker compose -f docker-compose.milvus.yml up -d
python scripts/init_rag.py
python scripts/ingest_novels.py
~~~

Milvus 模式使用：

- Milvus Standalone 2.6 或兼容版本。
- PyMilvus 2.6 以上版本。
- 1024 维稠密向量。
- Milvus BM25 Function 生成稀疏检索结果。
- 稠密检索与 BM25 结果通过 RRF 融合。
- 文档 Collection 保存书名、版本、章节、源文件和片段哈希。
- QA Collection 保存经审核的问答示例和来源字段。

Milvus 不可用时，系统应返回可读的服务状态和修复提示；健康检查不得隐式创建数据库、Collection 或导入数据。

## 6. 权限与安全

- 系统管理者、教务管理者、教师和档案管理者可以按权限上传或查看知识库状态。
- 学生只使用已发布的知识内容，不拥有管理资料的上传权限。
- 生产环境应增加文件大小限制、病毒扫描、内容审核、对象存储、备份和删除策略。
- 书籍和教材的访问权限应与学校的版权许可、课程范围和用户角色绑定。
- 引用内容应限制长度，避免直接暴露整本书。
- 不把学生问题、书籍内容和 API Key 写入公开日志。

## 7. 相关接口

- GET /api/multi-agent/knowledge/books：列出书籍处理状态。
- POST /api/multi-agent/knowledge/books：上传书籍并异步处理。
- GET /api/multi-agent/knowledge/books/{book_id}：查看版本和处理状态。
- POST /api/multi-agent/knowledge/books/{book_id}/retry：重试失败任务。
- POST /api/multi-agent/chat/stream：通过多智能体检索并流式生成回答。
- GET /api/rag/status：查看可选 Milvus RAG 状态。
- POST /api/rag/query：执行可选 Milvus 检索问答。

接口文档仅供开发者使用，客户端页面不展示 OpenAPI 入口。

## 8. 测试要求

自动化测试不得依赖真实 DeepSeek、Ollama、Milvus、书籍文件或外部网络。应使用 mock embedding、mock LLM 和临时目录验证：

- 文件扩展名校验和安全文件名。
- 文本提取和切片边界。
- 版本递增和旧版本标记。
- 后台任务成功、失败和重试状态。
- 检索结果中的书名、版本和来源。
- 无证据时的兜底回答。
- 角色权限和学生不可上传约束。
- Milvus schema、索引参数和健康检查。

## 9. 后续演进

1. 将文件登记表和异步任务迁移到 MySQL 与持久化任务队列。
2. 增加文档审核、删除、权限标签、页码引用和版本回滚。
3. 将默认 FAISS 索引按部署规模迁移到 Milvus 或独立向量服务。
4. 增加检索质量评测、引用正确率和大模型回答安全评估。
5. 对接学校统一身份认证、教务系统和图书馆系统。

