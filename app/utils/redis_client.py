import redis

from app.config.settings import settings as  st


redis.Redis(host=st.REDIS_HOST,port=st.REDIS_POST,db=st.REDIS_DB)