from typing import Optional,Any

from pydantic import BaseModel


class UnifiedResponse(BaseModel):
    """定义统一响应格式"""
    code : int = 200
    message : str = "success"
    data : Optional[Any] = None

    @staticmethod
    def success(code:int = 200,data:Any=None,message:str="success") -> dict:
        return {
            "code":code,
            "message":message,
            "data":data
        }

    @staticmethod
    def error(code:int=500,message:str="error",data:Any = None) -> dict:
        return {
            "code":code,
            "message":message,
            "data":data
        }
