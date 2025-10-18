from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("debug/", views.debug_prices),
]
