from dns.rdtypes import ANY
from jose import JWTError,jwt
from passlib.context import CryptContext
from datetime import datetime,timedelta

SECRET_ID = "my_secret_key_for_demo" # 加密前缀
ALGORITHM = "HS256" # 加密方式
expire_time = 60*24*7 # JWT令牌存在时间
# 生成加密上下文文本对象
pwd_content = CryptContext(schemes=["bcrypt"],deprecated="auto")

def generate_hash_password(password : str) -> str:
    """加密明文密码成指定的加密后的密码"""
    return pwd_content.hash(password)

def verify_password(target_value : str ,hash_password : str) -> bool | ANY:
    """校验密码和目标哈希值是否一样"""
    return pwd_content.verify(hash_password,target_value)

def create_access_token(data : dict) -> str:
    """生成JWT令牌方法"""
    base_token = data.copy()
    expire = datetime.now() + timedelta(expire_time)
    base_token.update({"exp":expire})
    return jwt.encode(base_token,SECRET_ID,algorithm=ALGORITHM)


def decode_token(token : str) -> dict:
    """解析JWT令牌方法,拿到令牌中的用户信息"""
    return jwt.decode(token,SECRET_ID,algorithms=[ALGORITHM])