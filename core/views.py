# from django.shortcuts import render

from django.http import Http404
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from core.models import Account, Album, AlbumType
from core.serializers import AccountSerializer, AlbumSerializer
from core.permissions import IsAccountOwnerOrReadOnly, IsAlbumOwnerAndDeleteCustom


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'accounts': reverse('account-list', request=request, format=format),
        'albums': reverse('album-list', request=request, format=format),
    })


class AccountList(generics.ListAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, )


class AccountDetail(generics.RetrieveUpdateAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrReadOnly)


class AlbumList(generics.ListCreateAPIView):

    def get_queryset(self):
        user = self.request.user
        return Album.active.filter(owner=user)

    def perform_create(self, serializer):
        custom_type = AlbumType.objects.get(name='CUSTOM')
        serializer.save(owner=self.request.user, album_type=custom_type)

    serializer_class = AlbumSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AlbumDetail(generics.RetrieveUpdateDestroyAPIView):

    def get_queryset(self):
        return Album.active.filter(owner=self.request.user)

    serializer_class = AlbumSerializer
    permission_classes = (permissions.IsAuthenticated, IsAlbumOwnerAndDeleteCustom)
