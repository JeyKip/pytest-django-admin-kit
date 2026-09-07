from django.contrib import admin
from django.urls import path

# Not `/admin/`. See the note in settings.py.
urlpatterns = [
    path("backoffice/", admin.site.urls),
]
