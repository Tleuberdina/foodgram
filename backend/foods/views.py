from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.views import APIView
from users.pagination import CustomLimitPagination

from .filters import RecipeFilter
from .models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                     ShoppingCart, Subscription, Tag)
from .pagination import SubscriptionsCustomLimitPagination
from .permissions import AuthorOrReadOnly, ReadOnly
from .serializers import (FavoriteListSerializer,
                          FavoriteShoppingCartSerializer, IngredientSerializer,
                          RecipeCreateSerializer, RecipeReadSerializer,
                          ShoppingCartListSerializer, SubscribeSerializer,
                          SubscriptionsSerializer, TagSerializer)

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
    ).order_by('-pub_date')
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
        elif self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            'favorites',
            'favorites__user',
            'shopping_carts',
            'shopping_carts__user'
        )
        user = self.request.user
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited and user.is_authenticated:
            is_favorited = is_favorited.lower() in ['1']
            if is_favorited:
                queryset = queryset.filter(favorites__user=user)
            else:
                queryset = queryset.exclude(favorites__user=user)
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        if is_in_shopping_cart and user.is_authenticated:
            is_in_shopping_cart = is_in_shopping_cart.lower() in ['1']
            if is_in_shopping_cart:
                queryset = queryset.filter(shopping_carts__user=user)
            else:
                queryset = queryset.exclude(shopping_carts__user=user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def partial_update(self, request, id):
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Страница не найдена."},
                status=status.HTTP_404_NOT_FOUND
            )
        if request.user != recipe.author:
            return Response(
                {'detail': 'У вас недостаточно прав.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(
            recipe,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, id):
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Страница не найдена."},
                status=status.HTTP_404_NOT_FOUND
            )
        if request.user != recipe.author:
            return Response(
                {'detail': 'У вас недостаточно прав.'},
                status=status.HTTP_403_FORBIDDEN
            )
        recipe.delete()
        return Response(
            {'detail': 'Рецепт успешно удален.'},
            status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['get'],
            url_path='get-link',
            url_name='get-link',
            permission_classes=[IsAuthenticatedOrReadOnly])
    def get_short_link(self, request, id=None):
        try:
            recipe = Recipe.objects.get(id=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        recipe = self.get_object()
        short_code = recipe.generate_short_code()
        return Response({
            "short-link": request.build_absolute_uri(f"/s/{short_code}")
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
        try:
            recipe = Recipe.objects.get(short_code=short_code)
            return redirect(f'/recipes/{recipe.id}')
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )


class IngredientViewSet(viewsets.ModelViewSet):
    """Обрабатывает операции CRUD для модели Ingredient."""
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = (permissions.IsAdminUser,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)

    def get_permissions(self):
        if self.action == 'retrieve' or self.action == 'list':
            return (ReadOnly(),)
        return super().get_permissions()


class TagViewSet(viewsets.ModelViewSet):
    """Обрабатывает операции CRUD для модели Tag."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAdminUser,)
    lookup_field = 'id'

    def get_permissions(self):
        if self.action == 'retrieve' or self.action == 'list':
            return (ReadOnly(),)
        return super().get_permissions()

    def retrieve(self, request, id):
        try:
            tag = Tag.objects.get(pk=id)
        except Tag.DoesNotExist:
            return Response(
                {"detail": "Страница не найдена."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = TagSerializer(tag, context={'request': request})
        return Response(serializer.data)


class SubscribeView(APIView):
    """Обрабатывает запросы get, post, delete для модели Subscription."""
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SubscriptionsCustomLimitPagination

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        url_name='subscriptions',
        permission_classes=[AuthorOrReadOnly]

    )
    def get(self, request):
        user = request.user
        subscriptions = Subscription.objects.filter(
            user=user).select_related('author')
        authors = [sub.author for sub in subscriptions]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(authors, request)
        recipes_limit = request.query_params.get('recipes_limit')
        try:
            recipes_limit = int(recipes_limit) if recipes_limit else None
        except (TypeError, ValueError):
            recipes_limit = 6

        serializer = SubscriptionsSerializer(page, many=True, context={
            'request': request,
            'recipes_limit': recipes_limit
        })
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        user = request.user
        author = get_object_or_404(User, pk=id)

        if user == author:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Subscription.objects.filter(user=user, author=author).exists():
            return Response(
                {'detail': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Subscription.objects.create(user=user, author=author)
        serializer = SubscribeSerializer(
            author,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        user = request.user
        try:
            author = User.objects.get(pk=id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            subscription = Subscription.objects.get(user=user, author=author)
            subscription.delete()
            return Response(
                {'detail': 'Подписка удалена.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Subscription.DoesNotExist:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class FavoriteView(APIView):
    """Обрабатывает get, post, delete для модели Favorite."""
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SubscriptionsCustomLimitPagination

    @action(
        detail=False,
        methods=['get'],
        url_path='favorites',
        url_name='favorites',
        permission_classes=[AuthorOrReadOnly]

    )
    def get(self, request):
        user = request.user
        favorites = Favorite.objects.filter(user=user).select_related('recipe')
        recipes = [sub.recipe for sub in favorites]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(recipes, request)
        serializer = FavoriteListSerializer(page, many=True, context={
            'request': request
        })
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        favorite, created = Favorite.objects.get_or_create(
            user=user,
            recipe=recipe
        )
        if not created:
            return Response(
                {'detail': 'Данный рецепт уже добавлен в избранное.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = FavoriteShoppingCartSerializer(
            recipe,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            favorite = Favorite.objects.get(user=user, recipe=recipe)
            favorite.delete()
            return Response(
                {'detail': 'Рецепт успешно удален из избранного.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Favorite.DoesNotExist:
            return Response(
                {'detail': 'Рецепт отсутствует в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ShoppingCartView(APIView):
    """
    Обрабатывает get, post, delete для модели ShoppingCart.
    """
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = SubscriptionsCustomLimitPagination

    @action(
        detail=False,
        methods=['get'],
        url_path='shopping_carts',
        url_name='shopping_carts',
        permission_classes=[AuthorOrReadOnly]

    )
    def get(self, request):
        user = request.user
        shopping_carts = ShoppingCart.objects.filter(
            user=user).select_related('recipe')
        recipes = [sub.recipe for sub in shopping_carts]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(recipes, request)
        serializer = ShoppingCartListSerializer(page, many=True, context={
            'request': request
        })
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        shopping_cart, created = ShoppingCart.objects.get_or_create(
            user=user,
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
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            return Response(
                {'detail': 'Страница не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            shopping_cart = ShoppingCart.objects.get(user=user, recipe=recipe)
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
