# -*- coding: utf-8 -*-
"""维护工具：清缓存 / 移除评测断点题目

用法（项目根目录执行）：
    python scripts/maintenance.py clear-cache        # 清 Redis 缓存键（前缀匹配，不 FLUSHDB）
    python scripts/maintenance.py retry 7,8,9        # 从评测断点中移除指定题（下次只重跑这些）

注意：清缓存后建议重启服务（语义缓存的内存向量索引随进程清空）。
"""
import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CHECKPOINT = os.path.join(ROOT, "app", "eval_agent_checkpoint.json")


def clear_cache():
    from app.config.settings import get_settings
    from app.utils.redis_client import get_redis

    s = get_settings()
    r = get_redis()
    prefix = getattr(s, "REDIS_USER_PREFIX", "rag")
    keys = list(r.scan_iter(f"{prefix}*"))
    if keys:
        r.delete(*keys)
    print(f"缓存清理完成：删除 {len(keys)} 个键（前缀 {prefix}*）")


def retry(targets):
    if not os.path.exists(CHECKPOINT):
        print("无断点文件（下次评测将全量跑）")
        return
    with open(CHECKPOINT, encoding="utf-8") as f:
        d = json.load(f)
    removed = [k for k in targets if d.get("results", {}).pop(k, None) is not None]
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    remain = sorted(d.get("results", {}).keys(), key=int)
    print(f"已移除: {removed}")
    print(f"剩余（跳过）: {remain}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RAG_Personal 维护工具")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("clear-cache", help="清 Redis 缓存键")
    p2 = sub.add_parser("retry", help="移除断点中的指定题")
    p2.add_argument("targets", nargs="+", help="题号，逗号或空格分隔，如 7,8,9")
    args = ap.parse_args()

    if args.cmd == "clear-cache":
        clear_cache()
    else:
        # 兼容 "7,8,9" / "7 8 9" / 多参数（PowerShell 拆参）等分隔形式
        raw = " ".join(args.targets)
        retry([t for t in re.split(r"[,\s]+", raw) if t])
