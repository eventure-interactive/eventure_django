from django.conf.urls import patterns, url
from fe import views

urlpatterns = [
    url(r'^create-account-email$', views.CreateAccountEmailView.as_view(), name='create-account-email'),
    url(r'^create-account-email/sent-verification$', views.create_account_email_sent, name='create-account-email-sent'),
    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),

    # TODO
    url(r'^$', views.todo_view, name='home'),
    url(r'^set-profile$', views.todo_view, name='set-profile'),
    url(r'^bad-channel-validation-token$', views.todo_view, name='bad-channel-validation')
]
