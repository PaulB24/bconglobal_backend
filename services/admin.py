from django.contrib import admin
from services.models import (
    Transactions,
    Address,
    BitcoinTransactions,
    TransactionsAddress,
    Blocks,
)


class TransactionsAddressInline(admin.TabularInline):
    model = TransactionsAddress
    can_delete = False
    readonly_fields = ("address", "value", "character", "vout_number", "spent")
    extra = 0


class BitcoinTransactionsAdmin(admin.ModelAdmin):
    inlines = [TransactionsAddressInline]
    list_display = ("transaction", "status", "created_at", "block_number")
    search_fields = ["transaction", "block_number", "tx_address__address"]


class AddressAdmin(admin.ModelAdmin):
    list_display = ("address", "chain")
    list_filter = ("chain",)
    search_fields = ["address"]


class BscTransactionsAdmin(admin.ModelAdmin):
    list_display = ("transaction", "from_addr", "to_addr", "value", "block_number")
    search_fields = ["from_addr", "to_addr", "transaction", "block_number"]


admin.site.register(Transactions, BscTransactionsAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(BitcoinTransactions, BitcoinTransactionsAdmin)
admin.site.register(Blocks)
