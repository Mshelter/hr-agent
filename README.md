# HR Agent

面向企业人力资源场景的智能 Agent 系统，提供招聘、知识库问答、简历评估、面试管理与培训考试等能力。

## 项目亮点

- 基于 FastAPI + Vue 3 构建前后端分离应用
- 集成 PostgreSQL + pgvector，实现文档向量化、相似度检索与 RAG 问答
- 支持通义千问模型、查询改写与 Rerank，提高知识库检索相关性
- 提供 JWT/OAuth2 认证、RBAC 权限控制、文档管理和流式对话接口
- 使用 Docker Compose 编排 PostgreSQL/pgvector 等基础服务

## 技术栈

**Backend:** Python 3.10+, FastAPI, SQLAlchemy, Alembic, LangChain  
**Frontend:** Vue 3, Vite, Pinia, Vue Router, Element Plus, Axios  
**Data & AI:** PostgreSQL, pgvector, Qwen, RAG  
**Deployment:** Docker, Docker Compose

## 目录结构

```text
backend/     后端 API、领域模型、业务服务与数据处理
frontend/    Vue 3 前端应用
```

## 本地运行

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

后端 API 文档默认地址：`http://localhost:8000/api/v1/docs`。运行前请在 `backend/.env` 中配置数据库和模型服务密钥；`.env` 不应提交到 Git。

## 项目说明

本仓库仅包含可公开的源代码与配置模板。运行时生成的虚拟环境、依赖缓存、上传文件、日志和密钥均已通过 `.gitignore` 排除。

## License

MIT
