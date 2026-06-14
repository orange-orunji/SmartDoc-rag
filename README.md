## 企业问答知识库

## ⭐项目背景:为企业内部及内外人员提供相关制度/资源获取

## 🧱 技术架构

```text
用户 → Streamlit 前端 → FastAPI 后端 → LangChain RAG 链
                                    ├── Chroma 向量库
                                    ├── HyDE 假设文档生成
                                    ├── BM25 关键词索引
                                    └── BGE-Reranker 重排序
```
## ✨ 核心亮点

- **多格式文档解析**：支持 PDF、Word (.docx)、Markdown、TXT 文件自动解析与向量化  
- **智能检索增强**：集成 **HyDE（假设文档嵌入）**、**BGE-Reranker 重排序**、**BM25 关键词检索**，构建三阶混合检索架构  
- **多轮对话记忆**：基于 LangChain `RunnableWithMessageHistory` + 自研文件持久化存储，支持会话隔离与历史回溯  
- **流式响应**：服务端 SSE 推送，前端逐字打字机效果，提升用户体验  
- **会话管理**：可新建/切换/搜索历史会话，每个会话独立保持上下文  
- **量化评估体系**：内置 Recall@K、MRR 自动化评测脚本，对比不同检索策略效果（详见 [`EVALUATION.md`](./EVALUATION.md)）

## 📊 检索策略对比（Top-1 召回率）
| 策略 | 纯模糊问题 (30) | 混合问题 (30模糊+13精确) |
|------|----------------|--------------------------|
| Baseline (向量) | 53.33% | 41.86% |
| HyDEOnly | 60.00% | 51.16% |
| HyDE + Rerank | **66.67%** | **48.84%** |
| HyDE + BM25 + Rerank | 50.00% | 39.53% |

> ⚡ 核心发现：HyDE+Rerank 在语义模糊场景下提升最显著；BM25 需在更大语料与精确查询中发挥作用。  
> 📄 详细实验分析见 [`EVALUATION.md`](./EVALUATION.md)。

## 🚀快速开始
### 1. 环境准备

pip install -r requirements.txt

#### 环境变量声明
## 复制环境变量模板并填写 API Key
cp .env.example .env
## 编辑 .env 文件，填入你的 API Key

### 2.运行项目
uvicorn main:app --reload  #运行后端

streamlit run ui.py    #运行前端界面后，进入http://localhost:8501

