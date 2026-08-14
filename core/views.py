"""Views for the VTU & Data Selling Platform (Boko-Data)."""

import hashlib
import hmac
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.db import transaction as db_transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

from .decorators import ajax_login_required, profile_required
from .forms import (
    BuyAirtimeForm,
    BuyDataForm,
    CableForm,
    ElectricityForm,
    FundWalletForm,
    LoginForm,
    RegistrationForm,
)
from .models import (
    ServiceCommission,
    ServicePlan,
    Transaction,
    UserProfile,
    WebAuthnCredential,
)
from .utils import CheapDataHubAPI, PaystackClient, VirtualAccountService

logger = logging.getLogger('core')

vtu_api = CheapDataHubAPI()
paystack = PaystackClient()
RP_NAME = "Boko-Data Hub"


# ======================================================================
# WebAuthn Helpers & Biometrics Endpoints
# ======================================================================
def get_rp_id(request):
    """Extract domain without port (e.g. 'localhost' or 'boko-data.com')."""
    return request.get_host().split(':')[0]


def get_origin(request):
    """Get scheme + host origin for WebAuthn validation."""
    scheme = 'https' if request.is_secure() else 'http'
    return f"{scheme}://{request.get_host()}"


@login_required
def webauthn_register_options(request):
    """Step 1: Generate challenge and store Base64URL string in session."""
    user = request.user
    existing_credentials = WebAuthnCredential.objects.filter(user=user)
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in existing_credentials
    ]

    options = generate_registration_options(
        rp_id=get_rp_id(request),
        rp_name=RP_NAME,
        user_id=str(user.id).encode('utf-8'),
        user_name=user.username,
        user_display_name=f"{user.first_name} {user.last_name}".strip() or user.username,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    request.session['webauthn_register_challenge'] = bytes_to_base64url(options.challenge)
    return JsonResponse(json.loads(options.json()))


@login_required
@require_POST
def webauthn_register_verify(request):
    """Step 2: Validate biometric signature and save credential to DB."""
    try:
        body = json.loads(request.body)
        nickname = body.get('nickname', '').strip() or 'Biometric Key'

        challenge_str = request.session.get('webauthn_register_challenge')
        if not challenge_str:
            return JsonResponse({
                'success': False,
                'message': 'Registration session expired or challenge missing. Please try again.'
            }, status=400)

        expected_challenge_bytes = base64url_to_bytes(challenge_str)

        credential_payload = {
            'id': body['id'],
            'rawId': body['rawId'],
            'type': body['type'],
            'response': body['response'],
        }

        verification = verify_registration_response(
            credential=credential_payload,
            expected_challenge=expected_challenge_bytes,
            expected_origin=get_origin(request),
            expected_rp_id=get_rp_id(request),
        )

        if 'webauthn_register_challenge' in request.session:
            del request.session['webauthn_register_challenge']

        cred_id = bytes_to_base64url(verification.credential_id)
        pub_key = bytes_to_base64url(verification.credential_public_key)

        credential, created = WebAuthnCredential.objects.get_or_create(
            credential_id=cred_id,
            defaults={
                'user': request.user,
                'public_key': pub_key,
                'sign_count': verification.sign_count,
                'nickname': nickname,
            }
        )

        if not created:
            credential.user = request.user
            credential.public_key = pub_key
            credential.sign_count = verification.sign_count
            credential.nickname = nickname
            credential.save()

        return JsonResponse({'success': True, 'message': 'Biometric key registered successfully!'})

    except Exception as e:
        logger.exception("WebAuthn Registration Error")
        return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'}, status=400)


@require_GET
def webauthn_login_options(request):
    """Generates authentication challenge for biometric login."""
    username = request.GET.get('username', '').strip()
    user = User.objects.filter(username=username).first() if username else None

    user_credentials = WebAuthnCredential.objects.filter(user=user) if user else []
    allow_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in user_credentials
    ]

    options = generate_authentication_options(
        rp_id=get_rp_id(request),
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    request.session['webauthn_login_challenge'] = bytes_to_base64url(options.challenge)
    return JsonResponse(json.loads(options.json()))


@require_POST
def webauthn_login_verify(request):
    """Verifies biometric authentication response and logs in user."""
    challenge_str = request.session.pop('webauthn_login_challenge', None)
    if not challenge_str:
        return JsonResponse({'success': False, 'message': 'Login session expired. Try again.'}, status=400)

    try:
        body = json.loads(request.body)
        cred_id = body.get('id')
        db_cred = WebAuthnCredential.objects.filter(credential_id=cred_id).first()

        if not db_cred:
            return JsonResponse({'success': False, 'message': 'Unrecognized device.'}, status=400)

        verification = verify_authentication_response(
            credential=body,
            expected_challenge=base64url_to_bytes(challenge_str),
            expected_origin=get_origin(request),
            expected_rp_id=get_rp_id(request),
            credential_public_key=base64url_to_bytes(db_cred.public_key),
            credential_current_sign_count=db_cred.sign_count,
        )

        db_cred.sign_count = verification.new_sign_count
        db_cred.save(update_fields=['sign_count'])

        login(request, db_cred.user)
        return JsonResponse({'success': True, 'redirect': reverse('dashboard')})

    except Exception as exc:
        logger.error("WebAuthn login failed: %s", exc)
        return JsonResponse({'success': False, 'message': 'Biometric login failed.'}, status=400)


# ======================================================================
# Authentication Views
# ======================================================================
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                user = form.save()
                profile = UserProfile.objects.create(
                    user=user,
                    phone_number=form.cleaned_data['phone_number'],
                )
                account = VirtualAccountService.generate_account(user)
                profile.allocated_bank_name = account['bank_name']
                profile.allocated_account_number = account['account_number']
                profile.allocated_account_name = account['account_name']
                profile.is_account_generated = True
                profile.save()

            login(request, user)
            messages.success(request, f"Welcome, {user.first_name or user.username}! Wallet created.")
            logger.info("User registered and virtual account generated: %s", user.username)
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class VTULoginView(LoginView):
    template_name = 'login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Welcome back, {self.request.user.first_name or self.request.user.username}!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username/email or password.")
        return super().form_invalid(form)


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


# ======================================================================
# Dashboard View
# ======================================================================
@profile_required
def dashboard_view(request):
    profile = request.user.profile

    if not profile.is_account_generated:
        account = VirtualAccountService.generate_account(request.user)
        profile.allocated_bank_name = account['bank_name']
        profile.allocated_account_number = account['account_number']
        profile.allocated_account_name = account['account_name']
        profile.is_account_generated = True
        profile.save()

    recent_transactions = request.user.transactions.all()[:8]

    context = {
        'profile': profile,
        'recent_transactions': recent_transactions,
        'fund_form': FundWalletForm(),
    }
    return render(request, 'dashboard.html', context)


# ======================================================================
# Wallet Funding & Paystack Webhook
# ======================================================================
@profile_required
def wallet_view(request):
    profile = request.user.profile
    fund_form = FundWalletForm()

    if request.method == 'POST':
        fund_form = FundWalletForm(request.POST)
        if fund_form.is_valid():
            amount = fund_form.cleaned_data['amount']
            reference = f"WALLET-{request.user.id}-{int(timezone.now().timestamp())}"

            txn = Transaction.objects.create(
                user=request.user,
                reference=reference,
                service=Transaction.Service.WALLET_FUNDING,
                provider='Paystack',
                amount=amount,
                status=Transaction.Status.PENDING,
            )

            callback_url = request.build_absolute_uri(reverse('wallet_verify'))
            result = paystack.initialize_transaction(
                email=request.user.email or f"{request.user.username}@boko-data.com",
                amount=amount,
                reference=reference,
                callback_url=callback_url,
            )

            if result.get('success'):
                return redirect(result['authorization_url'])

            txn.status = Transaction.Status.FAILED
            txn.api_response = result
            txn.save(update_fields=['status', 'api_response'])
            messages.error(request, result.get('message', 'Could not start payment. Please try again.'))
        else:
            messages.error(request, "Please enter a valid amount.")

    wallet_transactions = request.user.transactions.filter(service=Transaction.Service.WALLET_FUNDING)[:20]
    return render(request, 'wallet.html', {
        'profile': profile,
        'fund_form': fund_form,
        'wallet_transactions': wallet_transactions,
    })


@login_required
def wallet_verify_view(request):
    reference = request.GET.get('reference') or request.GET.get('trxref')

    if not reference:
        messages.error(request, "No payment reference was provided.")
        return redirect('wallet')

    txn = get_object_or_404(Transaction, reference=reference, user=request.user, service=Transaction.Service.WALLET_FUNDING)

    if txn.status == Transaction.Status.SUCCESS:
        messages.info(request, "This payment has already been confirmed.")
        return redirect('dashboard')

    result = paystack.verify_transaction(reference)

    if result.get('success') and result.get('status') == 'success':
        with db_transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=request.user)
            profile.credit_wallet(result['amount'])

            txn.status = Transaction.Status.SUCCESS
            txn.api_response = result.get('raw', {})
            txn.save(update_fields=['status', 'api_response', 'updated_at'])

        messages.success(request, f"Wallet funded successfully with ₦{result['amount']:.2f}!")
        logger.info("Wallet funded: user=%s amount=%s ref=%s", request.user.username, result['amount'], reference)
        return redirect('dashboard')

    txn.status = Transaction.Status.FAILED
    txn.api_response = result
    txn.save(update_fields=['status', 'api_response', 'updated_at'])
    messages.error(request, "Payment verification failed. If you were debited, please contact support.")
    return redirect('wallet')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Auto-credits wallet when payment is made to Dedicated Virtual Account (DVA)."""
    signature = request.headers.get('x-paystack-signature', '')
    computed_signature = hmac.new(
        key=settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        msg=request.body,
        digestmod=hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature, computed_signature):
        logger.warning("Paystack webhook rejected: invalid signature.")
        return HttpResponse(status=401)

    event = json.loads(request.body)
    event_type = event.get('event')
    data = event.get('data', {})

    if event_type == 'charge.success' and data.get('channel') == 'dedicated_nuban':
        reference = data.get('reference')
        amount = Decimal(str(data.get('amount', 0))) / Decimal('100')
        customer_code = data.get('customer', {}).get('customer_code', '')
        account_number = data.get('authorization', {}).get('receiver_bank_account_number', '')

        if Transaction.objects.filter(reference=reference).exists():
            return HttpResponse(status=200)

        profile = (
            UserProfile.objects.filter(paystack_customer_code=customer_code).first()
            or UserProfile.objects.filter(allocated_account_number=account_number).first()
        )

        if not profile:
            logger.error("Webhook: no UserProfile matched customer_code=%s account=%s", customer_code, account_number)
            return HttpResponse(status=200)

        with db_transaction.atomic():
            profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
            profile_locked.credit_wallet(amount)

            Transaction.objects.create(
                user=profile_locked.user,
                reference=reference,
                service=Transaction.Service.WALLET_FUNDING,
                provider='Paystack DVA',
                amount=amount,
                status=Transaction.Status.SUCCESS,
                extra_data={'account_number': account_number},
                api_response=data,
            )

        logger.info("Wallet auto-credited via DVA webhook: user=%s amount=%s ref=%s", profile.user.username, amount, reference)

    return HttpResponse(status=200)


# ======================================================================
# AJAX Service Fetchers
# ======================================================================
@ajax_login_required
@require_GET
def ajax_get_data_plans(request):
    network = request.GET.get('network', '').upper()
    if network not in ('MTN', 'AIRTEL', 'GLO', '9MOBILE'):
        return JsonResponse({'success': False, 'message': 'Unknown network.'}, status=400)

    plans = ServicePlan.objects.filter(service=ServicePlan.Service.DATA, network=network, is_active=True)
    return JsonResponse({
        'success': True,
        'plans': [
            {
                'plan_id': p.provider_plan_id,
                'name': p.name,
                'data_size': p.name.split(' ')[0],
                'validity': p.validity or '-',
                'price': float(p.selling_price),
            }
            for p in plans
        ],
    })


@ajax_login_required
@require_GET
def ajax_get_cable_bouquets(request):
    provider = request.GET.get('provider', '').upper()
    if provider not in ('DSTV', 'GOTV', 'STARTIMES'):
        return JsonResponse({'success': False, 'message': 'Unknown provider.'}, status=400)

    plans = ServicePlan.objects.filter(service=ServicePlan.Service.CABLE, network=provider, is_active=True)
    return JsonResponse({
        'success': True,
        'bouquets': [{'bouquet_id': p.provider_plan_id, 'name': p.name, 'price': float(p.selling_price)} for p in plans],
    })


@ajax_login_required
@require_POST
def ajax_validate_decoder(request):
    provider = request.POST.get('provider', '').upper()
    smartcard_number = request.POST.get('smartcard_number', '').strip()
    result = vtu_api.validate_decoder(provider, smartcard_number)
    return JsonResponse(result)


@ajax_login_required
@require_POST
def ajax_validate_meter(request):
    disco = request.POST.get('disco', '').upper()
    meter_number = request.POST.get('meter_number', '').strip()
    meter_type = request.POST.get('meter_type', 'prepaid')
    result = vtu_api.validate_meter(disco, meter_number, meter_type)
    return JsonResponse(result)


# ======================================================================
# VTU Services (Data, Airtime, Cable, Electricity)
# ======================================================================
@profile_required
def buy_data_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = BuyDataForm(request.POST)
        if form.is_valid():
            network = form.cleaned_data['network']
            plan_id = form.cleaned_data['plan_id']
            phone_number = form.cleaned_data['phone_number']

            plan = ServicePlan.objects.filter(
                service=ServicePlan.Service.DATA, network=network,
                provider_plan_id=plan_id, is_active=True,
            ).first()

            if not plan:
                messages.error(request, "Selected data plan could not be found. Please choose again.")
                return redirect('buy_data')

            price = plan.selling_price

            if not profile.has_sufficient_balance(price):
                messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                return redirect('buy_data')

            with db_transaction.atomic():
                profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
                if not profile_locked.has_sufficient_balance(price):
                    messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                    return redirect('buy_data')

                profile_locked.debit_wallet(price)
                api_result = vtu_api.buy_data(network, plan.provider_plan_id, phone_number)

                txn = Transaction.objects.create(
                    user=request.user,
                    service=Transaction.Service.DATA,
                    provider=network,
                    amount=price,
                    status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                    extra_data={
                        'phone': phone_number,
                        'plan_name': plan.name,
                        'cost_price': str(plan.cost_price),
                        'profit': str(plan.profit),
                    },
                    api_response=api_result,
                )

                if not api_result.get('success'):
                    profile_locked.credit_wallet(price)
                    messages.error(request, api_result.get('message', 'Data purchase failed. Your wallet has been refunded.'))
                    return redirect('buy_data')

            messages.success(request, f"{plan.name} sent to {phone_number} successfully!")
            logger.info("Data purchase success: user=%s ref=%s", request.user.username, txn.reference)
            return redirect('transactions')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = BuyDataForm()

    return render(request, 'buy_data.html', {'form': form, 'profile': profile})


@profile_required
def buy_airtime_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = BuyAirtimeForm(request.POST)
        if form.is_valid():
            network = form.cleaned_data['network']
            airtime_type = form.cleaned_data['airtime_type']
            phone_number = form.cleaned_data['phone_number']
            amount = form.cleaned_data['amount']

            commission = ServiceCommission.objects.filter(service=ServiceCommission.Service.AIRTIME).first()
            markup_percent = commission.commission_percent if commission else Decimal('0')
            selling_price = (amount * (1 + markup_percent / Decimal('100'))).quantize(Decimal('0.01'))

            if not profile.has_sufficient_balance(selling_price):
                messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                return redirect('buy_airtime')

            with db_transaction.atomic():
                profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
                if not profile_locked.has_sufficient_balance(selling_price):
                    messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                    return redirect('buy_airtime')

                profile_locked.debit_wallet(selling_price)
                api_result = vtu_api.buy_airtime(network, phone_number, amount, airtime_type)

                txn = Transaction.objects.create(
                    user=request.user,
                    service=Transaction.Service.AIRTIME,
                    provider=network,
                    amount=selling_price,
                    status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                    extra_data={'phone': phone_number, 'airtime_type': airtime_type, 'face_value': str(amount)},
                    api_response=api_result,
                )

                if not api_result.get('success'):
                    profile_locked.credit_wallet(selling_price)
                    messages.error(request, api_result.get('message', 'Airtime purchase failed. Your wallet has been refunded.'))
                    return redirect('buy_airtime')

            messages.success(request, f"₦{amount} {network} airtime sent to {phone_number} successfully!")
            logger.info("Airtime purchase success: user=%s ref=%s", request.user.username, txn.reference)
            return redirect('transactions')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = BuyAirtimeForm()

    return render(request, 'buy_airtime.html', {'form': form, 'profile': profile})


@profile_required
def buy_cable_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = CableForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data['provider']
            bouquet_id = form.cleaned_data['bouquet_id']
            smartcard_number = form.cleaned_data['smartcard_number']

            plan = ServicePlan.objects.filter(
                service=ServicePlan.Service.CABLE, network=provider,
                provider_plan_id=bouquet_id, is_active=True,
            ).first()

            if not plan:
                messages.error(request, "Selected cable package not found.")
                return redirect('buy_cable')

            price = plan.selling_price

            if not profile.has_sufficient_balance(price):
                messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                return redirect('buy_cable')

            with db_transaction.atomic():
                profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
                if not profile_locked.has_sufficient_balance(price):
                    messages.error(request, "Insufficient Wallet Balance.")
                    return redirect('buy_cable')

                profile_locked.debit_wallet(price)
                api_result = vtu_api.buy_cable(provider, bouquet_id, smartcard_number)

                txn = Transaction.objects.create(
                    user=request.user,
                    service=Transaction.Service.CABLE,
                    provider=provider,
                    amount=price,
                    status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                    extra_data={'smartcard': smartcard_number, 'bouquet_name': plan.name},
                    api_response=api_result,
                )

                if not api_result.get('success'):
                    profile_locked.credit_wallet(price)
                    messages.error(request, api_result.get('message', 'Cable subscription failed. Wallet refunded.'))
                    return redirect('buy_cable')

            messages.success(request, f"{plan.name} subscription active for smartcard {smartcard_number}!")
            return redirect('transactions')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = CableForm()

    return render(request, 'buy_cable.html', {'form': form, 'profile': profile})


@profile_required
def buy_electricity_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ElectricityForm(request.POST)
        if form.is_valid():
            disco = form.cleaned_data['disco']
            meter_number = form.cleaned_data['meter_number']
            meter_type = form.cleaned_data['meter_type']
            amount = form.cleaned_data['amount']

            commission = ServiceCommission.objects.filter(service=ServiceCommission.Service.ELECTRICITY).first()
            fee = commission.commission_percent if commission else Decimal('0')
            total_charge = (amount + fee).quantize(Decimal('0.01'))

            if not profile.has_sufficient_balance(total_charge):
                messages.error(request, "Insufficient Wallet Balance.")
                return redirect('buy_electricity')

            with db_transaction.atomic():
                profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
                if not profile_locked.has_sufficient_balance(total_charge):
                    messages.error(request, "Insufficient Wallet Balance.")
                    return redirect('buy_electricity')

                profile_locked.debit_wallet(total_charge)
                api_result = vtu_api.pay_electricity(disco, meter_number, amount, meter_type)

                txn = Transaction.objects.create(
                    user=request.user,
                    service=Transaction.Service.ELECTRICITY,
                    provider=disco,
                    amount=total_charge,
                    status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                    extra_data={'meter_number': meter_number, 'meter_type': meter_type, 'token': api_result.get('token', '')},
                    api_response=api_result,
                )

                if not api_result.get('success'):
                    profile_locked.credit_wallet(total_charge)
                    messages.error(request, api_result.get('message', 'Electricity payment failed. Wallet refunded.'))
                    return redirect('buy_electricity')

            messages.success(request, f"Electricity token generated for Meter {meter_number}!")
            return redirect('transactions')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ElectricityForm()

    return render(request, 'buy_electricity.html', {'form': form, 'profile': profile})


@profile_required
def transactions_view(request):
    transactions_list = request.user.transactions.all().order_by('-created_at')
    return render(request, 'transactions.html', {'transactions': transactions_list, 'profile': request.user.profile})