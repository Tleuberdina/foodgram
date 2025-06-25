from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import IngredientFilter, RecipeFilter
from .models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                     ShoppingCart, Tag)
from .pagination import CustomLimitPagination
from .permissions import AuthorOrReadOnly
from .serializers import (FavoriteSerializer, FavoriteShoppingCartSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          RecipeSerializer, ShoppingCartListSerializer,
                          TagSerializer)

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Обрабатывает операции CRUD, получение короткой ссылки на рецепт,
    скачать список покупок, сформированный из рецептов, добавленных
    в список покупок для модели Recipe.
    """
    queryset = Recipe.objects.prefetch_related(
        'tags',
        'ingredients_relations__ingredient'
    )
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = CustomLimitPagination
    filterset_class = RecipeFilter
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in ['update', 'destroy', 'partial_update']:
            return (AuthorOrReadOnly(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        elif self.action in ['create', 'update', 'partial_update', 'destroy',]:
            return RecipeSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            'favorites',
            'favorites__author',
            'shopping_carts',
            'shopping_carts__author'
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        url_name='favorite',
        permission_classes=[IsAuthenticated]

    )
    def favorite(self, request, id=None):
        author = request.user
        recipe = get_object_or_404(Recipe, pk=id)
        if request.method == 'POST':
            data = {
                'author': author.id,
                'recipe': id
            }
            serializer = FavoriteSerializer(
                data=data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            favorite = serializer.save()
            return Response(
                serializer.to_representation(favorite),
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            delete_cnt, _ = Favorite.objects.filter(
                recipe=recipe,
                author=author
            ).delete()
            if delete_cnt > 0:
                return Response(
                    {'detail': 'Рецепт удален из избранного.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {'detail': 'Рецепт отсутствует в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(detail=True,
            methods=['get'],
            url_path='get-link',
            url_name='get-link',
            permission_classes=[IsAuthenticatedOrReadOnly])
    def get_short_link(self, request, id=None):
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        recipe = self.get_object()
        return Response({
            "short-link": request.build_absolute_uri(f"/s/{recipe.short_code}")
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        shopping_cart = request.user.shopping_carts.all()
        recipe_ids = shopping_cart.values_list('recipe_id', flat=True)
        ingredients = IngredientRecipe.objects.filter(
            recipe_id__in=recipe_ids
        ).select_related('ingredient').values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')
        lines = []
        for item in ingredients:
            name = item['ingredient__name']
            unit = item['ingredient__measurement_unit']
            amount = item['total_amount']
            lines.append(f"{name} ({unit}) — {amount}")
        text_content = "\n".join(lines)
        response = HttpResponse(text_content, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class ShortLinkRedirectView(APIView):
    def get(self, request, short_code):
        recipe = Recipe.objects.get_object_or_404(short_code=short_code)
        return redirect(
            f'{settings.CSRF_TRUSTED_ORIGINS[0]}/recipes/{recipe.pk}/'
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Обрабатывает операции получения
    списка объектов и объекта для модели Ingredient.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ Обрабатывает операции получения
    списка объектов и объекта для модели Tag.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'id'


class ShoppingCartView(APIView):
    """
    Обрабатывает get, post, delete для модели ShoppingCart.
    """
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = CustomLimitPagination

    @action(
        detail=False,
        methods=['get'],
        url_path='shopping_carts',
        url_name='shopping_carts',
        permission_classes=[AuthorOrReadOnly]

    )
    def get(self, request):
        author = request.user
        shopping_carts = ShoppingCart.objects.filter(
            author=author).select_related('recipe')
        recipes = [sub.recipe for sub in shopping_carts]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(recipes, request)
        serializer = ShoppingCartListSerializer(page, many=True, context={
            'request': request
        })
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        author = request.user
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        shopping_cart, created = ShoppingCart.objects.get_or_create(
            author=author,
            recipe=recipe
        )
        if not created:
            return Response(
                {'detail': 'Данный рецепт уже добавлен в список покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = FavoriteShoppingCartSerializer(
            recipe,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        author = request.user
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            shopping_cart = ShoppingCart.objects.get(
                author=author, recipe=recipe
            )
            shopping_cart.delete()
            return Response(
                {'detail': 'Рецепт успешно удален из списка покупок.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except ShoppingCart.DoesNotExist:
            return Response(
                {'detail': 'Рецепт отсутствует в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
