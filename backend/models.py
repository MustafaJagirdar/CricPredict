from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    email = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    usertype = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'backend_user'
    
    def __str__(self):
        return self.username
