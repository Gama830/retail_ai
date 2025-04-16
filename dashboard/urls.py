from django.urls import path
from . import views

app_name = 'dashboard' # Add app_name for namespacing

urlpatterns = [
    # path('home/', views.home, name='home'),  # Removed old home view path
    path('', views.dashboard_view, name='dashboard_main'), # Map root to new view
]
