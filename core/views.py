"""Views for the VTU & Data Selling Platform."""
from decimal import Decimal
import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .decorators import profile_required, ajax_login_required
from .forms import (
    RegistrationForm, LoginForm, FundWalletForm,
    BuyDataForm, BuyAirtimeForm, CableForm, ElectricityForm,
)
from .models import UserProfile, Transaction, ServicePlan, ServiceCommission
from .utils import VirtualAccountService, CheapDataHubAPI, PaystackClient
import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator



logger = logging.getLogger('core')

vtu_api = CheapDataHubAPI()
paystack = PaystackClient()





import json
from django.contrib.auth.models import User
from .webauthn_utils import (
    build_registration_options, verify_registration, options_to_json,
    build_authentication_options, verify_authentication,
)

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from webauthn import generate_registration_options, verify_registration_response
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from .models import WebAuthnCredential

logger = logging.getLogger(__name__)
RP_NAME = "Boko-Data Hub"

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

    # FIX 1: Convert bytes challenge to Base64URL string so Django Session can serialize it
    request.session['webauthn_register_challenge'] = bytes_to_base64url(options.challenge)

    return JsonResponse(json.loads(options.json()))


@login_required
@require_POST
def webauthn_register_verify(request):
    """Step 2: Validate biometric signature and save credential to DB."""
    try:
        body = json.loads(request.body)
        nickname = body.get('nickname', '').strip() or 'Biometric Key'

        # FIX 2: Retrieve challenge string from session and convert back to bytes
        challenge_str = request.session.get('webauthn_register_challenge')
        if not challenge_str:
            return JsonResponse({
                'success': False, 
                'message': 'Registration session expired or challenge missing. Please try again.'
            }, status=400)

        expected_challenge_bytes = base64url_to_bytes(challenge_str)

        # FIX 3: Isolate pure WebAuthn credential dict (exclude 'nickname')
        credential_payload = {
            'id': body['id'],
            'rawId': body['rawId'],
            'type': body['type'],
            'response': body['response'],
        }

        # Validate with pywebauthn
        verification = verify_registration_response(
            credential=credential_payload,
            expected_challenge=expected_challenge_bytes,
            expected_origin=get_origin(request),
            expected_rp_id=get_rp_id(request),
        )

        # Delete session challenge after single use
        if 'webauthn_register_challenge' in request.session:
            del request.session['webauthn_register_challenge']

        # Save or Update Credential in DB
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





# @login_required
# @require_GET
# def webauthn_register_options(request):
#     options, challenge = build_registration_options(request.user)
#     request.session['webauthn_reg_challenge'] = challenge
#     return JsonResponse(json.loads(options_to_json(options)))


# @login_required
# @require_POST
# def webauthn_register_verify(request):
#     challenge = request.session.pop('webauthn_reg_challenge', None)
#     if not challenge:
#         return JsonResponse({'success': False, 'message': 'Registration session expired. Try again.'}, status=400)
#     try:
#         credential = json.loads(request.body)
#         nickname = request.POST.get('nickname', '') or credential.pop('nickname', '')
#         verify_registration(request.user, credential, challenge, nickname)
#         return JsonResponse({'success': True, 'message': 'Biometric login enabled.'})
#     except Exception as exc:
#         logger.error("WebAuthn registration failed for user=%s: %s", request.user.username, exc)
#         return JsonResponse({'success': False, 'message': 'Could not register this device.'}, status=400)


@require_GET
def webauthn_login_options(request):
    username = request.GET.get('username', '').strip()
    user = User.objects.filter(username=username).first() if username else None
    options, challenge = build_authentication_options(user)
    request.session['webauthn_auth_challenge'] = challenge
    return JsonResponse(json.loads(options_to_json(options)))


@require_POST
def webauthn_login_verify(request):
    challenge = request.session.pop('webauthn_auth_challenge', None)
    if not challenge:
        return JsonResponse({'success': False, 'message': 'Login session expired. Try again.'}, status=400)
    try:
        credential = json.loads(request.body)
        user = verify_authentication(credential, challenge)
        if not user:
            return JsonResponse({'success': False, 'message': 'Unrecognized device.'}, status=400)
        login(request, user)
        return JsonResponse({'success': True, 'redirect': '/'})
    except Exception as exc:
        logger.error("WebAuthn login failed: %s", exc)
        return JsonResponse({'success': False, 'message': 'Biometric login failed.'}, status=400)
# ======================================================================
# Authentication
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
                # Generate the dynamic virtual account immediately on registration.
                account = VirtualAccountService.generate_account(user)
                profile.allocated_bank_name = account['bank_name']
                profile.allocated_account_number = account['account_number']
                profile.allocated_account_name = account['account_name']
                profile.is_account_generated = True
                profile.save()

            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}! Your account and virtual wallet have been created.")
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


