# """WebAuthn (FIDO2 / biometric) registration and login helpers."""
# import base64

# from django.conf import settings
# from webauthn import (
#     generate_registration_options, verify_registration_response,
#     generate_authentication_options, verify_authentication_response,
#     options_to_json,
# )
# from webauthn.helpers.structs import (
#     PublicKeyCredentialDescriptor, UserVerificationRequirement,
#     AuthenticatorSelectionCriteria, ResidentKeyRequirement,
# )

# from .models import WebAuthnCredential


# def b64url_to_bytes(s: str) -> bytes:
#     padding = '=' * (-len(s) % 4)
#     return base64.urlsafe_b64decode(s + padding)


# def bytes_to_b64url(b: bytes) -> str:
#     return base64.urlsafe_b64encode(b).decode('utf-8').rstrip('=')


# def build_registration_options(user):
#     existing = [
#         PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.credential_id))
#         for c in WebAuthnCredential.objects.filter(user=user)
#     ]
#     options = generate_registration_options(
#         rp_id=settings.WEBAUTHN_RP_ID,
#         rp_name=settings.WEBAUTHN_RP_NAME,
#         user_id=str(user.id).encode('utf-8'),
#         user_name=user.username,
#         user_display_name=user.get_full_name() or user.username,
#         exclude_credentials=existing,
#         authenticator_selection=AuthenticatorSelectionCriteria(
#             resident_key=ResidentKeyRequirement.PREFERRED,
#             user_verification=UserVerificationRequirement.REQUIRED,  # forces biometric/PIN, not just "USB key present"
#         ),
#     )
#     return options, bytes_to_b64url(options.challenge)


# def verify_registration(user, credential_response: dict, expected_challenge_b64: str, nickname: str = ''):
#     verification = verify_registration_response(
#         credential=credential_response,
#         expected_challenge=b64url_to_bytes(expected_challenge_b64),
#         expected_origin=settings.WEBAUTHN_ORIGIN,
#         expected_rp_id=settings.WEBAUTHN_RP_ID,
#     )
#     WebAuthnCredential.objects.create(
#         user=user,
#         credential_id=bytes_to_b64url(verification.credential_id),
#         public_key=bytes_to_b64url(verification.credential_public_key),
#         sign_count=verification.sign_count,
#         nickname=nickname,
#     )
#     return True


# def build_authentication_options(user=None):
#     allowed = None
#     if user is not None:
#         allowed = [
#             PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.credential_id))
#             for c in WebAuthnCredential.objects.filter(user=user)
#         ]
#     options = generate_authentication_options(
#         rp_id=settings.WEBAUTHN_RP_ID,
#         allow_credentials=allowed,
#         user_verification=UserVerificationRequirement.REQUIRED,
#     )
#     return options, bytes_to_b64url(options.challenge)


# def verify_authentication(credential_response: dict, expected_challenge_b64: str):
#     credential_id_b64 = credential_response['id']
#     stored = WebAuthnCredential.objects.filter(credential_id=credential_id_b64).select_related('user').first()
#     if not stored:
#         return None

#     verification = verify_authentication_response(
#         credential=credential_response,
#         expected_challenge=b64url_to_bytes(expected_challenge_b64),
#         expected_origin=settings.WEBAUTHN_ORIGIN,
#         expected_rp_id=settings.WEBAUTHN_RP_ID,
#         credential_public_key=b64url_to_bytes(stored.public_key),
#         credential_current_sign_count=stored.sign_count,
#     )
#     stored.sign_count = verification.new_sign_count
#     stored.save(update_fields=['sign_count'])
#     return stored.user

"""WebAuthn (FIDO2 / biometric) registration and login helpers."""
import base64
import json

from django.conf import settings
from webauthn import (
    generate_registration_options, verify_registration_response,
    generate_authentication_options, verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor, UserVerificationRequirement,
    AuthenticatorSelectionCriteria, ResidentKeyRequirement,
)

from .models import WebAuthnCredential


def b64url_to_bytes(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def bytes_to_b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode('utf-8').rstrip('=')


def build_registration_options(user):
    existing = [
        PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.credential_id))
        for c in WebAuthnCredential.objects.filter(user=user)
    ]
    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=str(user.id).encode('utf-8'),
        user_name=user.username,
        user_display_name=user.get_full_name() or user.username,
        exclude_credentials=existing,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,  # forces biometric/PIN, not just "USB key present"
        ),
    )
    return options, bytes_to_b64url(options.challenge)


def verify_registration(user, credential_response: dict, expected_challenge_b64: str, nickname: str = ''):
    # The webauthn library expects a JSON STRING here, not a raw dict -
    # passing the dict directly fails validation silently and surfaces as a
    # generic "Biometric login failed" error with no useful detail.
    verification = verify_registration_response(
        credential=json.dumps(credential_response),
        expected_challenge=b64url_to_bytes(expected_challenge_b64),
        expected_origin=settings.WEBAUTHN_ORIGIN,
        expected_rp_id=settings.WEBAUTHN_RP_ID,
    )
    WebAuthnCredential.objects.create(
        user=user,
        credential_id=bytes_to_b64url(verification.credential_id),
        public_key=bytes_to_b64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        nickname=nickname,
    )
    return True


def build_authentication_options(user=None):
    allowed = None
    if user is not None:
        allowed = [
            PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.credential_id))
            for c in WebAuthnCredential.objects.filter(user=user)
        ]
    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        allow_credentials=allowed,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return options, bytes_to_b64url(options.challenge)


def verify_authentication(credential_response: dict, expected_challenge_b64: str):
    credential_id_b64 = credential_response['id']
    stored = WebAuthnCredential.objects.filter(credential_id=credential_id_b64).select_related('user').first()
    if not stored:
        return None

    # Same fix as verify_registration - the library needs a JSON string.
    verification = verify_authentication_response(
        credential=json.dumps(credential_response),
        expected_challenge=b64url_to_bytes(expected_challenge_b64),
        expected_origin=settings.WEBAUTHN_ORIGIN,
        expected_rp_id=settings.WEBAUTHN_RP_ID,
        credential_public_key=b64url_to_bytes(stored.public_key),
        credential_current_sign_count=stored.sign_count,
    )
    stored.sign_count = verification.new_sign_count
    stored.save(update_fields=['sign_count'])
    return stored.user