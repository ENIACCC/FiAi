from rest_framework import serializers
from django.contrib.auth.models import User
from .models import AIAnalysisLog, UserProfile, WatchlistGroup, Watchlist

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
    class Meta:
        model = UserProfile
        fields = ['ai_api_key', 'ai_model']

class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']
        read_only_fields = ['username']

    def get_profile(self, obj):
        profile, _ = UserProfile.objects.get_or_create(user_id=obj.id)
        return UserProfileSerializer(profile).data

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update Profile fields
        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user_id=instance.id)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            
        return instance

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

