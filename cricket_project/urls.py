from django.contrib import admin
from django.urls import path
from backend import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('index.html', views.index, name='index'),
    path('UserLogin.html', views.UserLogin, name='UserLogin'),
    path('Register.html', views.Register, name='Register'),
    path('Signup', views.Signup, name='Signup'),
    path('UserLoginAction', views.UserLoginAction, name='UserLoginAction'),
    path('dashboard/', views.Dashboard, name='Dashboard'),
    path('logout/', views.Logout, name='Logout'),
    path('Batsman', views.Batsman, name='Batsman'),
    path('Ballers', views.Ballers, name='Ballers'),
    path('next-match/', views.NextMatchInsights, name='NextMatchInsights'),
]
