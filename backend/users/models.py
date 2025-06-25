from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MaxLengthValidator
from django.db import models

from .constants import LIMIT_LENGTH_EMAIL, LIMIT_LENGTH_STRING


class ExtendedUser(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')
    email = models.EmailField(
        verbose_name='Email',
        unique=True,
        max_length=LIMIT_LENGTH_EMAIL,
        validators=[MaxLengthValidator(LIMIT_LENGTH_EMAIL)],
        error_messages={
            'unique': 'Пользователь с таким email уже существует.'
        }
    )
    username = models.CharField(
        verbose_name='Никнейм',
        max_length=LIMIT_LENGTH_STRING,
        unique=True,
        validators=[
            UnicodeUsernameValidator(),
            MaxLengthValidator(LIMIT_LENGTH_STRING)],
        error_messages={
            'unique': 'Этот никнейм уже занят.',
            'max_length': 'Никнейм не должен превышать 150 символов.'
        }
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=LIMIT_LENGTH_STRING,
        validators=[MaxLengthValidator(LIMIT_LENGTH_STRING)],
        blank=False
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=LIMIT_LENGTH_STRING,
        validators=[MaxLengthValidator(LIMIT_LENGTH_STRING)],
        blank=False
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users/',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)
        db_table = 'users_extendeduser'

    def __str__(self):
        return f'{self.last_name} {self.first_name} ({self.email})'

    def save(self, *args, **kwargs):
        if self.is_superuser and not all(
            [self.email, self.first_name, self.last_name]
        ):
            raise ValueError(
                'Суперпользователь должен иметь email, имя и фамилию'
            )
        super().save(*args, **kwargs)


User = get_user_model()


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Подписчик',
        related_name='subscriptions')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='subscribers')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author'
            )
        ]
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        ordering = ('user',)

    def __str__(self):
        return f'{self.user} {self.author}'
