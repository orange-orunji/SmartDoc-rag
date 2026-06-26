# 企业知识库智能问答系统

基于 FastAPI + LangChain + Chroma 构建的企业级 RAG 知识库系统，支持多格式文档上传、三阶混合检索、多用户认证与对话管理、热点问题缓存，并具备自动化检索质量评估体系。

## ⭐ 项目背景

为企业内部及外部人员提供制度/资源的高效检索与问答服务，解决传统文档查找耗时、信息过载的痛点。

## 🧱 技术架构

```
登录 → JWT 认证 → 用户 → Streamlit 前端 → FastAPI 后端 → LangChain RAG 链
  ├── SQLite 用户存储
  └── 用户 ID 会话隔离
                 后端服务：
                 ├── Chroma 向量库
                 ├── HyDE 假设文档生成
                 ├── BM25 关键词索引
                 ├── BGE-Reranker 重排序
                 └── Redis 热点缓存
```

## ✨ 核心亮点

- **多格式文档解析**：支持 PDF、Word(.docx)、Markdown、TXT 文件自动解析与向量化
- **智能检索增强**：集成 **HyDE（假设文档嵌入）**、**BGE-Reranker 重排序**、**BM25 关键词检索**，构建三阶混合检索架构
- **多轮对话记忆**：基于 LangChain `RunnableWithMessageHistory` + 自研文件持久化存储，支持会话隔离与历史回溯
- **流式响应**：服务端 SSE 推送，前端逐字打字机效果
- **多用户认证与隔离**：JWT 认证 + Cookie 持久化登录，用户数据完全物理隔离
- **会话管理**：可新建、切换、搜索历史会话，每个会话独立保持上下文
- **Redis 热点缓存**：缓存高频问题，避免重复推理，响应延迟从 23s 降至 0.01s
- **量化评估体系**：内置 Recall@K、MRR 自动化评测脚本，对比不同检索策略效果

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
├── main.py                         # FastAPI 入口
├── download_models.py              # 下载 BGE-Reranker 模型
├── requirements.txt                # Python 依赖
├── app/
│   ├── api/                        # FastAPI 接口层
│   │   ├── auth.py                 # 注册/登录
│   │   ├── chat.py                 # 对话流式、历史、会话管理
│   │   └── document.py             # 文档上传
│   ├── services/                   # 业务逻辑层
│   │   ├── llm.py                  # RAG 链构建
│   │   ├── hyde.py                 # HyDE 检索增强
│   │   ├── bm25_service.py         # BM25 关键词索引
│   │   ├── rerank.py              # BGE-Reranker 重排序
│   │   ├── vector_store.py         # Chroma 向量库封装
│   │   ├── history_service.py      # 对话历史持久化
│   │   ├── chat.py                 # 聊天业务逻辑
│   │   ├── document.py             # 文档处理逻辑
│   │   └── KnowledgeBase_md5_service.py  # MD5 去重
│   ├── schemas/                    # Pydantic 请求/响应模型
│   ├── config/                     # 配置文件
│   ├── utils/                      # 工具模块
│   │   ├── auth.py                 # JWT 令牌、密码加密
│   │   ├── SQL_database.py         # SQLite 数据库连接
│   │   ├── redis_client.py         # Redis 客户端
│   │   └── semantic_cache.py       # 语义缓存
│   ├── eval_questions.json         # 评测问题集
│   ├── eval_retrieval.py           # 检索质量评测脚本
│   ├── redis_retrieval.py          # Redis 压测脚本
│   └── ui.py                       # Streamlit 前端界面
└── models/                         # （需自行下载）BGE-Reranker 模型
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

**启动后端**：
```bash
uvicorn main:app --reload
```

**启动前端**：
```bash
streamlit run app/ui.py
```

浏览器访问 `http://localhost:8501` 即可体验。

## 😳 后续规划

- **Docker 一键部署**：编写 Dockerfile 和 docker-compose，实现容器化交付
- **历史文件索引和删除操作**：支持会话重命名、删除，以及历史记录的全文检索
- **前端 UI 优化**：提升移动端适配和交互体验