"""Settings for the package's own test project.

This project stands in for a consuming project. It is deliberately unlike the Django
tutorial in two ways that the package must cope with:

* the admin is mounted at `/backoffice/`, not `/admin/`;
* the user model has no `username` field and authenticates by email.

Both hold across the whole suite, so every later test proves them by construction
rather than through a special case.
"""

SECRET_KEY = "not-a-secret-this-project-only-ever-runs-under-pytest"

DEBUG = False

# Django's test setup appends "testserver"; the rest cover `live_server`, which binds
# a free port on localhost.
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "project.accounts",
    "project.shop",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ],
        },
    },
]

# In memory, because browser tests are transactional whatever mark they carry:
# pytest-django's autouse `_live_server_helper` promotes any test using `live_server`
# to `transactional_db`. SQLite keeps that reset cheap.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# The suite never tests hashing, and MD5 saves real time on every user it creates.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Set explicitly: the default flipped to True in Django 5.0, and the package's
# date and time normalization must not read differently across the matrix.
USE_TZ = True

TIME_ZONE = "UTC"

LANGUAGE_CODE = "en-us"
