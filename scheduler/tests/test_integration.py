"""
Integration tests for the scheduler app.

Tests cover end-to-end user flows and complex interactions.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from scheduler.models import Post, UserSettings


class UserRegistrationFlowTest(TestCase):
    """Test complete user registration and onboarding flow."""
    
    def setUp(self):
        self.client = Client()
    
    def test_complete_registration_to_dashboard_flow(self):
        """Test user can register and access dashboard."""
        # Register
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'securepass123!',
            'password2': 'securepass123!',
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        
        # User should exist
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # User should be logged in (check session)
        self.assertTrue('_auth_user_id' in self.client.session)


class PostLifecycleTest(TestCase):
    """Test complete post lifecycle: create, edit, delete."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_create_edit_delete_flow(self):
        """Test complete post lifecycle."""
        # Create post
        scheduled_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(reverse('post_create'), {
            'content': 'Initial content',
            'platform': 'twitter',
            'scheduled_for': scheduled_time,
        })
        
        post = Post.objects.filter(content='Initial content').first()
        self.assertIsNotNone(post)
        self.assertEqual(post.status, Post.Status.SCHEDULED)
        
        # Edit post
        new_scheduled_time = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(reverse('post_edit', kwargs={'pk': post.pk}), {
            'content': 'Updated content',
            'platform': 'instagram',
            'scheduled_for': new_scheduled_time,
        })
        
        post.refresh_from_db()
        self.assertEqual(post.content, 'Updated content')
        self.assertEqual(post.platform, 'instagram')
        
        # Delete post
        self.client.post(reverse('post_delete', kwargs={'pk': post.pk}))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())
    
    def test_post_appears_in_dashboard_context(self):
        """Test created post is counted in dashboard."""
        scheduled_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.client.post(reverse('post_create'), {
            'content': 'Dashboard post',
            'platform': 'twitter',
            'scheduled_for': scheduled_time,
        })
        
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['total_posts'], 1)
    
    def test_post_appears_in_calendar_context(self):
        """Test scheduled post appears in calendar posts_by_day."""
        tomorrow = timezone.now() + timedelta(days=1)
        scheduled_time = tomorrow.strftime('%Y-%m-%dT%H:%M')
        
        self.client.post(reverse('post_create'), {
            'content': 'Calendar post',
            'platform': 'twitter',
            'scheduled_for': scheduled_time,
        })
        
        response = self.client.get(reverse('calendar'), {
            'year': tomorrow.year,
            'month': tomorrow.month,
        })
        
        # Check the post is in posts_by_day context
        posts_by_day = response.context['posts_by_day']
        day = tomorrow.day
        self.assertIn(day, posts_by_day)
        self.assertEqual(posts_by_day[day][0].content, 'Calendar post')


