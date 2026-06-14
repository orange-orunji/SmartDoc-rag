import jieba
from rank_bm25 import BM25Okapi

class BM25Service:
    def __init__(self):
        self.documents = []
        self.tokenizes_content = []
        self.bm25 = None

    def build_index(self,documents):
        """
        构建文件的索引,初始化属性
        :param documents: 全部文件
        :return: 构建后的文件索引
        """
        # 获取初始定义的文件
        self.documents = documents
        # 切割文本
        self.tokenizes_content = [list(jieba.cut(doc.page_content)) for doc in documents]
        # 获取bm25模型并投喂切割后的文本内容
        self.bm25 = BM25Okapi(self.tokenizes_content)

    def search(self,query : str,top_k:int=10):
        if not self.bm25:
            return []
        # 获取当前问题的切片
        query_cut_list = [jieba.cut(query)]
        # 投喂给bm25模型打分
        scores = self.bm25.get_scores(query_cut_list)
        # 按分数排序，取 top_k 的下标
        result_rank_list = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.documents[i] for i in result_rank_list]