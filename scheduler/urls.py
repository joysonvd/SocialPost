"""
URL configuration for the scheduler app.

All routes are prefixed with '/' from the main urls.py.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),
    
    # Post CRUD
    path('post/create/', views.post_modal, name='post_create'),
    path('post/create/<int:year>/<int:month>/<int:day>/', views.post_modal, name='post_create_date'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),
    
    # AI Image Generation
    path('api/generate-image/', views.generate_ai_image, name='generate_ai_image'),
    
    # Settings
    path('settings/', views.user_settings, name='settings'),
    
    # Registration
    path('register/', views.register, name='register'),
]
