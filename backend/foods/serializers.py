from collections import OrderedDict

from django.contrib.auth import get_user_model
from rest_framework import serializers
from users.serializers import (Base64ImageField,
                               MyUserAvatarUsernameSerializer,
                               MyUserSerializer)

from .models import Ingredient, IngredientRecipe, Recipe, Subscription, Tag

User = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInputSerializer(serializers.Serializer):
    """Сериализатор ТОЛЬКО для ввода данных (не связан с моделью)"""
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)

    def validate_id(self, value):
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                f"Ингредиент '{value}' не найден"
            )
        return value


class IngredientRecipeOutputSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода данных (связан с IngredientRecipe)"""
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('name', 'measurement_unit', 'amount')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeReadSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)
    author = serializers.SerializerMethodField()
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

    def get_author(self, obj):
        request = self.context.get('request')
        serializer = MyUserSerializer(
            obj.author,
            context={'request': request}
        )
        return serializer.data

    def get_ingredients(self, obj):
        ingredient_recipes = obj.ingredients_relations.all()
        return IngredientRecipeOutputSerializer(
            ingredient_recipes, many=True
        ).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.shopping_carts.filter(user=request.user).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, use_url=True)
    author = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(
        many=True,
        slug_field='id',
        queryset=Tag.objects.all()
    )
    ingredients = IngredientInputSerializer(many=True, write_only=True)
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
        read_only_fields = ('author',)

    def get_author(self, obj):
        request = self.context.get('request')
        serializer = MyUserSerializer(obj.author, context={'request': request})
        return serializer.data

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Нужно указать хотя бы один ингредиент"
            )
        ingredient_ids = [item['id'] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться"
            )
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        ingredient_recipe_objects = [
            IngredientRecipe(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        IngredientRecipe.objects.bulk_create(ingredient_recipe_objects)
        return recipe

    def update(self, instance, validated_data):
        required_fields = [
            'name',
            'text',
            'cooking_time',
            'ingredients',
            'tags'
        ]
        for field in required_fields:
            if field not in validated_data:
                raise serializers.ValidationError(
                    {field: "Это поле обязательно для обновления"}
                )
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        if 'image' in validated_data:
            instance.image = validated_data['image']
        tags = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags)
        ingredients_data = validated_data.pop('ingredients')
        instance.ingredientrecipe_set.all().delete()
        for ingredient_data in ingredients_data:
            ingredient = Ingredient.objects.get(id=ingredient_data['id'])
            IngredientRecipe.objects.create(
                recipe=instance,
                ingredient=ingredient,
                amount=ingredient_data['amount']
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ingredients = IngredientRecipeOutputSerializer(
            instance.ingredients_relations.all(),
            many=True
        ).data
        ordered_ret = OrderedDict()
        field_order = [
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
        ]
        for field in field_order:
            if field == 'ingredients':
                ordered_ret[field] = ingredients
            else:
                ordered_ret[field] = ret[field]
        return ordered_ret

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.shopping_carts.filter(user=request.user).exists()
        return False


class RecipeSubscriptionsSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = Recipe
        fields = ('name', 'image')
        read_only_fields = ('author',)


class SubscribeSerializer(serializers.ModelSerializer):
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
        recipes_limit = request.query_params.get(
            'recipes_limit') if request else None
        recipes_qs = obj.recipes.all()
        if recipes_limit and recipes_limit.isdigit():
            recipes_qs = recipes_qs[:int(recipes_limit)]
        return RecipeSubscriptionsSerializer(
            recipes_qs,
            many=True,
            context={'request': request}
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False


class SubscriptionsSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True, use_url=True)
    recipes = serializers.SerializerMethodField()

    class Meta:
        fields = ('avatar', 'username', 'recipes')
        model = User

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = self.context.get('recipes_limit')
        recipes_qs = obj.recipes.all()
        if recipes_limit is not None:
            recipes_qs = recipes_qs[:recipes_limit]
        serializer = RecipeSubscriptionsSerializer(
            recipes_qs,
            many=True,
            context={'request': request}
        )
        return serializer.data


class FavoriteShoppingCartSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        fields = ('id', 'name', 'image', 'cooking_time')
        model = Recipe


class FavoriteListSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)
    author = serializers.SerializerMethodField()

    class Meta:
        fields = ('image', 'name', 'author', 'cooking_time')
        model = Recipe

    def get_author(self, obj):
        request = self.context.get('request')
        serializer = MyUserAvatarUsernameSerializer(
            obj.author,
            context={'request': request}
        )
        return serializer.data


class ShoppingCartListSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True, use_url=True)
    ingredients = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Ingredient.objects.all()
    )

    class Meta:
        fields = ('image', 'name', 'cooking_time', 'ingredients')
        model = Recipe
