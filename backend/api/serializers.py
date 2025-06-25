from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from users.constants import MAX_VALUE, MIN_VALUE
from users.serializers import Base64ImageField, ExtendedUserSerializer

from .models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                     ShoppingCart, Tag)

User = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInputSerializer(serializers.Serializer):
    """Сериализатор ТОЛЬКО для ввода данных (не связан с моделью)"""
    id = serializers.PrimaryKeyRelatedField(
        required=True,
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(
        required=True,
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        error_messages={
            'min_value': 'Количество не может быть меньше 1.',
            'max_value': 'Количество не может превышать 32000.'
        }
    )


class IngredientRecipeOutputSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода данных (связан с IngredientRecipe)"""
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
            'image',
            'name',
            'tags',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'text',
            'cooking_time',
            'author'
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
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (self.context.get('request')
                and self.context['request'].method in ['PATCH']):
            for field in ['ingredients', 'tags', 'name',
                          'text', 'cooking_time']:
                if field in self.fields:
                    self.fields[field].required = True

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
        ret = super().to_representation(instance)
        ret['tags'] = TagSerializer(instance.tags.all(), many=True).data
        ret['ingredients'] = IngredientRecipeOutputSerializer(
            instance.ingredients_relations.all(),
            many=True,
            context=self.context
        ).data
        return ret

    def create(self, validated_data):
        author = self.context['request'].user
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        for ing in ingredients_data:
            ing_instance = IngredientRecipe(
                recipe=recipe,
                ingredient=ing['id'],
                amount=ing['amount']
            )
            ing_instance.full_clean()
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=ing['id'],
                amount=ing['amount']
            )
            for ing in ingredients_data
        ])
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        with transaction.atomic():
            instance.ingredients_relations.all().delete()
            instance.tags.clear()
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            instance.tags.set(tags_data)
            IngredientRecipe.objects.bulk_create([
                IngredientRecipe(
                    recipe=instance,
                    ingredient=ingredient['id'],
                    amount=ingredient['amount']
                )
                for ingredient in ingredients_data
            ])
        return instance

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


class ShoppingCartListSerializer(serializers.ModelSerializer):
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
