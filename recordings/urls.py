"""URLs for recordings app"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Main views
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('recordings/', views.recordings_list_view, name='recordings_list'),
    path('recordings/<int:pk>/', views.recording_detail_view, name='recording_detail'),
    path('settings/', views.settings_view, name='settings'),
    
    # Actions
    path('recordings/upload/', views.upload_recording_view, name='upload_recording'),
    path('recordings/<int:pk>/transcribe/', views.transcribe_recording_view, name='transcribe_recording'),
    path('recordings/<int:pk>/cancel-transcription/', views.cancel_transcription_view, name='cancel_transcription'),
    path('recordings/<int:pk>/download/', views.download_audio_view, name='download_audio'),
    path('recordings/<int:pk>/download-transcription/', views.download_transcription_view, name='download_transcription'),
    path('recordings/<int:pk>/delete/', views.delete_recording_view, name='delete_recording'),
    
    # API
    path('api/dashboard-status/', views.dashboard_status_api, name='dashboard_status_api'),
    path('api/recordings/<int:recording_id>/status/', views.recording_status_api, name='recording_status_api'),
]

