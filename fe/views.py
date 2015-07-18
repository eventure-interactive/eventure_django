from django.db import transaction
from django.shortcuts import render_to_response, render, redirect
from django.http import HttpResponse
from django.template import Template
from django.views.generic import View
from django.views.decorators.http import require_safe
from django.contrib.auth import logout

from core import common as core_common
from fe import forms


class LoginView(View):

    template_name = "login.html"
    form_class = forms.LoginForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request=request)
        if form.is_valid():
            return redirect('/')

        return render(request, self.template_name, {'form': form})


class LogoutView(View):

    def get(self, request):

        logout(request)
        return redirect('/')


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
            account = core_common.create_account(cleaned, request)
            return redirect('fe:create-account-email-sent')

        return render(request, self.template_name, {'form': form})


@require_safe
def create_account_email_sent(request):
    return render(request, "create_account_email_sent.html")


def todo_view(request):
    return HttpResponse('TODO')
