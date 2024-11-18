import json
import logging

import pika
from django.conf import settings

logger = logging.getLogger(__name__)


class RabbitMQService:
    def __init__(self):
        self.credentials = pika.PlainCredentials(
            username=settings.RABBIT_USERNAME, password=settings.RABBIT_PASSWORD
        )
        self.connection_params = pika.ConnectionParameters(
            settings.RABBIT_HOST,
            port=settings.RABBIT_PORT,
            heartbeat=settings.RABBIT_HEARTBEAT,
            credentials=self.credentials,
            blocked_connection_timeout=settings.RABBIT_BLOCKED_CONNECTION_TIMEOUT,
        )

    def __enter__(self):
        self.connection = pika.BlockingConnection(self.connection_params)
        self._channel = self.connection.channel()
        self._channel.queue_declare(queue="crypto")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()

    @property
    def channel(self):
        return self._channel

    def properties(self, method):
        return pika.BasicProperties(method)

    def send(
        self,
        method,
        message,
        exchange="",
        routing_key="crypto",
        delivery_mode=2,
        priority=None,
    ):
        """rabbitmq sender"""
        self._channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                method, delivery_mode=delivery_mode, priority=priority
            ),
        )

    @classmethod
    def publish(cls, method, body):
        try:
            with cls() as rabbit_service:
                rabbit_service.send(method, body, routing_key="from_python")
            logger.info("=====publish===finish=====")
        except Exception as e:
            logger.error("==Exception===publish=====")
            logger.error(f"Exception details: {e}")
