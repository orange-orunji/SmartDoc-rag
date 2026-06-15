import requests
import time

# ==================== 配置区 ====================
API_BASE = "http://127.0.0.1:8000"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwidXNlcl9pZCI6MSwiZXhwIjoxNzgyMTYwMDY4fQ.zVXMLpvsEzFjfbihH5Ux7ovsDJOyAbX2-heB5_iRd5o"
SESSION_ID = "test_session"
QUESTIONS = [
    "python为什么是大冒险流行语言？",
    "Java 工程化人设是什么？",
    "Redis 分布式锁怎么用？",
    "HyDE 是什么？",
    "如何优化 SQL 查询？",
    "怎么进行docker部署",
    "Rerank是什么",
    "为什么redis需要看门狗",
    "docker前置知识要学Linux吗",
    "github是什么"
]
# =================================================

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def stream_chat(question: str, session_id: str) -> tuple[str, float, int]:
    """发送流式请求，返回完整答案、耗时(秒)和状态码"""
    start = time.time()
    full_response = ""
    status_code = 0
    with requests.post(
        f"{API_BASE}/api/chat/stream",
        json={"question": question, "session_id": session_id},
        headers=headers,
        stream=True,
    ) as resp:
        status_code = resp.status_code
        if status_code != 200:
            return "", time.time() - start, status_code
        for line in resp.iter_lines():
            if line:
                text = line.decode("utf-8")
                if text.startswith("data: ") and not text.startswith("data: [DONE]"):
                    full_response += text[6:]
    elapsed = time.time() - start
    return full_response, elapsed, status_code


if __name__ == "__main__":
    print("=" * 60)
    print("Redis 缓存效果测试 (压测脚本)")
    print(f"测试问题数: {len(QUESTIONS)}")
    print("=" * 60)

    # 第一轮：填充缓存
    print("\n[第一轮] 首次请求（写入缓存）...")
    first_times = []
    for i, q in enumerate(QUESTIONS, 1):
        ans, t, code = stream_chat(q, SESSION_ID)
        first_times.append(t)
        print(f"  {i}. {q[:20]:<20} 状态:{code} 长度:{len(ans)} 耗时:{t:.2f}s")

    # 第二轮：命中缓存
    print("\n[第二轮] 相同问题再次请求（应该命中缓存）...")
    second_times = []
    for i, q in enumerate(QUESTIONS, 1):
        ans, t, code = stream_chat(q, SESSION_ID)
        second_times.append(t)
        print(f"  {i}. {q[:20]:<20} 状态:{code} 长度:{len(ans)} 耗时:{t:.2f}s")

    # 统计
    avg_first = sum(first_times) / len(first_times)
    avg_second = sum(second_times) / len(second_times)

    print("\n" + "=" * 60)
    print("统计结果")
    print("=" * 60)
    print(f"首次请求平均耗时: {avg_first:.2f}s")
    print(f"缓存命中平均耗时: {avg_second:.2f}s")
    if avg_first > 0:
        speedup = avg_first / avg_second
        print(f"加速比: {speedup:.1f}x")
        print(f"延迟降低: {(avg_first - avg_second):.2f}s")
    else:
        print("首次请求耗时异常，请检查网络/服务")

"""
============================================================
Redis 缓存效果测试 (压测脚本)
测试问题数: 10
============================================================

[第一轮] 首次请求（写入缓存）...
  1. python为什么是大冒险流行语言？   状态:200 长度:1116 耗时:29.06s
  2. Java 工程化人设是什么？       状态:200 长度:1165 耗时:20.86s
  3. Redis 分布式锁怎么用？       状态:200 长度:1850 耗时:28.38s
  4. HyDE 是什么？            状态:200 长度:1382 耗时:16.79s
  5. 如何优化 SQL 查询？         状态:200 长度:2072 耗时:23.78s
  6. 怎么进行docker部署         状态:200 长度:2096 耗时:30.58s
  7. Rerank是什么            状态:200 长度:1408 耗时:16.88s
  8. 为什么redis需要看门狗        状态:200 长度:1169 耗时:17.29s
  9. docker前置知识要学Linux吗   状态:200 长度:1337 耗时:18.97s
  10. github是什么            状态:200 长度:1493 耗时:15.62s

[第二轮] 相同问题再次请求（应该命中缓存）...
  1. python为什么是大冒险流行语言？   状态:200 长度:55 耗时:0.00s
  2. Java 工程化人设是什么？       状态:200 长度:19 耗时:0.00s
  3. Redis 分布式锁怎么用？       状态:200 长度:85 耗时:0.00s
  4. HyDE 是什么？            状态:200 长度:130 耗时:0.00s
  5. 如何优化 SQL 查询？         状态:200 长度:87 耗时:0.00s
  6. 怎么进行docker部署         状态:200 长度:126 耗时:0.00s
  7. Rerank是什么            状态:200 长度:92 耗时:0.00s
  8. 为什么redis需要看门狗        状态:200 长度:56 耗时:0.00s
  9. docker前置知识要学Linux吗   状态:200 长度:51 耗时:0.00s
  10. github是什么            状态:200 长度:67 耗时:0.00s

============================================================
统计结果
============================================================
首次请求平均耗时: 21.82s
缓存命中平均耗时: 0.00s
加速比: 13141.2x
延迟降低: 21.82s
"""