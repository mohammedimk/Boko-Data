"""
Core models for the VTU & Data Selling Platform.

UserProfile   - extends Django's built-in User with wallet + virtual account info.
Transaction   - a unified ledger of every service purchase (data, airtime,
                cable, electricity) and every wallet funding event.
"""
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP


phone_validator = RegexValidator(
    regex=r'^0[7-9][0-1]\d{8}$',
    message="Enter a valid 11-digit Nigerian phone number, e.g. 08012345678."
)


class UserProfile(models.Model):
    """Extra information attached 1-to-1 to every Django User."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone_number = models.CharField(
        max_length=11,
        validators=[phone_validator],
        unique=True,
        help_text="11-digit Nigerian phone number, e.g. 08012345678",
    )
    wallet_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )

    # Dynamic virtual bank account (mocked provider details).
    allocated_bank_name = models.CharField(max_length=100, blank=True, default='')
    allocated_account_number = models.CharField(max_length=10, blank=True, default='')
    allocated_account_name = models.CharField(max_length=150, blank=True, default='')
    paystack_customer_code = models.CharField(max_length=50, blank=True, default='')  # ADD THIS LINE
    is_account_generated = models.BooleanField(default=False)


    date_created = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - ₦{self.wallet_balance}"

    def has_sufficient_balance(self, amount) -> bool:
        """Return True if the wallet can cover the given amount."""
        return self.wallet_balance >= amount

    def credit_wallet(self, amount):
        """Atomically add funds to the wallet. Caller must wrap in a transaction."""
        self.wallet_balance = models.F('wallet_balance') + amount
        self.save(update_fields=['wallet_balance'])
        self.refresh_from_db(fields=['wallet_balance'])

    def debit_wallet(self, amount):
        """Atomically remove funds from the wallet. Caller must wrap in a transaction."""
        self.wallet_balance = models.F('wallet_balance') - amount
        self.save(update_fields=['wallet_balance'])
        self.refresh_from_db(fields=['wallet_balance'])


class Transaction(models.Model):
    """A single ledger entry: wallet funding OR a paid-for service."""

    class Service(models.TextChoices):
        WALLET_FUNDING = 'wallet_funding', 'Wallet Funding'
        DATA = 'data', 'Data Purchase'
        AIRTIME = 'airtime', 'Airtime Purchase'
        CABLE = 'cable', 'Cable Subscription'
        ELECTRICITY = 'electricity', 'Electricity Bill'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REVERSED = 'reversed', 'Reversed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    reference = models.CharField(max_length=64, unique=True, default=uuid.uuid4, editable=False)
    service = models.CharField(max_length=20, choices=Service.choices)
    provider = models.CharField(
        max_length=50, blank=True, default='',
        help_text="e.g. MTN, Airtel, DSTV, GOTV, Paystack, CheapDataHub",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    # Free-form extra details: phone number, plan name, meter number, token, etc.
    extra_data = models.JSONField(default=dict, blank=True)

    # Raw response returned by the external API (Paystack / CheapDataHub) for audit purposes.
    api_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'service']),
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.reference} | {self.get_service_display()} | ₦{self.amount} | {self.get_status_display()}"

    @property
    def recipient(self):
        """Best-effort recipient identifier for display in tables (phone/meter/smartcard)."""
        return (
            self.extra_data.get('phone')
            or self.extra_data.get('meter_number')
            or self.extra_data.get('smartcard_number')
            or '-'
        )


class DataPurchase(Transaction):
    """Proxy model so Data purchases get their own Admin section."""

    class Meta:
        proxy = True
        verbose_name = 'Data Purchase'
        verbose_name_plural = 'Data Purchases'


class AirtimePurchase(Transaction):
    """Proxy model so Airtime purchases get their own Admin section."""

    class Meta:
        proxy = True
        verbose_name = 'Airtime Purchase'
        verbose_name_plural = 'Airtime Purchases'


class CablePayment(Transaction):
    """Proxy model so Cable payments get their own Admin section."""

    class Meta:
        proxy = True
        verbose_name = 'Cable Payment'
        verbose_name_plural = 'Cable Payments'


class ElectricityPayment(Transaction):
    """Proxy model so Electricity payments get their own Admin section."""

    class Meta:
        proxy = True
        verbose_name = 'Electricity Payment'
        verbose_name_plural = 'Electricity Payments'




# from decimal import Decimal


# class ServicePlan(models.Model):
#     """
#     A resellable Data or Cable TV plan, priced with your own markup on top
#     of CheapDataHub's real cost price. `provider_plan_id` is the exact ID
#     CheapDataHub expects in the purchase API call.
#     """

#     class Service(models.TextChoices):
#         DATA = 'data', 'Data'
#         CABLE = 'cable', 'Cable TV'

#     class CommissionType(models.TextChoices):
#         PERCENT = 'percent', 'Percentage'
#         FIXED = 'fixed', 'Fixed Amount (₦)'

#     service = models.CharField(max_length=10, choices=Service.choices)
#     network = models.CharField(max_length=20, help_text="MTN, AIRTEL, GLO, 9MOBILE, DSTV, GOTV, STARTIMES")
#     provider_plan_id = models.CharField(max_length=20, help_text="The plan_id CheapDataHub expects")
#     name = models.CharField(max_length=150)
#     validity = models.CharField(max_length=50, blank=True, default='')
#     cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="What CheapDataHub charges you")
#     commission_type = models.CharField(max_length=10, choices=CommissionType.choices, default=CommissionType.PERCENT)
#     commission_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('5.00'))
#     is_active = models.BooleanField(default=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         unique_together = ('service', 'network', 'provider_plan_id')
#         ordering = ['network', 'cost_price']

