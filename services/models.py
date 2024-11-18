from django.db import models

from services.choices import ChainChoice, CharacterChoice, StatusChoice


class Address(models.Model):
    address = models.CharField(max_length=255)
    chain = models.CharField(max_length=10, choices=ChainChoice.choices)

    def __str__(self):
        return f"address = {self.address}, chain = {self.chain}"


class BaseTransactions(models.Model):
    transaction = models.CharField(max_length=255)
    block_hash = models.CharField(max_length=255, blank=True, null=True, default="_")
    block_number = models.CharField(max_length=255, blank=True, null=True, default="_")
    timestamp = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoice.choices,
        default=StatusChoice.PARTIAL_CONFIRMED,
    )
    chain = models.CharField(max_length=10, choices=ChainChoice.choices)

    class Meta:
        abstract = True


class Transactions(BaseTransactions):
    from_addr = models.CharField(max_length=255, blank=True, null=True, default="_")
    to_addr = models.CharField(max_length=255, blank=True, null=True, default="_")
    value = models.CharField(max_length=255, blank=True, null=True, default="_")
    input_msg = models.CharField(max_length=255, blank=True, null=True, default="_")
    input_status = models.CharField(max_length=255, blank=True, null=True, default="_")

    def __str__(self):
        return f"transaction = {self.transaction}, status = {self.status}"

    class Meta:
        verbose_name = "Binance transactions"
        verbose_name_plural = "Binance transactions"


class BitcoinTransactions(BaseTransactions):
    def __str__(self):
        return f"transaction = {self.transaction}, status = {self.status}"


class TransactionsAddress(models.Model):
    address = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    character = models.CharField(max_length=10, choices=CharacterChoice.choices)
    transaction = models.ForeignKey(
        BitcoinTransactions, related_name="tx_address", on_delete=models.CASCADE
    )
    vout_number = models.IntegerField(default=1)
    spent = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"address = {self.address} value = {self.value}"


class Blocks(models.Model):
    chain = models.CharField(max_length=10, choices=ChainChoice.choices)
    block = models.PositiveIntegerField()

    def __str__(self):
        return f"chain = {self.chain}, block = {self.block}"


class BlockchainSettings(models.Model):
    chain = models.CharField(max_length=10, choices=ChainChoice.choices)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return f"chain = {self.chain}, is_blocked = {self.is_blocked}"
