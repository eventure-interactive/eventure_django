from django.forms import widgets
from rest_framework import serializers
from .models import Account, Album, AlbumType, AlbumFile, Thumbnail


class AccountSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Account
        fields = ('url', 'name')


class ThumbnailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Thumbnail
        fields = ('size_type', 'file_url', 'width', 'height', 'size_bytes')


class AlbumTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlbumType
        fields = ('id', 'name', 'description')


class AlbumFileSerializer(serializers.HyperlinkedModelSerializer):

    width = serializers.ReadOnlyField()
    height = serializers.ReadOnlyField()
    size_bytes = serializers.ReadOnlyField()
    thumbnails = ThumbnailSerializer(many=True, read_only=True)

    class Meta:
        model = AlbumFile
        fields = ('url', 'file_url', 'width', 'height', 'size_bytes', 'thumbnails')


class AlbumSerializer(serializers.HyperlinkedModelSerializer):

    album_type = AlbumTypeSerializer(read_only=True)
    files = serializers.HyperlinkedIdentityField(view_name='albumfiles-list')

    class Meta:
        model = Album
        fields = ('url', 'name', 'description', 'album_type', 'files')
