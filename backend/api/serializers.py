from rest_framework import serializers
from django.contrib.auth.models import User
from .models import AIAnalysisLog, AIModelConfig, UserProfile, WatchlistGroup, Watchlist, Event

class WatchlistGroupSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    class Meta:
        model = WatchlistGroup
        fields = ['id', 'name', 'created_at', 'item_count']
        read_only_fields = ['id', 'created_at', 'item_count']
    
    def get_item_count(self, obj):
        request = self.context.get('request', None)
        user_id = request.user.id if request and request.user and request.user.id else None
        if user_id is None:
            return 0
        return Watchlist.objects.filter(user_id=user_id, group_id=obj.id).count()

class AIAnalysisLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysisLog
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    ai_api_key = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    ai_api_key_configured = serializers.SerializerMethodField()
    ai_api_key_preview = serializers.SerializerMethodField()
    ai_models = serializers.SerializerMethodField()
    active_ai_model_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = UserProfile
        fields = ['ai_provider', 'ai_base_url', 'ai_model', 'ai_api_key', 'ai_api_key_configured', 'ai_api_key_preview', 'ai_models', 'active_ai_model_id']

    def _get_active_model_key(self, obj):
        active_id = getattr(obj, "active_ai_model_id", None)
        if active_id:
            cfg = AIModelConfig.objects.filter(id=active_id, user_id=obj.user_id).first()
            if cfg and getattr(cfg, "api_key", None):
                return str(cfg.api_key)
        key = getattr(obj, "ai_api_key", None)
        return str(key) if key else None

    def get_ai_api_key_configured(self, obj):
        return bool(self._get_active_model_key(obj))

    def get_ai_api_key_preview(self, obj):
        key = self._get_active_model_key(obj)
        if not key:
            return None
        k = str(key)
        if len(k) <= 6:
            return "*" * len(k)
        return f"{k[:3]}***{k[-4:]}"

    def get_ai_models(self, obj):
        qs = AIModelConfig.objects.filter(user_id=obj.user_id).order_by("-updated_at")[:50]
        return AIModelConfigSerializer(qs, many=True).data

class AIModelConfigSerializer(serializers.ModelSerializer):
    api_key_configured = serializers.SerializerMethodField()
    api_key_preview = serializers.SerializerMethodField()

    class Meta:
        model = AIModelConfig
        fields = ["id", "provider", "base_url", "model", "api_key_configured", "api_key_preview", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at", "api_key_configured", "api_key_preview"]

    def get_api_key_configured(self, obj):
        return bool(getattr(obj, "api_key", None))

    def get_api_key_preview(self, obj):
        key = getattr(obj, "api_key", None)
        if not key:
            return None
        k = str(key)
        if len(k) <= 6:
            return "*" * len(k)
        return f"{k[:3]}***{k[-4:]}"

class UserProfileProxyField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, value):
        profile, _ = UserProfile.objects.get_or_create(user_id=value.id)
        return UserProfileSerializer(profile).data

    def to_internal_value(self, data):
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise serializers.ValidationError("profile must be an object")
        s = UserProfileSerializer(data=data, partial=True)
        s.is_valid(raise_exception=True)
        return s.validated_data

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileProxyField(required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']
        read_only_fields = ['username']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user_id=instance.id)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            
        return instance

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'id',
            'symbol',
            'title',
            'event_type',
            'source',
            'source_url',
            'license_status',
            'evidence',
            'event_time',
            'market_effective_time',
        ]
        read_only_fields = ['id']

