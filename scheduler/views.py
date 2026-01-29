"""
Views for the Social Media Scheduler app.

All views are protected with @login_required and scope data to the current user.
HTMX is used for modal interactions and partial page updates.
"""

import os
import calendar
import time
import random
import requests
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
from django.contrib import messages

from .models import Post, UserSettings
from .forms import PostForm


def register(request):
    """
    Handle user registration.
    
    On successful registration, the user is automatically logged in
    and redirected to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard(request):
    """
    Display the main dashboard with aggregate analytics.
    
    Shows:
    - Total number of posts (all statuses)
    - Aggregated metrics: impressions, likes, comments, clicks
    - Engagement rate (weighted formula)
    - Best performing post
    - Recent posts list
    
    All data is scoped to the current user.
    """
    user_posts = Post.objects.filter(user=request.user)
    published_posts = user_posts.filter(status=Post.Status.PUBLISHED)
    
    # Aggregate metrics from all posts
    total_posts = user_posts.count()
    
    # Sum up metrics from the JSONField
    total_impressions = 0
    total_likes = 0
    total_comments = 0
    total_clicks = 0
    
    best_post = None
    best_engagement_score = 0
    
    for post in published_posts:
        total_impressions += post.metrics.get('impressions', 0)
        total_likes += post.metrics.get('likes', 0)
        total_comments += post.metrics.get('comments', 0)
        total_clicks += post.metrics.get('clicks', 0)
        
        # Track best performing post by engagement score
        if post.engagement_score > best_engagement_score:
            best_engagement_score = post.engagement_score
            best_post = post
    
    # Calculate overall engagement rate
    # Formula: (impressions * 0.5 + clicks * 1 + likes * 1 + comments * 2) / total_impressions * 100
    if total_impressions > 0:
        total_engagement_score = (
            (total_impressions * 0.5) + 
            (total_clicks * 1.0) + 
            (total_likes * 1.0) + 
            (total_comments * 2.0)
        )
        # Normalize by impressions for a percentage-like rate
        engagement_rate = ((total_likes + total_comments + total_clicks) / total_impressions) * 100
    else:
        engagement_rate = 0.0
    
    # Get recent posts for display
    recent_posts = user_posts[:5]
    
    context = {
        'total_posts': total_posts,
        'total_impressions': total_impressions,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'total_clicks': total_clicks,
        'engagement_rate': round(engagement_rate, 2),
        'best_post': best_post,
        'recent_posts': recent_posts,
        'draft_count': user_posts.filter(status=Post.Status.DRAFT).count(),
        'scheduled_count': user_posts.filter(status=Post.Status.SCHEDULED).count(),
        'published_count': published_posts.count(),
    }
    
    return render(request, 'scheduler/dashboard.html', context)


@login_required
def calendar_view(request):
    """
    Display a calendar view with scheduled posts.
    
    Supports two view modes:
    - Monthly: Full month grid view (default)
    - Weekly: Detailed 7-day view with time slots
    
    Query params:
    - view: 'month' or 'week' (default: 'month')
    - year: Year to display (default: current year)
    - month: Month to display (default: current month)
    - week_start: ISO format date for week start (weekly view only)
    """
    today = timezone.now().date()
    view_mode = request.GET.get('view', 'month')
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    if view_mode == 'week':
        # Weekly view logic
        week_start_str = request.GET.get('week_start')
        if week_start_str:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        else:
            # Default to current week (starting Sunday)
            days_since_sunday = (today.weekday() + 1) % 7
            week_start = today - timedelta(days=days_since_sunday)
        
        week_end = week_start + timedelta(days=6)
        
        # Generate week days
        week_days = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            week_days.append({
                'date': day_date,
                'day': day_date.day,
                'month': day_date.month,
                'year': day_date.year,
                'weekday': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][i],
                'is_today': day_date == today,
            })
        
        # Get posts for this week
        week_start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        week_end_dt = datetime.combine(week_end + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
        
        posts = Post.objects.filter(
            user=request.user,
            scheduled_for__gte=week_start_dt,
            scheduled_for__lt=week_end_dt
        ).order_by('scheduled_for')
        
        # Group posts by day
        posts_by_day = {}
        for post in posts:
            day_key = post.scheduled_for.date()
            if day_key not in posts_by_day:
                posts_by_day[day_key] = []
            posts_by_day[day_key].append(post)
        
        # Calculate prev/next week
        prev_week_start = week_start - timedelta(days=7)
        next_week_start = week_start + timedelta(days=7)
        
        context = {
            'view_mode': 'week',
            'week_days': week_days,
            'week_start': week_start,
            'week_end': week_end,
            'posts_by_day': posts_by_day,
            'prev_week_start': prev_week_start.strftime('%Y-%m-%d'),
            'next_week_start': next_week_start.strftime('%Y-%m-%d'),
            'today': today,
            'year': year,
            'month': month,
        }
        
        return render(request, 'scheduler/calendar.html', context)
    
    else:
        # Monthly view logic (existing)
        cal = calendar.Calendar(firstweekday=6)  # Sunday start
        month_days = cal.monthdayscalendar(year, month)
        
        # Get posts for this month, scoped to user
        first_day = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            last_day = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            last_day = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        posts = Post.objects.filter(
            user=request.user,
            scheduled_for__gte=first_day,
            scheduled_for__lt=last_day
        )
        
        # Group posts by day
        posts_by_day = {}
        for post in posts:
            day = post.scheduled_for.day
            if day not in posts_by_day:
                posts_by_day[day] = []
            posts_by_day[day].append(post)
        
        # Calculate prev/next month
        if month == 1:
            prev_month, prev_year = 12, year - 1
        else:
            prev_month, prev_year = month - 1, year
        
        if month == 12:
            next_month, next_year = 1, year + 1
        else:
            next_month, next_year = month + 1, year
        
        context = {
            'view_mode': 'month',
            'month_days': month_days,
            'month_name': calendar.month_name[month],
            'year': year,
            'month': month,
            'today': today,
            'posts_by_day': posts_by_day,
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
            'weekdays': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        }
        
        return render(request, 'scheduler/calendar.html', context)


@login_required
def post_modal(request, year=None, month=None, day=None):
    """
    Return the post creation modal as an HTMX partial.
    
    This view handles both:
    - GET: Display the empty form modal
    - POST: Process form submission and create the post
    
    Args:
        year, month, day: Optional date to pre-fill the scheduled_for field
    """
    # Set default date if provided
    initial = {}
    if year and month and day:
        scheduled_date = datetime(year, month, day, 9, 0)  # Default to 9 AM
        initial['scheduled_for'] = scheduled_date.strftime('%Y-%m-%dT%H:%M')
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.status = Post.Status.SCHEDULED
            
            # Handle AI-generated image if provided
            generated_image_url = request.POST.get('generated_image_url', '')
            if generated_image_url and not request.FILES.get('image'):
                try:
                    import os
                    from django.conf import settings
                    from django.core.files.base import ContentFile
                    
                    # Check if it's a local media URL
                    if generated_image_url.startswith('/media/'):
                        # It's a local file, copy it
                        relative_path = generated_image_url.replace('/media/', '', 1)
                        source_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                        if os.path.exists(source_path):
                            with open(source_path, 'rb') as f:
                                post.image.save(os.path.basename(source_path), ContentFile(f.read()), save=False)
                    else:
                        # It's a remote URL, download it
                        import requests
                        import uuid
                        resp = requests.get(generated_image_url, timeout=30)
                        if resp.status_code == 200:
                            filename = f"ai_generated_{uuid.uuid4().hex[:8]}.png"
                            post.image.save(filename, ContentFile(resp.content), save=False)
                except Exception as e:
                    print(f"Failed to save AI image: {e}")
            
            post.save()
            
            # Return success response that closes modal and refreshes calendar
            response = HttpResponse()
            response['HX-Trigger'] = 'postCreated'
            response['HX-Redirect'] = '/calendar/'
            return response
    else:
        form = PostForm(initial=initial)
    
    return render(request, 'scheduler/partials/post_modal.html', {
        'form': form,
        'year': year,
        'month': month,
        'day': day,
    })


@login_required
@require_POST
def generate_ai_image(request):
    """
    Generate an image using AI.
    
    Uses OpenAI DALL-E if an API key is configured, otherwise falls back
    to Pollinations.ai (free, no API key required).
    
    Takes a text prompt from the request and generates an image.
    The image is downloaded and saved to the media folder.
    
    Returns JSON with the generated image URL or an error message.
    """
    import urllib.parse
    import uuid
    from django.core.files.storage import default_storage
    from django.conf import settings
    
    prompt = request.POST.get('prompt', '').strip()
    
    if not prompt:
        return JsonResponse({
            'success': False,
            'error': 'Please enter a prompt for the image'
        }, status=400)
    
    # Check if user has an API key configured
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    api_key = user_settings.get_api_key()
    
    try:
        image_data = None
        provider_used = None
        
        # Try OpenAI DALL-E if API key is available
        if api_key:
            try:
                from openai import OpenAI
                
                client = OpenAI(api_key=api_key)
                
                # Generate image using DALL-E 2
                response = client.images.generate(
                    model="dall-e-2",
                    prompt=prompt,
                    n=1,
                    size="512x512"
                )
                
                image_url = response.data[0].url
                
                # Download the image
                image_response = requests.get(image_url, timeout=30)
                if image_response.status_code == 200:
                    image_data = image_response.content
                    provider_used = 'OpenAI DALL-E'
                    
            except Exception as openai_error:
                # Log the error but continue to fallback
                print(f"OpenAI error, falling back to Pollinations: {openai_error}")
        
        # Fallback to Pollinations.ai if no API key or OpenAI failed
        if image_data is None:
            encoded_prompt = urllib.parse.quote(prompt)
            pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
            
            image_response = requests.get(pollinations_url, timeout=60)
            
            if image_response.status_code == 200:
                image_data = image_response.content
                provider_used = 'Pollinations.ai'
        
        # Save the image if we got one
        if image_data:
            filename = f"ai_generated_{uuid.uuid4().hex[:8]}.png"
            file_path = f"post_images/{filename}"
            saved_path = default_storage.save(file_path, ContentFile(image_data))
            saved_url = f"{settings.MEDIA_URL}{saved_path}"
            
            return JsonResponse({
                'success': True,
                'image_url': saved_url,
                'message': f'Image generated successfully using {provider_used}!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to generate image. Please try again.'
            }, status=500)
            
    except requests.Timeout:
        return JsonResponse({
            'success': False,
            'error': 'Image generation timed out. Please try again.'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating image: {str(e)}'
        }, status=500)


@login_required
def post_detail(request, pk):
    """
    Display details of a single post.
    
    Ensures the post belongs to the current user.
    """
    post = get_object_or_404(Post, pk=pk, user=request.user)
    return render(request, 'scheduler/post_detail.html', {'post': post})


@login_required
def post_edit(request, pk):
    """
    Edit an existing post.
    
    Handles:
    - GET: Display the edit form with current post data
    - POST: Update the post with new data
    
    Ensures the post belongs to the current user.
    """
    post = get_object_or_404(Post, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            
            # Handle AI-generated image if provided
            ai_image_url = request.POST.get('ai_image_url', '')
            if ai_image_url and not request.FILES.get('image'):
                try:
                    import os
                    from django.conf import settings
                    from django.core.files.base import ContentFile
                    
                    # Check if it's a local media URL
                    if ai_image_url.startswith('/media/'):
                        # It's a local file, copy it
                        relative_path = ai_image_url.replace('/media/', '', 1)
                        source_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                        if os.path.exists(source_path):
                            with open(source_path, 'rb') as f:
                                updated_post.image.save(os.path.basename(source_path), ContentFile(f.read()), save=False)
                    else:
                        # It's a remote URL, download it
                        import requests as req
                        import uuid
                        response = req.get(ai_image_url, timeout=30)
                        if response.status_code == 200:
                            filename = f"ai_generated_{uuid.uuid4().hex[:8]}.png"
                            updated_post.image.save(filename, ContentFile(response.content), save=False)
                except Exception as e:
                    print(f"Failed to save AI image: {e}")
            
            updated_post.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post, initial={
            'scheduled_for': post.scheduled_for.strftime('%Y-%m-%dT%H:%M') if post.scheduled_for else ''
        })
    
    return render(request, 'scheduler/post_edit.html', {
        'form': form,
        'post': post,
    })



@login_required
def post_delete(request, pk):
    """
    Delete a post.
    
    Ensures the post belongs to the current user before deletion.
    """
    post = get_object_or_404(Post, pk=pk, user=request.user)
    
    if request.method == 'POST':
        post.delete()
        return redirect('calendar')
    
    return render(request, 'scheduler/post_confirm_delete.html', {'post': post})


@login_required
def user_settings(request):
    """
    User settings page for managing API keys and preferences.
    
    Handles:
    - GET: Display settings form with masked API key
    - POST: Save/update OpenAI API key (encrypted)
    
    The API key is encrypted at rest using Fernet symmetric encryption
    derived from Django's SECRET_KEY.
    """
    user_settings_obj, created = UserSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_api_key':
            api_key = request.POST.get('openai_api_key', '').strip()
            if api_key:
                user_settings_obj.set_api_key(api_key)
                user_settings_obj.save()
                messages.success(request, 'OpenAI API key saved successfully!')
            else:
                messages.error(request, 'Please enter a valid API key.')
        
        elif action == 'remove_api_key':
            user_settings_obj.set_api_key(None)
            user_settings_obj.save()
            messages.success(request, 'OpenAI API key removed.')
        
        return redirect('settings')
    
    # Mask the API key for display
    masked_key = None
    if user_settings_obj.gemini_api_key_encrypted:
        try:
            full_key = user_settings_obj.get_api_key()
            if full_key:
                masked_key = f"{full_key[:8]}...{full_key[-4:]}"
        except Exception:
            masked_key = "••••••••••••"
    
    context = {
        'settings': user_settings_obj,
        'masked_key': masked_key,
        'has_env_key': bool(os.environ.get('OPENAI_API_KEY')),
    }
    
    return render(request, 'scheduler/settings.html', context)
