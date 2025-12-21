from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

class AIModelConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(verbose_name="用户ID")
    provider = models.CharField(max_length=50, blank=True, null=True, default='deepseek', verbose_name="AI Provider")
    base_url = models.CharField(max_length=255, blank=True, null=True, default='https://api.deepseek.com', verbose_name="AI Base URL")
    model = models.CharField(max_length=50, blank=True, null=True, default='deepseek-chat', verbose_name="AI Model")
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="AI API Key")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        unique_together = ('user_id', 'provider', 'base_url', 'model', 'api_key')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=["user_id", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.model} - User({self.user_id})"

class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(unique=True, verbose_name="用户ID")
    ai_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="AI API Key")
    ai_provider = models.CharField(max_length=50, blank=True, null=True, default='deepseek', verbose_name="AI Provider")
    ai_base_url = models.CharField(max_length=255, blank=True, null=True, default='https://api.deepseek.com', verbose_name="AI Base URL")
    ai_model = models.CharField(max_length=50, blank=True, null=True, default='deepseek-chat', verbose_name="AI Model")
    active_ai_model_id = models.UUIDField(blank=True, null=True, verbose_name="当前使用的 AI 模型配置ID")

    def __str__(self):
        return f"User({self.user_id}) Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user_id=instance.id)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # No direct relationship anymore, so we might not need this if we don't update profile via user save
    # But if we did, we'd do:
    # UserProfile.objects.filter(user_id=instance.id).update(...)
    pass

class WatchlistGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(verbose_name="用户ID")
    name = models.CharField(max_length=100, verbose_name="分组名称")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'name')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} - User:{self.user_id}"

class Watchlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(verbose_name="用户ID")
    group = models.ForeignKey(WatchlistGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='stocks', verbose_name="所属分组")
    ts_code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'group', 'ts_code')

    def __str__(self):
        return f"{self.name} ({self.ts_code}) - Group:{self.group.name if self.group else 'None'}"

class AIAnalysisLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ts_code = models.CharField(max_length=20, verbose_name="股票代码")
    stock_name = models.CharField(max_length=100, verbose_name="股票名称", blank=True, null=True)
    analysis_content = models.TextField(verbose_name="分析内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="分析时间")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.stock_name}({self.ts_code}) - {self.created_at}"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(verbose_name="用户ID")
    symbol = models.CharField(max_length=20, verbose_name="标的代码")
    title = models.CharField(max_length=255, verbose_name="标题")
    event_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="事件类型")
    source = models.CharField(max_length=100, blank=True, null=True, verbose_name="来源")
    source_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="来源链接")
    license_status = models.CharField(max_length=30, blank=True, null=True, verbose_name="许可状态")
    evidence = models.TextField(blank=True, null=True, verbose_name="证据片段")
    event_time = models.DateTimeField(verbose_name="事件时间")
    market_effective_time = models.DateTimeField(verbose_name="可交易生效时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "symbol", "market_effective_time"]),
            models.Index(fields=["user_id", "symbol", "event_time"]),
        ]
        ordering = ["-market_effective_time", "-event_time"]

    def __str__(self):
        return f"{self.symbol} {self.title}"
