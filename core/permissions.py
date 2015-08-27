from rest_framework import permissions
from core.models import Event, EventGuest, Album, AlbumFile, Follow, Account, Comment
import logging
logger = logging.getLogger(__name__)


class IsAccountOwnerOrReadOnly(permissions.BasePermission):
    "Allows write access only if the requestor is the Account owner."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    "If log in, allow read/write. If not, allow read only"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated()

# DEPRICATED/UNUSED
# class IsAlbumOwnerAndDeleteCustom(permissions.BasePermission):

#     def has_object_permission(self, request, view, obj):

#         if request.method == 'DELETE' and obj.album_type.name != 'CUSTOM':
#             return False

#         return obj.owner_id == request.user.id


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
            if obj.owner_id == request.user.id:
                return True
            # If User granted access to at least one album that this media belongs to, access is granted
            for album in obj.albums.all():
                if self.has_object_permission(request, view, album):
                    return True
            return False


class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id


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


class CanCommentOnEvent(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Event):
            event = obj
        elif isinstance(obj, Comment):
            event = obj.content_object
        else:
            raise ValueError("Unexpected object type {}".format(type(obj)))

        # These are my best guesses at permissions; don't treat as gospel.

        if request.method in permissions.SAFE_METHODS:
            return event.privacy != Event.PRIVATE or _is_event_member(event, request.user)

        if request.method == 'POST':
            # Only guests can comment. ? Is public open to everyone? Not as implemented...
            return _is_event_member(event, request.user)

        if request.method in ('PUT', 'PATCH'):
            # Only the owner of the comment can edit it
            return obj.owner_id == request.user.id

        if request.method == 'DELETE':
            # Only the owner of the comment or the owner of the event can delete it
            return request.user.id in (obj.owner_id, event.owner_id)

        logger.error("Unexpected request method: {}".format(request.method))
        return False


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
