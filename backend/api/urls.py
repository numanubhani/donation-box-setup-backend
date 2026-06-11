from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('register-admin/', views.register_admin_view, name='register-admin'),
    path('collectors/', views.collectors_list, name='collectors-list'),
    path('collectors/<int:pk>/', views.collector_detail, name='collector-detail'),
    path('collectors/<int:pk>/change-password/', views.change_password_view, name='change-password'),
    path('boxes/', views.boxes_list, name='boxes-list'),
    path('boxes/<int:pk>/', views.box_detail, name='box-detail'),
    path('assignments/', views.assignments_list, name='assignments-list'),
    path('assignments/<int:pk>/', views.assignment_detail, name='assignment-detail'),
    path('collections/', views.collections_list, name='collections-list'),
    path('expenses/', views.expenses_list, name='expenses-list'),
    path('complaints/', views.complaints_list, name='complaints-list'),
    path('complaints/<int:pk>/', views.complaint_detail, name='complaint-detail'),
    path('activities/', views.activities_list, name='activities-list'),
    path('messages/', views.messages_list, name='messages-list'),
    path('messages/read/', views.mark_messages_read, name='messages-read'),
    path('settings/twilio/', views.twilio_settings_view, name='twilio-settings'),
    path('settings/twilio/test/', views.twilio_test_sms_view, name='twilio-test'),
]
