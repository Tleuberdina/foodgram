import hashlib

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

User = get_user_model()


class Ingredient(models.Model):
    name = models.CharField(verbose_name='Название', max_length=64)
    measurement_unit = models.CharField(
        verbose_name='Еденица измерения',
        max_length=16
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(verbose_name='Название', max_length=64)
    slug = models.SlugField(verbose_name='Идентификатор', unique=True)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
        help_text='Начните вводить название',
        through='IngredientRecipe'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        through='TagRecipe'
    )
    image = models.ImageField(
        verbose_name='Изображение рецепта',
        upload_to='recipes/images/'
    )
    name = models.CharField(verbose_name='Название рецепта', max_length=256)
    text = models.TextField(
        verbose_name='Описание рецепта',
        help_text='Опишите действия'
    )
    cooking_time = models.IntegerField(
        verbose_name='Время приготовления',
        validators=[MinValueValidator(1)]
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор рецепта',
        related_name='recipes',
        on_delete=models.CASCADE
    )
    pub_date = models.DateTimeField('Дата публикации', default=timezone.now)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name

    @property
    def short_code(self):
        return hashlib.md5(str(self.id).encode()).hexdigest()[:3]

    def get_by_short_code(short_code):
        recipes = Recipe.objects.all()
        for recipe in recipes:
            if recipe.short_code == short_code:
                return recipe
        return None


class IngredientRecipe(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients_relations'
    )
    amount = models.PositiveIntegerField(verbose_name='Количество', default=0)

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'


class TagRecipe(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.tag} {self.recipe}'


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscriptions')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscribers')

    class Meta:
        unique_together = ('user', 'author')


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='favorites')

    class Meta:
        unique_together = ('user', 'recipe')


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping_carts')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='shopping_carts')

    class Meta:
        unique_together = ('user', 'recipe')
