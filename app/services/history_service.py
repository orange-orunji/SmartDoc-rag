import json
import os.path

from langchain_core.chat_history import BaseChatMessageHistory

from app.config.settings import CHAT_HISTORY_STORAGY_PATH
from langchain_core.messages import BaseMessage,message_to_dict,messages_from_dict



class FileChatHistory(BaseChatMessageHistory):

    def __init__(self,session_id,storage_path):
        self.session_id = session_id
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.file_path = os.path.join(storage_path,session_id)
    """添加历史记忆文档"""
    def add_message(self,messages:BaseMessage) -> None:
        current_messages = self.messages.copy()
        current_messages.append(messages)
        """
        将数据同步写入到本地文件中
        类对象写入文件  ->  一堆二进制
        为了方便，可以将BaseMessage消息转为字典(借助json模块以json字符串写入文件)
        官方message_to_dic:单个消息对象(BaseMessage类示例)->字典
        """
        all_message = [message_to_dict(messages) for messages in current_messages]
        with open(self.file_path,"w",encoding="utf-8") as a:
            json.dump(all_message,a)

    """将数据转换成列表对象并返回"""
    @property
    def messages(self) -> list[BaseMessage]:
        if not os.path.exists(self.file_path):
            return []
        else:
            try:
                with open(self.file_path,"r",encoding="utf-8") as r:
                    history_message =  json.load(r)
                    return messages_from_dict(history_message)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
    """清理历史数据"""
    def clear(self):
        with open(self.file_path,"w",encoding="utf-8"):
            pass

def get_file_chat_history(session_id):
    return FileChatHistory(session_id,CHAT_HISTORY_STORAGY_PATH)