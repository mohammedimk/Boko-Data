import uuid

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(default=uuid.uuid4, editable=False, max_length=64, unique=True)),
                ('service', models.CharField(choices=[
                    ('wallet_funding', 'Wallet Funding'),
                    ('data', 'Data Purchase'),
                    ('airtime', 'Airtime Purchase'),
                    ('cable', 'Cable Subscription'),
                    ('electricity', 'Electricity Bill'),
                ], max_length=20)),
                ('provider', models.CharField(blank=True, default='', help_text='e.g. MTN, Airtel, DSTV, GOTV, Paystack, CheapDataHub', max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('status', models.CharField(choices=[
                    ('pending', 'Pending'), ('success', 'Success'),
                    ('failed', 'Failed'), ('reversed', 'Reversed'),
                ], default='pending', max_length=10)),
                ('extra_data', models.JSONField(blank=True, default=dict)),
                ('api_response', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(help_text='11-digit Nigerian phone number, e.g. 08012345678', max_length=11, unique=True, validators=[django.core.validators.RegexValidator(message='Enter a valid 11-digit Nigerian phone number, e.g. 08012345678.', regex='^0[7-9][0-1]\\d{8}$')])),
                ('wallet_balance', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('allocated_bank_name', models.CharField(blank=True, default='', max_length=100)),
                ('allocated_account_number', models.CharField(blank=True, default='', max_length=10)),
                ('allocated_account_name', models.CharField(blank=True, default='', max_length=150)),
                ('is_account_generated', models.BooleanField(default=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'User Profiles',
                'ordering': ['-date_created'],
            },
        ),
        migrations.CreateModel(
            name='DataPurchase',
            fields=[],
            options={
                'verbose_name': 'Data Purchase',
                'verbose_name_plural': 'Data Purchases',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.transaction',),
        ),
        migrations.CreateModel(
            name='AirtimePurchase',
            fields=[],
            options={
                'verbose_name': 'Airtime Purchase',
                'verbose_name_plural': 'Airtime Purchases',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.transaction',),
        ),
        migrations.CreateModel(
            name='CablePayment',
            fields=[],
            options={
                'verbose_name': 'Cable Payment',
                'verbose_name_plural': 'Cable Payments',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.transaction',),
        ),
        migrations.CreateModel(
            name='ElectricityPayment',
            fields=[],
            options={
                'verbose_name': 'Electricity Payment',
                'verbose_name_plural': 'Electricity Payments',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.transaction',),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'service'], name='core_transa_user_id_9e5e77_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['reference'], name='core_transa_referen_2e1f7a_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['status'], name='core_transa_status_9b6e2a_idx'),
        ),
    ]
