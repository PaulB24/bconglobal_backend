import logging
import time
from datetime import timedelta

import requests
from django.utils import timezone
from pymempool import MempoolAPI

from services.choices import ChainChoice, CharacterChoice, StatusChoice
from services.models import (
    Address,
    BitcoinTransactions,
    TransactionsAddress, Blocks,
)
from services.rabbit_mq_service import RabbitMQService
from services.serializer import BitcoinTransactionsSerializer

logger = logging.getLogger(__name__)


class BitcoinMemPool:
    def __init__(self):
        self.enable = True

    def toggle_enable(self, status=True):
        self.enable = status

    def check_mempool(self):
        mp = MempoolAPI()
        while self.enable:
            self.remove_old_transactions()
            monitored_addresses = self.fetch_monitored_addresses()
            print(f"check MEMPOOL block tip height{mp.get_block_tip_height()}")
            for addr in monitored_addresses:
                try:
                    info = mp.get_address_transactions_mempool(addr)
                except BaseException as e:
                    print(f"BitcoinMemPool ERROR -> {e}")
                    print(repr(e))
                    continue
                for tx in info:
                    if BitcoinTransactions.objects.filter(
                        transaction=tx["txid"],
                        status=StatusChoice.UNCONFIRMED,
                        chain=ChainChoice.BITCOIN,
                    ).exists():
                        continue
                    transaction, created = BitcoinTransactions.objects.get_or_create(
                        transaction=tx["txid"],
                        status=StatusChoice.UNCONFIRMED,
                        chain=ChainChoice.BITCOIN,
                    )

                    # Обрабатываем входы транзакции
                    for vin in tx["vin"]:
                        address = vin["prevout"].get("scriptpubkey_address")
                        value = vin["prevout"].get("value", 0)
                        value_in_bitcoins = value / 100_000_000
                        if address:
                            TransactionsAddress.objects.create(
                                address=address,
                                value=value_in_bitcoins,
                                character=CharacterChoice.INPUT,
                                transaction=transaction,
                                vout_number=vin["vout"],
                            )
                    for vout in tx["vout"]:
                        address = vout.get("scriptpubkey_address")
                        value = vout.get("value", 0)
                        value_in_bitcoins = value / 100_000_000
                        if address:
                            TransactionsAddress.objects.create(
                                address=address,
                                value=value_in_bitcoins,
                                character=CharacterChoice.OUTPUT,
                                transaction=transaction,
                            )
                    serialized_data = BitcoinTransactionsSerializer(transaction).data
                    RabbitMQService.publish("new_transaction", serialized_data)
            time.sleep(60)

    def process_blockchain_data(self, data):
        start_block = Blocks.objects.filter(chain=ChainChoice.BITCOIN).first()
        block = start_block.block if start_block else None
        for tx in data["txs"]:
            if BitcoinTransactions.objects.filter(
                transaction=tx["hash"],
                chain=ChainChoice.BITCOIN,
            ).exists():
                continue
            block_height = tx.get("block_height")

            if block_height and block and block_height < block:
                continue
            status = (
                StatusChoice.PARTIAL_CONFIRMED
                if block_height
                else StatusChoice.UNCONFIRMED
            )
            try:
                transaction = BitcoinTransactions.objects.get(
                    transaction=tx["hash"], chain=ChainChoice.BITCOIN
                )
            except BitcoinTransactions.DoesNotExist:
                transaction = BitcoinTransactions.objects.create(
                    transaction=tx["hash"],
                    status=status,
                    chain=ChainChoice.BITCOIN,
                    block_number=block_height,
                )

            # Обрабатываем входы транзакции
            for vin in tx["inputs"]:
                prev_out = vin["prev_out"]
                address = prev_out.get("addr")
                value = prev_out.get("value", 0)
                value_in_bitcoins = value / 100_000_000
                if address:
                    TransactionsAddress.objects.create(
                        address=address,
                        value=value_in_bitcoins,
                        character=CharacterChoice.INPUT,
                        transaction=transaction,
                        vout_number=prev_out["n"],
                    )
            # Обрабатываем выходы транзакции
            for vout in tx["out"]:
                address = vout.get("addr")
                value = vout.get("value", 0)
                value_in_bitcoins = value / 100_000_000
                if address:
                    TransactionsAddress.objects.create(
                        address=address,
                        value=value_in_bitcoins,
                        character=CharacterChoice.OUTPUT,
                        transaction=transaction,
                    )
            serialized_data = BitcoinTransactionsSerializer(transaction).data
            RabbitMQService.publish("new_transaction", serialized_data)

    def fetch_data_from_blockchain(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            print(response.content)
        else:
            return response.json()

    def fetch_monitored_addresses(self):
        return list(
            Address.objects.filter(chain=ChainChoice.BITCOIN).values_list(
                "address", flat=True
            )
        )

    def remove_old_transactions(self):
        two_days_ago = timezone.now() - timedelta(days=2)
        BitcoinTransactions.objects.filter(
            created_at__lt=two_days_ago, status=StatusChoice.UNCONFIRMED
        ).delete()

    def check_mempool_blockchain(self):
        base_url = "https://blockchain.info/multiaddr?active="
        while True:
            self.remove_old_transactions()
            monitored_addresses = self.fetch_monitored_addresses()
            url = base_url
            len_addresses = len(monitored_addresses)
            for count, addr in enumerate(monitored_addresses, 1):
                url += f"{addr}|"
                if len(url) >= 220 or count == len_addresses:
                    if data := self.fetch_data_from_blockchain(url):
                        self.process_blockchain_data(data)
                    time.sleep(10)
                    url = base_url
            time.sleep(10)


btc_service_mempool = BitcoinMemPool()