# class VTULoginView(LoginView):
#     template_name = 'login.html'
#     authentication_form = LoginForm
#     redirect_authenticated_user = True

#     def form_valid(self, form):
#         response = super().form_valid(form)
#         messages.success(self.request, f"Welcome back, {self.request.user.first_name or self.request.user.username}!")
#         return response

#     def form_invalid(self, form):
#         messages.error(self.request, "Invalid username/email or password.")
#         return super().form_invalid(form)


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


# ======================================================================
# Dashboard
# ======================================================================
@profile_required
def dashboard_view(request):
    profile = request.user.profile

    # Ensure a virtual account exists even for users created before this
    # feature, or via the admin, by generating it lazily on first dashboard visit.
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
# Wallet Funding (Paystack)
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
                email=request.user.email or f"{request.user.username}@vtuplatform.com",
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
        'profile': profile, 'fund_form': fund_form, 'wallet_transactions': wallet_transactions,
    })


@login_required
def wallet_verify_view(request):
    """Paystack redirects here after payment (callback_url) with ?reference=..."""
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
    """
    Receives Paystack webhook events. Used specifically to auto-credit a
    user's wallet the moment money is transferred into their auto-generated
    Dedicated Virtual Account (DVA) — no page visit or manual verify needed.
    """
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
        amount = data.get('amount', 0) / 100
        customer_code = data.get('customer', {}).get('customer_code', '')
        account_number = data.get('authorization', {}).get('receiver_bank_account_number', '')

        # Idempotency: never credit the same Paystack reference twice
        if Transaction.objects.filter(reference=reference).exists():
            return HttpResponse(status=200)

        profile = (
            UserProfile.objects.filter(paystack_customer_code=customer_code).first()
            or UserProfile.objects.filter(allocated_account_number=account_number).first()
        )

        if not profile:
            logger.error("Webhook: no UserProfile matched customer_code=%s account=%s", customer_code, account_number)
            return HttpResponse(status=200)  # Ack anyway so Paystack stops retrying

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
# AJAX: Dynamic data plans
# ======================================================================
# @ajax_login_required
# @require_GET
# def ajax_get_data_plans(request):
#     network = request.GET.get('network', '').upper()
#     if network not in ('MTN', 'AIRTEL', 'GLO', '9MOBILE'):
#         return JsonResponse({'success': False, 'message': 'Unknown network.'}, status=400)

#     result = vtu_api.get_data_plans(network)
#     return JsonResponse(result)




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






# @ajax_login_required
# @require_GET
# def ajax_get_cable_bouquets(request):
#     provider = request.GET.get('provider', '').upper()
#     if provider not in ('DSTV', 'GOTV', 'STARTIMES'):
#         return JsonResponse({'success': False, 'message': 'Unknown provider.'}, status=400)

#     result = vtu_api.get_cable_bouquets(provider)
#     return JsonResponse(result)




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
# Buy Data
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

            price = plan.selling_price  # what the CUSTOMER pays

            # plans_result = vtu_api.get_data_plans(network)
            # plan = next((p for p in plans_result.get('plans', []) if p['plan_id'] == plan_id), None)

            # if not plan:
            #     messages.error(request, "Selected data plan could not be found. Please choose again.")
            #     return redirect('buy_data')

            # price = plan['price']

            if not profile.has_sufficient_balance(price):
                messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                return redirect('buy_data')

            with db_transaction.atomic():
                profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
                if not profile_locked.has_sufficient_balance(price):
                    messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                    return redirect('buy_data')

                profile_locked.debit_wallet(price)

                # api_result = vtu_api.buy_data(network, plan_id, phone_number)

                # txn = Transaction.objects.create(
                #     user=request.user,
                #     service=Transaction.Service.DATA,
                #     provider=network,
                #     amount=price,
                #     status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                #     extra_data={'phone': phone_number, 'plan': plan},
                #     api_response=api_result,
                # )

                api_result = vtu_api.buy_data(network, plan.provider_plan_id, phone_number)

                txn = Transaction.objects.create(
                    user=request.user,
                    service=Transaction.Service.DATA,
                    provider=network,
                    amount=price,
                    status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                    extra_data={
                        'phone': phone_number, 'plan_name': plan.name,
                        'cost_price': str(plan.cost_price), 'profit': str(plan.profit),
                    },
                    api_response=api_result,
                )


                if not api_result.get('success'):
                    # Refund on provider failure.
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


