import os
import hashlib
from datetime import datetime

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config.settings import get_settings
from app.schemas.response import UnifiedResponse
"""切割/检查文本"""


def check_md5(md5_file_path : str,md5_value : str):
    """检测文件md5是否存在,不存在则创建文件并返回false,成功返回True"""
    if not os.path.exists(md5_file_path):
        with open(md5_file_path,"a",encoding="utf-8"):
            pass
        return False
    else:
        with open(md5_file_path,"r",encoding="utf-8") as f:
            readiness = f.readlines()
            for line in readiness:
                if line.strip() == md5_value:
                    return True
    return False

def save_md5(md5_file_path: str,md5_value: str):
    """保存文件md5"""
    with open(md5_file_path,"a",encoding="utf-8") as f:
        f.write(md5_value+"\n")

def get_string_md5(input_str: str, encoding ="utf-8"):
    # 转成对应字符
    encode = input_str.encode(encoding)

    md_5 = hashlib.md5()
    md_5.update(encode)
    return md_5.hexdigest()

class KnowledgeBaseService:
    def __init__(self):
        self.s = get_settings()

        self.chroma = Chroma(
            embedding_function=DashScopeEmbeddings(
                dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
            ),
            persist_directory=self.s.CHROMA_DIR,
            collection_name=self.s.CHROMA_NAME
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=self.s.CHUNK_SIZE,
            chunk_overlap=self.s.CHUNK_OVERLAP,
            separators=self.s.SEPARATORS
        )

    def upload_by_str(self, data : str,filename) -> UnifiedResponse:
#       获取当前数据的MD5值
        md_5 = get_string_md5(data)
#       判断是否存在该MD5值
        if check_md5(self.s.MD5_PATH,md_5):
           #              """已存在则直接返回"""
            return UnifiedResponse(data="[Pass] 文件已存在,请勿重复上传")
        try:
        #     判断文件是否需要切割成列表对象
            if len(data)>self.s.CHUNK_SIZE:
                # 分割器对数据字符串进行切割成列表
                chunked_array = self.spliter.split_text(data)
            else:
                chunked_array = [data]
        #     进行向量存储
            # 定义存储信息(包含创建时间和创建人)
            metadatas = [{
                "source": filename,
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "operator": "system",
                "md5": md_5,
                "chunk_index": i,
                "total_chunks": len(chunked_array)
            }
                for i in range(len(chunked_array))
            ]

            self.chroma.add_texts(chunked_array,metadatas=metadatas)
        #     不存在则进行md5存储
            save_md5(self.s.MD5_PATH,md_5)
        except Exception as e:
             return UnifiedResponse(code=500,message="error",data=f"数据异常上传失败: {str(e)}")
        return UnifiedResponse(data="[Success] 文件上传成功")