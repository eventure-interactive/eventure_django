from rest_framework import permissions


class IsAccountOwnerOrReadOnly(permissions.BasePermission):
    "Allows write access only if the requestor is the Account owner."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user
