import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.templatetags.static import static
from djoser.serializers import (TokenCreateSerializer, UserCreateSerializer,
                                UserSerializer)
from rest_framework import serializers

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class MyUserCreateSerializer(UserCreateSerializer):

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'password',
            'last_name'
        )

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user


class TokenSerializer(TokenCreateSerializer):
    """Сериализатор для получения токена."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class MyUserSerializer(UserSerializer):
    avatar = Base64ImageField(required=False, use_url=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get('avatar'):
            request = self.context.get('request')
            default_avatar_url = static('images/avatar-icon.png')
            data['avatar'] = request.build_absolute_uri(default_avatar_url)
        return data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.subscribers.filter(user=request.user).exists()
        return False


class MyUserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True, use_url=True)

    class Meta:
        model = User
        fields = ('avatar',)


class MyUserAvatarUsernameSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = User
        fields = ('avatar', 'username')
