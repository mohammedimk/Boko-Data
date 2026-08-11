"""Forms for authentication, wallet funding, and every VTU service."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from .models import UserProfile, phone_validator

NETWORK_CHOICES = [
    ('MTN', 'MTN'),
    ('AIRTEL', 'Airtel'),
    ('GLO', 'Glo'),
    ('9MOBILE', '9mobile'),
]

AIRTIME_TYPE_CHOICES = [
    ('VTU', 'VTU'),
    ('SHARE_AND_SELL', 'Share & Sell'),
]

CABLE_PROVIDER_CHOICES = [
    ('DSTV', 'DSTV'),
    ('GOTV', 'GOTV'),
    ('STARTIMES', 'StarTimes'),
]

METER_TYPE_CHOICES = [
    ('prepaid', 'Prepaid'),
    ('postpaid', 'Postpaid'),
]


DISCO_CHOICES = [
    ('1', 'Abuja Electric (AEDC)'),
    ('2', 'Eko Electric (EKEDC)'),
    ('3', 'Ibadan Electric (IBEDC)'),
    ('4', 'Ikeja Electric (IKEDC)'),
    ('5', 'Kaduna Electric'),
    ('6', 'Port Harcourt Electric'),
    ('7', 'Jos Electricity Distribution PLC (JEDplc)'),
    ('8', 'Enugu Electric'),
    ('9', 'Yola Electric'),
    ('10', 'Benin Electric'),
]


class RegistrationForm(UserCreationForm):
    """Extended registration form collecting name, email and phone number."""

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=11,
        required=True,
        validators=[phone_validator],
        help_text="11-digit Nigerian phone number, e.g. 08012345678",
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'phone_number', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if UserProfile.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Styled login form (username or email + password)."""
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control', 'placeholder': 'Username or Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class FundWalletForm(forms.Form):
    """Amount to fund via Paystack."""
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=100, max_value=1000000,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount (min ₦100)'}),
        help_text="Minimum ₦100, Maximum ₦1,000,000",
    )


class BuyDataForm(forms.Form):
    network = forms.ChoiceField(choices=NETWORK_CHOICES, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_network'}))
    plan_id = forms.CharField(widget=forms.HiddenInput(attrs={'id': 'id_plan_id'}))
    phone_number = forms.CharField(
        max_length=11, validators=[phone_validator],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipient phone number'})
    )


class BuyAirtimeForm(forms.Form):
    network = forms.ChoiceField(choices=NETWORK_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    airtime_type = forms.ChoiceField(choices=AIRTIME_TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    phone_number = forms.CharField(
        max_length=11, validators=[phone_validator],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipient phone number'})
    )
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=50, max_value=100000,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount'})
    )


class CableForm(forms.Form):
    provider = forms.ChoiceField(choices=CABLE_PROVIDER_CHOICES, widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_provider'}))
    smartcard_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Smart Card / IUC Number', 'id': 'id_smartcard'})
    )
    bouquet_id = forms.CharField(widget=forms.HiddenInput(attrs={'id': 'id_bouquet_id'}))
    phone_number = forms.CharField(
        max_length=11, validators=[phone_validator],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number for notification'})
    )


class ElectricityForm(forms.Form):
    disco = forms.ChoiceField(choices=DISCO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    meter_type = forms.ChoiceField(choices=METER_TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    meter_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meter number', 'id': 'id_meter_number'})
    )
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=500, max_value=500000,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount'})
    )
    phone_number = forms.CharField(
        max_length=11, validators=[phone_validator],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number for notification'})
    )
