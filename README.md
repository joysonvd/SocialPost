# PostPilot - Social Media Scheduler

<div align="center">
  <h3>📅 Schedule, Automate & Grow Your Social Presence</h3>
  <p>A lightweight social media scheduling SaaS built with Django, HTMX, and Tailwind CSS</p>
</div>

---

## ✨ Features

### Core Features
- **📊 Dashboard Analytics** - Track impressions, likes, comments, clicks, and engagement rate
- **🗓️ Visual Calendar** - Monthly calendar view with clickable dates for easy scheduling  
- **⚡ HTMX Modals** - Smooth, no-refresh post creation experience
- **🔐 Multi-tenant** - Each user only sees their own data
- **📱 Responsive Design** - Works beautifully on desktop and mobile

### AI Image Generation
- **🤖 OpenAI DALL-E Integration** - Generate images with your API key
- **🆓 Pollinations.ai Fallback** - Free, unlimited image generation when no API key configured
- **🔄 Automatic Provider Switching** - Seamlessly falls back if primary fails

### Post Management
- **📝 Create, Edit, Delete Posts** - Full CRUD operations
- **🎯 Multi-Platform Support** - Twitter/X, Instagram, Facebook, LinkedIn, TikTok
- **⏰ Past Date Warning** - Alerts when scheduling posts in the past
- **🏆 Best Performing Post** - Highlights your top content on dashboard

### Analytics & Metrics
- **�️ Impressions** - Total times your posts were seen
- **❤️ Likes** - Total likes across all posts
- **💬 Comments** - Total comments received
- **🖱️ Clicks** - Total link clicks
- **📈 Engagement Rate** - Calculated as `(Likes + Comments + Clicks) / Impressions × 100`
- **⭐ Engagement Score** - Weighted formula: `Impressions×0.5 + Clicks×1 + Likes×1 + Comments×2`

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone git@github.com:joysonvd/SocialPost.git
cd SocialPost

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser (optional)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

Visit **http://127.0.0.1:8000** and create your account!

### Test User
- **Username:** `testuser`
- **Password:** `TestPass123!`

---

## 🔌 AI Image Generation

PostPilot supports two image generation providers:

### Option 1: OpenAI DALL-E (Paid)
1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Add it in Settings page, or set environment variable:
   ```bash
   export OPENAI_API_KEY="sk-your-api-key"
   ```

### Option 2: Pollinations.ai (Free)
- **No API key required**
- Automatically used when no OpenAI key is configured
- Free and unlimited image generation

> 💡 The app automatically detects which provider to use and tells you in the success message!

---

## 📊 Performance

Profiled on local development server:

| Endpoint | Response Time |
|----------|---------------|
| Dashboard | ~3ms |
| Calendar | ~3ms |
| Settings | ~22ms |
| Login | ~55ms |
| AI Image Generation | ~1.5s (external API) |

Run the profiler yourself:
```bash
python profile_api.py
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (User)                          │
│                   HTMX + Tailwind CSS                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Django Server                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│   │   Views     │  │  Templates  │  │  Management Cmds    │ │
│   │  (SSR)      │  │  (Jinja2)   │  │  (run_scheduler)    │ │
│   └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                    Models                            │   │
│   │   User ←──FK── Post (with Platform & Metrics)       │   │
│   │   User ←──FK── UserSettings (encrypted API keys)    │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │   SQLite DB   │
              │  (db.sqlite3) │
              └───────────────┘
```

---

## 📁 Project Structure

```
SocialPost/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── profile_api.py           # API performance profiler
├── db.sqlite3               # SQLite database (auto-created)
│
├── core/                    # Project configuration
│   ├── settings.py          # Django settings
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI application
│
├── scheduler/               # Main application
│   ├── models.py            # Post, UserSettings models
│   ├── views.py             # Dashboard, Calendar, Post, Settings views
│   ├── forms.py             # PostForm
│   ├── urls.py              # App routes
│   ├── admin.py             # Admin configuration
│   ├── templatetags/        # Custom template filters
│   └── management/
│       └── commands/
│           └── run_scheduler.py  # Background job
│
├── templates/               # HTML templates
│   ├── base.html            # Base layout
│   ├── registration/        # Login/Register
│   └── scheduler/           # App templates
│       ├── dashboard.html
│       ├── calendar.html
│       ├── settings.html
│       ├── post_detail.html
│       ├── post_edit.html
│       └── partials/
│           └── post_modal.html
│
└── media/                   # User uploads (post images)
```

