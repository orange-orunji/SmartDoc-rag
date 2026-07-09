# 企业知识库智能问答系统

基于 FastAPI + LangChain + Chroma + RabbitMQ + Redis 构建的企业级 RAG 知识库系统，支持多格式文档异步上传、三阶混合检索、多层热点缓存、多用户认证与对话管理，并内置自动化检索质量评估体系。

---

## 📑 目录

- [项目背景](#-项目背景)
- [技术架构](#-技术架构)
- [核心亮点](#-核心亮点)
- [检索策略对比](#-检索策略对比)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [常见问题](#-常见问题)
- [更新日志](#更新日志)

---

## ⭐ 项目背景

为企业内部及外部人员提供制度/资源的高效检索与问答服务，解决传统文档查找耗时、信息过载的痛点。

## 🧱 技术架构

```
浏览器（HTML 单页前端） 
│ ▼ FastAPI 服务（单进程托管 API + 静态资源） 
├── JWT 认证 → SQLite 用户存储 
├── SSE 流式对话 → LangChain RAG 链 
│ ├── HyDE 假设文档生成 
│ ├── Chroma 向量检索（DashScope Embedding） 
│ ├── BM25 关键词索引（jieba 分词） 
│ └── BGE-Reranker Cross-Encoder 重排序 
├── 双层缓存 
│ ├── MD5 精确匹配缓存（Redis） 
│ └── 语义相似度缓存（Faiss-like 内存向量） 
├── 文档异步上传 
│ ├── RabbitMQ Topic 交换机 
│ ├── 文件内容 Redis 暂存（600s 过期） 
│ └── 内嵌 Worker 异步消费 
└── 对话历史持久化（JSON 文件按用户/会话隔离）
```

> 前端为纯 HTML/CSS/JS 单页应用，由 FastAPI 直接托管，无需额外进程。

## ✨ 核心亮点

- **多格式文档解析**：支持 PDF、Word(.docx)、Markdown、TXT 文件自动解析与向量化
- **三阶混合检索**：**HyDE（假设文档嵌入）** 语义扩展 → **BM25 关键词召回** → **BGE-Reranker 重排序**，覆盖模糊语义与精确关键词两种场景
- **异步文档处理**：基于 RabbitMQ 消息队列的异步上传架构，文件内容临时存于 Redis，内嵌 Worker 后台消费，接口即时响应（HTTP 202）
- **上传任务追踪**：文档上传后通过 task_id 轮询处理状态（Pending → Processing → Completed/Failed）
- **文档 MD5 去重**：上传时自动检测内容 MD5，避免相同文档重复入库，同时重建 BM25 全量索引
- **双层热点缓存**：MD5 精确匹配（Redis）+ 语义相似度匹配（内存向量），缓存命中时延迟从 ~20s 降至 ~0.01s
- **流式 SSE 响应**：服务端推送 + 前端打字机效果，Markdown 实时渲染（表格、代码块、标题、列表）
- **多轮对话记忆**：基于 LangChain `RunnableWithMessageHistory` + 自研文件持久化存储，支持会话隔离与历史回溯
- **多用户认证与隔离**：JWT 认证 + HTTP Bearer Token，用户数据完全物理隔离
- **会话管理**：新建、切换、重命名、删除会话，每个会话独立保持上下文
- **量化评估体系**：内置 Recall@K、MRR 自动化评测脚本，支持多种检索策略对比
- **纯 HTML 单页前端**：零依赖浏览器端渲染，由 FastAPI 内置托管，无需前端框架或额外进程

## 📊 检索策略对比（Top-1 召回率）

| 策略 | 纯模糊问题 (30) | 混合问题 (30模糊+13精确) |
|------|----------------|--------------------------|
| Baseline (向量) | 53.33% | 41.86% |
| HyDEOnly | 60.00% | 51.16% |
| HyDE + Rerank | **66.67%** | **48.84%** |
| HyDE + BM25 + Rerank | 50.00% | 39.53% |

> ⚡ 核心发现：HyDE+Rerank 在语义模糊场景下提升最显著。详细实验分析见 [`EVALUATION.md`](./EVALUATION.md)。

## 📂 项目结构

```
RAG_Personal/
├── main.py                          # 入口：FastAPI + 内嵌 Worker + 托管前端
├── app/
│   ├── api/                         # 接口层
│   │   ├── auth.py                  # 注册/登录
│   │   ├── chat.py                  # SSE 流式对话、会话管理
│   │   └── document.py              # 文档异步上传
│   ├── services/                    # 业务层
│   │   ├── llm.py                   # RAG 链（LCEL）
│   │   ├── hyde.py                  # HyDE 检索增强
│   │   ├── bm25_service.py          # BM25 关键词索引
│   │   ├── rerank.py                # BGE-Reranker 重排序
│   │   ├── vector_store.py          # Chroma 向量库
│   │   ├── history_service.py       # 对话历史持久化
│   │   ├── document.py              # 文件解析 + 校验
│   │   └── KnowledgeBase_md5_service.py  # MD5 去重 + 入库
│   ├── schemas/                     # Pydantic 模型
│   ├── config/settings.py           # 环境配置
│   ├── utils/                       # 工具模块
│   │   ├── auth.py                  # JWT + 密码哈希
│   │   ├── SQL_database.py          # SQLite 连接
│   │   ├── redis_client.py          # Redis 客户端
│   │   ├── rabbitmq.py              # RabbitMQ 客户端
│   │   ├── semantic_cache.py        # 语义缓存
│   │   └── task_status.py           # 任务追踪
│   ├── static/index.html            # HTML 前端
│   ├── eval_retrieval.py            # 检索评测
│   └── worker.py                    # 独立 Worker（可选）
├── models/bge-reranker-base/        # Reranker 模型
├── requirements.txt
└── .env.example
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <你的仓库地址>
cd RAG_Personal

# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 下载模型

```bash
python download_models.py
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，并填入你的 API Key：

```bash
cp .env.example .env
```

`.env` 文件内容示例：

```ini
SILICON_API_KEY=你的API_KEY
DASHSCOPE_API_KEY=你的API_KEY
SILICON_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SILICON_MODEL=qwen-flash
```

### 4. 启动 Redis（使用缓存功能时需要）

**Windows（Docker）**：
```bash
docker run -d -p 6379:6379 redis
```

**macOS / Linux**：
```bash
redis-server
```

### 5. 运行项目

```bash
# 一键启动（前端 + 后端同一进程，访问 http://127.0.0.1:8000）
python main.py

# 如端口被占用，指定其他端口
python -m uvicorn main:app --host 127.0.0.1 --port 9000
```

浏览器访问 `http://127.0.0.1:8000` 即可体验。

> **注意**：HTML 前端已内置于 FastAPI 中，无需额外启动 Streamlit。旧版 Streamlit 前端（`app/ui.py`）仍保留可用。

## 🔧 常见问题

| 问题 | 解决方法 |
|------|---------|
| 端口 8000 被占用 | `netstat -ano \| findstr :8000` 查看 PID，`taskkill /F /PID <号>` 释放 |
| 页面加载不出来 | 确认已执行 `pip install aiofiles`，重启后端 |
| 重命名会话失败 | 需先发送一条消息创建会话文件，或刷新页面后重试 |
| RabbitMQ 连接失败 | 检查 vhost 用户权限是否为 `.*`（正则），不能只用 `*` |
| 文档上传后无响应 | 检查 RabbitMQ 是否运行，Redis 是否可连接（文件内容通过 Redis 传递） |
| Redis 连接失败 | 缓存功能自动降级，不影响核心问答；启动 Redis 后重启服务即可启用 |

# 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

| 版本 | 日期         | 关键变更 |
|------|------------|---------|
| **1.4.0** | 2026-07-09 | 工程化加固 |
| **1.3.0** | 2026-06-28 | RabbitMQ 异步文档上传 + 任务状态追踪 + 语义相似度缓存 + 独立 Worker 进程；Redis 懒加载降级 |
| **1.2.0** | 2026-06-27 | HTML 单页前端替代 Streamlit；SSE 流式 + Markdown 渲染；BM25 关键词检索；MD5 去重；会话管理增强 |
| **1.1.0** | 2026-06-20 | HyDE 假设文档检索 + BGE-Reranker 重排序；JWT 多用户认证；多格式文档解析；LCEL 链式 RAG |
| **1.0.0** | 2026-06-15 | 项目初始化：FastAPI + LangChain + Chroma + DashScope；文档上传与问答；Recall@K/MRR 评测；Streamlit 原型 |

### 🗺️ 路线图

**近期计划**

- Docker 一键部署
- 会话全文检索与过滤
- 文档管理增强（列表查看、删除）
- 查询意图分类，按需启用 BM25

**🤖 Agent 升级方案（v2.0 目标）**

从被动检索式 RAG 升级为具备自主决策能力的 Agent，最终打造一个能理解指令、调用工具、处理文件的智能办公助手。

| 阶段 | 内容 | 说明 |
|------|------|------|
| **1. Agent 架构升级** | RAG 链式调用 → Agent 自主决策 | 引入 LangChain Agent 框架，让模型不再按固定链路执行，而是根据用户意图自主规划与调用工具 |
| **2. 上下文持久化记忆** | 对话上下文文本存储 + 多轮会话记忆 | 将完整对话上下文持久化，支撑 Agent 在多轮交互中保持连贯推理与状态追踪 |
| **3. Function Calling 工具封装** | 检索能力封装为 LangChain Tool | 将现有 HyDE 检索、BM25 召回、Rerank 重排序等能力封装成标准 Function Calling 工具，供 Agent 按需调用 |
| **4. AgentExecutor 串联** | Tools + Memory + LLM 统一调度 | 通过 `AgentExecutor` 将工具集、对话记忆、LLM 推理串联，跑通首个能自主决策的 Agent 工作流 |
| **5. 智能办公助手** | 文件处理 + 文件发送 | 最终目标：Agent 不仅能检索问答，还能处理用户上传的文件、生成报告并主动发送，成为全功能智能办公助手 |

> 🔗 技术路线：`RAG 检索能力` → `Function Calling Tool 封装` → `AgentExecutor (Tools + Memory + LLM)` → `智能办公助手`
