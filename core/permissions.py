from rest_framework import permissions


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
