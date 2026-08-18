# Project Positioning

## One-sentence definition

Shanhe University is an AI Vibecoding and multi-agent engineering learning project presented as a fictional digital university.

It uses a believable campus management system as the application context so that the author can learn, by building a real workflow, how to use AI-assisted coding, design APIs and data models, orchestrate multiple agents, connect retrieval and LLM services, and evaluate the safety and usability of AI features.

## Why “Shanhe University”

In common online Chinese usage, “Shanhe University” is an imagined university rather than an official institution. The name is often connected with the public discussion around “Shanhe Four Provinces” and the uneven distribution of higher-education opportunities. It represents an imagined institution built from shared hopes for education, fairness, and belonging.

This project adds a personal interpretation:

- Shanhe means mountains and rivers, but also the places people leave and the places they hope to reach.
- University means a shared learning space, not only a campus or a degree.
- The project is intended to acknowledge people who study, work, or live away from home and feel that they are constantly moving between places.
- The interface theme “山河无恙” expresses a wish for stability, dignity, and a place where a person can continue learning without being reduced to an account number.
- The motto “崇山仰止 · 纳川致远” connects respect for knowledge with the ability to accept different experiences and keep moving forward.

This is a creative interpretation for this repository, not an official definition or claim about the origin of the Internet meme.

## Learning goals

The project is organized around the following learning goals:

1. AI Vibecoding: learn to turn requirements, screenshots, design references, and iterative feedback into working frontend and backend changes.
2. Full-stack engineering: practice authentication, role-based permissions, data modeling, APIs, asynchronous jobs, frontend state, and deployment.
3. Multi-agent engineering: build a primary agent, specialist agents, semantic routing, tool calls, multi-intent decomposition, memory, streaming, and fallbacks.
4. RAG engineering: upload authorized books, extract and chunk text, create local embeddings with Ollama bge-m3, retrieve evidence, and synthesize answers with DeepSeek.
5. AI product judgment: distinguish a demo from a production service, surface uncertainty, protect personal data, and design human handoff for sensitive topics.
6. Continuous learning: use the campus application as a long-running laboratory rather than trying to finish every domain module at once.

## What this project is and is not

### It is

- A learning laboratory for AI-assisted software development.
- A multi-agent reference implementation with visible routing and tool boundaries.
- A full-stack prototype that makes AI engineering concrete through academic and campus workflows.
- A narrative interface about learning, movement, memory, and belonging.

### It is not

- An official system of Shanhe University.
- A replacement for a real university ERP, academic system, library system, or psychological counseling service.
- A claim that generated academic, career, or emotional advice is authoritative.
- A license to upload student records, copyrighted books, or private institutional data.

## Product principles

- Show the agent's role and evidence instead of hiding all orchestration behind a generic chat box.
- Let the primary agent coordinate, but keep specialist responsibilities narrow and testable.
- Prefer tool results and citations for academic facts; use the LLM for explanation and communication.
- Treat emotional support as companionship and triage, never diagnosis.
- Keep demo data fictional and configuration secrets outside the repository.
- Optimize for learning value and explainability before optimization for scale.
- Record failures and fallback paths as part of the learning artifact.

## Current stage

The repository currently demonstrates:

- Role-based student, teacher, and system administrator workspaces.
- A DeepSeek-backed primary agent with seven specialist agents.
- Fuzzy semantic routing and multi-intent decomposition.
- SSE token streaming in the multi-agent workspace.
- Ollama bge-m3 local embeddings.
- Uploadable book knowledge bases with FAISS persistence and optional Milvus RAG.
- Academic data, course selection, GPA, library, dormitory, student development, and issue feedback demos.

The main gaps are production-grade evaluation, durable background jobs, document governance, observability, and real integrations. These gaps are intentional learning targets, not features to conceal.

## Suggested learning path

1. Build a small page with AI assistance and review every generated change.
2. Add a real database model and an authenticated API.
3. Separate user roles and enforce permissions on the server.
4. Implement one specialist agent with one reliable tool.
5. Add a primary router and route traces.
6. Add streaming and conversation memory.
7. Add a small authorized knowledge base with source display.
8. Add offline tests for routing, retrieval, safety, and fallback behavior.
9. Document what is simulated, what is connected, and what remains experimental.

