"""Middleware for recordings app"""
from django.contrib.auth.models import User
from .models import UserSettings


class CreateUserSettingsMiddleware:
    """Automatically create UserSettings for new users"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            UserSettings.objects.get_or_create(user=request.user)
        
        response = self.get_response(request)
        return response

