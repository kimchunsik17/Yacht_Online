from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create_match/', views.create_match, name='create_match'),
    path('room/<str:room_name>/', views.room, name='room'),
]
