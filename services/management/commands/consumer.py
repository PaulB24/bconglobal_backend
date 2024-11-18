import json
import logging
import time

from django.core.management.base import BaseCommand

from services.rabbit_mq_service import RabbitMQService
from services.serializer import AddressSerializer, AddressDeleteSerializer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # threading.Thread(target=websocket_blockchain.listen_to_transactions).start()

        def callback(ch, method, properties, body):
            data = json.loads(body)
            logger.info(data)
            logger.info(f"content_type {properties.content_type} ")

            if properties.content_type == "new_address":
                logger.info("new_address created")
                serializer = AddressSerializer(data=data)
                if serializer.is_valid():
                    res = serializer.save()
                    # if res.chain == ChainChoice.BITCOIN:
                    #     websocket_blockchain.subscribe_new_address(res.address)
                    logger.info(res)
                else:
                    logger.info(serializer.errors)
                    logger.info(data)
            elif properties.content_type == "del_address":
                logger.info("delete address")
                serializer = AddressDeleteSerializer(data=data)
                if serializer.is_valid():
                    # address_value = serializer.validated_data["address"]
                    # address = Address.objects.filter(address=address_value).first()
                    # if address and address.chain == ChainChoice.BITCOIN:
                    #     websocket_blockchain.unsubscribe_address(address.address)
                    serializer.delete()
                    logger.info(f"Success delete {data}")
                else:
                    logger.info(serializer.errors)
                    logger.info(data)

            time.sleep(1)

        with RabbitMQService() as rabbit_service:

            rabbit_service.channel.basic_consume(
                queue="crypto", on_message_callback=callback, auto_ack=True
            )
            logger.info("Started Consuming...")
            print("Started Consuming...")
            rabbit_service.channel.start_consuming()
