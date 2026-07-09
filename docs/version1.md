# 工程化改造 Version 1 — 八大要点

---

## 1. 日志系统：`print()` → `logging`

**做了什么：** 全项目 `print()` 替换为 `logging.getLogger("rag.模块名")`，输出带时间戳、级别、模块名。

**涉及文件：**
- [main.py](file://D:/phython/RAG_Personal/main.py) — 主入口日志
- [app/api/chat.py](file://D:/phython/RAG_Personal/app/api/chat.py) — 对话接口日志
- [app/api/auth.py](file://D:/phython/RAG_Personal/app/api/auth.py) — 认证接口日志
- [app/utils/redis_client.py](file://D:/phython/RAG_Personal/app/utils/redis_client.py) — Redis 连接日志
- [app/utils/rabbitmq.py](file://D:/phython/RAG_Personal/app/utils/rabbitmq.py) — RabbitMQ 日志
- [app/worker.py](file://D:/phython/RAG_Personal/app/worker.py) — Worker 日志

**面试要点：**
- 为什么 `INFO` / `WARNING` / `ERROR` 要分级
- 生产环境为什么不能靠 `print()` 排查问题
- `logger.exception()` vs `logger.error()` 的区别（前者自动带堆栈）

---

## 2. 异常处理脱敏

**做了什么：**
- 全局异常处理器：生产环境返回通用 `"服务器内部错误"`，开发环境返回详情
- SSE 流异常：同样脱敏，不泄露 `str(exc)` 到前端

**涉及文件：**
- [main.py](file://D:/phython/RAG_Personal/main.py) — `global_exception_handler`，根据 `cfg.is_production` 决定返回内容
- [app/api/chat.py](file://D:/phython/RAG_Personal/app/api/chat.py) — SSE 流内 `try/except` 脱敏

**面试要点：**
- 为什么不应该把 `str(exc)` 返回给用户（信息泄露风险：数据库路径、API Key 等）
- 异常信息去哪了（日志里，运维人员可见，用户不需要看到）

---

## 3. CORS 收紧

**做了什么：** `allow_origins=["*"]` → 白名单模式 `["http://localhost:8501", "http://127.0.0.1:8000", "http://localhost:3000"]`

**涉及文件：**
- [main.py](file://D:/phython/RAG_Personal/main.py) — CORS 中间件配置
- [app/config/settings.py](file://D:/phython/RAG_Personal/app/config/settings.py) — `CORS_ORIGINS` 白名单

**面试要点：**
- 浏览器同源策略是什么
- `*` 在生产环境的危害：任意域名可调用你的 API（CSRF 风险）

---

## 4. API 限流（slowapi）

**做了什么：** 对话接口 `@limiter.limit("10/minute")`，注册 `SlowAPIASGIMiddleware` 中间件，由配置文件 `RATE_LIMIT_ENABLED` 控制开关。

**涉及文件：**
- [app/api/chat.py](file://D:/phython/RAG_Personal/app/api/chat.py) — `@limiter.limit` 装饰器
- [main.py](file://D:/phython/RAG_Personal/main.py) — 中间件注册 + `_rate_limit_exceeded_handler`
- [app/config/settings.py](file://D:/phython/RAG_Personal/app/config/settings.py) — `RATE_LIMIT_ENABLED` / `RATE_LIMIT_CHAT_PER_MINUTE`

**踩坑：** `@limiter.limit` 要求函数有名为 `request: Request` 的 Starlette 参数，不能叫别的名字。

**面试要点：**
- 为什么需要限流（防刷、保护 LLM API 额度）
- slowapi 工作原理：基于 IP 计数，可配合 Redis 存储

---

## 5. 消息队列可靠性三件套：重试 + 死信队列 + 幂等

**做了什么：**
- `consume()` 消费时加入重试循环（默认 3 次，间隔 5 秒），超限 `raise` 进死信队列
- Worker 处理前检查 `task:processed:{task_id}` Redis 键，防重复消费
- `lifespan` 里 `try/except` 包裹 RabbitMQ 连接，失败只打 WARNING 不崩溃

**涉及文件：**
- [app/utils/rabbitmq.py](file://D:/phython/RAG_Personal/app/utils/rabbitmq.py) — `consume()` 重试逻辑 + 死信交换声明
- [app/worker.py](file://D:/phython/RAG_Personal/app/worker.py) — 幂等键检查
- [main.py](file://D:/phython/RAG_Personal/main.py) — 内嵌 Worker 幂等 + `lifespan` 降级

**面试要点：**
- 为什么要有死信队列（失败消息不能丢弃，需人工/自动兜底）
- 幂等性场景：网络抖动导致同一条消息被投递两次
- 降级设计：RabbitMQ 挂了不影响对话和登录，只影响文档异步上传

---

## 6. 数据库连接池

**做了什么：** SQLite 加入 `pool_size`、`max_overflow`、`pool_timeout`、`pool_recycle`、`pool_pre_ping` 参数，启用 WAL 模式 + 外键约束。

**涉及文件：**
- [app/utils/SQL_database.py](file://D:/phython/RAG_Personal/app/utils/SQL_database.py) — `create_engine` 参数 + `@event.listens_for` 启用 WAL
- [app/config/settings.py](file://D:/phython/RAG_Personal/app/config/settings.py) — `DB_POOL_*` 配置项

**面试要点：**
- 连接池解决什么问题（频繁创建/销毁连接的开销）
- `pool_pre_ping` 作用：每次使用前 ping 一下，断开自动重连
- WAL 模式好处：读写不互斥，适合并发场景

---

## 7. 多环境配置

**做了什么：** `ENV = dev | staging | production`，配合 `is_production` / `is_dev` 属性控制行为。

**涉及文件：**
- [app/config/settings.py](file://D:/phython/RAG_Personal/app/config/settings.py) — 全部配置集中管理

**面试要点：**
- 为什么开发和生产行为要不同（开发看详情，生产做脱敏）
- 如何扩展：加 `is_staging` 属性，staging 连测试数据库

---

## 8. 前端 401 自动登出

**做了什么：** `loadSessions()` 和 `loadHistory()` 响应 401 时调用 `logout()` 清空 token 回到登录页。

**涉及文件：**
- [app/static/index.html](file://D:/phython/RAG_Personal/app/static/index.html)

**面试要点：**
- 之前 token 过期页面假死的原因：前端认为已登录，后端返回 401，前端未处理
- 修复思路：关键 API 调用处加 401 检测 → 自动清理本地状态 → 跳转登录页

---

## 🎯 面试话术

> "我在这个项目上做了几处工程化加固。
>
> 第一是日志，全项目用 logging 替代 print，分模块分级，线上出问题能快速定位。
>
> 第二是 RabbitMQ 消费加了三次重试和死信队列兜底，还有幂等标记防重复。
>
> 第三是做了降级设计，MQ 不可用时服务不崩，只关闭异步上传功能。
>
> 第四是异常安全，生产环境不向客户端泄露内部错误详情。
>
> 此外还有 CORS 白名单、API 限流、DB 连接池、多环境配置切换、前端 401 自动清理等。"

---

## 📋 改动文件清单

| 文件 | 改动类型 |
|------|----------|
| [main.py](file://D:/phython/RAG_Personal/main.py) | 日志、异常脱敏、CORS、限流中间件、MQ 降级、幂等 |
| [app/config/settings.py](file://D:/phython/RAG_Personal/app/config/settings.py) | 多环境、CORS 白名单、限流、DB 连接池、MQ 重试、Redis 密码 |
| [app/api/chat.py](file://D:/phython/RAG_Personal/app/api/chat.py) | 日志、限流装饰器、SSE 异常脱敏 |
| [app/api/auth.py](file://D:/phython/RAG_Personal/app/api/auth.py) | 日志 |
| [app/utils/rabbitmq.py](file://D:/phython/RAG_Personal/app/utils/rabbitmq.py) | 消费重试 + 死信队列 |
| [app/utils/redis_client.py](file://D:/phython/RAG_Personal/app/utils/redis_client.py) | 日志、密码支持 |
| [app/utils/SQL_database.py](file://D:/phython/RAG_Personal/app/utils/SQL_database.py) | 连接池 + WAL 模式 |
| [app/worker.py](file://D:/phython/RAG_Personal/app/worker.py) | 日志、幂等防护 |
| [app/static/index.html](file://D:/phython/RAG_Personal/app/static/index.html) | 前端 401 自动登出 |
