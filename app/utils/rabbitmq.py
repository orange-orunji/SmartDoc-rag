import asyncio
import json
import logging
from typing import Callable, Awaitable

import aio_pika
from app.config.settings import get_settings

logger = logging.getLogger("rag.rabbitmq")


class RabbitMQClient:
    def __init__(self):
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._exchange: aio_pika.RobustExchange | None = None

    async def connect(self):
        s = get_settings()
        self._connection = await aio_pika.connect_robust(
            host=s.RABBITMQ_HOST,
            port=s.RABBITMQ_PORT,
            login=s.RABBITMQ_USER,
            password=s.RABBITMQ_PASSWORD,
            virtualhost=s.RABBITMQ_VHOST,
        )
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "document.tasks", aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def publish(self, routing_key: str, message: dict):
        if not self._exchange:
            raise RuntimeError("RabbitMQ 未连接，请先调用 connect()")
        body = json.dumps(message, ensure_ascii=False).encode()
        await self._exchange.publish(
            aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=routing_key,
        )

    async def consume(
        self,
        queue_name: str,
        routing_keys: list[str],
        callback: Callable[[dict], Awaitable[None]],
        prefetch_count: int = 1,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        if not self._channel:
            raise RuntimeError("RabbitMQ 未连接")
        queue = await self._channel.declare_queue(
            queue_name, durable=True,
            arguments={"x-dead-letter-exchange": "document.tasks.dlx",
                       "x-dead-letter-routing-key": "document.failed"}
        )
        for key in routing_keys:
            await queue.bind(self._exchange, routing_key=key)

        await self._channel.set_qos(prefetch_count=prefetch_count)

        async with queue.iterator() as iterator:
            async for msg in iterator:
                async with msg.process():
                    payload = json.loads(msg.body.decode())
                    task_id = payload.get("task_id", "unknown")
                    retry_count = 0

                    while True:
                        try:
                            await callback(payload)
                            break  # 成功则退出重试循环
                        except Exception as e:
                            retry_count += 1
                            logger.error(
                                "消息处理失败 | task_id=%s | 第%d次重试 | error=%s",
                                task_id, retry_count, str(e)
                            )
                            if retry_count >= max_retries:
                                logger.error(
                                    "消息重试耗尽，进入死信队列 | task_id=%s | max_retries=%d",
                                    task_id, max_retries
                                )
                                raise  # 超过重试次数，抛异常让消息进入死信队列
                            await asyncio.sleep(retry_delay)

    async def close(self):
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()


rabbitmq = RabbitMQClient()
