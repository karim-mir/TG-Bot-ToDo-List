from django.db import models
from datetime import datetime
import secrets


class Category(models.Model):
    id = models.CharField(max_length=50, primary_key=True, editable=False)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.id:
            timestap = datetime.now().strftime("%Y%m%d")
            random_part = secrets.token_hex(3).upper()
            self.id = f"CAT-{timestap}-{random_part}"
        super().save(*args, **kwargs)


class Task(models.Model):
    id = models.CharField(max_length=50, primary_key=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    completed = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category, blank=True)
