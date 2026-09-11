"""The admin at a prefix other than `/admin/`, used by `@pytest.mark.urls`."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("backoffice/", admin.site.urls),
]
