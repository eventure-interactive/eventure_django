from django import forms as django_forms
from django.conf import settings
from django.db import transaction
from django.shortcuts import render_to_response, render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.template import Template
from django.views.generic import View
from django.views.decorators.http import require_safe
from django.contrib.auth import logout

from core import common as core_common
from core import models as core_models
from core import views as core_views
from fe import forms


class LoginView(View):

    template_name = "login.html"
    form_class = forms.LoginForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            email = cleaned.get('email')
            password = cleaned.get('password')

            user = core_views.Login.do_login(request, email, password)
            if not user:
                err = django_forms.ValidationError('An account with that email and password was not found.',
                                                   code="invalid")
                form.add_error(None, err)
                return render(request, self.template_name, {'form': form})
            else:
                # Success, we logged them in
                return redirect('fe:home')

        return render(request, self.template_name, {'form': form})


class LogoutView(View):

    def get(self, request):

        logout(request)
        return redirect(settings.EVENTURE_STATIC_SITE_URL)


class CreateAccountEmailView(View):
    template_name = "create_account_email.html"
    form_class = forms.CreateAccountEmailForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    @transaction.atomic
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            # check for existing registered email
            email = cleaned['email']
            Account, AccountStatus = core_models.Account, core_models.AccountStatus
            if Account.objects.filter(email=email, status__gt=AccountStatus.SIGNED_UP).exists():
                form.add_error('email', 'This email address is already in use.')
                return render(request, self.template_name, {'form': form})
            else:
                account = core_common.create_account(cleaned, request)
                return render(request, "create_account_email_sent.html")

        return render(request, self.template_name, {'form': form})


class ForgotPasswordView(View):

    template_name = "forgot_password.html"
    form_class = forms.ForgotPasswordForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            core_common.send_password_reset(form.cleaned_data, request)
            return render(request, "forgot_password_email_sent.html")

        return render(request, self.template_name, {'form': form})


class ResetForgotPasswordView(View):
    form_class = forms.ResetForgotPasswordForm
    template_name = "reset_forgot_password.html"

    def _validate_reset_token(self, pw_reset, token_param):
        if not pw_reset.can_still_use():
            raise Http404('Token expired or used')

        if pw_reset.get_password_reset_token() != token_param:
            raise Http404('Token not valid')

    def get(self, request, pw_reset_id, token):
        pw_reset = get_object_or_404(core_models.PasswordReset, pk=pw_reset_id)
        self._validate_reset_token(pw_reset, token)

        form = self.form_class()
        return render(request, self.template_name, {'form': form, 'email': pw_reset.email})

    @transaction.atomic
    def post(self, request, pw_reset_id, token):
        pw_reset = get_object_or_404(core_models.PasswordReset, pk=pw_reset_id)
        self._validate_reset_token(pw_reset, token)

        form = self.form_class(request.POST)
        if form.is_valid():
            pw_reset.update_password(form.cleaned_data['password1'])
            return render(request, "reset_forgot_password_done.html")

        return render(request, self.template_name, {'form': form, 'email': pw_reset.email})


def todo_view(request):
    return HttpResponse('TODO')
