import os
import json
from app.services.vector_store import vector_store_service as vs
from app.services.hyde import hyde_plus_rerank_retrieve, hyde_retrieve,hyde_plus_rerank_bm25_retrieve
from app.services.rerank import rerank

# 评估指标函数
def recall_at_k(docs, keywords, k=3):
    """Top-K 中是否包含至少一个预期关键词"""
    for doc in docs[:k]:
        if any(kw in doc.page_content for kw in keywords):
            return True
    return False

def reciprocal_rank(docs, keywords):
    """第一个正确答案的排名倒数"""
    for i, doc in enumerate(docs):
        if any(kw in doc.page_content for kw in keywords):
            return 1.0 / (i + 1)
    return 0.0

# 不同检索策略
def baseline_retrieve(query: str, k=3):
    return vs.get_vector(query, k=k)

def hyde_only(query: str, k=3):
    # hyde_retrieve 内部可能已包含 Rerank？请根据实际调整
    return hyde_retrieve(query, k=k)

def hyde_plus_rerank(query: str, k=3):
    """HyDE 召回 10 个候选，再用 Rerank 精排取前 k 个"""
    # 用 Rerank 精排
    return hyde_plus_rerank_retrieve(query, k=k)
def hyde_plus_rerank_bm25(query: str, k=3):
    """HyDE 召回 10 个候选，再用 Rerank 精排取前 k 个"""
    # 用 Rerank 精排
    return hyde_plus_rerank_bm25_retrieve(question=query,final_k=k)

# 加载测试问题
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(BASE_DIR, "eval_questions.json")
with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    test_questions = json.load(f)

# 评估函数
def evaluate(name, retriever, k=3):
    total = len(test_questions)
    hit = 0
    mrr_sum = 0.0
    for idx, item in enumerate(test_questions, 1):   # 从1开始计数，更直观
        q = item["question"]
        keywords = item["expected_keywords"]
        docs = retriever(q, k=k)
        if recall_at_k(docs, keywords, k):
            hit += 1
        mrr_sum += reciprocal_rank(docs, keywords)
        # 进度打印（加在这里）
        print(f"[{name}] 处理第 {idx}/{total} 个问题：{q[:40]}...")
    recall = hit / total
    mrr = mrr_sum / total
    print(f"{name}: Recall@{k} = {recall:.2%}, MRR = {mrr:.3f}")

# 运行对比（请根据你的 hyde_retrieve 内部实现决定是否需要 hyde_plus_rerank）
# evaluate("Baseline", baseline_retrieve, k=1)
# evaluate("HyDEOnly", hyde_only, k=1)
evaluate("HyDE_plus_rerank", hyde_plus_rerank, k=1)
evaluate("hyde_plus_rerank_bm25", hyde_plus_rerank_bm25, k=1)
# Baseline: Recall@1 = 60.00%, MRR = 0.600
# HyDE+Rerank: Recall@1 = 63.33%, MRR = 0.633


# TODO 将模糊类型数据和准确分析数据分开来查询再进行对比
"""
    语义化问题情况下查询
    纯模糊测试结果:
    Baseline: Recall@1 = 53.33%, MRR = 0.533
    HyDEOnly: Recall@1 = 60.00%, MRR = 0.600
    HyDE_plus_rerank: Recall@1 = 66.67%, MRR = 0.667
    hyde_plus_rerank_bm25: Recall@1 = 50.00%, MRR = 0.500
    
    HyDE+Rerank 在纯模糊语义场景下是最优的
    BM25 不是万能的，它需要配合精确查询才能体现优势
    
    
    添加13条专为 BM25 精确匹配设计的测试数据后
    Baseline: Recall@1 = 41.86%, MRR = 0.419
    HyDEOnly: Recall@1 = 51.16%, MRR = 0.512
    HyDE_plus_rerank: Recall@1 = 48.84%, MRR = 0.488
    hyde_plus_rerank_bm25: Recall@1 = 39.53%, MRR = 0.395
"""