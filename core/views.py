# from django.shortcuts import render

from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from core.models import Account, Album, AlbumType, AlbumFile
from core.serializers import AccountSerializer, AlbumSerializer, AlbumFileSerializer
from core.permissions import IsAccountOwnerOrReadOnly, IsAlbumOwnerAndDeleteCustom, IsOwner


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'accounts': reverse('account-list', request=request, format=format),
        'albums': reverse('album-list', request=request, format=format),
    })


class AccountList(generics.ListAPIView):
    "Provides a list of active Accounts."
    queryset = Account.objects.filter(status=Account.ACTIVE)
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, )


class AccountDetail(generics.RetrieveUpdateAPIView):
    "Show detailed information for the given account."
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrReadOnly)


class AlbumList(generics.ListCreateAPIView):
    "Shows the current account's active albums."

    def get_queryset(self):
        user = self.request.user
        return Album.active.filter(owner=user).select_related('album_type')  # TODO: will need to add in Event albums

    def perform_create(self, serializer):
        custom_type = AlbumType.objects.get(name='CUSTOM')
        serializer.save(owner=self.request.user, album_type=custom_type)

    serializer_class = AlbumSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AlbumDetail(generics.RetrieveUpdateDestroyAPIView):

    def get_queryset(self):
        return Album.active.filter(owner=self.request.user).select_related('album_type')

    def get_object(self):
        album = super().get_object()
        album.files = list(album.albumfiles_queryset(self.request.user))
        return album

    serializer_class = AlbumSerializer
    permission_classes = (permissions.IsAuthenticated, IsAlbumOwnerAndDeleteCustom)


class AlbumFileDetail(generics.RetrieveUpdateAPIView):

    queryset = AlbumFile.active.all()
    serializer_class = AlbumFileSerializer
    permission_classes = (permissions.IsAuthenticated, )  # TODO: Permissions on this


class AlbumFilesList(generics.ListAPIView):
    "List the files in the album."

    permission_classes = (permissions.IsAuthenticated, )  # TODO
    serializer_class = AlbumFileSerializer
    queryset = Album.active.all().select_related('album_type')

    def list(self, request, *args, **kwargs):
        album = self.get_object()
        files = album.albumfiles_queryset(request.user)

        page = self.paginate_queryset(files)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)
