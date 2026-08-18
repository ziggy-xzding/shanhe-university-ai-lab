# Shanhe University Student Management System

[简体中文](README.zh-CN.md)

Shanhe University is a fictional institution used by this project. Its motto is “崇山仰止 · 纳川致远”. This repository contains a role-based university management demo for students, teachers, campus administrators, multi-agent assistants, and book knowledge retrieval.

> Demo accounts and fictional records are for local development only. Never commit real student data, copyrighted books, database dumps, logs, model indexes, or API keys.

## Project Purpose and Positioning

This is primarily a learning laboratory for AI Vibecoding and multi-agent engineering, not a finished commercial campus ERP. The university scenario gives the learning work a coherent domain: authentication, permissions, academic data, knowledge retrieval, emotional support, and campus services can be built and tested together.

The fictional name Shanhe University draws on the common online association with “Shanhe Four Provinces” and shared hopes for education and belonging. This project extends that symbol into a digital place for people who study, work, or live away from home and feel they are always moving between places. “山河无恙” expresses a wish for stability and dignity; “崇山仰止 · 纳川致远” connects respect for knowledge with openness and continued progress.

The interpretation is creative and personal, not an official definition of the Internet term. See [Project Positioning](PROJECT_POSITIONING.md) for the learning goals, product boundaries, principles, and roadmap.

## Features

- Unified login with automatic role-based redirection.
- Student modules for academics, grades and GPA, course selection, timetable, dormitory, library loans, student development, and actionable todos.
- Teacher modules for courses, teaching sections, enrollment, grading, and student support.
- Administrator workflows for receiving system issues from students and teachers and forwarding them to IT maintenance staff.
- A primary assistant with fuzzy semantic routing, seven specialist agents, multi-intent decomposition, conversation memory, and SSE streaming.
- TXT, PDF, and DOCX book uploads with background extraction, chunking, local Ollama bge-m3 embeddings, FAISS indexing, source metadata, and DeepSeek answer synthesis.
- Excel as an upload format for domain modules, not as a standalone business module.
- Server-side authorization based on the authenticated role.

## Architecture

~~~text
Browser
  |  HTML/CSS/JavaScript + Server-Sent Events
  v
FastAPI application
  |-- SQLAlchemy / MySQL 8       Business data
  |-- Multi-agent orchestration  Routing, tools, specialist answers
  |-- DeepSeek API                Semantic routing and generation
  |-- Ollama + bge-m3             Local embedding model
  |-- FAISS                       Default local knowledge index
  +-- Milvus                      Optional high-scale RAG mode
~~~

The recommended multi-user setup uses MySQL 8 in Docker. Host port 3307 maps to container port 3306. Local SQLite-compatible paths remain available for development tests.

## Project Structure

| Path | Purpose |
| --- | --- |
| main.py | FastAPI entry point |
| Api/ | Authentication, student, teacher, administrator, agent, and RAG routes |
| Service/ | Business services, orchestration, knowledge upload, and processing |
| Engine/ | LLM, Ollama embedding, FAISS, and infrastructure clients |
| rag_core/ | Optional Milvus hybrid retrieval implementation |
| Model/, Schema/, DAO/ | Models, schemas, and data access |
| templates/, css/, js/, img/ | Frontend templates, styles, scripts, and assets |
| scripts/ | Demo data and RAG initialization scripts |
| data/ | Local runtime data, ignored by Git |
| docker-compose.yml | MySQL and application services |
| docker-compose.milvus.yml | Optional Milvus service |
| .env.example | Safe configuration template |

## Quick Start

### Python environment

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
~~~

Set these values in .env:

- AUTH_SECRET: a random value with at least 32 characters.
- DB_PASSWORD and MYSQL_ROOT_PASSWORD: matching local MySQL passwords.
- DEEPSEEK_API_KEY: your own key, never a key copied from a chat or screenshot.

### Start MySQL and the application

~~~powershell
docker compose up -d db
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3307"
python scripts/seed_demo_data.py
python main.py
~~~

Open http://127.0.0.1:8801/pages/login.

To run the application in Docker:

~~~powershell
docker compose up -d --build
docker compose ps
~~~

The container reaches host Ollama through host.docker.internal:11434. On Linux, set OLLAMA_BASE_URL to an address reachable from the container when needed.

### Pull the embedding model

~~~powershell
ollama pull bge-m3
ollama list
~~~

Default embedding configuration:

~~~dotenv
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
~~~

## Demo Accounts

Run python scripts/seed_demo_data.py first.

