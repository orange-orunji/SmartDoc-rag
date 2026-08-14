"""统一日志配置：控制台 + 按天轮转文件。

供 main.py（FastAPI 主进程）、app/worker.py（独立 Worker）、
app/utils/task_handler.py（内嵌消费）共用，避免三处重复 basicConfig。

约定：各模块通过 logging.getLogger("rag.<子模块>") 获取 logger，
统一格式为 `时间 | 级别 | logger 名 | 消息`。
"""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from app.config.settings import get_settings, BASE_DIR

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """初始化根日志（幂等，重复调用不会叠加 handler）。

    - 控制台：实时输出，格式与之前 basicConfig 一致
    - 文件：app/data/logs/app.log，每天午夜轮转，保留 7 份，UTF-8 编码
    """
    root = logging.getLogger()
    if root.handlers:  # 已被其他模块初始化过（如 task_handler 先被 import）
        return

    cfg = get_settings()
    root.setLevel(getattr(logging, cfg.LOG_LEVEL))

    # 库级降噪：httpx/uvicorn 的请求细节太吵，业务日志才需要 INFO
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    log_dir = BASE_DIR / "app/data/logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        log_dir / "app.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
