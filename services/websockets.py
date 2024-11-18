import json

import websocket

from .choices import ChainChoice, StatusChoice, CharacterChoice
from .crypto_services.btc_mempool import btc_service_mempool
from .models import Address, BitcoinTransactions, TransactionsAddress
from .rabbit_mq_service import RabbitMQService
from .serializer import BitcoinTransactionsSerializer


class WebsocketBlockchain:
    def __init__(self):
        self.ws = None

    @staticmethod
    def on_message(ws, message, *args, **kwargs):
        print("\x1b[6;30;42m" + "+++++on_message+++++" + "\x1b[0m")
        message = json.loads(message)
        op: str = message.get("op", "")
        if op.lower() != "utx":
            print(f"Received message: {message}")
            return

        transaction_hash = message.get("hash")
        if BitcoinTransactions.objects.filter(
            transaction=transaction_hash,
            status=StatusChoice.UNCONFIRMED,
            chain=ChainChoice.BITCOIN,
        ).exists():
            return
        transaction, created = BitcoinTransactions.objects.get_or_create(
            transaction=transaction_hash,
            status=StatusChoice.UNCONFIRMED,
            chain=ChainChoice.BITCOIN,
        )

        for vin in message["inputs"]:
            prev_out = vin["prev_out"]
            address = prev_out.get("addr")
            value = prev_out.get("value", 0)
            vout = prev_out.get("n", 0)
            value_in_bitcoins = value / 100_000_000
            if address:
                TransactionsAddress.objects.create(
                    address=address,
                    value=value_in_bitcoins,
                    character=CharacterChoice.INPUT,
                    transaction=transaction,
                    vout_number=vout,
                )
        for vout in message["out"]:
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
        print(f"Received message: {transaction_hash}")

    @staticmethod
    def on_error(ws, error):
        print(f"Error occurred: {error}")
        print("\x1b[6;30;42m" + "+++++on_error+++++" + "\x1b[0m")

    @staticmethod
    def on_close(*args, **kwargs):
        print("\x1b[6;30;42m" + "+++++on_close+++++" + "\x1b[0m")
        print("### connection closed ###")
        try:
            websocket_blockchain.listen_to_transactions()
        except Exception as e:
            print(f"Exception on_close -> {e}")
            btc_service_mempool.toggle_enable(True)
            btc_service_mempool.check_mempool()

    @staticmethod
    def on_open(ws):
        print("\x1b[6;30;42m" + "+++++on_open+++++" + "\x1b[0m")
        print("### connection opened ###")
        btc_service_mempool.toggle_enable(False)

        for address in Address.objects.filter(chain=ChainChoice.BITCOIN):
            sub_request = {"op": "addr_sub", "addr": address.address}
            ws.send(json.dumps(sub_request))

        sub_request = {"op": "ping"}
        ws.send(json.dumps(sub_request))

    def connect_to_websocket(self):
        print("\x1b[6;30;42m" + "+++++connect_to_websocket+++++" + "\x1b[0m")
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            "wss://ws.blockchain.info/inv",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        self.ws.run_forever()

    def subscribe_new_address(self, address):
        if self.ws is not None and self.ws.sock and self.ws.sock.connected:
            sub_request = {"op": "addr_sub", "addr": address}
            self.ws.send(json.dumps(sub_request))
        else:
            print(
                f"Failed to subscribe to address {address}: websocket is not connected"
            )

    def unsubscribe_address(self, address):
        if self.ws is not None and self.ws.sock and self.ws.sock.connected:
            sub_request = {"op": "addr_unsub", "addr": address}
            self.ws.send(json.dumps(sub_request))
        else:
            print(
                f"Failed to unsubscribe from address {address}: websocket is not connected"
            )

    def listen_to_transactions(self):
        print("\x1b[6;30;42m" + "+++++listen_to_transactions+++++" + "\x1b[0m")
        self.connect_to_websocket()

    def ping(self):
        print("\x1b[6;30;42m" + "++++ping++++++" + "\x1b[0m")
        if self.ws is not None and self.ws.sock and self.ws.sock.connected:
            sub_request = {"op": "ping"}
            self.ws.send(json.dumps(sub_request))


websocket_blockchain = WebsocketBlockchain()
