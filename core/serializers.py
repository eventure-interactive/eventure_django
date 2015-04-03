from django.forms import widgets
from rest_framework import serializers
from .models import Account, Album, AlbumType


class AccountSerializer(serializers.HyperlinkedModelSerializer):

    phone = serializers.ReadOnlyField()

    class Meta:
        model = Account
        fields = ('url', 'phone', 'name', 'status', 'show_welcome_page')


class AlbumTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlbumType
        fields = ('id', 'name', 'description')


class AlbumSerializer(serializers.HyperlinkedModelSerializer):

    album_type = AlbumTypeSerializer(read_only=True)

    class Meta:
        model = Album
        fields = ('url', 'name', 'description', 'album_type')
