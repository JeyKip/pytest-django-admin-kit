"""The project's URLs plus the second admin site, used by `@pytest.mark.urls`."""

from django.contrib import admin
from django.urls import path

from .ops import ops_site

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ops/", ops_site.urls),
]
