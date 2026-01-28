"""App configuration for scheduler."""

from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    """Configuration for the scheduler application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'
    verbose_name = 'Social Media Scheduler'
