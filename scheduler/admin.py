"""
Admin configuration for the scheduler app.

Registers the Post model with useful list display and filtering options.
"""

from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Admin interface for Post model."""
    
    list_display = ['content_preview', 'user', 'status', 'scheduled_for', 'created_at']
    list_filter = ['status', 'created_at', 'scheduled_for']
    search_fields = ['content', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'metrics']
    date_hierarchy = 'scheduled_for'
    
    def content_preview(self, obj):
        """Return truncated content for list display."""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
