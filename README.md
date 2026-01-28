# PostPilot - Social Media Scheduler

<div align="center">
  <h3>📅 Schedule, Automate & Grow Your Social Presence</h3>
  <p>A lightweight social media scheduling SaaS built with Django, HTMX, and Tailwind CSS</p>
</div>

---

## ✨ Features

- **📊 Dashboard Analytics** - Track total posts, likes, views, and engagement metrics
- **🗓️ Visual Calendar** - Monthly calendar view with clickable dates for easy scheduling  
- **🤖 AI Image Generation** - Mock integration ready for OpenAI DALL-E (swap in your API key)
- **⚡ HTMX Modals** - Smooth, no-refresh post creation experience
- **🔐 Multi-tenant** - Each user only sees their own data
- **📱 Responsive Design** - Works beautifully on desktop and mobile

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
cd /path/to/miniSaas

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser (optional, for admin access)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

Visit **http://127.0.0.1:8000** and create your account!

---

## 🏗️ Architecture Overview

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
│   │     User (Django Auth)  ←──FK──  Post               │   │
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
miniSaas/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # SQLite database (auto-created)
│
├── core/                    # Project configuration
│   ├── settings.py          # Django settings
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI application
│
├── scheduler/               # Main application
│   ├── models.py            # Post model
│   ├── views.py             # Dashboard, Calendar, Post views
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
│
├── static/                  # Static files
└── media/                   # User uploads
```

---

## 🔧 Key Components

### Post Model

```python
class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True)
    scheduled_for = models.DateTimeField()
    status = models.CharField(choices=['draft', 'scheduled', 'published'])
    metrics = models.JSONField(default=dict)  # {"likes": 0, "views": 0}
```

### Scheduler Command

```bash
# Process scheduled posts and generate mock metrics
python manage.py run_scheduler

# Preview without making changes
python manage.py run_scheduler --dry-run
```

---

## 🎨 Design Decisions

### Why Django + HTMX?

| Approach | Pros | Why We Chose It |
|----------|------|-----------------|
| **Django SSR** | Simple, fast development, no build step | Perfect for MVP timeline |
| **HTMX** | Interactive UX without React/Vue complexity | Modals work beautifully |
| **Tailwind CDN** | No webpack/vite needed, instant styling | Rapid prototyping |
| **SQLite** | Zero config, file-based, portable | Great for demos |

### Multi-Tenancy Strategy

- Every `Post` has a `user` ForeignKey
- All views filter by `request.user`
- `@login_required` on every protected view
- No user can ever see another user's data

---

## 🔌 AI Image Generation

The MVP includes a **mocked** AI image endpoint. To enable real generation:

1. Add to `settings.py`:
   ```python
   OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
   ```

2. Update `views.py` `generate_ai_image()`:
   ```python
   import openai
   openai.api_key = settings.OPENAI_API_KEY
   response = openai.Image.create(prompt=prompt, n=1, size="512x512")
   image_url = response['data'][0]['url']
   ```

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test scheduler

# Run with verbose output
python manage.py test scheduler -v 2
```

---

## 📝 License

MIT License - Feel free to use this for your own projects!

---

<div align="center">
  <p>Built with ❤️ using Django, HTMX, and Tailwind CSS</p>
</div>
