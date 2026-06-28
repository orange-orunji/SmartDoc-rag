深度思考
```The user wants a summary of how the workflow changed after adding RabbitMQ. Let me provide a clear comparison.
```
## RabbitMQ 异步改造 — 工作流程对比总结

---

### 架构变化

```
改造前（同步阻塞）                    改造后（消息驱动异步）
─────────────────────                ─────────────────────
                                     
  用户上传文件                           用户上传文件
       │                                     │
       ▼                                     ▼
  FastAPI 接收                            FastAPI 接收
       │                                     │
       ├─ 校验大小/格式         ←相同→        ├─ 校验大小/格式
       ├─ 解析PDF/DOCX                      ├─ 存文件内容到 Redis  ← 新
       ├─ MD5去重                           ├─ 记状态 pending       ← 新
       ├─ 文本切割                           ├─ 发消息到 RabbitMQ    ← 新
       ├─ 向量化(API调用)                    │
       ├─ 存 ChromaDB                       └─ 立即返回 202 + task_id  
       ├─ 重建BM25索引                                               │
       │                                                        异步 ↓
       └─ 返回 200                                              Worker 收到消息
            │                                                       │
       用户等 5~30 秒 ← 阻塞                                       ├─ 从 Redis 取文件
                                                                   ├─ 解析PDF/DOCX
                                                                   ├─ MD5去重
                                                                   ├─ 文本切割
                                                                   ├─ 向量化(API调用)
                                                                   ├─ 存 ChromaDB
                                                                   ├─ 重建BM25索引
                                                                   └─ 记状态 completed/failed
```


---

### 核心变化一览

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| **用户体验** | 上传后白屏等 5~30 秒 | 秒级返回，后台处理 |
| **文件处理** | 请求线程内同步执行 | Worker 异步消费 |
| **大文件** | 可能超时断开 | 无超时风险 |
| **重试机制** | 失败即丢失 | 死信队列可自动重试 |
| **并发上传** | 串行排队 | Worker `prefetch_count=2` 并发 |
| **进度感知** | 无 | Redis 状态追踪 `pending→processing→completed` |
| **文件传输** | — | 大文件走 Redis，消息体只传 task_id |

---

### 新增文件

| 文件 | 作用 |
|------|------|
| `app/utils/rabbitmq.py` | RabbitMQ 连接管理、发布、消费 |
| `app/utils/task_status.py` | Redis 任务状态追踪（pending/processing/completed/failed） |
| `app/worker.py` | 独立 Worker 进程，消费队列并处理文件 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `app/api/document.py` | 上传接口：只校验 → 存 Redis → 发消息 → 返回 202 |
| `app/services/document.py` | 拆分出纯校验 `validate_upload()` |
| `main.py` | lifespan 中连接 RabbitMQ，启动时建 BM25 |
| `app/config/settings.py` | 新增 RabbitMQ + vhost 配置 |
| `requirements.txt` | 新增 `aio-pika` |

---

### 数据流

```
用户 → FastAPI → Redis(存文件) + RabbitMQ(发消息) → Worker → ChromaDB + BM25
                    │                                          │
                    └── TaskTracker ↔ Redis(状态) ←─────────────┘
                              ↑
                    前端轮询 GET /upload/status/{task_id}
```


---

### 启动方式

```powershell
# 终端 1：Worker（消费者）
python -m app.worker

# 终端 2：FastAPI（生产者 + API）
python main.py
```


**一句话总结：** 上传从「同步等待全流程走完」变成了「秒级确认 + 后台异步处理」，用户不用再对着白屏干等了。