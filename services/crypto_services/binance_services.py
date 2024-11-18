import logging
import time

import requests
from django.conf import settings
from web3.auto import Web3
from web3.middleware import geth_poa_middleware

from services.choices import ChainChoice, StatusChoice
from services.crypto_services.bsc_utils import (
    sending_transaction_to_broker,
    BinanceSmartChainBlockHandler,
)
from services.models import Transactions, Blocks

logger = logging.getLogger(__name__)


class BinanceSmartChainService:
    def __init__(self):
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        self.web3 = Web3(
            Web3.HTTPProvider(settings.BSC_HTTPS_ENDPOINTS, session=session)
        )
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        logger.info(self.web3.isConnected())
        self.block_handle = BinanceSmartChainBlockHandler(self.web3)

    def update_transaction_statuses(self, block_count):
        for tr in Transactions.objects.filter(status=StatusChoice.PARTIAL_CONFIRMED):
            try:
                if transaction := self.web3.eth.get_transaction_receipt(tr.transaction):
                    if (
                        transaction["status"]
                        and (
                            int(transaction["blockNumber"])
                            + settings.NUMBER_OF_CONFIRMATIONS
                        )
                        <= block_count
                    ):
                        tr.status = StatusChoice.CONFIRMED
                        tr.save(update_fields=["status"])
                        sending_transaction_to_broker("update_transaction", tr)
            except Exception as e:
                print(e)

    def process_blocks(self, start_block):
        current_block = start_block.block
        while True:
            latest_block = int(self.web3.eth.get_block_number())
            if latest_block - 20 > current_block:
                self.update_transaction_statuses(latest_block)
                for block_number in range(current_block + 1, latest_block - 19):
                    start_time = time.time()
                    self.block_handle.handle_block(block_number)
                    end_time = time.time()
                    print(
                        f"time=={end_time - start_time}--parse= {block_number} -- current= {latest_block} =="
                    )
                    start_block.block = block_number
                    start_block.save(update_fields=["block"])
                    current_block = block_number
            else:
                time.sleep(0.5)

    def get_starting_block(self):
        latest_block = self.web3.eth.get_block_number()
        block = Blocks.objects.create(
            chain=ChainChoice.BINANCE, block=int(latest_block) - 20
        )
        return block

    def start(self):
        logger.info(
            "\x1b[6;30;42m" + "++++BinanceSmartChainService start++++++" + "\x1b[0m"
        )
        block = self.get_starting_block()
        self.process_blocks(block)


bsc_service = BinanceSmartChainService()
