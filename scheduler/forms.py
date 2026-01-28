"""
Forms for the scheduler app.

Provides the PostForm for creating and editing social media posts.
"""

from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    """
    Form for creating and editing Post instances.
    
    Excludes `user`, `status`, and `metrics` fields as these are
    set programmatically in the view.
    """
    
    class Meta:
        model = Post
        fields = ['content', 'platform', 'image', 'scheduled_for']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none',
                'rows': 4,
                'placeholder': 'What do you want to share?'
            }),
            'scheduled_for': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'accept': 'image/*'
            }),
        }
        labels = {
            'content': 'Post Content',
            'image': 'Image (optional)',
            'scheduled_for': 'Schedule For',
        }
