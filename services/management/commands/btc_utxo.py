from django.core.management.base import BaseCommand

from services.crypto_services.btc_service import btc_service


class Command(BaseCommand):
    def handle(self, *args, **options):
        btc_service.start_utxo()
