"""
Tests for the scheduler app views.

Tests cover:
- Authentication requirements
- Dashboard view and analytics
- Calendar view functionality
- Post CRUD operations
- User settings management
- Multi-tenancy (user isolation)
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from scheduler.models import Post, UserSettings


class BaseViewTest(TestCase):
    """Base test class with common setup."""
    
    def setUp(self):
        """Create test client and users."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )


class RegisterViewTest(BaseViewTest):
    """Tests for user registration."""
    
    def test_register_page_loads(self):
        """Test registration page is accessible."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
    
    def test_register_success(self):
        """Test successful user registration."""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
        })
        
        # Should redirect to dashboard on success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_register_password_mismatch(self):
        """Test registration fails with password mismatch."""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'complexpass123!',
            'password2': 'differentpass123!',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())


class DashboardViewTest(BaseViewTest):
    """Tests for the dashboard view."""
    
    def test_dashboard_requires_login(self):
        """Test dashboard redirects unauthenticated users."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_dashboard_loads_for_authenticated_user(self):
        """Test dashboard loads for logged in users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_context_has_required_keys(self):
        """Test dashboard context contains expected keys."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        
        # Check required context keys from the view
        expected_keys = [
            'total_posts', 'total_impressions', 'total_likes',
            'total_comments', 'total_clicks', 'engagement_rate',
            'recent_posts', 'draft_count', 'scheduled_count', 'published_count'
        ]
        
        for key in expected_keys:
            self.assertIn(key, response.context)
    
    def test_dashboard_empty_state(self):
        """Test dashboard handles empty state correctly."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.context['total_posts'], 0)
        self.assertEqual(response.context['total_impressions'], 0)
    
    def test_dashboard_aggregates_user_posts_only(self):
        """Test dashboard only aggregates current user's posts."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create posts for test user
        Post.objects.create(
            user=self.user,
            content='My post',
            scheduled_for=timezone.now() + timedelta(days=1),
            status=Post.Status.PUBLISHED,
            metrics={'impressions': 100, 'likes': 10, 'comments': 5, 'clicks': 20}
        )
        
        # Create post for other user
        Post.objects.create(
            user=self.other_user,
            content='Other user post',
            scheduled_for=timezone.now() + timedelta(days=1),
            status=Post.Status.PUBLISHED,
            metrics={'impressions': 500, 'likes': 50, 'comments': 25, 'clicks': 100}
        )
        
        response = self.client.get(reverse('dashboard'))
        
        # Should only include test user's metrics
        self.assertEqual(response.context['total_posts'], 1)
        self.assertEqual(response.context['total_impressions'], 100)
        self.assertEqual(response.context['total_likes'], 10)


class CalendarViewTest(BaseViewTest):
    """Tests for the calendar view."""
    
    def test_calendar_requires_login(self):
        """Test calendar redirects unauthenticated users."""
        response = self.client.get(reverse('calendar'))
        self.assertEqual(response.status_code, 302)
    
    def test_calendar_loads_month_view(self):
        """Test calendar loads monthly view by default."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('calendar'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['view_mode'], 'month')
    
    def test_calendar_week_view(self):
        """Test calendar can load weekly view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('calendar'), {'view': 'week'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['view_mode'], 'week')
    
    def test_calendar_navigation(self):
        """Test calendar supports year/month navigation."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('calendar'), {
            'year': 2026,
            'month': 6,
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['year'], 2026)
        self.assertEqual(response.context['month'], 6)


class PostCreateViewTest(BaseViewTest):
    """Tests for post creation."""
    
    def test_post_create_requires_login(self):
        """Test post creation requires authentication."""
        response = self.client.get(reverse('post_create'))
        self.assertEqual(response.status_code, 302)
    
    def test_post_create_modal_loads(self):
        """Test post creation modal loads."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('post_create'))
        
        self.assertEqual(response.status_code, 200)
    
    def test_post_create_success(self):
        """Test successful post creation."""
        self.client.login(username='testuser', password='testpass123')
        
        scheduled_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('post_create'), {
            'content': 'New test post',
            'platform': 'twitter',
            'scheduled_for': scheduled_time,
        })
        
        # Post should be created
        self.assertTrue(Post.objects.filter(content='New test post').exists())
    
    def test_post_create_with_date_prefill(self):
        """Test post creation with pre-filled date."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(
            reverse('post_create_date', kwargs={'year': 2026, 'month': 2, 'day': 15})
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_post_assigned_to_current_user(self):
        """Test created post is assigned to current user."""
        self.client.login(username='testuser', password='testpass123')
        
        scheduled_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(reverse('post_create'), {
            'content': 'User post',
            'platform': 'twitter',
            'scheduled_for': scheduled_time,
        })
        
        post = Post.objects.filter(content='User post').first()
        self.assertIsNotNone(post)
        self.assertEqual(post.user, self.user)
    
    def test_post_created_as_scheduled(self):
        """Test created post has scheduled status."""
        self.client.login(username='testuser', password='testpass123')
        
        scheduled_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(reverse('post_create'), {
            'content': 'Scheduled post',
            'platform': 'twitter',
            'scheduled_for': scheduled_time,
        })
        
        post = Post.objects.get(content='Scheduled post')
        self.assertEqual(post.status, Post.Status.SCHEDULED)


class PostDetailViewTest(BaseViewTest):
    """Tests for post detail view."""
    
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            user=self.user,
            content='Test post for detail',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
    
    def test_post_detail_requires_login(self):
        """Test post detail requires authentication."""
        response = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 302)
    
    def test_post_detail_loads(self):
        """Test post detail page loads."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        
        self.assertEqual(response.status_code, 200)
    
    def test_post_detail_user_isolation(self):
        """Test user cannot view another user's post details."""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        
        # Should return 404 for other user's post
        self.assertEqual(response.status_code, 404)


