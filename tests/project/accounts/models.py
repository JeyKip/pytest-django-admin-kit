from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    Permission,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Creates users keyed by email, since this model has no `username` field."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        # `None` gives an unusable password, which is what a project using SSO would
        # have. The package must be able to log such a user in regardless.
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # PermissionsMixin names its reverse accessors `user_set` and `user`, and so does
    # `auth.User`, which is installed alongside this model. Two models claiming the
    # same names on Group and Permission is a system check error (fields.E304), and
    # permission lookups then resolve to whichever model won.
    groups = models.ManyToManyField(
        Group, blank=True, related_name="accounts_users", related_query_name="accounts_user"
    )
    user_permissions = models.ManyToManyField(
        Permission, blank=True, related_name="accounts_users", related_query_name="accounts_user"
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    # Django defines this attribute as a mutable list, so RUF012 does not apply.
    REQUIRED_FIELDS = []  # noqa: RUF012

    def __str__(self):
        return self.email
