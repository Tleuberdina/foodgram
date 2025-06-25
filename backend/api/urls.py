from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import ExtendedUserViewSet
from .views import (IngredientViewSet, RecipeViewSet, ShoppingCartView,
                    TagViewSet)

app_name = 'api'

router = DefaultRouter()
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'users', ExtendedUserViewSet)


urlpatterns = [
    path('users/shopping_carts/',
         ShoppingCartView.as_view(),
         name='shopping_carts'),
    path('recipes/<int:id>/shopping_cart/',
         ShoppingCartView.as_view(),
         name='shopping_cart'),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
