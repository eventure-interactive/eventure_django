from django.core.exceptions import ValidationError
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import ugettext_lazy as _
from phonenumbers.phonenumberutil import NumberParseException
from .models import Account, AlbumType, Album, AlbumFile, Thumbnail


class AccountAdminMixin(object):

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        try:
            phone = Account.canonical_phone(phone)
        except (ValueError, NumberParseException):
            raise ValidationError(_("%(phone)s is does not appear to be a valid phone number"),
                                  code='invalid', params={'phone': phone})
        return phone


class AccountCreationForm(UserCreationForm, AccountAdminMixin):
    "Form for Account creation."
    class Meta:
        model = Account
        fields = ('name',)


class AccountChangeForm(UserChangeForm, AccountAdminMixin):
    "Form for Account changes."


@admin.register(Account)
class AccountAdmin(UserAdmin):
    model = Account

    list_display = ('phone', 'name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'status', 'groups')
    search_fields = ('name', 'phone')
    ordering = ('name',)

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        (_('Personal info'), {'fields': ('name',)}),
        (_('Permissions'), {'fields': ('status', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'name', 'password1', 'password2'),
        }),
    )

    form = AccountChangeForm
    add_form = AccountCreationForm


@admin.register(AlbumType)
class AlbumTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'sort_order', 'is_virtual', 'is_deletable')


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_filter = ('status', 'album_type')
    list_display = ('name', 'owner', 'album_type', 'status')
    search_fields = ('name', 'owner__phone')


@admin.register(AlbumFile)
class AlbumFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')


@admin.register(Thumbnail)
class ThumbnailAdmin(admin.ModelAdmin):
    list_display = ('albumfile', 'size_type')
