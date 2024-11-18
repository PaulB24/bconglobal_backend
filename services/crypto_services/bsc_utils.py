import logging
import time

from web3.auto import Web3

from services.choices import ChainChoice, StatusChoice
from services.models import Address, Transactions
from services.rabbit_mq_service import RabbitMQService
from services.serializer import TransactionsSerializer

logger = logging.getLogger(__name__)


def sending_transaction_to_broker(routing_key, transaction):
    serialized_data = TransactionsSerializer(transaction).data
    RabbitMQService.publish(routing_key, serialized_data)


class BinanceSmartChainBlockHandler:
    def __init__(self, web3):
        self.web3 = web3
        self.monitored_addresses = []

    def get_block(self, block_number, attempt=1):
        try:
            block = self.web3.eth.get_block(block_number, full_transactions=True)
        except Exception as e:
            blockcount = int(self.web3.eth.get_block_number())
            if attempt > 5:
                return None
            if blockcount >= block_number:
                time.sleep(1)
                block = self.get_block(block_number, attempt + 1)
            else:
                return None
        return block

    def handle_block(self, block_number):
        block = self.get_block(block_number)
        if not block:
            return 1
        self.monitored_addresses = list(
            Address.objects.filter(chain=ChainChoice.BINANCE).values_list(
                "address", flat=True
            )
        )
        transactions = block["transactions"]
        block_hash = Web3.toJSON(block["hash"]).strip('"')
        relevant_transactions = [
            Transactions(
                transaction=Web3.toJSON(tx["hash"]).strip('"'),
                from_addr=tx["from"],
                to_addr=tx["to"],
                value=self.web3.fromWei(tx["value"], "ether"),
                block_hash=block_hash,
                block_number=block["number"],
                timestamp=block["timestamp"],
                status=StatusChoice.PARTIAL_CONFIRMED,
                chain=ChainChoice.BINANCE,
                input_msg=tx["input"],
                input_status="decode",
            )
            for tx in transactions
            if tx["from"] in self.monitored_addresses
            or tx["to"] in self.monitored_addresses
        ]
        if relevant_transactions:
            Transactions.objects.bulk_create(relevant_transactions)
            for tx in relevant_transactions:
                sending_transaction_to_broker("new_transaction", tx)
        return 1
