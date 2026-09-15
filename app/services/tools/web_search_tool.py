import httpx
from langchain_classic.memory import summary
from langchain_core.tools import tool
from app.config.settings import get_settings

s = get_settings()

def search_web(query: str, count: int = 5) -> str:
    """博查联网搜索 → 格式化文本（纯函数，供工具与图节点复用）"""
    if not query.strip():
        return "联网搜索失败：查询内容为空"
    if not s.BOCHA_API_KEY:
        return "联网搜索失败：未配置 BOCHA_API_KEY"
    try:
        r = httpx.post(
            "https://api.bochaai.com/v1/web-search",
            headers={"Authorization": f"Bearer {s.BOCHA_API_KEY}"},
            json={"query": query, "count": count, "summary": True},
            timeout=20,
        )
        data = r.json()
        # ① 错误分支：字段是 message / msg（探针实测），取到啥算啥
        if r.status_code != 200 or data.get("code") != 200:
            err = data.get("message") or data.get("msg") or "未知错误"
            return f"联网搜索失败：{err}"
        # ② 取网页列表：链式 .get 必须带默认 {}，最后 or [] 兜底
        pages = data.get("data",{}).get("webPages",{}).get("value",{}) or []
        # ③ 空判断放在格式化【之前】——名字也叫对了（pages 是列表）
        if not pages:
            return "联网搜索无相关结果"
        # ④ 逐条格式化：形状像 retrieve，但字段全换（name/url/summary）
        #    可选加分：带上发布日期（datePublished 前 10 位）
        texts = []
        for p in pages:
            name = p.get("name","无标题")
            url =  p.get("url", "")
            content = p.get("summary") or p.get("snippet") or ""
            date = (p.get("datePublished") or "")[:10] # 发布时间
            texts.append(f"【网页：{name}】{url}\n{date} {content[:300]}")
        return "\n\n".join(texts)

    except Exception as e:
        return f"联网搜索失败：{e}"

@tool
def web_search(query: str) -> str:
    """（docstring 你写——参照 search_tool.py 的规范：适用场景 / 不适用场景 都要写）
    提示：适用=时效性/实时信息（今天/最新/最近）；不适用=知识库已有答案的问题/闲聊
    """
    return search_web(query)