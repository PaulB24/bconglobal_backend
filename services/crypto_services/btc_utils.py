import json
import logging
import time
from base64 import b64encode
from dataclasses import dataclass
from typing import Any

import requests

from services.crypto_services.utils import DisableLogger

logger = logging.getLogger(__name__)


class Bitcoin:
    __id_count = 0

    def __init__(self, rpcuser, rpcpasswd, rpchost, rpcport, rpc_call=None):
        self.__rpcuser = rpcuser
        self.__rpcpasswd = rpcpasswd
        self.__rpchost = rpchost
        self.__rpcport = rpcport
        self.__auth_header = " ".join(
            ["Basic", b64encode(":".join([rpcuser, rpcpasswd]).encode()).decode()]
        )
        self.__headers = {
            "Host": self.__rpchost,
            "User-Agent": "Bitcoin python binding",
            "Authorization": self.__auth_header,
            "Content-type": "application/json",
        }
        self.__rpc_call = rpc_call

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            # Python internal stuff
            raise AttributeError
        if self.__rpc_call is not None:
            name = "%s.%s" % (self.__rpc_call, name)
        return Bitcoin(
            self.__rpcuser, self.__rpcpasswd, self.__rpchost, self.__rpcport, name
        )

    def __call__(self, *args):
        with DisableLogger():
            Bitcoin.__id_count += 1
            postdata = {
                "params": args,
                "method": self.__rpc_call,
                "id": Bitcoin.__id_count,
            }
            protocol = "https" if int(self.__rpcport) == 443 else "http"
            url = "{0}://{1}:{2}".format(protocol, self.__rpchost, self.__rpcport)
            encoded = json.dumps(postdata)
            logger.info("Request: %s" % encoded)
            r = requests.post(url, data=encoded, headers=self.__headers, timeout=15)
            if r.status_code == 200:
                return r.json()["result"]
            else:
                print(f"{postdata} error call ")
                print(r.content)
                print("Error! Status code: %s" % r.status_code)
                print("Text: %s" % r.text)
                raise Exception(f"Error! Status code: {r.status_code}\n Text: {r.text}")


@dataclass
class BlockInfo:
    hash: Any
    height: Any
    time: Any
