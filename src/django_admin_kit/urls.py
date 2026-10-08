"""Admin URLs, resolved through the site under test.

Every URL comes from Django's resolver, so a project that mounts its admin at
``/backoffice/`` or runs a second ``AdminSite`` gets correct URLs without changing a
test. Nothing here assembles a path from string pieces.

Resolution says nothing about access. Asking for the URL of a page the current user
could not open still returns that URL; whether it works is a separate question.
"""

from __future__ import annotations

from typing import Any, Sequence

from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.module_loading import import_string


def registered_models(site: AdminSite) -> list[type[Any]]:
    """The models ``site`` registers, in the order they were registered."""
    return list(_registry(site))


def model_admin(site: AdminSite, model: type[Any]) -> ModelAdmin:
    """The model admin ``site`` registers ``model`` with."""
    # Django 5.0 added a public accessor; before it there is only the registry.
    if hasattr(site, "get_model_admin"):
        return site.get_model_admin(model)
    return _registry(site)[model]


def _registry(site: AdminSite) -> dict[type[Any], ModelAdmin]:
    # The one place the site's registry is read: Django lists the registered models
    # nowhere public on any version.
    registry: dict[type[Any], ModelAdmin] = site._registry
    return registry


def resolve_site(site: str | None = None) -> AdminSite:
    """Turn the ``site`` setting into an ``AdminSite``.

    Takes a dotted path, or ``None`` for the default ``django.contrib.admin.site``.
    Only a path, because settings are imported before Django's app registry is ready
    and an ``AdminSite`` written into settings raises ``AppRegistryNotReady`` there.
    Code holding a site already can pass it straight to ``AdminUrls``.
    """
    if site is None:
        from django.contrib import admin

        return admin.site

    try:
        imported = import_string(site)
    except ImportError as error:
        raise ImproperlyConfigured(
            f"DJANGO_ADMIN_KIT['site'] is {site!r}, which does not import: {error}"
        ) from error

    if not isinstance(imported, AdminSite):
        raise ImproperlyConfigured(
            f"DJANGO_ADMIN_KIT['site'] is {site!r}, which is a "
            f"{type(imported).__name__}, not an AdminSite."
        )
    return imported


class AdminUrls:
    """Every admin page this package knows, addressable without opening it."""

    def __init__(self, site: AdminSite) -> None:
        self._site = site

    @property
    def site(self) -> AdminSite:
        return self._site

    def index(self) -> str:
        return self._reverse("index")

    def login(self) -> str:
        return self._reverse("login")

    def list(self, model: type[Any]) -> str:
        return self._reverse_model(model, "changelist")

    def create(self, model: type[Any]) -> str:
        return self._reverse_model(model, "add")

    def edit(self, instance: Any) -> str:
        return self._reverse_model(type(instance), "change", [self._pk(instance, "edit")])

    def delete(self, instance: Any) -> str:
        return self._reverse_model(type(instance), "delete", [self._pk(instance, "delete")])

    def _reverse(self, name: str, args: Sequence[Any] | None = None) -> str:
        # The app namespace is always "admin"; the site's own name is the instance
        # namespace, which is what picks between two mounted sites.
        return str(reverse(f"admin:{name}", args=args, current_app=self._site.name))

    def _reverse_model(
        self, model: type[Any], action: str, args: Sequence[Any] | None = None
    ) -> str:
        if not self._site.is_registered(model):
            labels = sorted(m._meta.label for m in registered_models(self._site))
            raise LookupError(
                f"{model._meta.label} is not registered with the {self._site.name!r} admin "
                f"site, so it has no admin URLs. Registered models: "
                f"{', '.join(labels) or 'none'}."
            )
        return self._reverse(f"{model._meta.app_label}_{model._meta.model_name}_{action}", args)

    @staticmethod
    def _pk(instance: Any, action: str) -> Any:
        if instance.pk is None:
            raise ValueError(
                f"Cannot build the {action} URL for an unsaved "
                f"{type(instance)._meta.label}: it has no primary key yet."
            )
        return instance.pk
