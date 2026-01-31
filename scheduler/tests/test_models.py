"""
Tests for the scheduler app models.

Tests cover:
- Post model creation, validation, and properties
- UserSettings model with API key encryption/decryption
- Multi-tenancy (user scoping)
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from scheduler.models import Post, UserSettings


class PostModelTest(TestCase):
    """Tests for the Post model."""
    
    def setUp(self):
        """Create a test user for all tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_post(self):
        """Test that a post can be created with required fields."""
        scheduled_time = timezone.now() + timedelta(days=1)
        post = Post.objects.create(
            user=self.user,
            content='Test post content',
            scheduled_for=scheduled_time,
        )
        
        self.assertEqual(post.content, 'Test post content')
        self.assertEqual(post.user, self.user)
        self.assertEqual(post.status, Post.Status.DRAFT)
        self.assertEqual(post.platform, Post.Platform.TWITTER)
        self.assertIsNotNone(post.created_at)
        self.assertIsNotNone(post.updated_at)
    
    def test_post_str_short_content(self):
        """Test string representation for short content."""
        post = Post.objects.create(
            user=self.user,
            content='Short',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(str(post), 'Short')
    
    def test_post_str_long_content(self):
        """Test string representation truncates long content."""
        long_content = 'A' * 100
        post = Post.objects.create(
            user=self.user,
            content=long_content,
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(str(post), 'A' * 50 + '...')
    
    def test_default_metrics_initialization(self):
        """Test that metrics are initialized with default values on save."""
        post = Post.objects.create(
            user=self.user,
            content='Test metrics',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        
        expected_metrics = {'impressions': 0, 'likes': 0, 'comments': 0, 'clicks': 0}
        self.assertEqual(post.metrics, expected_metrics)
    
    def test_custom_metrics_preserved(self):
        """Test that custom metrics are preserved on save."""
        custom_metrics = {'impressions': 100, 'likes': 50, 'comments': 10, 'clicks': 25}
        post = Post.objects.create(
            user=self.user,
            content='Test custom metrics',
            scheduled_for=timezone.now() + timedelta(days=1),
            metrics=custom_metrics
        )
        
        self.assertEqual(post.metrics, custom_metrics)
    
    def test_is_past_due_future(self):
        """Test is_past_due returns False for future posts."""
        post = Post.objects.create(
            user=self.user,
            content='Future post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        self.assertFalse(post.is_past_due)
    
    def test_is_past_due_past(self):
        """Test is_past_due returns True for past posts."""
        post = Post.objects.create(
            user=self.user,
            content='Past post',
            scheduled_for=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(post.is_past_due)
    
    def test_is_ready_to_publish(self):
        """Test is_ready_to_publish for scheduled past due post."""
        post = Post.objects.create(
            user=self.user,
            content='Ready to publish',
            scheduled_for=timezone.now() - timedelta(hours=1),
            status=Post.Status.SCHEDULED,
        )
        self.assertTrue(post.is_ready_to_publish)
    
    def test_is_not_ready_to_publish_draft(self):
        """Test is_ready_to_publish returns False for draft posts."""
        post = Post.objects.create(
            user=self.user,
            content='Draft post',
            scheduled_for=timezone.now() - timedelta(hours=1),
            status=Post.Status.DRAFT,
        )
        self.assertFalse(post.is_ready_to_publish)
    
    def test_is_not_ready_to_publish_future(self):
        """Test is_ready_to_publish returns False for future scheduled posts."""
        post = Post.objects.create(
            user=self.user,
            content='Future scheduled',
            scheduled_for=timezone.now() + timedelta(days=1),
            status=Post.Status.SCHEDULED,
        )
        self.assertFalse(post.is_ready_to_publish)
    
    def test_engagement_score_calculation(self):
        """Test engagement score is calculated correctly."""
        post = Post.objects.create(
            user=self.user,
            content='Engagement test',
            scheduled_for=timezone.now() + timedelta(days=1),
            metrics={
                'impressions': 1000,  # 1000 * 0.5 = 500
                'clicks': 50,         # 50 * 1.0 = 50
                'likes': 100,         # 100 * 1.0 = 100
                'comments': 25,       # 25 * 2.0 = 50
            }
        )
        # Total: 500 + 50 + 100 + 50 = 700
        self.assertEqual(post.engagement_score, 700.0)
    
    def test_engagement_score_empty_metrics(self):
        """Test engagement score with default empty metrics."""
        post = Post.objects.create(
            user=self.user,
            content='Empty metrics',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(post.engagement_score, 0.0)
    
    def test_engagement_rate_calculation(self):
        """Test engagement rate is calculated correctly."""
        post = Post.objects.create(
            user=self.user,
            content='Rate test',
            scheduled_for=timezone.now() + timedelta(days=1),
            metrics={
                'impressions': 1000,
                'clicks': 50,
                'likes': 100,
                'comments': 25,
            }
        )
        # Rate: ((100 + 25 + 50) / 1000) * 100 = 17.5%
        self.assertEqual(post.engagement_rate, 17.5)
    
    def test_engagement_rate_zero_impressions(self):
        """Test engagement rate returns 0 when no impressions."""
        post = Post.objects.create(
            user=self.user,
            content='Zero impressions',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(post.engagement_rate, 0.0)
    
    def test_post_ordering(self):
        """Test posts are ordered by scheduled_for descending."""
        post1 = Post.objects.create(
            user=self.user,
            content='First post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        post2 = Post.objects.create(
            user=self.user,
            content='Second post',
            scheduled_for=timezone.now() + timedelta(days=3),
        )
        post3 = Post.objects.create(
            user=self.user,
            content='Third post',
            scheduled_for=timezone.now() + timedelta(days=2),
        )
        
        posts = list(Post.objects.all())
        self.assertEqual(posts[0], post2)  # Day 3 - most recent scheduled
        self.assertEqual(posts[1], post3)  # Day 2
        self.assertEqual(posts[2], post1)  # Day 1
    
    def test_platform_choices(self):
        """Test all platform choices are valid."""
        platforms = [
            Post.Platform.TWITTER,
            Post.Platform.INSTAGRAM,
            Post.Platform.FACEBOOK,
            Post.Platform.LINKEDIN,
            Post.Platform.TIKTOK,
        ]
        
        for platform in platforms:
            post = Post.objects.create(
                user=self.user,
                content=f'Test {platform}',
                scheduled_for=timezone.now() + timedelta(days=1),
                platform=platform,
            )
            self.assertEqual(post.platform, platform)
    
    def test_status_choices(self):
        """Test all status choices are valid."""
        statuses = [
            Post.Status.DRAFT,
            Post.Status.SCHEDULED,
            Post.Status.PUBLISHED,
        ]
        
        for status in statuses:
            post = Post.objects.create(
                user=self.user,
                content=f'Test {status}',
                scheduled_for=timezone.now() + timedelta(days=1),
                status=status,
            )
            self.assertEqual(post.status, status)
    
    def test_multi_tenancy_user_posts(self):
        """Test that posts are correctly scoped to users."""
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        Post.objects.create(
            user=self.user,
            content='User 1 post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        Post.objects.create(
            user=user2,
            content='User 2 post',
            scheduled_for=timezone.now() + timedelta(days=1),
        )
        
        user1_posts = Post.objects.filter(user=self.user)
        user2_posts = Post.objects.filter(user=user2)
        
        self.assertEqual(user1_posts.count(), 1)
        self.assertEqual(user2_posts.count(), 1)
        self.assertEqual(user1_posts.first().content, 'User 1 post')
        self.assertEqual(user2_posts.first().content, 'User 2 post')


class UserSettingsModelTest(TestCase):
    """Tests for the UserSettings model."""
    
    def setUp(self):
        """Create a test user for all tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_user_settings(self):
        """Test that user settings can be created."""
        settings = UserSettings.objects.create(user=self.user)
        
        self.assertEqual(settings.user, self.user)
        self.assertIsNone(settings.gemini_api_key_encrypted)
        self.assertIsNotNone(settings.created_at)
        self.assertIsNotNone(settings.updated_at)
    
    def test_user_settings_str(self):
        """Test string representation."""
        settings = UserSettings.objects.create(user=self.user)
        self.assertEqual(str(settings), 'Settings for testuser')
    
    def test_set_and_get_api_key(self):
        """Test that API key can be set and retrieved."""
        settings = UserSettings.objects.create(user=self.user)
        
        test_api_key = 'test-api-key-12345'
        settings.set_api_key(test_api_key)
        settings.save()
        
        # Refresh from database
        settings.refresh_from_db()
        
        retrieved_key = settings.get_api_key()
        self.assertEqual(retrieved_key, test_api_key)
    
    def test_set_empty_api_key(self):
        """Test that setting empty API key clears it."""
        settings = UserSettings.objects.create(user=self.user)
        
        # Set a key first
        settings.set_api_key('some-key')
        settings.save()
        
        # Clear it
        settings.set_api_key('')
        settings.save()
        
        self.assertIsNone(settings.gemini_api_key_encrypted)
    
    def test_set_none_api_key(self):
        """Test that setting None API key clears it."""
        settings = UserSettings.objects.create(user=self.user)
        
        settings.set_api_key('some-key')
        settings.save()
        
        settings.set_api_key(None)
        settings.save()
        
        self.assertIsNone(settings.gemini_api_key_encrypted)
    
    def test_has_api_key_with_stored_key(self):
        """Test has_api_key returns True when key is stored."""
        settings = UserSettings.objects.create(user=self.user)
        settings.set_api_key('test-key')
        settings.save()
        
        self.assertTrue(settings.has_api_key)
    
    def test_has_api_key_without_key(self):
        """Test has_api_key returns False when no key is set."""
        settings = UserSettings.objects.create(user=self.user)
        self.assertFalse(settings.has_api_key)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env-api-key'})
    def test_has_api_key_from_environment(self):
        """Test has_api_key returns True when env var is set."""
        settings = UserSettings.objects.create(user=self.user)
        self.assertTrue(settings.has_api_key)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env-api-key'})
    def test_get_api_key_fallback_to_env(self):
        """Test get_api_key falls back to environment variable."""
        settings = UserSettings.objects.create(user=self.user)
        self.assertEqual(settings.get_api_key(), 'env-api-key')
    
    def test_api_key_source_stored(self):
        """Test api_key_source returns 'stored' when key is encrypted."""
        settings = UserSettings.objects.create(user=self.user)
        settings.set_api_key('test-key')
        settings.save()
        
        self.assertEqual(settings.api_key_source, 'stored')
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env-api-key'})
    def test_api_key_source_environment(self):
        """Test api_key_source returns 'environment' when only env var is set."""
        settings = UserSettings.objects.create(user=self.user)
        self.assertEqual(settings.api_key_source, 'environment')
    
    def test_api_key_source_none(self):
        """Test api_key_source returns 'none' when no key is configured."""
        settings = UserSettings.objects.create(user=self.user)
        self.assertEqual(settings.api_key_source, 'none')
    
    def test_one_to_one_relationship(self):
        """Test that UserSettings has one-to-one relationship with User."""
        settings = UserSettings.objects.create(user=self.user)
        
        # Access settings via user's related name
        self.assertEqual(self.user.settings, settings)
    
    def test_api_key_encryption(self):
        """Test that API key is actually encrypted (not stored as plaintext)."""
        settings = UserSettings.objects.create(user=self.user)
        
        test_api_key = 'my-secret-api-key'
        settings.set_api_key(test_api_key)
        settings.save()
        
        # The encrypted value should not contain the plaintext key
        encrypted_bytes = bytes(settings.gemini_api_key_encrypted)
        self.assertNotIn(test_api_key.encode(), encrypted_bytes)
