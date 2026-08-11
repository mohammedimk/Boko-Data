"""
Business-logic helpers and third-party API clients.

- VirtualAccountService : generates a dynamic virtual bank account for every
                           user. Currently backed by a local mock generator
                           so the platform is fully demo-able without a real
                           banking partner. Swap `_mock_generate` for a real
                           HTTP call (Monnify / SquadCo / Flutterwave /
                           Paystack Dedicated Accounts) without touching any
                           calling code - the public interface stays the same.

- CheapDataHubAPI       : thin, typed wrapper around the CheapDataHub VTU
                           reseller API used for data, airtime, cable and
                           electricity. Falls back to a realistic local mock
                           when `settings.VTU_USE_MOCK_PROVIDER` is True, or
                           when no real API key has been configured, so the
                           app remains fully functional for demos/tests.

- PaystackClient        : wrapper around the Paystack Transactions API used
                           for wallet funding (initialize + verify).
"""
import hashlib
import json
import logging
import random
import string
import uuid

import requests
from django.conf import settings

logger = logging.getLogger('core')


# ======================================================================
# Virtual Account Service
# ======================================================================
class VirtualAccountService:
    """
    Generates a dynamic virtual bank account for a user.

    This mocks providers such as Monnify, SquadCo, Flutterwave, or Paystack
    Dedicated Virtual Accounts. To go live with a real provider, replace the
    body of `generate_account` with an HTTP call to that provider's API and
    map its response onto the same dict shape returned here. No other part
    of the codebase needs to change.
    """

    MOCK_BANKS = [
        'Wema Bank', 'Providus Bank', 'Sterling Bank', 'Moniepoint MFB',
    ]

    @classmethod
    def generate_account(cls, user) -> dict:
        full_name = (user.get_full_name() or user.username).strip()

        if settings.PAYSTACK_DVA_ENABLED:
            return cls._live_generate(user, full_name)
        return cls._mock_generate(user, full_name)

    @classmethod
    def _live_generate(cls, user, full_name: str) -> dict:
        """Create a real Paystack customer + Dedicated Virtual Account (test-mode ready)."""
        from .utils import PaystackClient  # local import avoids circular import at module load
        from .models import UserProfile

        client = PaystackClient()
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else user.username

        customer_result = client.create_customer(
            email=user.email or f"{user.username}@vtuplatform.com",
            first_name=first_name,
            last_name=last_name,
            phone=getattr(getattr(user, 'profile', None), 'phone_number', ''),
        )
        if not customer_result.get('success'):
            logger.error("Failed to create Paystack customer for user_id=%s: %s", user.id, customer_result.get('message'))
            return cls._mock_generate(user, full_name)  # graceful fallback so registration never breaks

        customer_code = customer_result['customer_code']
        UserProfile.objects.filter(user=user).update(paystack_customer_code=customer_code)

        dva_result = client.create_dedicated_virtual_account(
            customer_code=customer_code,
            preferred_bank=settings.PAYSTACK_DVA_PREFERRED_BANK,
        )
        if not dva_result.get('success'):
            logger.error("Failed to create DVA for user_id=%s: %s", user.id, dva_result.get('message'))
            return cls._mock_generate(user, full_name)

        logger.info("Real Paystack DVA created for user_id=%s", user.id)
        return {
            'bank_name': dva_result['bank_name'],
            'account_number': dva_result['account_number'],
            'account_name': dva_result['account_name'],
        }

    @classmethod
    def _mock_generate(cls, user, full_name: str) -> dict:
        """Deterministic-but-unique mock account generation for demo/dev use."""
        rng = random.Random(f"{user.id}-{user.username}-vtu-account")
        account_number = ''.join(rng.choice(string.digits) for _ in range(10))
        bank_name = rng.choice(cls.MOCK_BANKS)

        style = rng.choice(['prefix', 'suffix'])
        if style == 'prefix':
            account_name = f"VTUHUB - {full_name}"
        else:
            account_name = f"{full_name} VTU"

        logger.info("Mock virtual account generated for user_id=%s", user.id)
        return {
            'bank_name': bank_name,
            'account_number': account_number,
            'account_name': account_name,
        }


