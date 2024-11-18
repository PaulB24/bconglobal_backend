import logging

from core.celery import app
from services.choices import ChainChoice
from services.crypto_services.binance_services import bsc_service
from services.crypto_services.btc_service import btc_service
from services.models import BlockchainSettings

logger = logging.getLogger(__name__)


def observer_wrapper(service, chain):
    try:
        service.start()
    except Exception as e:
        logger.error(f"{service.__name__} Exception --> {e}")
        if settings := BlockchainSettings.objects.filter(chain=chain).first():
            settings.is_blocked = False
            settings.save(update_fields=["is_blocked"])


@app.task(time_limit=1000, soft_time_limit=950)
def binance_observer():
    observer_wrapper(bsc_service, ChainChoice.BINANCE)


@app.task(time_limit=1000, soft_time_limit=950)
def btc_observer():
    observer_wrapper(btc_service, ChainChoice.BITCOIN)
