import os

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from app.config.settings import get_settings


class vector_store_service:
    def __init__(self,embedding_model):
        self.embedding = embedding_model

        self.s = get_settings()
        self.chroma = Chroma(
            embedding_function=DashScopeEmbeddings(
                dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
            ),
            persist_directory=self.s.CHROMA_DIR,
            collection_name=self.s.CHROMA_NAME
        )

    def get_vector(self,query: str, k: int = 3):
        return self.chroma.similarity_search(query, k=k)

