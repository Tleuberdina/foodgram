from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomLimitPagination
from .permissions import AuthorOrReadOnly
from .serializers import (ExtendedUserAvatarSerializer, ExtendedUserSerializer,
                          FavoriteSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeSerializer,
                          ShoppingCartSerializer, SubscribeSerializer,
                          SubscriptionsSerializer, TagSerializer)
from reviews.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscription

User = get_user_model()


class ExtendedUserViewSet(DjoserUserViewSet):
    """
    Обрабатывает операции для модели ExtendedUser
    с помощью djoser.
    """
    queryset = User.objects.all()
    serializer_class = ExtendedUserSerializer
    lookup_field = 'id'
    paginator = CustomLimitPagination()

    @action(
        methods=['get'],
        detail=False,
        permission_classes=(permissions.IsAuthenticated,),
        url_path='me',
        url_name='me'
    )
    def me(self, request, *args, **kwargs):
        """
        Ограниченная версия эндпоинта /me/
        Только GET-запросы для аутентифицированных пользователей.
        """
        return super().me(request, *args, **kwargs)

    @action(
        methods=['put'],
        detail=False,
        permission_classes=(permissions.IsAuthenticated,),
        url_path='me/avatar',
        url_name='me/avatar'
    )
    def avatar(self, request):
        """
        Обрабатывает операцию по добавлению аватара
        пользователя для модели User.
        """
        serializer = ExtendedUserAvatarSerializer(
            instance=request.user,
            data=request.data,
            partial=False,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request, pk=None):
        """
        Обрабатывает операцию по удалению аватара
        пользователя для модели User.
        """
        user = request.user
        user.avatar.delete(save=False)
        user.save()
        return Response(
            {'detail': 'Аватар успешно удален.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        url_name='subscriptions',
        permission_classes=[permissions.IsAuthenticated],
        pagination_class=CustomLimitPagination
    )
    def subscriptions(self, request):
        """
        Обрабатывает операцию получения
        списка объектов модели Subscription.
        """
        user = request.user
        subscriptions = Subscription.objects.filter(
            user=user).select_related('author')
        authors = [sub.author for sub in subscriptions]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(authors, request)
        serializer = SubscriptionsSerializer(page, many=True, context={
            'request': request
        })
        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        url_path='subscribe',
        url_name='subscribe',
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        """
        Обрабатывает post запросы модели Subscription.
        """
        user = request.user
        author = get_object_or_404(User, pk=id)
        data = {
            'user': user.id,
            'author': author.id
        }
        serializer = SubscribeSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        """
        Обрабатывает delete запросы модели Subscription.
        """
        user = request.user
        author = get_object_or_404(User, pk=id)
        delete_cnt, _ = Subscription.objects.filter(
            user=user,
            author=author
        ).delete()
        if not delete_cnt:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'detail': 'Подписка удалена.'},
            status=status.HTTP_204_NO_CONTENT
        )


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Обрабатывает операции CRUD для модели Recipe.
    """
    queryset = Recipe.objects.prefetch_related(
        'tags',
        'ingredients_relations__ingredient',
        'favorites',
        'favorites__author',
        'shopping_carts',
        'shopping_carts__author'
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
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return RecipeSerializer
        return super().get_serializer_class()

    @action(
        detail=True,
        methods=['post'],
        url_path='favorite',
        url_name='favorite',
        permission_classes=[IsAuthenticated]

    )
    def favorite(self, request, id=None):
        """
        Обрабатывает операцию по добавлению рецепта в избранное.
        """
        author = request.user
        recipe = get_object_or_404(Recipe, pk=id)
        data = {
            'author': author.id,
            'recipe': recipe.id
        }
        serializer = FavoriteSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, id=None):
        """
        Обрабатывает операцию по удалению рецепта
        из избранного.
        """
        author = request.user
        recipe = get_object_or_404(Recipe, pk=id)
        delete_cnt, _ = Favorite.objects.filter(
            recipe=recipe,
            author=author
        ).delete()
        if not delete_cnt:
            return Response(
                {'detail': 'Рецепт отсутствует в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'detail': 'Рецепт удален из избранного.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True,
            methods=['get'],
            url_path='get-link',
            url_name='get-link',
            permission_classes=[IsAuthenticatedOrReadOnly])
    def get_short_link(self, request, id=None):
        """
        Обрабатывает операцию по получению короткой ссылки на рецепт.
        """
        recipe = get_object_or_404(Recipe, pk=id)
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
        """
        Обрабатывает операцию по скачиванию списка покупок,
        сформированный из рецептов, добавленных
        в список покупок.
        """
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

    @action(
        detail=True,
        methods=['post'],
        url_path='shopping_cart',
        url_name='shopping_cart',
        permission_classes=[IsAuthenticated]

    )
    def shopping_cart(self, request, id=None):
        """
        Обрабатывает операцию по добавлению рецепта
        в список покупок.
        """
        author = request.user
        recipe = get_object_or_404(Recipe, pk=id)
        data = {
            'author': author.id,
            'recipe': recipe.id
        }
        serializer = ShoppingCartSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, id=None):
        """
        Обрабатывает операцию по удалению рецепта
        из списка покупок.
        """
        author = request.user
        recipe = get_object_or_404(Recipe, pk=id)
        delete_cnt, _ = ShoppingCart.objects.filter(
            recipe=recipe,
            author=author
        ).delete()
        if not delete_cnt:
            return Response(
                {'detail': 'Рецепт отсутствует в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'detail': 'Рецепт успешно удален из списка покупок.'},
            status=status.HTTP_204_NO_CONTENT
        )


class ShortLinkRedirectView(APIView):
    """
    Обрабатывает операцию по отображению страницы рецепта
    по полученной короткой ссылки на рецепт.
    """
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
