from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra customer details used to pre-fill checkout."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user}"

    @classmethod
    def for_user(cls, user):
        """Return the user's profile, creating it on first access."""
        profile, _ = cls.objects.get_or_create(user=user)
        return profile
