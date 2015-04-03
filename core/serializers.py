from django.forms import widgets
from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.HyperlinkedModelSerializer):

    phone = serializers.ReadOnlyField()

    class Meta:
        model = Account
        fields = ('url', 'phone', 'name', 'status', 'show_welcome_page')
