from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    ai_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="AI API Key")
    ai_model = models.CharField(max_length=50, blank=True, null=True, default='deepseek-chat', verbose_name="AI Model")

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Watchlist(models.Model):
    ts_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.ts_code})"

class AIAnalysisLog(models.Model):
    ts_code = models.CharField(max_length=20, verbose_name="股票代码")
    stock_name = models.CharField(max_length=100, verbose_name="股票名称", blank=True, null=True)
    analysis_content = models.TextField(verbose_name="分析内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="分析时间")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.stock_name}({self.ts_code}) - {self.created_at}"