---

## 🔧 Key Models

### Post Model

```python
class Post(models.Model):
    user = models.ForeignKey(User)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True)
    scheduled_for = models.DateTimeField()
    status = models.CharField(choices=['draft', 'scheduled', 'published'])
    platform = models.CharField(choices=['twitter', 'instagram', 'facebook', 'linkedin', 'tiktok'])
    metrics = models.JSONField()  # {"impressions": 0, "likes": 0, "comments": 0, "clicks": 0}
```

### UserSettings Model

```python
class UserSettings(models.Model):
    user = models.OneToOneField(User)
    gemini_api_key_encrypted = models.BinaryField()  # AES-256 encrypted
    
    def get_api_key(self):  # Decrypts and returns key
    def set_api_key(self, key):  # Encrypts and stores key
```

---

## 🗓️ Scheduler

Process scheduled posts and generate mock engagement metrics:

```bash
# Run the scheduler
python manage.py run_scheduler

# Preview without making changes
python manage.py run_scheduler --dry-run
```

The scheduler:
1. Finds all posts with `status=scheduled` and `scheduled_for <= now`
2. Updates status to `published`
3. Generates mock engagement metrics (impressions, likes, comments, clicks)

---

## 🎨 Design Decisions

| Choice | Why |
|--------|-----|
| **Django SSR** | Simple, fast development, no build step |
| **HTMX** | Interactive UX without React/Vue complexity |
| **Tailwind CDN** | No webpack/vite needed, instant styling |
| **SQLite** | Zero config, file-based, portable |
| **Fernet Encryption** | API keys encrypted at rest |
| **Pollinations.ai Fallback** | Free option for users without API keys |

---

## 🐘 Switching to PostgreSQL

By default, PostPilot uses SQLite for simplicity. To switch to PostgreSQL for production:

### 1. Install PostgreSQL adapter

```bash
pip install psycopg2-binary
```

### 2. Update `core/settings.py`

Replace the `DATABASES` configuration:

```python
# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'postpilot'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

### 3. Create the database

```bash
psql -U postgres -c "CREATE DATABASE postpilot;"
```

### 4. Run migrations

```bash
python manage.py migrate
```

### Migrating existing data (optional)

```bash
# Export from SQLite
python manage.py dumpdata > data.json

# Switch settings to PostgreSQL, then:
python manage.py migrate
python manage.py loaddata data.json
```

---

## 🔐 Security

- **Encrypted API Keys** - Stored using AES-256 (Fernet) encryption
- **CSRF Protection** - Django's built-in CSRF middleware
- **Login Required** - All views protected with `@login_required`
- **Multi-Tenant Isolation** - Users can only see their own data

---

## 📦 Dependencies

```
Django>=4.2,<5.0
Pillow>=9.0.0
openai>=1.0.0
google-genai>=1.0.0
cryptography>=41.0.0
requests>=2.31.0
```

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test scheduler

# Run with verbose output
python manage.py test scheduler -v 2

# Profile API performance
python profile_api.py
```

---

## � Future Improvements

1. **PostgreSQL Migration** - Move from SQLite to PostgreSQL for production scalability
2. **Team-based Multitenancy** - Currently multitenancy is user-based; add team-level access where multiple users can view and manage shared team data
3. **Real Social API Integration** - Integrate actual social media APIs (Twitter, Instagram, etc.) to replace simulated metrics with real engagement data
4. **UTC Datetime Handling** - Store and process all datetimes in UTC instead of local time for consistency across timezones
5. **Celery Task Queue** - Replace the current cron-based scheduler with Celery for more robust background job processing
6. **AWS Secrets Manager** - Use AWS Secrets Manager (or similar) for API key storage instead of database encryption
7. **Team Approval Workflow** - Add a content approval workflow where team owners can review and approve posts before publishing
8. **Image Storage** - Use AWS S3 for image storage instead of local storage

---