from typing import Literal

import logging
import re
import jieba

from app.services.bm25_service import bm25_service

PATTERN = re.compile(
    r'《[^》]+》|“[^”]+”|‘[^’]+’|"[^"]+"|\'[^\']+\'|\b[a-zA-Z_][a-zA-Z0-9_]*\b|\b[vV]?\d+(\.\d+)+([\-_][a-zA-Z0-9]+)?\b',
    re.VERBOSE)

# 中文精确句式模板：事实提取型提问（答案通常是语料中的词面/数值），
# 经 300 题评测集验证：命中这些句式的 semantic 题转双路零风险（收益>0 且无误伤），
# 目的是给无英文/引号信号的纯中文精确题补上 BM25 词面兜底
CN_FACT_PATTERN = re.compile(
    r'是什么|是多少|有多少|有几个|哪几个|哪种|哪个|叫什么|意味着什么|什么反应|影响什么|会发生什么|有什么好处|怎么实现|为什么')

# IDF 阈值（初始经验值，后续用评测集分布校准）
IDF_THRESHOLD = 4.0

def query_router(query : str) -> Literal["semantic", "keyword"]:
    """
    查询意图路由器

    根据用户输入的原始问题，返回意图路由器的输出

    :param query: 用户输入的原始问题
    :return: 意图路由器的输出

    问题进来
         ├─ 第1层：正则命中（《》/引号/英文术语/版本号/中文精确句式）→ keyword，直接返回
         ├─ 第2层：IDF 信号
         │    ├─ jieba 分词，过滤标点和单字停用词
         │    ├─ 查每个词的 IDF
         │    ├─ max(IDF) > 阈值 → keyword
         │    └─ 否则继续
         └─ 第3层：默认 → semantic（走 HyDE 单路）
    """

    logging.getLogger("query_router")
    logging.info("Agent 调用了 query_router | query : %s", query)

    # 第一层： 正则命中（《》/引号/英文术语/版本号/中文精确句式）→ keyword，直接返回

    if PATTERN.findall(query):
        logging.info("路由结果 | intent=keyword | 命中正则精确标记")
        return "keyword"

    if CN_FACT_PATTERN.search(query):
        logging.info("路由结果 | intent=keyword | 命中中文精确句式")
        return "keyword"

    # 第二层 : 分词 + 过滤标点/单字；注意 jieba.cut 返回生成器，必须 list 化
    # 守卫对象是 bm25（索引），不是单例本身：索引未构建时 bm25 为 None
    if bm25_service.bm25 is not None:
        idf = bm25_service.bm25.idf  # idf 是属性（dict），不是方法，不能加括号
        tokens = [w for w in jieba.cut(query) if len(w.strip()) > 1]

        scores = [idf.get(w) for w in tokens]
        scores = [s for s in scores if s is not None]

        if scores and max(scores) > IDF_THRESHOLD:

            logging.info("路由结果 | intent=keyword | IDF 信号命中")
            return "keyword"

    # 第三层： 默认 → semantic（走 HyDE 单路）
    logging.info("路由结果 | intent=semantic")
    return "semantic"