# ======================================================================
# Buy Airtime
# ======================================================================
# @profile_required
# def buy_airtime_view(request):
#     profile = request.user.profile

#     if request.method == 'POST':
#         form = BuyAirtimeForm(request.POST)
#         if form.is_valid():
#             network = form.cleaned_data['network']
#             airtime_type = form.cleaned_data['airtime_type']
#             phone_number = form.cleaned_data['phone_number']
#             amount = form.cleaned_data['amount']

#             commission = ServiceCommission.objects.filter(service=ServiceCommission.Service.AIRTIME).first()
#             markup_percent = commission.commission_percent if commission else Decimal('0')
#             selling_price = (amount * (1 + markup_percent / 100)).quantize(Decimal('0.01'))

#             if not profile.has_sufficient_balance(amount):
#                 messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
#                 return redirect('buy_airtime')

#             with db_transaction.atomic():
#                 profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
#                 if not profile_locked.has_sufficient_balance(amount):
#                     messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
#                     return redirect('buy_airtime')

#                 profile_locked.debit_wallet(amount)
#                 api_result = vtu_api.buy_airtime(network, phone_number, amount, airtime_type)

#                 txn = Transaction.objects.create(
#                     user=request.user,
#                     service=Transaction.Service.AIRTIME,
#                     provider=network,
#                     amount=amount,
#                     status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
#                     extra_data={'phone': phone_number, 'airtime_type': airtime_type},
#                     api_response=api_result,
#                 )

#                 if not api_result.get('success'):
#                     profile_locked.credit_wallet(amount)
#                     messages.error(request, api_result.get('message', 'Airtime purchase failed. Your wallet has been refunded.'))
#                     return redirect('buy_airtime')

#             messages.success(request, f"₦{amount} {network} airtime sent to {phone_number} successfully!")
#             logger.info("Airtime purchase success: user=%s ref=%s", request.user.username, txn.reference)
#             return redirect('transactions')
#         else:
#             messages.error(request, "Please correct the errors in the form.")
#     else:
#         form = BuyAirtimeForm()

#     return render(request, 'buy_airtime.html', {'form': form, 'profile': profile})


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
            selling_price = (amount * (1 + markup_percent / 100)).quantize(Decimal('0.01'))

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






# ======================================================================
# Cable Subscription
# ======================================================================
@profile_required
def cable_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = CableForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data['provider']
            smartcard_number = form.cleaned_data['smartcard_number']
            bouquet_id = form.cleaned_data['bouquet_id']
            phone_number = form.cleaned_data['phone_number']

            # bouquets_result = vtu_api.get_cable_bouquets(provider)
            # bouquet = next((b for b in bouquets_result.get('bouquets', []) if b['bouquet_id'] == bouquet_id), None)

            # if not bouquet:
            #     messages.error(request, "Selected bouquet could not be found. Please choose again.")
            #     return redirect('cable')

            # price = bouquet['price']

            bouquet = ServicePlan.objects.filter(
                service=ServicePlan.Service.CABLE, network=provider,
                provider_plan_id=bouquet_id, is_active=True,
            ).first()

            if not bouquet:
                messages.error(request, "Selected bouquet could not be found. Please choose again.")
                return redirect('cable')

            price = bouquet.selling_price





            if not profile.has_sufficient_balance(price):
                messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                return redirect('cable')

            with db_transaction.atomic():
                profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
                if not profile_locked.has_sufficient_balance(price):
                    messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                    return redirect('cable')

                profile_locked.debit_wallet(price)

                # api_result = vtu_api.pay_cable(provider, smartcard_number, bouquet_id, phone_number)

                # txn = Transaction.objects.create(
                #     user=request.user,
                #     service=Transaction.Service.CABLE,
                #     provider=provider,
                #     amount=price,
                #     status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                #     extra_data={'smartcard_number': smartcard_number, 'bouquet': bouquet, 'phone': phone_number},
                #     api_response=api_result,
                # )


                api_result = vtu_api.pay_cable(provider, smartcard_number, bouquet.provider_plan_id, phone_number)

                txn = Transaction.objects.create(
                    user=request.user,
                    service=Transaction.Service.CABLE,
                    provider=provider,
                    amount=price,
                    status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                    extra_data={
                        'smartcard_number': smartcard_number, 'bouquet_name': bouquet.name,
                        'phone': phone_number, 'cost_price': str(bouquet.cost_price), 'profit': str(bouquet.profit),
                    },
                    api_response=api_result,
                )

                if not api_result.get('success'):
                    profile_locked.credit_wallet(price)
                    messages.error(request, api_result.get('message', 'Cable subscription failed. Your wallet has been refunded.'))
                    return redirect('cable')

            
            messages.success(request, f"{bouquet.name} subscription activated for card {smartcard_number}!")
            logger.info("Cable payment success: user=%s ref=%s", request.user.username, txn.reference)
            return redirect('transactions')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = CableForm()

    return render(request, 'cable.html', {'form': form, 'profile': profile})


