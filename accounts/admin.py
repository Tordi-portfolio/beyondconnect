from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile

User = get_user_model()

admin.site.site_header = "BeyondConnect Admin"
admin.site.site_title = "BeyondConnect"
admin.site.index_title = "Manage your store"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "date_joined", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
