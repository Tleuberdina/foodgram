from http import HTTPStatus

from django.test import Client, TestCase
from foods import models


class RecipeAPITestCase(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_list_exists(self):
        """Проверка доступности списка рецептов."""
        response = self.guest_client.get('/api/recipes/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_recipe_creation(self):
        """Проверка создания рецепта."""
        data = {
          "ingredients": [
            {"name": "авокадо", "amount": 1}
          ],
          "tags": [1],
          "name": "Test",
          "text": "приготовление авокадо",
          "cooking_time": "20",
          "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4>
        }

        response = self.guest_client.post('/api/recipes/', data=data)