# ======================================================================
# Electricity Bills
# ======================================================================
# @profile_required
# def electricity_view(request):
#     profile = request.user.profile

#     if request.method == 'POST':
#         form = ElectricityForm(request.POST)
#         if form.is_valid():
#             disco = form.cleaned_data['disco']
#             meter_type = form.cleaned_data['meter_type']
#             meter_number = form.cleaned_data['meter_number']
#             amount = form.cleaned_data['amount']
#             phone_number = form.cleaned_data['phone_number']

#             if not profile.has_sufficient_balance(amount):
#                 messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
#                 return redirect('electricity')

#             with db_transaction.atomic():
#                 profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
#                 if not profile_locked.has_sufficient_balance(amount):
#                     messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
#                     return redirect('electricity')

#                 profile_locked.debit_wallet(amount)
#                 api_result = vtu_api.pay_electricity(disco, meter_number, meter_type, amount, phone_number)

#                 txn = Transaction.objects.create(
#                     user=request.user,
#                     service=Transaction.Service.ELECTRICITY,
#                     provider=disco,
#                     amount=amount,
#                     status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
#                     extra_data={
#                         'meter_number': meter_number, 'meter_type': meter_type,
#                         'phone': phone_number, 'token': api_result.get('token', ''),
#                     },
#                     api_response=api_result,
#                 )

#                 if not api_result.get('success'):
#                     profile_locked.credit_wallet(amount)
#                     messages.error(request, api_result.get('message', 'Electricity payment failed. Your wallet has been refunded.'))
#                     return redirect('electricity')

#             messages.success(request, f"Payment successful! Token: {api_result.get('token', 'N/A')}")
#             logger.info("Electricity payment success: user=%s ref=%s", request.user.username, txn.reference)
#             return redirect('transactions')
#         else:
#             messages.error(request, "Please correct the errors in the form.")
#     else:
#         form = ElectricityForm()

#     return render(request, 'electricity.html', {'form': form, 'profile': profile})


# ======================================================================
# Electricity Bills
# ======================================================================
@profile_required
def electricity_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ElectricityForm(request.POST)
        if form.is_valid():
            disco = form.cleaned_data['disco']
            meter_type = form.cleaned_data['meter_type']
            meter_number = form.cleaned_data['meter_number']
            amount = form.cleaned_data['amount']
            phone_number = form.cleaned_data['phone_number']

            if not profile.has_sufficient_balance(amount):
                messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                return redirect('electricity')

            with db_transaction.atomic():
                profile_locked = UserProfile.objects.select_for_update().get(pk=profile.pk)
                if not profile_locked.has_sufficient_balance(amount):
                    messages.error(request, "Insufficient Wallet Balance. Please fund your wallet.")
                    return redirect('electricity')

                profile_locked.debit_wallet(amount)
                api_result = vtu_api.pay_electricity(disco, meter_number, meter_type, amount, phone_number)

                txn = Transaction.objects.create(
                    user=request.user,
                    service=Transaction.Service.ELECTRICITY,
                    provider=disco,
                    amount=amount,
                    status=Transaction.Status.SUCCESS if api_result.get('success') else Transaction.Status.FAILED,
                    extra_data={
                        'meter_number': meter_number,
                        'meter_type': meter_type,
                        'phone': phone_number,
                        'token': api_result.get('token', ''),
                    },
                    api_response=api_result,
                )

                if not api_result.get('success'):
                    profile_locked.credit_wallet(amount)
                    messages.error(request, api_result.get('message', 'Electricity payment failed. Your wallet has been refunded.'))
                    return redirect('electricity')

            messages.success(request, f"Electricity payment of ₦{amount} for meter {meter_number} successful!")
            logger.info("Electricity payment success: user=%s ref=%s", request.user.username, txn.reference)
            return redirect('transactions')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ElectricityForm()

    return render(request, 'electricity.html', {'form': form, 'profile': profile})


# ======================================================================
# Transactions
# ======================================================================
@profile_required
def transactions_view(request):
    service_filter = request.GET.get('service', '')
    qs = request.user.transactions.all()
    if service_filter in dict(Transaction.Service.choices):
        qs = qs.filter(service=service_filter)

    return render(request, 'transactions.html', {
        'transactions': qs,
        'service_filter': service_filter,
        'service_choices': Transaction.Service.choices,
    })
