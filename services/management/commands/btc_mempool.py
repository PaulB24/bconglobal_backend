from django.core.management.base import BaseCommand

from services.crypto_services.btc_mempool import btc_service_mempool


class Command(BaseCommand):
    def handle(self, *args, **options):
        btc_service_mempool.check_mempool_blockchain()
