#main/urls.py

from django.urls import include, path
from main.views import *
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("", index, name="index"),
    path('delete_user/', delete_user, name='delete_user'),
    path('accounts/', accounts_view, name='account'),
    path('account/add_account/', AddAccountView.as_view(), name='add_account'),
    path('account/update_favorite/', csrf_exempt(update_favorite), name='update_favorite'),
    path('account/<str:account_name>/', account_view, name='account_details'),
    path('new_manual_transaction/<str:account_name>/', new_transaction, name='new_transaction'),
    path('account/info/<str:account_name>/', account_info, name='account_info'),
    path('account/delete/<str:account_name>/', delete_account, name='delete_account'),
    path('account/edit/<str:account_name>/<str:field>/', edit_account, name='edit_account'),
    path('transaction/<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    path('transaction/delete/<int:pk>/', delete_transaction, name='delete_transaction'),
    path('user_info/', UserInfoView.as_view(), name='user_info'),
    path('paychecks/', paychecks, name='paychecks'),
    path('add_paycheck/', AddNewPaycheckView.as_view(), name='add_paycheck'),
    path('paycheck/<int:pk>/', paycheck_info, name='paycheck_info'),
    path('paycheck/delete/<int:pk>/', delete_paycheck, name='delete_paycheck'),
    path('transaction/upload_receipt/<str:account_name>/', AnalyzeReceiptView.as_view(), name='analyze_receipt'),
    path('new_transaction/<str:account_name>/', TransactionImportChoiceView.as_view(), name='new_transaction_choice'),
    path('transaction/confirmReceiptAnalysis/<str:account_name>/', ConfirmReceiptAnalysisView.as_view(), name='confirmReceiptAnalysis'),
    path('accounts/2fa/', CustomSecurityIndexView.as_view(), name='mfa_index'),
    path('terminate_all_sessions/', TerminateAllSessionsView.as_view(), name='terminate_all_sessions'),
    path('terminate_session/<str:session_key>/', terminate_session, name='terminate_session'),
]
