# ═══════════════════════════════════════
# 多阶段构建：builder 阶段减少最终镜像体积
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

# 创建数据目录（应用数据位于 app/data 下）
RUN mkdir -p /app/app/data/uploads /app/app/data/storage /app/app/data/chat_history /app/app/data/report

# 暴露端口
EXPOSE 8000

# 默认启动 API 服务（通过 docker-compose 可覆盖为 worker）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
