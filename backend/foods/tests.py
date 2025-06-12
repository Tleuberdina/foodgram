from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from foods import models

User = get_user_model()


class RecipeAPITestCase(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_list_exists(self):
        """Проверка доступности списка рецептов."""
        response = self.guest_client.get('/api/recipes/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_recipe_creation(self):
        """Проверка создания рецепта."""
        user = User.objects.create_user(
            email='ooo@mail.ru',
            password='testpass1232025'
        )
        self.client.force_login(user)
        data = {
            "ingredients": [
                {"name": "авокадо", "amount": 1}
            ],
            "tags": [1],
            "name": "Test",
            "text": "приготовление авокадо",
            "cooking_time": "20",
            "image": "data:image/png;base64,iVBORw0K"
                     "GgoAAAANSUhEUgAAAAEAAAABAgMAAAB"
                     "ieywaAAAACVBMVEUAAAD///9fX1/S0e"
                     "cCAAAACXBIWXMAAA7EAAAOxAGVKw4bA"
                     "AAACklEQVQImWNoAAAAggCByxOyYQAAA"
                     "ABJRU5ErkJggg==",
        }
        response = self.guest_client.post('/api/recipes/', data=data)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(models.Recipe.objects.filter(name='Test').exists())
