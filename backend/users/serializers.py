import base64

from api.models import Recipe
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import TokenCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Subscription

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class TokenSerializer(TokenCreateSerializer):
    """Сериализатор для получения токена."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class ExtendedUserSerializer(UserSerializer):
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

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and obj.subscribers.filter(user=request.user).exists()
        )


class ExtendedUserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True, use_url=True, allow_null=False)

    class Meta:
        model = User
        fields = ('avatar',)


class RecipeSubscribeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'cooking_time', 'image')


class SubscriptionsSerializer(UserSerializer):
    avatar = Base64ImageField(required=False, allow_null=True, use_url=True)
    recipes = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )
        model = User

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        queryset = obj.recipes.all().order_by('-pub_date')
        if recipes_limit and recipes_limit.isdigit():
            queryset = queryset[:int(recipes_limit)]
        return RecipeSubscribeSerializer(
            queryset,
            many=True,
            context={'request': request}
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and obj.subscribers.filter(user=request.user).exists()
        )


class SubscribeSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    user = serializers.PrimaryKeyRelatedField(
        default=serializers.CurrentUserDefault(),
        queryset=User.objects.all()
    )

    class Meta:
        fields = ('user', 'author')
        model = Subscription
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=['user', 'author'],
                message='Вы уже подписаны на этого пользователя!'
            )
        ]

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                'Вы не можете подписаться на себя!')
        return data

    def to_representation(self, instance):
        return SubscriptionsSerializer(
            instance.author,
            context=self.context
        ).data
