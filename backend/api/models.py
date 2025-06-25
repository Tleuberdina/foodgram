import hashlib

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from users.constants import LIMIT_LENGTH_NAME, MAX_VALUE, MIN_VALUE

User = get_user_model()


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name='Название',
        max_length=LIMIT_LENGTH_NAME
    )
    measurement_unit = models.CharField(
        verbose_name='Еденица измерения',
        max_length=LIMIT_LENGTH_NAME
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_name_measurement_unit'
            )
        ]
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} {self.measurement_unit}'


class Tag(models.Model):
    name = models.CharField(
        verbose_name='Название',
        max_length=LIMIT_LENGTH_NAME
    )
    slug = models.SlugField(verbose_name='Идентификатор', unique=True)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} {self.slug}'


class Recipe(models.Model):
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
        help_text='Начните вводить название',
        through='IngredientRecipe'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги'
    )
    image = models.ImageField(
        verbose_name='Изображение рецепта',
        upload_to='recipes/images/'
    )
    name = models.CharField(
        verbose_name='Название рецепта',
        max_length=LIMIT_LENGTH_NAME
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
        help_text='Опишите действия'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[MinValueValidator(MIN_VALUE),
                    MaxValueValidator(MAX_VALUE)],
        error_messages={
            'min_value': 'Значение меньше 1.',
            'max_value': 'Значение больше 32000.'
        }
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор рецепта',
        related_name='recipes',
        on_delete=models.CASCADE
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        default=timezone.now
    )
    short_code = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        null=True,
        verbose_name='Короткий код'
    )

    def generate_short_code(self):
        base = str(self.pk).zfill(6)
        hash_str = hashlib.md5(base.encode()).hexdigest()[:8].upper()
        return hash_str

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)
        if not self.short_code:
            with transaction.atomic():
                for attempt in range(10):
                    new_code = self.generate_short_code()
                    if not Recipe.objects.filter(short_code=new_code).exists():
                        self.short_code = new_code
                        super().save(update_fields=['short_code'])
                        break
                else:
                    raise ValueError("Не удалось сгенерировать уникальный код")

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    def __str__(self):
        return f'{self.name} {self.author} {self.pub_date}'


class IngredientRecipe(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients_relations'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        default=1,
        validators=[MinValueValidator(MIN_VALUE),
                    MaxValueValidator(MAX_VALUE)],
        error_messages={
            'min_value': 'Значение меньше 1.',
            'max_value': 'Значение больше 32000.'
        }
    )

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'


class Favorite(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorites')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='favorites')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'recipe'],
                name='unique_favorite_user_recipe'
            )
        ]
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранные рецепты'
        ordering = ('recipe',)

    def __str__(self):
        return f'{self.author} {self.recipe}'


class ShoppingCart(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='shopping_carts')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='shopping_carts')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'recipe'],
                name='unique_shoppingcart_user_recipe'
            )
        ]
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ('recipe',)

    def __str__(self):
        return f'{self.author} {self.recipe}'
