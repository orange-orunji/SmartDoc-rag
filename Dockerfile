# ═══════════════════════════════════════
# 三阶段构建：frontend 产出 Vue 构建产物 → builder 安装 Python 依赖 → runtime 集成
# ═══════════════════════════════════════

# ── 前端构建阶段（Vue 3 + Vite）──
FROM node:22-alpine AS frontend

WORKDIR /fe

# 先复制依赖清单，利用 Docker 缓存层
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# 复制前端源码并构建（产物输出至 /fe/dist）
COPY frontend/ ./
RUN npm run build

# ═══════════════════════════════════════
# Python 依赖构建阶段（减少最终镜像体积）
# ═══════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ═══════════════════════════════════════
# 运行时阶段
# ═══════════════════════════════════════
FROM python:3.11-slim AS runtime

WORKDIR /app

# 安装运行时依赖（jieba 分词等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制已安装的包
COPY --from=builder /root/.local /root/.local

# 确保 pip 安装的包在 PATH 中
ENV PATH=/root/.local/bin:$PATH

# 复制项目代码
COPY . .

# 复制前端构建产物（FastAPI 检测到 frontend/dist 存在时自动托管 Vue 前端）
COPY --from=frontend /fe/dist ./frontend/dist

# 创建数据目录（应用数据位于 app/data 下）
RUN mkdir -p /app/app/data/uploads /app/app/data/storage /app/app/data/chat_history /app/app/data/report

# 暴露端口
EXPOSE 8000

# 默认启动 API 服务（通过 docker-compose 可覆盖为 worker）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