# ======================================================================
# CheapDataHub API Client
# ======================================================================
class CheapDataHubAPI:
    """
    Wrapper around the CheapDataHub VTU reseller API.

    Every public method returns a plain dict with at least a `success` key
    so calling views never need to know whether the mock or the live
    provider answered the request.
    """

    def __init__(self):
        self.base_url = settings.CHEAPDATAHUB_BASE_URL.rstrip('/')
        self.api_key = settings.CHEAPDATAHUB_API_KEY
        self.use_mock = settings.VTU_USE_MOCK_PROVIDER
        self.timeout = 20

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            try:
                raw = response.json()
            except (ValueError, json.JSONDecodeError):
                # Server returned something that isn't JSON (e.g. an HTML
                # error page from a wrong URL, or a gateway timeout page).
                logger.error("CheapDataHub %s returned non-JSON (%s): %s", endpoint, response.status_code, response.text[:500])
                return {'success': False, 'message': f'Provider returned an unexpected response (HTTP {response.status_code}).'}

            logger.info("CheapDataHub %s response (%s): %s", endpoint, response.status_code, raw)
            return {
                'success': response.status_code in (200, 201) and str(raw.get('status', '')).lower() in ('success', 'successful', 'true', '1'),
                'message': raw.get('message', ''),
                'reference': raw.get('reference', ''),
                'raw': raw,
            }
        except requests.RequestException as exc:
            logger.error("CheapDataHub API error on %s: %s", endpoint, exc)
            return {'success': False, 'message': f'Provider error: {exc}'}

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.get(url, params=params or {}, headers=self._headers(), timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("CheapDataHub API error on %s: %s", endpoint, exc)
            return {'success': False, 'message': f'Provider error: {exc}'}

    @staticmethod
    def _mock_reference() -> str:
        return f"CDH-{uuid.uuid4().hex[:12].upper()}"

    # -- Networks -----------------------------------------------------
    def get_networks(self) -> dict:
        if self.use_mock:
            return {
                'success': True,
                'networks': [
                    {'id': 'MTN', 'name': 'MTN'},
                    {'id': 'AIRTEL', 'name': 'Airtel'},
                    {'id': 'GLO', 'name': 'Glo'},
                    {'id': '9MOBILE', 'name': '9mobile'},
                ],
            }
        return self._get('networks')

    # -- Data plans -----------------------------------------------------
    def get_data_plans(self, network: str) -> dict:
        """Return the dynamic list of data plans for the given network."""
        if self.use_mock:
            return {'success': True, 'plans': self._mock_data_plans(network)}
        return self._get('data/plans', params={'network': network})

    @staticmethod
    def _mock_data_plans(network: str) -> list:
        """
        Fallback catalog only. NOTE: buy_data() no longer validates against
        this - the real plan catalog/pricing now live in
        core.models.ServicePlan, checked in views.py before this API runs.
        """
        catalog = {
            'MTN': [
                {'plan_id': 'MTN-500MB-30D', 'name': 'MTN 500MB Monthly', 'data_size': '500MB', 'validity': '30 Days', 'price': 130.00},
                {'plan_id': 'MTN-1GB-30D', 'name': 'MTN 1GB Monthly', 'data_size': '1GB', 'validity': '30 Days', 'price': 250.00},
                {'plan_id': 'MTN-2GB-30D', 'name': 'MTN 2GB Monthly', 'data_size': '2GB', 'validity': '30 Days', 'price': 490.00},
                {'plan_id': 'MTN-5GB-30D', 'name': 'MTN 5GB Monthly', 'data_size': '5GB', 'validity': '30 Days', 'price': 1400.00},
                {'plan_id': 'MTN-10GB-30D', 'name': 'MTN 10GB Monthly', 'data_size': '10GB', 'validity': '30 Days', 'price': 2500.00},
            ],
            'AIRTEL': [
                {'plan_id': 'AIRTEL-500MB-30D', 'name': 'Airtel 500MB Monthly', 'data_size': '500MB', 'validity': '30 Days', 'price': 130.00},
                {'plan_id': 'AIRTEL-1GB-30D', 'name': 'Airtel 1GB Monthly', 'data_size': '1GB', 'validity': '30 Days', 'price': 260.00},
                {'plan_id': 'AIRTEL-2GB-30D', 'name': 'Airtel 2GB Monthly', 'data_size': '2GB', 'validity': '30 Days', 'price': 500.00},
                {'plan_id': 'AIRTEL-5GB-30D', 'name': 'Airtel 5GB Monthly', 'data_size': '5GB', 'validity': '30 Days', 'price': 1450.00},
            ],
            'GLO': [
                {'plan_id': 'GLO-1GB-30D', 'name': 'Glo 1GB Monthly', 'data_size': '1GB', 'validity': '30 Days', 'price': 220.00},
                {'plan_id': 'GLO-2GB-30D', 'name': 'Glo 2.5GB Monthly', 'data_size': '2.5GB', 'validity': '30 Days', 'price': 450.00},
                {'plan_id': 'GLO-5GB-30D', 'name': 'Glo 5.8GB Monthly', 'data_size': '5.8GB', 'validity': '30 Days', 'price': 1300.00},
                {'plan_id': 'GLO-10GB-30D', 'name': 'Glo 10GB Monthly', 'data_size': '10GB', 'validity': '30 Days', 'price': 2300.00},
            ],
            '9MOBILE': [
                {'plan_id': '9MOBILE-1GB-30D', 'name': '9mobile 1GB Monthly', 'data_size': '1GB', 'validity': '30 Days', 'price': 240.00},
                {'plan_id': '9MOBILE-2GB-30D', 'name': '9mobile 2GB Monthly', 'data_size': '2GB', 'validity': '30 Days', 'price': 480.00},
                {'plan_id': '9MOBILE-4_5GB-30D', 'name': '9mobile 4.5GB Monthly', 'data_size': '4.5GB', 'validity': '30 Days', 'price': 1200.00},
            ],
        }
        return catalog.get(network.upper(), [])

    def buy_data(self, network: str, plan_id: str, phone_number: str) -> dict:
        """
        Purchase a data bundle for `phone_number` on `network`.

        NOTE: plan existence/pricing is validated against ServicePlan in
        views.py BEFORE this method runs, so the mock branch only simulates
        success - it must not re-check plan_id against _mock_data_plans().
        """
        if self.use_mock:
            return {
                'success': True,
                'reference': self._mock_reference(),
                'message': f"Data plan {plan_id} delivered to {phone_number}.",
            }

        return self._post('data/purchase/', {
            'bundle_id': plan_id,
            'phone_number': phone_number,
        })

    # -- Airtime -----------------------------------------------------
    def buy_airtime(self, network: str, phone_number: str, amount, airtime_type: str = 'VTU') -> dict:
        """Purchase airtime of `amount` for `phone_number` on `network`."""
        if self.use_mock:
            return {
                'success': True,
                'reference': self._mock_reference(),
                'message': f"₦{amount} {network} airtime ({airtime_type}) sent to {phone_number}.",
            }

        # NOTE: these provider_id values are unverified guesses. Confirm the
        # real numeric IDs CheapDataHub assigns to each network from your
        # dashboard's "API for Developers" reference page before trusting
        # this mapping with real money - a wrong ID here is a very plausible
        # reason airtime silently fails to deliver.
        provider_id_map = {'MTN': 1, 'AIRTEL': 3, 'GLO': 2, '9MOBILE': 4}
        provider_id = provider_id_map.get(network.upper())
        if provider_id is None:
            return {'success': False, 'message': f'No provider_id mapped for network {network}.'}

        return self._post('airtime/purchase/', {
            'provider_id': provider_id,
            'phone_number': phone_number,
            'amount': str(amount),
        })

    # -- Cable -----------------------------------------------------
    def get_cable_bouquets(self, provider: str) -> dict:
        if self.use_mock:
            return {'success': True, 'bouquets': self._mock_cable_bouquets(provider)}
        return self._get('cable/bouquets', params={'provider': provider})

    @staticmethod
    def _mock_cable_bouquets(provider: str) -> list:
        """Fallback catalog only - pay_cable() validates against ServicePlan in views.py."""
        catalog = {
            'DSTV': [
                {'bouquet_id': 'DSTV-PADI', 'name': 'DStv Padi', 'price': 4400.00},
                {'bouquet_id': 'DSTV-YANGA', 'name': 'DStv Yanga', 'price': 6000.00},
                {'bouquet_id': 'DSTV-CONFAM', 'name': 'DStv Confam', 'price': 11000.00},
                {'bouquet_id': 'DSTV-COMPACT', 'name': 'DStv Compact', 'price': 19000.00},
                {'bouquet_id': 'DSTV-PREMIUM', 'name': 'DStv Premium', 'price': 37000.00},
            ],
            'GOTV': [
                {'bouquet_id': 'GOTV-SMALLIE', 'name': 'GOtv Smallie', 'price': 1900.00},
                {'bouquet_id': 'GOTV-JINJA', 'name': 'GOtv Jinja', 'price': 3900.00},
                {'bouquet_id': 'GOTV-JOLLI', 'name': 'GOtv Jolli', 'price': 5800.00},
                {'bouquet_id': 'GOTV-MAX', 'name': 'GOtv Max', 'price': 8500.00},
            ],
            'STARTIMES': [
                {'bouquet_id': 'ST-NOVA', 'name': 'StarTimes Nova', 'price': 1700.00},
                {'bouquet_id': 'ST-BASIC', 'name': 'StarTimes Basic', 'price': 3200.00},
                {'bouquet_id': 'ST-SMART', 'name': 'StarTimes Smart', 'price': 4800.00},
                {'bouquet_id': 'ST-CLASSIC', 'name': 'StarTimes Classic', 'price': 5900.00},
            ],
        }
        return catalog.get(provider.upper(), [])

    def validate_decoder(self, provider: str, smartcard_number: str) -> dict:
        """Validate a smart card / IUC number and return the customer's name."""
        if not smartcard_number.isdigit() or len(smartcard_number) < 10:
            return {'success': False, 'message': 'Invalid smart card / IUC number.'}
        if self.use_mock:
            seed = int(hashlib.sha256(smartcard_number.encode()).hexdigest(), 16) % 1000
            return {
                'success': True,
                'customer_name': f"CUSTOMER-{seed:03d}",
                'smartcard_number': smartcard_number,
            }
        return self._post('cable/validate', {'provider': provider, 'smartcard_number': smartcard_number})

    # def pay_cable(self, provider: str, smartcard_number: str, bouquet_id: str, phone_number: str) -> dict:
    #     """
    #     NOTE: bouquet existence/pricing is validated against ServicePlan in
    #     views.py BEFORE this method runs, so the mock branch only simulates
    #     success.
    #     """
    #     if self.use_mock:
    #         return {
    #             'success': True,
    #             'reference': self._mock_reference(),
    #             'message': f"Bouquet {bouquet_id} activated for card {smartcard_number}.",
    #         }

    #     return self._post('cable/purchase/', {
    #         'plan_id': bouquet_id,
    #         'cardnumber': smartcard_number,
    #         'phone': phone_number,
    #     })

    # # -- Electricity -----------------------------------------------------
    # def validate_meter(self, disco: str, meter_number: str, meter_type: str) -> dict:
    #     if not meter_number.isdigit() or len(meter_number) < 10:
    #         return {'success': False, 'message': 'Invalid meter number.'}
    #     if self.use_mock:
    #         seed = int(hashlib.sha256(meter_number.encode()).hexdigest(), 16) % 1000
    #         return {
    #             'success': True,
    #             'customer_name': f"METER-CUSTOMER-{seed:03d}",
    #             'address': f"No. {seed % 90 + 1} Independence Layout",
    #             'meter_number': meter_number,
    #         }
    #     return self._post('electricity/validate', {
    #         'disco': disco, 'meter_number': meter_number, 'meter_type': meter_type,
    #     })

    # def pay_electricity(self, disco: str, meter_number: str, meter_type: str, amount, phone_number: str) -> dict:
    #     if self.use_mock:
    #         token = '-'.join(''.join(random.choices(string.digits, k=4)) for _ in range(5))
    #         return {
    #             'success': True,
    #             'reference': self._mock_reference(),
    #             'token': token,
    #             'message': f"Token generated for meter {meter_number}.",
    #         }
    #     return self._post('electricity/pay', {
    #         'disco': disco, 'meter_number': meter_number, 'meter_type': meter_type,
    #         'amount': str(amount), 'phone_number': phone_number,
    #     })

    def pay_cable(self, provider: str, smartcard_number: str, bouquet_id: str, phone_number: str) -> dict:
        """
        NOTE: bouquet existence/pricing is validated against ServicePlan in
        views.py BEFORE this method runs, so the mock branch only simulates
        success.
        """
        if self.use_mock:
            return {
                'success': True,
                'reference': self._mock_reference(),
                'message': f"Bouquet {bouquet_id} activated for card {smartcard_number}.",
            }

        cable_provider_id_map = {'GOTV': 1, 'DSTV': 2, 'STARTIMES': 3}
        return self._post('cable/purchase/', {
            'provider_id': cable_provider_id_map.get(provider.upper()),
            'plan_id': bouquet_id,
            'cardnumber': smartcard_number,
            'phone': phone_number,
        })

    # -- Electricity -----------------------------------------------------
    def validate_meter(self, disco: str, meter_number: str, meter_type: str) -> dict:
        """`disco` is now the numeric disco_id (e.g. '4' for Ikeja Electric), matching forms.py DISCO_CHOICES."""
        if not meter_number.isdigit() or len(meter_number) < 10:
            return {'success': False, 'message': 'Invalid meter number.'}
        if self.use_mock:
            seed = int(hashlib.sha256(meter_number.encode()).hexdigest(), 16) % 1000
            return {
                'success': True,
                'customer_name': f"METER-CUSTOMER-{seed:03d}",
                'address': f"No. {seed % 90 + 1} Independence Layout",
                'meter_number': meter_number,
            }
        return self._post('electricity/validate', {
            'disco_id': disco, 'meter_number': meter_number, 'meter_type': meter_type,
        })

    def pay_electricity(self, disco: str, meter_number: str, meter_type: str, amount, phone_number: str) -> dict:
        """`disco` is now the numeric disco_id (e.g. '4' for Ikeja Electric), matching forms.py DISCO_CHOICES."""
        if self.use_mock:
            token = '-'.join(''.join(random.choices(string.digits, k=4)) for _ in range(5))
            return {
                'success': True,
                'reference': self._mock_reference(),
                'token': token,
                'message': f"Token generated for meter {meter_number}.",
            }
        return self._post('electricity/purchase/', {
            'disco_id': disco, 'meter_number': meter_number, 'meter_type': meter_type,
            'amount': str(amount), 'phone_number': phone_number,
        })
# ======================================================================
# Paystack Client
# ======================================================================
class PaystackClient:
    """Wrapper around the Paystack Transactions API (test mode by default)."""

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
        self.timeout = 20

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def initialize_transaction(self, email: str, amount, reference: str, callback_url: str) -> dict:
        url = f"{self.base_url}/transaction/initialize"
        payload = {
            'email': email,
            'amount': int(float(amount) * 100),
            'reference': reference,
            'callback_url': callback_url,
        }
        try:
            response = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            data = response.json()
            if response.status_code == 200 and data.get('status'):
                return {'success': True, 'authorization_url': data['data']['authorization_url'], 'access_code': data['data']['access_code']}
            logger.warning("Paystack initialize failed: %s", data)
            return {'success': False, 'message': data.get('message', 'Could not initialize payment.')}
        except requests.RequestException as exc:
            logger.error("Paystack initialize error: %s", exc)
            return {'success': False, 'message': 'Payment gateway is currently unreachable.'}

    def verify_transaction(self, reference: str) -> dict:
        url = f"{self.base_url}/transaction/verify/{reference}"
        try:
            response = requests.get(url, headers=self._headers(), timeout=self.timeout)
            data = response.json()
            if response.status_code == 200 and data.get('status'):
                tx_data = data['data']
                return {
                    'success': True,
                    'status': tx_data.get('status'),
                    'amount': tx_data.get('amount', 0) / 100,
                    'reference': tx_data.get('reference'),
                    'raw': tx_data,
                }
            return {'success': False, 'message': data.get('message', 'Verification failed.')}
        except requests.RequestException as exc:
            logger.error("Paystack verify error: %s", exc)
            return {'success': False, 'message': 'Payment gateway is currently unreachable.'}

    def create_customer(self, email: str, first_name: str, last_name: str, phone: str) -> dict:
        url = f"{self.base_url}/customer"
        payload = {'email': email, 'first_name': first_name, 'last_name': last_name, 'phone': phone}
        try:
            response = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            data = response.json()
            if response.status_code in (200, 201) and data.get('status'):
                return {'success': True, 'customer_code': data['data']['customer_code']}
            return {'success': False, 'message': data.get('message', 'Could not create customer.')}
        except requests.RequestException as exc:
            logger.error("Paystack create_customer error: %s", exc)
            return {'success': False, 'message': 'Payment gateway is currently unreachable.'}

    def create_dedicated_virtual_account(self, customer_code: str, preferred_bank: str) -> dict:
        url = f"{self.base_url}/dedicated_account"
        payload = {'customer': customer_code, 'preferred_bank': preferred_bank}
        try:
            response = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            data = response.json()
            if response.status_code in (200, 201) and data.get('status'):
                account = data['data']
                return {
                    'success': True,
                    'bank_name': account['bank']['name'],
                    'account_number': account['account_number'],
                    'account_name': account['account_name'],
                }
            return {'success': False, 'message': data.get('message', 'Could not create dedicated account.')}
        except requests.RequestException as exc:
            logger.error("Paystack create_dedicated_virtual_account error: %s", exc)
            return {'success': False, 'message': 'Payment gateway is currently unreachable.'}