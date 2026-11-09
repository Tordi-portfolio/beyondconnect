from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),  # Django's built-in admin (full data management)
    path("manage/", include("dashboard.urls")),  # Custom admin dashboard (overview of the whole site)
    path("accounts/", include("accounts.urls")),
    path("", include("store.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "store.views.permission_denied"
handler404 = "store.views.page_not_found"
