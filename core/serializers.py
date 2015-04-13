from django.forms import widgets
from rest_framework import serializers
from .models import Account, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest
from django.utils import timezone


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

class EventSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail')
    albums = serializers.HyperlinkedRelatedField(many=True, view_name='album-detail', read_only=True)
    guests = serializers.HyperlinkedRelatedField(many=True, view_name='account-detail', read_only=True)
    lat = serializers.FloatField(allow_null=True, read_only=True)
    lon = serializers.FloatField(allow_null=True, read_only=True)

    class Meta:
        model = Event 
        fields = ('id', 'url', 'title', 'start', 'end', 'owner', 'guests', 'albums', 'location', 'lat', 'lon')

    def validate(self, data): 
        ''' End Date must be later than Start Date '''
        if data['start'] > data['end']:
            raise serializers.ValidationError('End Date must be later than Start Date')
        return data
    def validate_start(self, value): 
        ''' Start date must be in future '''
        if value < timezone.now():
            raise serializers.ValidationError('Start Date must not be in the past')
        return value
    



class EventGuestSerializer(serializers.HyperlinkedModelSerializer):
    event = serializers.HiddenField( default=None )# queryset=Event.objects.all())#, )
    guest = serializers.HyperlinkedRelatedField(queryset=Account.objects.all(), view_name='account-detail')

    class Meta:
        model = EventGuest
        fields = ('id', 'event', 'guest' , 'rsvp')
        
    
class EventGuestUpdateSerializer(EventGuestSerializer): 
    ''' to be used with Event Guest Detail view '''
    guest = serializers.HyperlinkedRelatedField(view_name='account-detail', read_only=True)

class AlbumSerializer(serializers.HyperlinkedModelSerializer):

    album_type = AlbumTypeSerializer(read_only=True)
    files = serializers.HyperlinkedIdentityField(view_name='albumfiles-list')
    event = serializers.HyperlinkedRelatedField(queryset=Event.objects.all(), view_name='event-detail', allow_null=True)

    class Meta:
        model = Album
        fields = ('id', 'url', 'name', 'description', 'album_type', 'files', 'event') #owner

class AlbumUpdateSerializer(AlbumSerializer):
    ''' When updating album, should not allow update event '''
    event = serializers.HyperlinkedRelatedField(read_only=True, view_name='event-detail', allow_null=True)

