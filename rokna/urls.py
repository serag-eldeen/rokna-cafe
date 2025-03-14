from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cafe/', include('cafe.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='cafe/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/cafe/'), name='logout'),
    path('', lambda request: redirect('cafe:home'), name='root_redirect'),
] + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)