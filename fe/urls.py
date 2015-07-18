from django.conf.urls import patterns, url
from fe import views

urlpatterns = [
    url(r'^create-account-email$', views.CreateAccountEmailView.as_view(), name='create-account-email'),
    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),
    url(r'^forgot-password$', views.ForgotPasswordView.as_view(), name='forgot-password'),
    url(r'^finish-reset/(?P<pw_reset_id>[0-9]+)/(?P<token>[0-9a-f]+)$',
        views.ResetForgotPasswordView.as_view(),
        name='reset-forgot'),

    # TODO
    url(r'^$', views.todo_view, name='home'),
    url(r'^set-profile$', views.todo_view, name='set-profile'),  # After we validate email, we are redirected here...
    url(r'^bad-channel-validation-token$', views.todo_view, name='bad-channel-validation'),
]
