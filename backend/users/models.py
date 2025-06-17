from django.contrib.auth.models import AbstractUser
from django.db import models
from django.templatetags.static import static


class MyUser(AbstractUser):
    email = models.EmailField(unique=True)
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

    def __str__(self):
        return self.email

    @property
    def avatar_url(self):
        if hasattr(self, '_cached_avatar_url'):
            return self._cached_avatar_url

        if self.avatar and hasattr(self.avatar, 'url'):
            url = self.avatar.url
        else:
            url = static('images/avatar-icon.png')
        self._cached_avatar_url = url
        return url

    def __getattr__(self, name):
        if name == 'avatar':
            return self.avatar_url
        return super().__getattribute__(name)
