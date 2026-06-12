**企业问答知识库**

**项目背景**:为企业内部及内外人员提供相关制度/资源获取

**技术栈**: FastAPI,python,langchain相关框架

**核心亮点**:
基于向量检索,向量存储,LLM流来实现问答查询相关操作,暂未完善多轮历史记录查询
支持txt,docs,md,pdf文件上传

## 快速开始

### 1. 环境准备
按requirements.text文件下载相关配置

### 2.运行项目
uvicorn main:app --reload  #运行后端
streamlit run ui.py    #运行前端界面后，进入http://localhost:8501界面访问项目

