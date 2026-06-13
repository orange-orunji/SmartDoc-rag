import os
from sentence_transformers import CrossEncoder

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../models/bge-reranker-base")
_model = CrossEncoder(_MODEL_PATH)

def rerank(query : str ,docs : list , top_k : int = 3):
    """

    :param query: 用户输入的原始问题
    :param docs: 候选文件列表
    :param top_k: 最后保留相似度/分数最高的top——k个文件
    :return:    返回得分列表中top_k个元素
    """
    if not docs:
        return docs
    # 获取各个文件和问题组合的相似度
    pairs = [[query, doc.page_content] for doc in docs]
    # 用模型对每个组合进行打分 返回的是对象
    scores = _model.predict(pairs)
    # 调用模型对每个配对进行打分，返回一个浮点数列表（相关性分数，越高越相关）
    score_docs = [doc for _,doc in sorted(zip(scores,docs),key=lambda x: x[0],reverse=True)]
    return score_docs[:top_k]
