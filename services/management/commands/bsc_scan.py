import logging

from django.core.management.base import BaseCommand

from services.choices import ChainChoice
from services.crypto_services.binance_services import bsc_service
from services.models import Blocks

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        Blocks.objects.filter(chain=ChainChoice.BINANCE).delete()
        bsc_service.start()
