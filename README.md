# 智能办公助手

基于 FastAPI + LangChain + Chroma + RabbitMQ + Redis 构建的企业级 AI 办公助手。具备知识库问答、报告生成、文件转换、邮件发送等能力——用自然语言驱动，完成从检索到交付的完整办公闭环。

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

面向企业内部知识管理与办公自动化场景，提供文档检索问答、报告生成、格式转换、邮件发送等一站式 AI 办公能力。用自然语言驱动 Agent，完成从信息查询到文件交付的完整闭环。

## 🧱 技术架构

```
浏览器（HTML 单页前端） 
│ ▼ FastAPI 服务（单进程托管 API + 静态资源） 
├── JWT 认证 → SQLite 用户存储 
├── SSE 流式对话
│   ├── 🤖 Agent 智能体（主路径）─ create_tool_calling_agent + AgentExecutor
│   │   ├── search_knowledge_base ─ HyDE + 向量 + BM25 + Rerank 全流程检索
│   │   ├── upload_document ─ 文档内容直接入库
│   │   ├── get_document_status ─ 知识库统计 + 关键词过滤
│   │   ├── generate_report ─ 检索 + LLM 汇总 → Markdown 报告
│   │   ├── convert_format ─ 报告格式转换（md/txt/docx）
│   │   └── send_email ─ SMTP 邮件发送 + 附件支持
│   └── RAG 链（备选路径）─ LCEL + RunnableWithMessageHistory
│       ├── HyDE 假设文档生成 
│       ├── Chroma 向量检索（DashScope Embedding） 
│       ├── BM25 关键词索引（jieba 分词） 
│       └── BGE-Reranker Cross-Encoder 重排序 
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
- **Agent 自主决策**：6 个 Function Calling 工具，自动选择检索/上传/统计/报告生成/格式转换/邮件发送
- **报告生成 + 下载**：Agent 检索知识库 → LLM 汇总 → 保存 Markdown → SSE 推送下载按钮
- **文件格式转换**：支持 md → docx / txt / md 互转，Markdown 语法自动清洗
- **邮件发送**：SMTP 协议发送，支持正文 + 附件（QQ 邮箱 / 企业邮箱）
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
│   ├── agent/                       # Agent 智能体
│   │   └── agent.py                 # Agent 定义 + 工具注册 + Prompt
│   ├── services/                    # 业务层
│   │   ├── tools/                   # Agent 工具集
│   │   │   ├── status_tool.py       # 知识库统计 + 报告生成 + 格式转换 + 邮件发送
│   │   │   ├── search_tool.py       # 知识库检索工具
│   │   │   └── upload_tool.py       # 文档上传工具
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
│   ├── data/                         # 持久化数据
│   │   ├── storage/                  # ChromaDB + MD5 记录
│   │   ├── chat_history/             # 对话历史文件
│   │   └── report/                   # 生成的报告文件
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
SILICON_BASE_URL=https://api.deepseek.com
SILICON_MODEL=deepseek-chat

# 邮件发送（可选，使用邮件功能时需要）
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=你的QQ号@qq.com
SMTP_PASSWORD=QQ邮箱授权码
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
| 邮件发送失败 | 检查 `.env` 中 SMTP 配置是否正确，QQ 邮箱需使用授权码而非登录密码 |
| 报告下载按钮不显示 | 确保 `app/data/report/` 目录存在，重启服务后自动创建 |

# 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

| 版本 | 日期         | 关键变更 |
|------|------------|---------|
| **1.6.0** | 2026-07-15 | 智能办公助手：报告生成 + 格式转换 + 邮件发送 + 附件支持 |
| **1.5.0** | 2026-07-14 | Agent 升级：Function Calling 工具封装 + AgentExecutor 串联 + 多轮会话记忆 + DeepSeek 模型切换 |
| **1.4.0** | 2026-07-09 | 工程化加固 |
| **1.3.0** | 2026-06-28 | RabbitMQ 异步文档上传 + 任务状态追踪 + 语义相似度缓存 + 独立 Worker 进程；Redis 懒加载降级 |
| **1.2.0** | 2026-06-27 | HTML 单页前端替代 Streamlit；SSE 流式 + Markdown 渲染；BM25 关键词检索；MD5 去重；会话管理增强 |
| **1.1.0** | 2026-06-20 | HyDE 假设文档检索 + BGE-Reranker 重排序；JWT 多用户认证；多格式文档解析；LCEL 链式 RAG |
| **1.0.0** | 2026-06-15 | 项目初始化：FastAPI + LangChain + Chroma + DashScope；文档上传与问答；Recall@K/MRR 评测；Streamlit 原型 |

### 🗺️ 路线图

**近期计划**