class MultiTenancyTest(TestCase):
    """Test complete multi-tenancy isolation between users."""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='testpass123'
        )
    
    def test_user_posts_isolated_in_database(self):
        """Test users' posts are isolated when querying."""
        # Create posts for each user directly
        post1 = Post.objects.create(
            user=self.user1,
            content='User 1 secret post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        post2 = Post.objects.create(
            user=self.user2,
            content='User 2 secret post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        
        # Verify isolation via model queries
        user1_posts = Post.objects.filter(user=self.user1)
        user2_posts = Post.objects.filter(user=self.user2)
        
        self.assertEqual(user1_posts.count(), 1)
        self.assertEqual(user2_posts.count(), 1)
        self.assertEqual(user1_posts.first().content, 'User 1 secret post')
        self.assertEqual(user2_posts.first().content, 'User 2 secret post')
    
    def test_user_cannot_access_other_user_post_detail(self):
        """Test user cannot access another user's post via direct URL."""
        # Create post as user1
        post = Post.objects.create(
            user=self.user1,
            content='Private post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        
        # Try to access as user2
        self.client.login(username='user2', password='testpass123')
        
        # Detail view should return 404
        response = self.client.get(reverse('post_detail', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, 404)
    
    def test_user_cannot_edit_other_user_post(self):
        """Test user cannot edit another user's post."""
        post = Post.objects.create(
            user=self.user1,
            content='Original content',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        
        self.client.login(username='user2', password='testpass123')
        
        # Edit view should return 404
        response = self.client.get(reverse('post_edit', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, 404)
        
        # POST to edit should also return 404
        scheduled_time = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(reverse('post_edit', kwargs={'pk': post.pk}), {
            'content': 'Hacked content',
            'platform': 'twitter',
            'scheduled_for': scheduled_time,
        })
        self.assertEqual(response.status_code, 404)
        
        # Verify content unchanged
        post.refresh_from_db()
        self.assertEqual(post.content, 'Original content')
    
    def test_user_cannot_delete_other_user_post(self):
        """Test user cannot delete another user's post."""
        post = Post.objects.create(
            user=self.user1,
            content='Protected post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        
        self.client.login(username='user2', password='testpass123')
        
        # Delete should return 404
        response = self.client.post(reverse('post_delete', kwargs={'pk': post.pk}))
        self.assertEqual(response.status_code, 404)
        
        # Post should still exist
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())


class SettingsFlowTest(TestCase):
    """Test settings management flow."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_api_key_save_and_retrieve(self):
        """Test API key can be saved and retrieved."""
        # Save API key
        self.client.post(reverse('settings'), {
            'action': 'save_api_key',
            'openai_api_key': 'my-test-api-key',
        })
        
        # Verify it's saved
        settings = UserSettings.objects.get(user=self.user)
        self.assertEqual(settings.get_api_key(), 'my-test-api-key')
        self.assertEqual(settings.api_key_source, 'stored')
    
    def test_api_key_update(self):
        """Test API key can be updated."""
        # Save initial key
        self.client.post(reverse('settings'), {
            'action': 'save_api_key',
            'openai_api_key': 'initial-key',
        })
        
        # Update key
        self.client.post(reverse('settings'), {
            'action': 'save_api_key',
            'openai_api_key': 'updated-key',
        })
        
        settings = UserSettings.objects.get(user=self.user)
        self.assertEqual(settings.get_api_key(), 'updated-key')
    
    def test_api_key_removal(self):
        """Test API key can be removed."""
        # Save key first
        self.client.post(reverse('settings'), {
            'action': 'save_api_key',
            'openai_api_key': 'temp-key',
        })
        
        # Remove it
        self.client.post(reverse('settings'), {
            'action': 'remove_api_key',
        })
        
        settings = UserSettings.objects.get(user=self.user)
        self.assertFalse(settings.has_api_key)


class DashboardAnalyticsTest(TestCase):
    """Test dashboard analytics calculations."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_empty_dashboard(self):
        """Test dashboard works with no posts."""
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_posts'], 0)
        self.assertEqual(response.context['total_impressions'], 0)
        self.assertEqual(response.context['engagement_rate'], 0)
    
    def test_dashboard_aggregates_published_metrics(self):
        """Test dashboard aggregates metrics from published posts."""
        # Create multiple published posts with metrics
        Post.objects.create(
            user=self.user,
            content='Post 1',
            scheduled_for=timezone.now() + timedelta(days=1),
            status=Post.Status.PUBLISHED,
            metrics={'impressions': 1000, 'likes': 100, 'comments': 50, 'clicks': 75}
        )
        Post.objects.create(
            user=self.user,
            content='Post 2',
            scheduled_for=timezone.now() + timedelta(days=2),
            status=Post.Status.PUBLISHED,
            metrics={'impressions': 2000, 'likes': 200, 'comments': 100, 'clicks': 150}
        )
        
        response = self.client.get(reverse('dashboard'))
        
        # Aggregate metrics should sum up published posts
        self.assertEqual(response.context['total_impressions'], 3000)
        self.assertEqual(response.context['total_likes'], 300)
        self.assertEqual(response.context['total_comments'], 150)
        self.assertEqual(response.context['total_clicks'], 225)
    
    def test_dashboard_counts_all_posts(self):
        """Test dashboard counts all posts regardless of status."""
        Post.objects.create(
            user=self.user,
            content='Draft',
            scheduled_for=timezone.now() + timedelta(days=1),
            status=Post.Status.DRAFT,
        )
        Post.objects.create(
            user=self.user,
            content='Scheduled',
            scheduled_for=timezone.now() + timedelta(days=2),
            status=Post.Status.SCHEDULED,
        )
        Post.objects.create(
            user=self.user,
            content='Published',
            scheduled_for=timezone.now() - timedelta(days=1),
            status=Post.Status.PUBLISHED,
        )
        
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.context['total_posts'], 3)
        self.assertEqual(response.context['draft_count'], 1)
        self.assertEqual(response.context['scheduled_count'], 1)
        self.assertEqual(response.context['published_count'], 1)
