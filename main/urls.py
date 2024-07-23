#main/urls.py

from django.urls import include, path
from main.views import *
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("", index, name="index"),
    path('sign_up/', sign_up, name='sign_up'),
    path('delete_user/', delete_user, name='delete_user'),
    path('account/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('account/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('account/', account_view, name='account'),
    path('account/add_account/', add_account, name='add_account'),
    path('account/update_favorite/', csrf_exempt(updateFavorite), name='update_favorite'),
    path('account/<str:account_name>/', account_details, name='account_details'),
    path('new_transaction/<str:account_name>/', new_transaction, name='new_transaction'),
    path('account/info/<str:account_name>/', account_info, name='account_info'),
    path('account/delete/<str:account_name>/', delete_account, name='delete_account'),
    path('account/edit/<str:account_name>/<str:field>/', edit_account, name='edit_account'),
    path('transaction/<int:pk>/', transaction_detail, name='transaction_detail'),
    path('transaction/delete/<int:pk>/', delete_transaction, name='delete_transaction'),
    path('user_info/', user_info, name='user_info'),
]