"""
Post model for Social Media Scheduler.

This module defines the core Post model which stores all social media posts
for users. Each post is scoped to a specific user for multi-tenancy.
"""

from typing import Optional
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Post(models.Model):
    """
    Represents a social media post that can be drafted, scheduled, or published.
    
    Multi-tenancy: Each post belongs to exactly one user via the `user` ForeignKey.
    All queries should filter by user to ensure data isolation.
    
    Attributes:
        user: The owner of this post (ForeignKey to auth.User)
        content: The text content of the post
        image: Optional image attachment (uploaded or AI-generated)
        scheduled_for: When the post should be published
        status: Current state - 'draft', 'scheduled', or 'published'
        metrics: JSON field storing engagement data (likes, views, etc.)
        created_at: Timestamp when post was created
        updated_at: Timestamp of last modification
    """
    
    class Status(models.TextChoices):
        """Available status choices for a post."""
        DRAFT = 'draft', 'Draft'
        SCHEDULED = 'scheduled', 'Scheduled'
        PUBLISHED = 'published', 'Published'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        help_text='Owner of this post'
    )
    content = models.TextField(
        help_text='The text content of the social media post'
    )
    image = models.ImageField(
        upload_to='post_images/',
        blank=True,
        null=True,
        help_text='Optional image for the post'
    )
    scheduled_for = models.DateTimeField(
        help_text='When this post should be published'
    )
    
    class Platform(models.TextChoices):
        """Social media platforms for posting."""
        TWITTER = 'twitter', 'Twitter/X'
        INSTAGRAM = 'instagram', 'Instagram'
        FACEBOOK = 'facebook', 'Facebook'
        LINKEDIN = 'linkedin', 'LinkedIn'
        TIKTOK = 'tiktok', 'TikTok'
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text='Current status of the post'
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        default=Platform.TWITTER,
        help_text='Target social media platform'
    )
    metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text='Engagement metrics: {"impressions": 0, "likes": 0, "comments": 0, "clicks": 0}'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_for']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
    
    def __str__(self):
        """Return a truncated version of the content for display."""
        return f"{self.content[:50]}..." if len(self.content) > 50 else self.content
    
    def save(self, *args, **kwargs):
        """Initialize metrics with default values if empty."""
        if not self.metrics:
            self.metrics = {'impressions': 0, 'likes': 0, 'comments': 0, 'clicks': 0}
        super().save(*args, **kwargs)
    
    @property
    def is_past_due(self):
        """Check if the scheduled time has passed."""
        return self.scheduled_for <= timezone.now()
    
    @property
    def is_ready_to_publish(self):
        """Check if post is scheduled and ready to be published."""
        return self.status == self.Status.SCHEDULED and self.is_past_due
    
    @property
    def engagement_score(self):
        """
        Calculate engagement score using weighted formula.
        
        Weights:
        - Impressions: 0.5
        - Clicks: 1.0
        - Likes: 1.0  
        - Comments: 2.0
        
        Returns:
            float: The weighted engagement score
        """
        impressions = self.metrics.get('impressions', 0)
        clicks = self.metrics.get('clicks', 0)
        likes = self.metrics.get('likes', 0)
        comments = self.metrics.get('comments', 0)
        
        return (impressions * 0.5) + (clicks * 1.0) + (likes * 1.0) + (comments * 2.0)
    
    @property
    def engagement_rate(self):
        """
        Calculate engagement rate as a percentage of impressions.
        
        Formula: ((likes + comments + clicks) / impressions) * 100
        
        Returns:
            float: Engagement rate percentage, or 0 if no impressions
        """
        impressions = self.metrics.get('impressions', 0)
        if impressions == 0:
            return 0.0
        
        clicks = self.metrics.get('clicks', 0)
        likes = self.metrics.get('likes', 0)
        comments = self.metrics.get('comments', 0)
        
        return ((likes + comments + clicks) / impressions) * 100


class UserSettings(models.Model):
    """
    User settings for the Social Media Scheduler.
    
    Stores per-user configuration, including encrypted API keys.
    Uses Fernet symmetric encryption for API key storage at rest.
    
    Attributes:
        user: One-to-one relationship with auth.User
        gemini_api_key_encrypted: Encrypted Gemini API key
        created_at: Timestamp when settings were created
        updated_at: Timestamp of last modification
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings',
        help_text='User these settings belong to'
    )
    gemini_api_key_encrypted = models.BinaryField(
        blank=True,
        null=True,
        help_text='Encrypted Gemini API key'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Settings'
        verbose_name_plural = 'User Settings'
    
    def __str__(self):
        return f"Settings for {self.user.username}"
    
    @staticmethod
    def _get_encryption_key():
        """
        Get or generate the encryption key for API keys.
        
        Uses Django's SECRET_KEY to derive a Fernet-compatible key.
        In production, consider using a separate encryption key.
        """
        from django.conf import settings
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        # Derive a key from Django's SECRET_KEY
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'postpilot_api_key_salt',  # Static salt for consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        return Fernet(key)
    
    def set_api_key(self, api_key: str):
        """
        Encrypt and store the Google API key.
        
        Args:
            api_key: The plaintext API key to encrypt and store
        """
        if api_key:
            fernet = self._get_encryption_key()
            self.gemini_api_key_encrypted = fernet.encrypt(api_key.encode())
        else:
            self.gemini_api_key_encrypted = None
    
    def get_api_key(self) -> Optional[str]:
        """
        Decrypt and return the Google API key.
        
        Returns:
            The decrypted API key, or None if not set
        """
        import os
        
        # First try the stored encrypted key
        if self.gemini_api_key_encrypted:
            try:
                fernet = self._get_encryption_key()
                return fernet.decrypt(bytes(self.gemini_api_key_encrypted)).decode()
            except Exception:
                return None
        
        # Fall back to environment variable
        return os.environ.get('OPENAI_API_KEY')
    
    @property
    def has_api_key(self):
        """Check if an API key is configured (either stored or via env var)."""
        import os
        return bool(self.gemini_api_key_encrypted) or bool(os.environ.get('OPENAI_API_KEY'))
    
    @property
    def api_key_source(self):
        """Return the source of the API key for display purposes."""
        import os
        if self.gemini_api_key_encrypted:
            return 'stored'
        elif os.environ.get('OPENAI_API_KEY'):
            return 'environment'
        return 'none'