| Role | Username | Password |
| --- | --- | --- |
| System administrator | admin01 | Admin@123 |
| Teacher | teacher01 | Teacher@123 |
| Freshman demo student | ST240001 | 123456 |
| Ding Xiaozhu demo student | ST2401001 | 123456 |

These accounts are local demo accounts only. Change them before any shared or production deployment. Students log in with their student number and password.

## Multi-Agent System

The multi-agent workspace is at the bottom of the left navigation. Natural-language questions are supported; exact keywords are not required.

The primary agent uses role, conversation context, rules, and DeepSeek semantic routing. It can decompose a message containing multiple requests and synthesize the specialist results.

| Specialist | Responsibility |
| --- | --- |
| Academic assistant | Courses, timetable, enrollment, grades, terms, and GPA |
| Learning coach | Study plans, revision methods, and knowledge retrieval |
| Mental companion | Emotional support, stress relief, and safety referrals |
| Safety guardian | Fraud detection, account security, and urgent safety advice |
| Career advisor | Internships, recruitment, resumes, and interviews |
| Counselor assistant | Leave requests, hardship support, alerts, and student affairs |
| Campus life manager | Dormitory, events, maintenance, and campus services |

The streaming endpoint is /api/multi-agent/chat/stream. It returns status events, route metadata, answer tokens, and a final event as text/event-stream.

## Book Knowledge Base

The knowledge agent retrieves learning and library content from authorized TXT, PDF, and DOCX books.

~~~text
Upload -> validate -> create version -> extract text -> split chunks
       -> Ollama bge-m3 -> FAISS index -> retrieve sources -> DeepSeek answer
~~~

Answers should identify the book or books that supplied evidence before presenting the LLM response. The demo uses Romance of the Three Kingdoms. Upload textbooks and library books only after confirming copyright and access permissions.

### Optional Milvus mode

The rag_core directory and docker-compose.milvus.yml provide an optional Milvus 2.6 hybrid retrieval mode:

~~~powershell
docker compose -f docker-compose.milvus.yml up -d
python scripts/init_rag.py
python scripts/ingest_novels.py
~~~

Configure MILVUS_URI, MILVUS_DATABASE, and NOVEL_SOURCE_DIR in .env. Source files and Milvus volumes are ignored.

## API Index

OpenAPI documentation is for developers and is not exposed as a client-facing module.

| Route | Description |
| --- | --- |
| /api/auth/* | Login, logout, and current session |
| /api/multi-agent/agents | Agent metadata |
| /api/multi-agent/chat/stream | Multi-agent SSE chat |
| /api/multi-agent/knowledge/books | Book list and upload |
| /api/student-agent/* | Student development, todos, and profile |
| /api/university/* | University academic data |
| /api/teacher/* | Teacher courses, sections, and grades |
| /api/archives/* | Electronic archives and audit |
| /api/rag/* | Optional Milvus RAG |

## Excel Imports

Excel is an upload format supported by domain modules.

| Sheet | Purpose | Example fields |
| --- | --- | --- |
| students | Student records | student_no, name, college_code, major_code, class_no, grade |
| classes | Classes | class_no, name, start_date, head_teacher_id |
| courses | Courses | code, name, credits, hours |
| teaching_sections | Teaching sections | course_code, term_code, teacher_id, capacity, timetable_json |

Use the application workflow: download a template, upload for validation, fix errors, and confirm the import.

## Testing

~~~powershell
$runTemp = Join-Path (Get-Location) "pytest-run"
python -m pytest -q -p no:cacheprovider --basetemp $runTemp
python -m compileall -q Service Api Engine rag_core
~~~

Automated tests should not require real DeepSeek, Ollama, Milvus, or external network access.

## Security and Privacy

Keep .env, database exports, logs, local files, FAISS indexes, Milvus volumes, student records, and book contents out of Git. Rotate any key that has ever appeared in a chat, screenshot, commit, or remote repository. Production should use a random authentication secret, strong database credentials, HTTPS, secure cookies, restricted CORS origins, file scanning, access-controlled storage, and a retention policy.

## Roadmap

1. Move the book registry and background jobs to MySQL and a durable task queue.
2. Move large knowledge collections from local FAISS to Milvus or another vector service.
3. Add document review, deletion, access labels, page citations, and version rollback.
4. Add agent observability, prompt versioning, offline evaluation, and human handoff.
5. Integrate real academic and library systems after contracts and permissions are defined.

## License

No open-source license has been declared yet. Add a suitable LICENSE file before publishing, after checking rights for branding, images, datasets, books, and third-party dependencies.
