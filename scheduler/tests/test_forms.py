"""
Tests for the scheduler app forms.

Tests cover:
- PostForm validation
- Field requirements and widgets
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from scheduler.forms import PostForm


class PostFormTest(TestCase):
    """Tests for the PostForm."""
    
    def test_form_valid_with_required_fields(self):
        """Test form is valid with all required fields."""
        form_data = {
            'content': 'Test post content',
            'platform': 'twitter',
            'scheduled_for': timezone.now() + timedelta(days=1),
        }
        form = PostForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_invalid_without_content(self):
        """Test form is invalid without content."""
        form_data = {
            'platform': 'twitter',
            'scheduled_for': timezone.now() + timedelta(days=1),
        }
        form = PostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_invalid_without_scheduled_for(self):
        """Test form is invalid without scheduled_for."""
        form_data = {
            'content': 'Test content',
            'platform': 'twitter',
        }
        form = PostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('scheduled_for', form.errors)
    
    def test_form_includes_correct_fields(self):
        """Test form includes expected fields."""
        form = PostForm()
        expected_fields = ['content', 'platform', 'image', 'scheduled_for']
        
        for field in expected_fields:
            self.assertIn(field, form.fields)
    
    def test_form_excludes_user_status_metrics(self):
        """Test form does not include user, status, or metrics fields."""
        form = PostForm()
        excluded_fields = ['user', 'status', 'metrics']
        
        for field in excluded_fields:
            self.assertNotIn(field, form.fields)
    
    def test_form_all_platforms_valid(self):
        """Test form accepts all valid platform choices."""
        platforms = ['twitter', 'instagram', 'facebook', 'linkedin', 'tiktok']
        
        for platform in platforms:
            form_data = {
                'content': f'Test post for {platform}',
                'platform': platform,
                'scheduled_for': timezone.now() + timedelta(days=1),
            }
            form = PostForm(data=form_data)
            self.assertTrue(form.is_valid(), f"Form should be valid for platform: {platform}")
    
    def test_form_invalid_platform(self):
        """Test form rejects invalid platform."""
        form_data = {
            'content': 'Test content',
            'platform': 'invalid_platform',
            'scheduled_for': timezone.now() + timedelta(days=1),
        }
        form = PostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('platform', form.errors)
    
    def test_content_widget_is_textarea(self):
        """Test content field uses textarea widget."""
        form = PostForm()
        widget = form.fields['content'].widget
        self.assertEqual(widget.__class__.__name__, 'Textarea')
    
    def test_scheduled_for_widget_is_datetime_input(self):
        """Test scheduled_for field uses datetime-local input."""
        form = PostForm()
        widget = form.fields['scheduled_for'].widget
        self.assertEqual(widget.input_type, 'datetime-local')
    
    def test_image_field_is_optional(self):
        """Test image field is not required."""
        form_data = {
            'content': 'Test post without image',
            'platform': 'twitter',
            'scheduled_for': timezone.now() + timedelta(days=1),
        }
        form = PostForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_labels(self):
        """Test form has correct labels."""
        form = PostForm()
        
        self.assertEqual(form.fields['content'].label, 'Post Content')
        self.assertEqual(form.fields['image'].label, 'Image (optional)')
        self.assertEqual(form.fields['scheduled_for'].label, 'Schedule For')
