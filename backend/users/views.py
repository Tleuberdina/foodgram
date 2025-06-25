from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.pagination import CustomLimitPagination
from api.permissions import AuthorOrReadOnly
from .models import Subscription
from .serializers import (ExtendedUserAvatarSerializer, ExtendedUserSerializer,
                          SubscribeSerializer, SubscriptionsSerializer)

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
        methods=["get"],
        detail=False,
        permission_classes=(permissions.IsAuthenticated,),
        url_path="me",
        url_name="me"
    )
    def me(self, request, *args, **kwargs):
        """
        Ограниченная версия эндпоинта /me/
        Только GET-запросы для аутентифицированных пользователей.
        """
        return super().me(request, *args, **kwargs)

    @action(
        methods=["put", "delete"],
        detail=False,
        permission_classes=(permissions.IsAuthenticated,),
        url_path="me/avatar",
        url_name="me/avatar"
    )
    def me_avatar(self, request):
        """
        Обрабатывает операцию по добавлению/удалению аватара
        пользователя для модели User.
        """
        if request.method == 'PUT':
            serializer = ExtendedUserAvatarSerializer(
                instance=request.user,
                data=request.data,
                partial=False,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        elif request.method == 'DELETE':
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
        permission_classes=[AuthorOrReadOnly],
        pagination_class=CustomLimitPagination
    )
    def subscriptions(self, request):
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

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        url_name='subscribe',
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, pk=id)
        if request.method == 'POST':
            data = {
                'user': user.id,
                'author': id
            }
            serializer = SubscribeSerializer(
                data=data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            subscription = serializer.save()
            return Response(
                serializer.to_representation(subscription),
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            delete_cnt, _ = Subscription.objects.filter(
                user=user,
                author=author
            ).delete()
            if delete_cnt > 0:
                return Response(
                    {'detail': 'Подписка удалена.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {'detail': 'Вы не подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
