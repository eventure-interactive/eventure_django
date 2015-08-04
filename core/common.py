"Common logic shared between API and frontend."
from datetime import timedelta
from functools import partial
from django.utils import timezone
from django.core import urlresolvers
from django.contrib.auth import authenticate, login
from core import models
from core import tasks

from core.email_sender import send_validation_email


def _generate_validation_url(request, validation_token):
    local_url = urlresolvers.reverse('email-validate', kwargs=dict(validation_token=validation_token))
    return request.build_absolute_uri(local_url)


def create_account(validated_data, request):

    email = validated_data['email']
    password = validated_data['password']
    Account = models.Account
    # see if the account exists (could be a dummy acocunt or a signed-up but not verified.)
    account = None
    try:
        account = Account.objects.get(email=email, status__lt=models.AccountStatus.ACTIVE)
    except models.Account.DoesNotExist:
        pass

    if account:
        RESEND_THRESHOLD = timedelta(minutes=5)
        cutoff_time = timezone.now() - RESEND_THRESHOLD
        commchannel_count = account.commchannel_set.filter(comm_type=models.CommChannel.EMAIL,
                                                           message_sent_date__gt=cutoff_time).count()
        if commchannel_count:
            # We've sent an email in the last five minutes. Let' do nothing.
            return account
    else:
        account = Account.objects.create_user(email, password)

    send_validation_email(account.id, account.email, partial(_generate_validation_url, request))
    account = authenticate(email=email, password=password)
    login(request, account)
    return account


def send_password_reset(validated_data, request):

    # Sending off email async now, as we don't wan't to leak whether or not
    # this is an active email account. And if we aren't going to tell the user if that's a
    # valid email, we may as well return ASAP.

    dummy_id = '00800'
    dummy_token = 'ffffaaafff'
    fake_path = urlresolvers.reverse('fe:reset-forgot', kwargs={'pw_reset_id': dummy_id, 'token': dummy_token})
    fake_uri = request.build_absolute_uri(fake_path)

    template_uri = fake_uri.replace(dummy_id, '{pw_reset_id}', 1)
    template_uri = template_uri.replace(dummy_token, '{token}', 1)

    tasks.send_password_reset_email.delay(validated_data['email'], template_uri)
