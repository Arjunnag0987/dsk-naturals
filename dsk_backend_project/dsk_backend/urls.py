from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib import admin
from api import views
from api.views import login_view, order_detail, register_view, logout_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('export-sales/', views.export_sales_excel, name='export_sales_excel'),

    # home
    path("", TemplateView.as_view(template_name="index.html"), name="home"),

    # auth pages (CLEAN URLS)
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
    

    # api routes
    path("api/", include("api.urls")),
    path("api/orders/<int:order_id>/", order_detail),

]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )