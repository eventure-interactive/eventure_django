from rest_framework import permissions
from core.models import Event, EventGuest, Album, AlbumFile, Follow, Account
import logging
logger = logging.getLogger(__name__)


class IsAccountOwnerOrReadOnly(permissions.BasePermission):
    "Allows write access only if the requestor is the Account owner."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user


# DEPRICATED/UNUSED
class IsAlbumOwnerAndDeleteCustom(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        if request.method == 'DELETE' and obj.album_type.name != 'CUSTOM':
            return False

        return obj.owner_id == request.user.id


class IsAlbumUploadableOrReadOnly(permissions.BasePermission):
    "Restrict uploads to read-only albums."

    def has_permission(self, request, view):
        # raise ValueError(view)

        if request.method in permissions.SAFE_METHODS:
            return True

        album = view.get_album()

        return not album.album_type.is_virtual


class IsGrantedAccessToAlbum(permissions.BasePermission):
    """
    Read access Granted for private event albums that user is member or public event album, all else Denied
    Write access Granted for owner of album or owner of album event, all else Denied
    """
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Album):
            if request.method in permissions.SAFE_METHODS and obj.event is not None:
                return obj.event.privacy == Event.PRIVATE and _is_event_member(obj.event, request.user) or obj.event.privacy == Event.PUBLIC
            return obj.owner == request.user or (obj.event is not None and obj.event.owner == request.user)
        elif isinstance(obj, AlbumFile):
            #If User granted access to at least one album that this media belongs to, access is granted
            for album in obj.albums.all():
                if self.has_object_permission(request, view, album):
                    return True
            return False


class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id


# DEPRICATED/UNUSED
class IsEventOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owner of the event to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the event.
        # Only Event Owner can edit Guests
        if isinstance(obj, EventGuest):
            return obj.event.owner == request.user
        # Only Event Owner can edit event
        elif isinstance(obj, Event):
            return obj.owner == request.user


class IsGrantedAccessToEvent(permissions.BasePermission):
    """
    Read access Denied for Private Event that user is not a member, all else Granted
    Write access Granted for owner, all else Denied
    """

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Event):
            # Read access Denied for Private Event, all else Granted
            if request.method in permissions.SAFE_METHODS:
                return obj.privacy != Event.PRIVATE or _is_event_member(obj, request.user)
            # Write access Granted for owner, all else Denied
            return obj.owner == request.user
        elif isinstance(obj, EventGuest):
            # The guest himself can read/write or if user can access event
            return self.has_object_permission(request, view, obj.event) or obj.guest == request.user


def _is_event_member(event, account):
    ''' Check if account is owner or guest of event '''
    return event.owner == account or EventGuest.objects.filter(event=event.id, guest=account.id).exists()


class IsAccountOwnerOrDenied(permissions.BasePermission):
    """ For Follower List and Update view
    Only account owner/followee can see/update his followers
    """
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Follow):
            return obj.followee == request.user
        elif isinstance(obj, Account):
            return obj == request.user

# EOF
