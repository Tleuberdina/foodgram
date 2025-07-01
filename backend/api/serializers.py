import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from djoser.serializers import UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from reviews.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscription

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


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


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInputSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=Ingredient.objects.all()
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class IngredientRecipeOutputSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeReadSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)
    author = ExtendedUserSerializer()
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )
        read_only_fields = ('author', 'tags')

    def get_ingredients(self, obj):
        ingredients = obj.ingredients_relations.select_related(
            'ingredient'
        ).all()
        return IngredientRecipeOutputSerializer(
            ingredients,
            many=True
        ).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and obj.favorites.filter(author=request.user).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and obj.shopping_carts.filter(author=request.user).exists()
        )


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, use_url=True)
    author = ExtendedUserSerializer(required=False)
    tags = serializers.PrimaryKeyRelatedField(
        required=True,
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = IngredientInputSerializer(
        required=True,
        many=True,
        write_only=True
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time'
        )
        read_only_fields = ('author',)

    def validate(self, data):
        ingredients = data.get('ingredients', [])
        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': 'Нужно указать хотя бы один ингредиент'
            })
        seen_ingredient_ids = set()
        for item in ingredients:
            ingredient_id = item.get('id')
            if ingredient_id in seen_ingredient_ids:
                raise serializers.ValidationError({
                    'ingredients': 'Ингредиент указан более одного раза'
                })
            seen_ingredient_ids.add(ingredient_id)
        tags = data.get('tags', [])
        if not tags:
            raise serializers.ValidationError({
                'tags': 'Нужно указать хотя бы один тег'
            })
        seen_tag_ids = set()
        for tag in tags:
            if tag.id in seen_tag_ids:
                raise serializers.ValidationError({
                    'tags': 'Теги должны быть уникальны'
                })
            seen_tag_ids.add(tag.id)
        return data

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context=self.context
        ).data

    def _create_ingredients(self, recipe, ingredients_data):
        ingredients = []
        for ingredient in ingredients_data:
            obj = IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            )
            obj.full_clean()
            ingredients.append(obj)
        IngredientRecipe.objects.bulk_create(ingredients)

    @transaction.atomic
    def create(self, validated_data):
        author = self.context['request'].user
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        validated_data['author'] = author
        recipe = super().create(validated_data)
        recipe.tags.set(tags_data)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        required_fields = ['name', 'text', 'cooking_time']
        missing_fields = [field for field in required_fields
                          if field not in validated_data]
        if missing_fields:
            raise serializers.ValidationError(
                {field: "Обязательное поле" for field in missing_fields}
            )
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        instance.ingredients_relations.all().delete()
        instance.tags.clear()
        return (self._create_ingredients(
            updated_instance := super().update(instance, validated_data),
            ingredients_data),
            updated_instance.tags.set(tags_data)
        ) and updated_instance


class FavoriteShoppingCartSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        fields = ('id', 'name', 'image', 'cooking_time')
        model = Recipe


class FavoriteSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all()
    )

    class Meta:
        fields = ('author', 'recipe')
        model = Favorite
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=['author', 'recipe'],
                message='Этот рецепт уже добавлен в избранное!'
            )
        ]

    def to_representation(self, instance):
        return FavoriteShoppingCartSerializer(
            instance.recipe,
            context=self.context
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all()
    )

    class Meta:
        fields = ('author', 'recipe')
        model = ShoppingCart
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=['author', 'recipe'],
                message='Этот рецепт уже добавлен в список покупок!'
            )
        ]

    def to_representation(self, instance):
        return FavoriteShoppingCartSerializer(
            instance.recipe,
            context=self.context
        ).data
