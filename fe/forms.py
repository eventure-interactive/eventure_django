from django import forms
from core.models import Account, EventPrivacy

PASSWORD_MIN_LENGTH = 5
_email_field = forms.EmailField(label='Your email',
                                widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
_password_field = forms.CharField(label='Your password',
                                  min_length=PASSWORD_MIN_LENGTH,
                                  widget=forms.PasswordInput(attrs={'class': 'form-control',
                                                                    'placeholder': 'Password'}))


class CreateAccountEmailForm(forms.Form):

    email = _email_field
    password = _password_field


class LoginForm(forms.Form):

    email = _email_field
    password = _password_field


class ForgotPasswordForm(forms.Form):

    email = _email_field


class ResetForgotPasswordForm(forms.Form):

    password1 = forms.CharField(label="Enter your new password", min_length=PASSWORD_MIN_LENGTH,
                                widget=forms.PasswordInput(attrs={'class': 'form-control',
                                                                  'placeholder': 'Password'}))
    password2 = forms.CharField(label="Re-enter your new password", min_length=PASSWORD_MIN_LENGTH,
                                widget=forms.PasswordInput(attrs={'class': 'form-control',
                                                                  'placeholder': 'Password'}))

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('password1')
        pw2 = cleaned.get('password2')

        if pw1 != pw2:
            raise forms.ValidationError('Passwords did not match.', code="nomatch")


class SetProfileForm(forms.Form):

    name = forms.CharField(label="Your name",
                           widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name'}))


class AccountSettingsForm(forms.Form):

    email_rsvp_updates = forms.BooleanField(label="Receive Email RSVP Updates", required=False)
    email_social_activity = forms.BooleanField(label="Receive Email Social Activities", required=False)
    email_promotions = forms.BooleanField(label="Receive Email Promotions", required=False)
    text_rsvp_updates = forms.BooleanField(label="Receive Text RSVP Updates", required=False)
    text_social_activity = forms.BooleanField(label="Receive Text Social Activities", required=False)
    text_promotions = forms.BooleanField(label="Receive Text Promotions", required=False)
    default_event_privacy = forms.ChoiceField(label="Event Privacy", choices=EventPrivacy.PRIVACY_CHOICES,)
    profile_privacy = forms.ChoiceField(choices=Account.PRIVACY_CHOICES, required=False)