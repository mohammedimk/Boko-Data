# """Django Admin customisation for the VTU platform."""
# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.models import User


# from .models import (
#     UserProfile, Transaction, DataPurchase, AirtimePurchase,
#     CablePayment, ElectricityPayment, ServicePlan, ServiceCommission,  # ADD ServicePlan, ServiceCommission
# )


# class UserProfileInline(admin.StackedInline):
#     model = UserProfile
#     can_delete = False
#     extra = 0
#     readonly_fields = ('date_created',)
#     fk_name = 'user'


# class UserAdmin(BaseUserAdmin):
#     inlines = (UserProfileInline,)
#     list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'wallet_balance_display')

#     def wallet_balance_display(self, obj):
#         return getattr(getattr(obj, 'profile', None), 'wallet_balance', '-')
#     wallet_balance_display.short_description = 'Wallet Balance'


# admin.site.unregister(User)
# admin.site.register(User, UserAdmin)


# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = (
#         'user', 'phone_number', 'wallet_balance', 'allocated_bank_name',
#         'allocated_account_number', 'is_account_generated', 'date_created',
#     )
#     search_fields = ('user__username', 'user__email', 'phone_number', 'allocated_account_number')
#     list_filter = ('is_account_generated', 'allocated_bank_name')
#     readonly_fields = ('date_created',)


# class BaseTransactionAdmin(admin.ModelAdmin):
#     list_display = ('reference', 'user', 'service', 'provider', 'amount', 'status', 'created_at')
#     list_filter = ('service', 'status', 'provider', 'created_at')
#     search_fields = ('reference', 'user__username', 'user__email', 'provider')
#     readonly_fields = ('reference', 'created_at', 'updated_at', 'api_response')
#     date_hierarchy = 'created_at'
#     ordering = ('-created_at',)


# @admin.register(Transaction)
# class TransactionAdmin(BaseTransactionAdmin):
#     pass


# @admin.register(DataPurchase)
# class DataPurchaseAdmin(BaseTransactionAdmin):
#     def get_queryset(self, request):
#         return super().get_queryset(request).filter(service=Transaction.Service.DATA)


# @admin.register(AirtimePurchase)
# class AirtimePurchaseAdmin(BaseTransactionAdmin):
#     def get_queryset(self, request):
#         return super().get_queryset(request).filter(service=Transaction.Service.AIRTIME)


# @admin.register(CablePayment)
# class CablePaymentAdmin(BaseTransactionAdmin):
#     def get_queryset(self, request):
#         return super().get_queryset(request).filter(service=Transaction.Service.CABLE)


# @admin.register(ElectricityPayment)
# class ElectricityPaymentAdmin(BaseTransactionAdmin):
#     def get_queryset(self, request):
#         return super().get_queryset(request).filter(service=Transaction.Service.ELECTRICITY)



# @admin.register(ServicePlan)
# class ServicePlanAdmin(admin.ModelAdmin):
#     list_display = ('network', 'service', 'name', 'provider_plan_id', 'cost_price', 'commission_type', 'commission_value', 'selling_price_display', 'is_active')
#     list_editable = ('commission_type', 'commission_value', 'is_active')
#     list_filter = ('service', 'network', 'is_active')
#     search_fields = ('name', 'network', 'provider_plan_id')

#     def selling_price_display(self, obj):
#         return f"₦{obj.selling_price}"
#     selling_price_display.short_description = 'Selling Price'



# # from django.contrib import admin
# # from .models import Network, DataPlan

# # @admin.register(Network)
# # class NetworkAdmin(admin.ModelAdmin):
# #     list_display = ("name", "code", "is_active")
# #     list_filter = ("is_active",)

# # @admin.register(DataPlan)
# # class DataPlanAdmin(admin.ModelAdmin):
# #     list_display = ("network", "name", "size_label", "provider_bundle_id", "price", "validity_days", "is_active")
# #     list_filter = ("network", "is_active")
# #     search_fields = ("name", "provider_bundle_id")
# #     list_editable = ("price", "is_active")  # Allows quick price adjustments directly from the admin table






# @admin.register(ServiceCommission)
# class ServiceCommissionAdmin(admin.ModelAdmin):
#     list_display = ('service', 'commission_percent')
#     list_editable = ('commission_percent',)



# admin.site.site_header = "VTU Platform Administration"
# admin.site.site_title = "VTU Admin"
# admin.site.index_title = "Platform Management"


"""Django Admin customisation for the VTU platform."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    UserProfile,
    Transaction,
    DataPurchase,
    AirtimePurchase,
    CablePayment,
    ElectricityPayment,
    ServicePlan,
    ServiceCommission,
    WebAuthnCredential,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    readonly_fields = ('date_created',)
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'wallet_balance_display')

    def wallet_balance_display(self, obj):
        return getattr(getattr(obj, 'profile', None), 'wallet_balance', '-')
    wallet_balance_display.short_description = 'Wallet Balance'


# Safely unregister default User admin to prevent NotRegistered exceptions
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'phone_number', 'wallet_balance', 'allocated_bank_name',
        'allocated_account_number', 'is_account_generated', 'date_created',
    )
    search_fields = ('user__username', 'user__email', 'phone_number', 'allocated_account_number')
    list_filter = ('is_account_generated', 'allocated_bank_name')
    readonly_fields = ('date_created',)


class BaseTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'service', 'provider', 'amount', 'status', 'created_at')
    list_filter = ('service', 'status', 'provider', 'created_at')
    search_fields = ('reference', 'user__username', 'user__email', 'provider')
    readonly_fields = ('reference', 'created_at', 'api_response')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(Transaction)
class TransactionAdmin(BaseTransactionAdmin):
    pass


@admin.register(DataPurchase)
class DataPurchaseAdmin(BaseTransactionAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(service=Transaction.Service.DATA)


@admin.register(AirtimePurchase)
class AirtimePurchaseAdmin(BaseTransactionAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(service=Transaction.Service.AIRTIME)


@admin.register(CablePayment)
class CablePaymentAdmin(BaseTransactionAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(service=Transaction.Service.CABLE)


@admin.register(ElectricityPayment)
class ElectricityPaymentAdmin(BaseTransactionAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(service=Transaction.Service.ELECTRICITY)


@admin.register(ServicePlan)
class ServicePlanAdmin(admin.ModelAdmin):
    list_display = (
        'network', 'service', 'name', 'provider_plan_id',
        'cost_price', 'commission_type', 'commission_value',
        'selling_price_display', 'is_active'
    )
    list_editable = ('commission_type', 'commission_value', 'is_active')
    list_filter = ('service', 'network', 'is_active')
    search_fields = ('name', 'network', 'provider_plan_id')

    def selling_price_display(self, obj):
        return f"₦{obj.selling_price}"
    selling_price_display.short_description = 'Selling Price'


@admin.register(ServiceCommission)
class ServiceCommissionAdmin(admin.ModelAdmin):
    list_display = ('service', 'commission_percent')
    list_editable = ('commission_percent',)


@admin.register(WebAuthnCredential)
class WebAuthnCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'credential_id_short', 'sign_count', 'created_at')
    search_fields = ('user__username', 'nickname', 'credential_id')
    readonly_fields = ('credential_id', 'public_key', 'sign_count', 'created_at')

    def credential_id_short(self, obj):
        return f"{obj.credential_id[:16]}..."
    credential_id_short.short_description = 'Credential ID'


admin.site.site_header = "VTU Platform Administration"
admin.site.site_title = "VTU Admin"
admin.site.index_title = "Platform Management"