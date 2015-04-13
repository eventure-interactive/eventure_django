from rest_framework import permissions
from core.models import Event, EventGuest

class IsAccountOwnerOrReadOnly(permissions.BasePermission):
    "Allows write access only if the requestor is the Account owner."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user


class IsAlbumOwnerAndDeleteCustom(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        if request.method == 'DELETE' and obj.album_type.name != 'CUSTOM':
            return False

        return obj.owner_id == request.user.id


class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id

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