from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from fe import views

urlpatterns = [
    url(r'^create-account-email$', views.CreateAccountEmailView.as_view(), name='create-account-email'),
    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),
    url(r'^forgot-password$', views.ForgotPasswordView.as_view(), name='forgot-password'),
    url(r'^finish-reset/(?P<pw_reset_id>[0-9]+)/(?P<token>[0-9a-f]+)$',
        views.ResetForgotPasswordView.as_view(),
        name='reset-forgot'),
    # After we validate email, we are redirected here...
    url(r'^set-profile$', login_required(views.SetProfileView.as_view()), name='set-profile'),
    url(r'^account-settings$', login_required(views.AccountSettingsView.as_view()), name='account-settings'),
    url(r'^$', views.ProfileView.as_view(), name='home'),

    # TODO
    url(r'^bad-channel-validation-token$', views.todo_view, name='bad-channel-validation'),
    url(r'^welcome-tour$', views.todo_view, name='welcome-tour'),
]
