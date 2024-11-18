from django.db import models


class ChainChoice(models.TextChoices):
    BINANCE = "BINANCE"
    BITCOIN = "BITCOIN"


class CharacterChoice(models.TextChoices):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class StatusChoice(models.TextChoices):
    UNCONFIRMED = "UNCONFIRMED"
    CONFIRMED = "CONFIRMED"
    PARTIAL_CONFIRMED = "PARTIAL CONFIRMED"
