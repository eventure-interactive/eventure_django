from django import forms
from core import views as core_views
from core import models as core_models


_email_field = forms.EmailField(label='Your email',
                                widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
_password_field = forms.CharField(label='Your password',
                                  min_length=5,
                                  widget=forms.PasswordInput(attrs={'class': 'form-control',
                                                                    'placeholder': 'Password'}))


class CreateAccountEmailForm(forms.Form):

    email = _email_field
    password = _password_field

    def clean_email(self):
        Account = core_models.Account
        AccountStatus = core_models.AccountStatus
        email = self.cleaned_data['email']
        if Account.objects.filter(email=email, status__gt=AccountStatus.SIGNED_UP).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email


class LoginForm(forms.Form):

    email = _email_field
    password = _password_field

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        password = cleaned.get('password')

        if email and password:
            user = core_views.Login.do_login(self.request, email, password)
            if not user:
                raise forms.ValidationError('An account with that email and password was not found.', code="invalid")
