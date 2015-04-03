# from django.shortcuts import render

from django.http import Http404
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from core.models import Account
from core.serializers import AccountSerializer
from core.permissions import IsAccountOwnerOrReadOnly


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'accounts': reverse('account-list', request=request, format=format),
    })


class AccountList(generics.ListAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, )


class AccountDetail(generics.RetrieveUpdateAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrReadOnly)
