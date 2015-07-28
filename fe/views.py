from django import forms as django_forms
from django.conf import settings
from django.db import transaction
from django.shortcuts import render_to_response, render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.template import Template
from django.views.generic import View
from django.views.decorators.http import require_safe

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from core import common as core_common
from core import models as core_models
from core import views as core_views
from fe import forms
import logging
logger = logging.getLogger(__name__)


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
                next_ = request.GET.get('next', 'fe:home')  # check for Django ?next=/path/to/redirect
                return redirect(next_)

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


class SetProfileView(View):
    "Set initial profile (name and profile image)."

    template_name = "set_profile.html"
    form_class = forms.SetProfileForm

    def get(self, request):
        form = self.form_class(initial={'name': request.user.name})
        profile_img_url = self._get_profile_img_url(request.user)
        return render(request, self.template_name, {'form': form, 'profile_img_url': profile_img_url})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            request.user.name = form.cleaned_data['name']
            request.user.save()
            return redirect('fe:welcome-tour')

        profile_img_url = self._get_profile_img_url(request.user)
        return render(request, self.template_name, {'form': form, 'profile_img_url': profile_img_url})

    def _get_profile_img_url(self, user):
        af = user.profile_albumfile

        if not af:
            return None

        try:
            # Spec calls for 180*180 so should be serving 360*360, but we don't have a
            # thumbnail that size. Serving the closest thing we have.
            thumb = af.thumbnails.get(size_type=core_models.Thumbnail.SIZE_320).file_url
        except core_models.Thumbnail.DoesNotExist:
            thumb = af.file_url

        return thumb


class AccountSettingsView(View):
    "Account Settings & Deactivation"

    template_name = "account_settings.html"
    form_class = forms.AccountSettingsForm

    def get(self, request):
        acc_settings = get_object_or_404(core_models.AccountSettings, account=request.user.id)
        form = self.form_class(acc_settings.__dict__)
        return render(request, self.template_name, {'form': form})

    @transaction.atomic
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            instance = get_object_or_404(core_models.AccountSettings, account=request.user.id)

            normal_fields = ('email_rsvp_updates', 'email_social_activity', 'email_promotions',
                            'text_rsvp_updates', 'text_social_activity', 'text_promotions',
                            'default_event_privacy',)

            for field in normal_fields:
                val = form.cleaned_data.get(field, getattr(instance, field))
                setattr(instance, field, val)

            instance.save()

            account = get_object_or_404(core_models.Account, pk=request.user.id)
            account.profile_privacy = form.cleaned_data.get('profile_privacy', account.profile_privacy)
            account.save()

        return render(request, self.template_name, {'form': form})


class ProfileView(View):

    template_name = "account_profile.html"

    @method_decorator(login_required)
    def get(self, request):
        account = {'name': request.user.name}
        return render(request, self.template_name, {'account': account})


def todo_view(request):
    return HttpResponse('TODO')
