# Generated by Django 4.0.7 on 2023-01-21 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0006_transactionsaddress_spent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transactions',
            name='input_msg',
            field=models.CharField(blank=True, default='_', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='transactions',
            name='input_status',
            field=models.CharField(blank=True, default='_', max_length=255, null=True),
        ),
    ]