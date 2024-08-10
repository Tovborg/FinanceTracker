#main/urls.py

from django.urls import include, path
from main.views import *
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("", index, name="index"),
    path('delete_user/', delete_user, name='delete_user'),
    path('account/', account_view, name='account'),
    path('account/add_account/', add_account, name='add_account'),
    path('account/update_favorite/', csrf_exempt(updateFavorite), name='update_favorite'),
    path('account/<str:account_name>/', account_details, name='account_details'),
    path('new_manual_transaction/<str:account_name>/', new_transaction, name='new_transaction'),
    path('account/info/<str:account_name>/', account_info, name='account_info'),
    path('account/delete/<str:account_name>/', delete_account, name='delete_account'),
    path('account/edit/<str:account_name>/<str:field>/', edit_account, name='edit_account'),
    path('transaction/<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    path('transaction/delete/<int:pk>/', delete_transaction, name='delete_transaction'),
    path('user_info/', user_info, name='user_info'),
    path('paychecks/', paychecks, name='paychecks'),
    path('add_paycheck/', add_new_paycheck, name='add_paycheck'),
    path('paycheck/<int:pk>/', paycheck_info, name='paycheck_info'),
    path('paycheck/delete/<int:pk>/', delete_paycheck, name='delete_paycheck'),
    path('transaction/upload_receipt/<str:account_name>/', analyze_receipt_view, name='analyze_receipt'),
    path('new_transaction/<str:account_name>/', transaction_import_choice, name='new_transaction_choice'),
    path('transaction/confirmReceiptAnalysis/<str:account_name>/', ConfirmReceiptAnalysisView.as_view(), name='confirmReceiptAnalysis'),
]