class PostEditViewTest(BaseViewTest):
    """Tests for post editing."""
    
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            user=self.user,
            content='Original content',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
    
    def test_post_edit_requires_login(self):
        """Test post edit requires authentication."""
        response = self.client.get(reverse('post_edit', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 302)
    
    def test_post_edit_loads(self):
        """Test post edit form loads."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('post_edit', kwargs={'pk': self.post.pk}))
        
        self.assertEqual(response.status_code, 200)
    
    def test_post_edit_success(self):
        """Test successful post edit."""
        self.client.login(username='testuser', password='testpass123')
        
        scheduled_time = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('post_edit', kwargs={'pk': self.post.pk}), {
            'content': 'Updated content',
            'platform': 'instagram',
            'scheduled_for': scheduled_time,
        })
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, 'Updated content')
        self.assertEqual(self.post.platform, 'instagram')
    
    def test_post_edit_user_isolation(self):
        """Test user cannot edit another user's post."""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('post_edit', kwargs={'pk': self.post.pk}))
        
        self.assertEqual(response.status_code, 404)


class PostDeleteViewTest(BaseViewTest):
    """Tests for post deletion."""
    
    def setUp(self):
        super().setUp()
        self.post = Post.objects.create(
            user=self.user,
            content='Post to delete',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
    
    def test_post_delete_requires_login(self):
        """Test post delete requires authentication."""
        response = self.client.post(reverse('post_delete', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 302)
    
    def test_post_delete_success(self):
        """Test successful post deletion."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('post_delete', kwargs={'pk': self.post.pk}))
        
        # Should redirect after deletion
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())
    
    def test_post_delete_user_isolation(self):
        """Test user cannot delete another user's post."""
        self.client.login(username='otheruser', password='testpass123')
        
        response = self.client.post(reverse('post_delete', kwargs={'pk': self.post.pk}))
        
        # Should return 404 and post should still exist
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())
    
    def test_post_delete_get_shows_confirmation(self):
        """Test GET request shows delete confirmation."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('post_delete', kwargs={'pk': self.post.pk}))
        
        self.assertEqual(response.status_code, 200)
        # Post should still exist
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())


class UserSettingsViewTest(BaseViewTest):
    """Tests for user settings view."""
    
    def test_settings_requires_login(self):
        """Test settings page requires authentication."""
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 302)
    
    def test_settings_loads(self):
        """Test settings page loads."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('settings'))
        
        self.assertEqual(response.status_code, 200)
    
    def test_settings_creates_user_settings(self):
        """Test visiting settings creates UserSettings if not exists."""
        self.client.login(username='testuser', password='testpass123')
        
        # UserSettings should not exist yet
        self.assertFalse(UserSettings.objects.filter(user=self.user).exists())
        
        self.client.get(reverse('settings'))
        
        # UserSettings should be created
        self.assertTrue(UserSettings.objects.filter(user=self.user).exists())
    
    def test_settings_save_api_key(self):
        """Test saving API key through settings form."""
        self.client.login(username='testuser', password='testpass123')
        
        # Use correct form fields as per view implementation
        response = self.client.post(reverse('settings'), {
            'action': 'save_api_key',
            'openai_api_key': 'test-api-key-12345',
        })
        
        # Should redirect after save
        self.assertEqual(response.status_code, 302)
        
        settings = UserSettings.objects.get(user=self.user)
        self.assertTrue(settings.has_api_key)
        self.assertEqual(settings.get_api_key(), 'test-api-key-12345')
    
    def test_settings_remove_api_key(self):
        """Test removing API key through settings."""
        self.client.login(username='testuser', password='testpass123')
        
        # First save a key
        settings = UserSettings.objects.create(user=self.user)
        settings.set_api_key('my-key')
        settings.save()
        
        # Now remove it
        response = self.client.post(reverse('settings'), {
            'action': 'remove_api_key',
        })
        
        settings.refresh_from_db()
        self.assertFalse(settings.has_api_key)


class AIImageGenerationViewTest(BaseViewTest):
    """Tests for AI image generation endpoint."""
    
    def test_generate_image_requires_login(self):
        """Test AI image generation requires authentication."""
        response = self.client.post(reverse('generate_ai_image'), {'prompt': 'A sunset'})
        self.assertEqual(response.status_code, 302)
    
    def test_generate_image_missing_prompt(self):
        """Test image generation fails without prompt."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('generate_ai_image'), {})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_generate_image_empty_prompt(self):
        """Test image generation fails with empty prompt."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('generate_ai_image'), {'prompt': '   '})
        
        self.assertEqual(response.status_code, 400)
    
    @patch('scheduler.views.requests.get')
    def test_generate_image_pollinations_fallback(self, mock_get):
        """Test image generation uses Pollinations as fallback."""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'\x89PNG\r\n\x1a\n fake image data'
        mock_get.return_value = mock_response
        
        response = self.client.post(
            reverse('generate_ai_image'),
            {'prompt': 'A beautiful sunset'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('image_url', data)
