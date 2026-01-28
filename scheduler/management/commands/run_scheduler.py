"""
Scheduler management command for processing scheduled posts.

This command checks for posts that are due to be published and updates
their status accordingly. It also generates mock engagement metrics.

Usage:
    python manage.py run_scheduler

This should be run periodically (e.g., via cron job every minute) in production.
"""

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from scheduler.models import Post


class Command(BaseCommand):
    """
    Django management command to process scheduled posts.
    
    Finds all posts with status='scheduled' and scheduled_for <= now,
    then updates them to 'published' status with mocked engagement metrics.
    """
    
    help = 'Process scheduled posts and update their status to published'
    
    def add_arguments(self, parser):
        """Add optional command arguments."""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be published without making changes',
        )
    
    def handle(self, *args, **options):
        """
        Main command execution.
        
        1. Query for posts ready to be published
        2. Update status to 'published'
        3. Generate random engagement metrics
        4. Report results
        """
        dry_run = options.get('dry_run', False)
        now = timezone.now()
        
        # Find posts that are scheduled and past due
        posts_to_publish = Post.objects.filter(
            status=Post.Status.SCHEDULED,
            scheduled_for__lte=now
        )
        
        count = posts_to_publish.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No posts to publish at this time.')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Would publish {count} post(s):')
            )
            for post in posts_to_publish:
                self.stdout.write(f'  - {post.id}: {post.content[:50]}...')
            return
        
        # Process each post
        published_count = 0
        for post in posts_to_publish:
            # Update status
            post.status = Post.Status.PUBLISHED
            
            # Generate mock engagement metrics
            # In production, these would come from actual social media APIs
            impressions = random.randint(500, 10000)
            post.metrics = {
                'impressions': impressions,
                'likes': random.randint(10, int(impressions * 0.1)),
                'comments': random.randint(0, int(impressions * 0.02)),
                'clicks': random.randint(5, int(impressions * 0.05)),
            }
            
            post.save()
            published_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Published: {post.content[:40]}... '
                    f'(Impressions: {post.metrics["impressions"]}, Likes: {post.metrics["likes"]})'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully published {published_count} post(s).')
        )
