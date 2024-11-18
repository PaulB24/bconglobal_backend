from rest_framework import serializers
from services.models import (
    Address,
    BitcoinTransactions,
    TransactionsAddress,
    Transactions,
)


class TransactionsAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionsAddress
        fields = ("address", "value", "character", "spent")


class BitcoinTransactionsSerializer(serializers.ModelSerializer):
    tx_address = TransactionsAddressSerializer(many=True)

    class Meta:
        model = BitcoinTransactions
        fields = (
            "transaction",
            "block_hash",
            "block_number",
            "timestamp",
            "chain",
            "status",
            "tx_address",
        )


class TransactionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transactions
        fields = (
            "transaction",
            "from_addr",
            "to_addr",
            "value",
            "block_hash",
            "block_number",
            "timestamp",
            "status",
            "chain",
            "input_msg",
            "input_status",
        )


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "address",
            "chain",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        address = attrs.get("address", "")
        chain = attrs.get("chain", "")
        if Address.objects.filter(address=address, chain=chain).exists():
            raise serializers.ValidationError(f"address={address} already exists")
        return attrs


class AddressDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("address",)

    def delete(self):
        address_value = self.validated_data["address"]
        Address.objects.filter(address=address_value).delete()
