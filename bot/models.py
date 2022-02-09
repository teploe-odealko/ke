from django.db import models

class UserChat(models.Model):
    chat_id = models.DecimalField(max_digits=30, decimal_places=0)
    # state = models.CharField(max_length=20)
    google_sheet = models.TextField(null=True)


class Shop(models.Model):
    user_chat = models.ForeignKey(UserChat, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)