#     def __str__(self):
#         return f"{self.network} - {self.name} (cost ₦{self.cost_price}, sell ₦{self.selling_price})"
    

#     @property
#     def selling_price(self) -> int:
#         """What the customer actually pays — returned as a whole number (integer)."""
#         if self.commission_type == self.CommissionType.PERCENT:
#             markup = self.cost_price * (self.commission_value / Decimal('100'))
#         else:
#             markup = self.commission_value
        
#         total = self.cost_price + markup
#         # Quantize to Decimal('1') to remove decimals and cast to int
#         return int(total.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


    



class ServicePlan(models.Model):
    """
    A resellable Data, Cable TV, or Electricity service plan priced with your
    own markup on top of CheapDataHub's real cost price.
    """

    class Service(models.TextChoices):
        DATA = 'data', 'Data'
        CABLE = 'cable', 'Cable TV'
        ELECTRICITY = 'electricity', 'Electricity'  # Added Electricity support

    class CommissionType(models.TextChoices):
        PERCENT = 'percent', 'Percentage'
        FIXED = 'fixed', 'Fixed Amount (₦)'

    service = models.CharField(max_length=15, choices=Service.choices)
    network = models.CharField(
        max_length=30,
        help_text="MTN, AIRTEL, GLO, 9MOBILE, DSTV, GOTV, STARTIMES, AEDC, EKEDC, etc."
    )
    provider_plan_id = models.CharField(
        max_length=20,
        help_text="The plan_id/ID CheapDataHub expects in API calls"
    )
    name = models.CharField(max_length=150)
    validity = models.CharField(max_length=50, blank=True, default='')
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="What CheapDataHub charges you (API Price)"
    )
    commission_type = models.CharField(
        max_length=10,
        choices=CommissionType.choices,
        default=CommissionType.PERCENT
    )
    commission_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('20.00'),
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('service', 'network', 'provider_plan_id')
        ordering = ['network', 'cost_price']

    def __str__(self):
        return f"{self.network} - {self.name} (cost ₦{self.cost_price}, sell ₦{self.selling_price})"

    @property
    def selling_price(self) -> int:
        """
        Calculates selling price (cost + markup) and returns it as a clean whole number (integer).
        """
        if self.commission_type == self.CommissionType.PERCENT:
            markup = self.cost_price * (self.commission_value / Decimal('100'))
        else:
            markup = self.commission_value
        
        total = self.cost_price + markup
        # Quantizes to nearest whole unit and casts to int (e.g., 309.75 -> 310)
        return int(total.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    @property
    def profit(self) -> Decimal:
        return Decimal(self.selling_price) - self.cost_price




    # @property
    # def selling_price(self) -> Decimal:
    #     """What the customer actually pays — your cost plus commission."""
    #     if self.commission_type == self.CommissionType.PERCENT:
    #         markup = self.cost_price * (self.commission_value / Decimal('100'))
    #     else:
    #         markup = self.commission_value
    #     return (self.cost_price + markup).quantize(Decimal('0.01'))

    # @property
    # def profit(self) -> Decimal:
    #     return self.selling_price - self.cost_price


class ServiceCommission(models.Model):
    """
    Flat percentage markup for amount-based services (Airtime, Electricity)
    that don't have a fixed plan catalog — the customer names their own amount.
    """

    class Service(models.TextChoices):
        AIRTIME = 'airtime', 'Airtime'
        ELECTRICITY = 'electricity', 'Electricity'

    service = models.CharField(max_length=15, choices=Service.choices, unique=True)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('2.00'))

    def __str__(self):
        return f"{self.get_service_display()} commission: {self.commission_percent}%"



# class WebAuthnCredential(models.Model):
#     """A registered biometric/security-key credential for passwordless login."""
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='webauthn_credentials')
#     credential_id = models.CharField(max_length=255, unique=True)
#     public_key = models.TextField()
#     sign_count = models.PositiveIntegerField(default=0)
#     nickname = models.CharField(max_length=50, blank=True, default='', help_text="e.g. 'iPhone Face ID', 'Laptop Fingerprint'")
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user.username} - {self.nickname or self.credential_id[:12]}"





from django.db import models
from django.conf import settings


class WebAuthnCredential(models.Model):
    """A registered biometric/security-key credential for passwordless login."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webauthn_credentials'
    )
    credential_id = models.CharField(max_length=255, unique=True)
    public_key = models.TextField()
    sign_count = models.PositiveIntegerField(default=0)
    nickname = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="e.g. 'iPhone Face ID', 'Laptop Fingerprint'"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.nickname or self.credential_id[:12]}"


# # ======================================================================
# # Transaction Service Proxy Models (Required for separate Admin Tabs)
# # ======================================================================
# class DataPurchase(Transaction):
#     class Meta:
#         proxy = True
#         verbose_name = "Data Purchase"
#         verbose_name_plural = "Data Purchases"


# class AirtimePurchase(Transaction):
#     class Meta:
#         proxy = True
#         verbose_name = "Airtime Purchase"
#         verbose_name_plural = "Airtime Purchases"


# class CablePayment(Transaction):
#     class Meta:
#         proxy = True
#         verbose_name = "Cable TV Payment"
#         verbose_name_plural = "Cable TV Payments"


# class ElectricityPayment(Transaction):
#     class Meta:
#         proxy = True
#         verbose_name = "Electricity Payment"
#         verbose_name_plural = "Electricity Payments"