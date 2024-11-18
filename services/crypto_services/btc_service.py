import concurrent.futures
import logging
import time
from datetime import timedelta
from typing import Any

import numpy as np
import requests
from bitcoinlib.transactions import Transaction
from bitcoinlib.values import Value
from django.conf import settings
from django.utils import timezone

from services.choices import ChainChoice, CharacterChoice, StatusChoice
from services.crypto_services.btc_utils import Bitcoin, BlockInfo
from services.models import (
    Blocks,
    Address,
    BitcoinTransactions,
    TransactionsAddress,
)
from services.rabbit_mq_service import RabbitMQService
from services.serializer import BitcoinTransactionsSerializer

logger = logging.getLogger(__name__)


class BitcoinService:
    def __init__(self):
        print(
            "\x1b[6;30;44m"
            + f"+++++BitcoinService START - BITCOIN_NETWORK = {settings.BITCOIN_NETWORK}+++++"
            + "\x1b[0m"
        )
        self.bitcoin_rpc = Bitcoin(
            settings.BITCOIN_USERNAME,
            settings.BITCOIN_PASSWORD,
            settings.BITCOIN_HOST,
            settings.BITCOIN_PORT,
        )
        info = self.bitcoin_rpc.getblockchaininfo()
        print(info)
        self.monitored_addresses = []

    def create_btc_transaction(self, tx_id: str, block_info: Any):
        """
        Create a new Bitcoin transaction or get an existing one with the given transaction ID and block information.

        :param tx_id: The transaction ID
        :param block_info: Block information containing the hash, height, and time
        :return: A tuple containing the created or retrieved transaction and a boolean indicating if the transaction was created
        """
        transaction = BitcoinTransactions.objects.create(
            transaction=tx_id,
            chain=ChainChoice.BITCOIN,
            block_hash=block_info.hash,
            block_number=block_info.height,
            timestamp=block_info.time,
            status=StatusChoice.PARTIAL_CONFIRMED,
        )
        return transaction

    def get_input_value(self, tx_input):
        """
        Get the input value of a transaction input.

        :param tx_input: A transaction input object
        :return: The input value
        """
        input_tx_id = tx_input.prev_txid.hex()
        input_tx_output_index = tx_input.output_n_int
        input_tx_decoded = self.get_decoded_transaction(input_tx_id)
        input_value = (
            input_tx_decoded.outputs[input_tx_output_index].value
            if input_tx_decoded
            else 0
        )
        return input_value

    def check_addresses_in_transaction(
        self, connected_addresses: Any, address_list: list, address_type: str
    ):
        """
        Check if the monitored addresses are involved in the transaction and populate the address_list.

        :param connected_addresses: Addresses connected to the transaction (Either inputs or outputs)
        :param address_list: List to store the transaction address objects
        :param address_type: Either 'INPUT' or 'OUTPUT', indicating the type of connected addresses
        :return: A boolean value indicating if any monitored addresses were found in the transaction
        """
        address_found = False
        for transaction in connected_addresses:
            try:
                value = transaction.value
                transaction_address = TransactionsAddress(
                    address=transaction.address,
                    value=float(Value.from_satoshi(value)),
                    character=address_type,
                )
                if address_type == CharacterChoice.OUTPUT:
                    transaction_address.vout_number = transaction.output_n
                    transaction_address.spent = False

                if transaction.address in self.monitored_addresses:
                    address_found = True

                address_list.append(transaction_address)
            except:
                continue
        return address_found

    def create_transactions_data(self, tx_id: str, block_info: Any, address_list: list):
        """
        Create transaction data and save it to the database.

        :param tx_id: The transaction ID
        :param block_info: Block information containing the hash, height, and time
        :param address_list: List of transaction address objects
        """
        btc_tx = self.create_btc_transaction(tx_id, block_info)
        for address_data in address_list:
            address_data.transaction = btc_tx

        TransactionsAddress.objects.bulk_create(address_list)
        serialized_data = BitcoinTransactionsSerializer(btc_tx).data
        RabbitMQService.publish("new_transaction", serialized_data)

    def update_transaction_status(self, block_number: int):
        """
        Update the status of partially confirmed transactions based on the current block number.

        :param block_number: The current block number
        """
        partially_confirmed_txs = BitcoinTransactions.objects.filter(
            status=StatusChoice.PARTIAL_CONFIRMED
        )
        for tr in partially_confirmed_txs:
            if int(tr.block_number) + settings.NUMBER_OF_CONFIRMATIONS <= block_number:
                tr.status = StatusChoice.CONFIRMED
                tr.save(update_fields=["status"])
                serialized_data = BitcoinTransactionsSerializer(tr).data
                RabbitMQService.publish("update_transaction", serialized_data)

    def check_unspent_transactions(self):
        """
        Check and update the spent status of unspent transaction outputs.
        """
        unspent_outputs = TransactionsAddress.objects.filter(
            character=CharacterChoice.OUTPUT, spent=False
        ).select_related("transaction")
        for output in unspent_outputs:
            try:
                tx_output = self.bitcoin_rpc.gettxout(
                    output.transaction.transaction, output.vout_number
                )
                if not tx_output:
                    output.spent = True
                    output.save(update_fields=["spent"])
                    serialized_data = BitcoinTransactionsSerializer(
                        output.transaction
                    ).data
                    RabbitMQService.publish("update_transaction", serialized_data)
            except:
                pass

    def get_rawtransaction(self, tx, attempt=1):
        """
        Retrieve the raw transaction data for a given transaction ID.

        :param tx: The transaction ID
        :param attempt: The current attempt number (default is 1)
        :return: The raw transaction data or None if unsuccessful after 5 attempts
        """
        try:
            raw_transaction = self.bitcoin_rpc.getrawtransaction(tx)
        except requests.Timeout:
            if attempt >= 5:
                return None
            raw_transaction = self.get_rawtransaction(tx, attempt + 1)
        return raw_transaction

    def get_decoded_transaction(self, tx: str):
        """
        Retrieve and decode the transaction data for a given transaction ID.

        :param tx: The transaction ID
        :return: The decoded transaction data or None if an error occurs
        """
        try:
            if raw_transaction := self.get_rawtransaction(tx):
                decoded_transaction = Transaction.parse(
                    raw_transaction, network=settings.BITCOIN_NETWORK
                )
                return decoded_transaction
        except Exception as e:
            logger.info(f"Transaction error = {tx}")
            logger.error(e)

    @staticmethod
    def find_transaction(adress, list_transactions):
        for tx in list_transactions:
            if adress == tx.address:
                return tx

    def process_transaction_chunk(self, tx_chunk, block_info):
        """
        Process a chunk of transactions and save the relevant transaction data.

        :param tx_chunk: A list of transaction IDs
        :param block_info: Block information containing the hash, height, and time
        """
        for tx_id in tx_chunk:
            decoded_transaction = self.get_decoded_transaction(tx_id)
            if not decoded_transaction:
                continue
            involved_addresses = []
            input_addresses = []
            has_output_addresses = self.check_addresses_in_transaction(
                decoded_transaction.outputs, involved_addresses, CharacterChoice.OUTPUT
            )
            has_input_addresses = self.check_addresses_in_transaction(
                decoded_transaction.inputs, input_addresses, CharacterChoice.INPUT
            )
            if has_input_addresses or has_output_addresses:
                for input_addr in decoded_transaction.inputs:

                    input_value = self.get_input_value(input_addr)
                    transaction = self.find_transaction(
                        input_addr.address, input_addresses
                    )
                    transaction.value = float(Value.from_satoshi(input_value))
                    involved_addresses.append(transaction)

                self.create_transactions_data(
                    str(tx_id), block_info, involved_addresses
                )

    def process_transactions(self, block):
        """
        Process all transactions in a block.

        :param block: The block data
        """
        block_info = BlockInfo(
            hash=block["hash"], height=block["height"], time=block["time"]
        )
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for tx_chunk in np.array_split(block["tx"], 20):
                futures.append(
                    executor.submit(
                        self.process_transaction_chunk, tx_chunk, block_info
                    )
                )
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    print(f"generated an exception: {exc}")

    def process_block(self, block_number: int):
        """
        Process a block with the given block number.

        :param block_number: The block number to process
        """
        block_hash = self.bitcoin_rpc.getblockhash(block_number)
        block = self.bitcoin_rpc.getblock(block_hash)
        self.monitored_addresses = list(
            Address.objects.filter(chain=ChainChoice.BITCOIN).values_list(
                "address", flat=True
            )
        )
        self.process_transactions(block)

    def start_utxo(self):
        start_block, _ = Blocks.objects.get_or_create(chain=ChainChoice.BITCOIN)
        latest_block_number = int(self.bitcoin_rpc.getblockcount())

        while True:
            if latest_block_number > start_block.block:
                self.check_unspent_transactions()
            else:
                latest_block_number = int(self.bitcoin_rpc.getblockcount())
                time.sleep(30)

    def start(self):
        """
        Start the BitcoinService to continuously process new blocks and parse transactions.
        """
        Blocks.objects.filter(chain=ChainChoice.BITCOIN).delete()
        latest_block_number = int(self.bitcoin_rpc.getblockcount())
        start_block = Blocks.objects.create(
            chain=ChainChoice.BITCOIN, block=latest_block_number - 1
        )

        while True:
            two_days_ago = timezone.now() - timedelta(days=2)
            BitcoinTransactions.objects.filter(
                created_at__lt=two_days_ago, status=StatusChoice.UNCONFIRMED
            ).delete()
            if latest_block_number > start_block.block:
                self.update_transaction_status(latest_block_number)
                for current_block_number in range(
                    start_block.block + 1, latest_block_number + 1
                ):
                    print(
                        "\x1b[6;30;42m"
                        + f"++++block = {current_block_number}++++++"
                        + "\x1b[0m"
                    )
                    self.process_block(current_block_number)
                    start_block.block = current_block_number
                    start_block.save(update_fields=["block"])
            else:
                time.sleep(30)
            latest_block_number = int(self.bitcoin_rpc.getblockcount())

    def start_v2(self):
        while True:
            latest_block_number = int(self.bitcoin_rpc.getblockcount())
            block_hash = self.bitcoin_rpc.getblockhash(latest_block_number)
            block = self.bitcoin_rpc.getblock(block_hash, 2)
            # Продолжаем обход всех транзакций в блоке
            for tx in block["tx"]:
                save_tx = False
                raw_tx_addrs = []
                transaction = BitcoinTransactions(
                    transaction=tx["txid"],
                    block_hash=block_hash,
                    block_number=latest_block_number,
                    timestamp=block["time"],
                    status=StatusChoice.PARTIAL_CONFIRMED,
                    chain=ChainChoice.BITCOIN,
                )
                for vin in tx["vin"]:
                    if "txid" in vin:
                        previous_tx = self.bitcoin_rpc.getrawtransaction(
                            vin["txid"], True
                        )
                        prev_vout = previous_tx["vout"][vin["vout"]]
                        if "address" in prev_vout["scriptPubKey"]:
                            address = prev_vout["scriptPubKey"]["address"]
                            raw_tx_addrs.append(
                                TransactionsAddress(
                                    address=address,
                                    value=prev_vout["value"],
                                    character=CharacterChoice.INPUT,
                                    transaction=transaction,
                                    vout_number=vin["vout"],
                                    # spent=True
                                )
                            )
                            if address in self.monitored_addresses:
                                save_tx = True
                for vout in tx["vout"]:
                    if "address" in vout["scriptPubKey"]:
                        address = vout["scriptPubKey"]["address"]
                        raw_tx_addrs.append(
                            TransactionsAddress(
                                address=address,
                                value=vout["value"],
                                character=CharacterChoice.OUTPUT,
                                transaction=transaction,
                                vout_number=vout["n"],
                                spent=False,
                            )
                        )
                        if address in self.monitored_addresses:
                            save_tx = True
                if save_tx and raw_tx_addrs:
                    transaction.save()
                    TransactionsAddress.objects.bulk_create(raw_tx_addrs)


btc_service = BitcoinService()
