from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from foods import models
from rest_framework.test import APIClient

User = get_user_model()


class RecipeAPITestCase(TestCase):
    def setUp(self):
        self.guest_client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='ooo@mail.ru',
            password='testpass1232025'
        )
        self.client = APIClient()
        from rest_framework.authtoken.models import Token
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_list_exists(self):
        """Проверка доступности списка рецептов."""
        response = self.guest_client.get('/api/recipes')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_recipe_creation(self):
        """Проверка создания рецепта."""
        models.Tag.objects.create(
            id=1,
            name="Завтрак",
            slug="breakfast"
        )
        models.Ingredient.objects.create(
            id=100,
            name="Авокадо",
            measurement_unit="шт"
        )
        data = {
            "ingredients": [
                {"id": 100, "amount": 1}
            ],
            "tags": [1],
            "name": "Test",
            "text": "приготовление авокадо",
            "cooking_time": 20,
            "image": "data:image/png;base64,iVBORw0K"
                     "GgoAAAANSUhEUgAAAAEAAAABAgMAAAB"
                     "ieywaAAAACVBMVEUAAAD///9fX1/S0e"
                     "cCAAAACXBIWXMAAA7EAAAOxAGVKw4bA"
                     "AAACklEQVQImWNoAAAAggCByxOyYQAAA"
                     "ABJRU5ErkJggg==",
        }
        response = self.client.post(
            '/api/recipes',
            data=data,
            format='json',
            HTTP_AUTHORIZATION=f'Token {self.token.key}'
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(models.Recipe.objects.filter(name='Test').exists())
