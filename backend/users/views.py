from django.contrib.auth import get_user_model
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .pagination import CustomLimitPagination
from .serializers import MyUserAvatarSerializer, MyUserSerializer

User = get_user_model()


class MyUserViewSet(APIView):
    """
    Обрабатывает операции по просмотрю списка пользователей,
    регистрации пользователей для модели User.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        queryset = User.objects.all()
        paginator = CustomLimitPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = MyUserSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        django_request = request._request
        create_view = DjoserUserViewSet.as_view({'post': 'create'})
        return create_view(django_request)


class MyUserProfileViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Обрабатывает операцию по просмотру профиля пользователя модели User."""
    queryset = User.objects.all()
    serializer_class = MyUserSerializer
    lookup_field = 'id'
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def retrieve(self, request, id):
        try:
            user = User.objects.get(pk=id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Страница не найдена."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = MyUserSerializer(user, context={'request': request})
        return Response(serializer.data)


class MyUserAvatarViewSet(viewsets.ViewSet):
    """
    Обрабатывает операции по добавлению и
    удалению аватара пользователя для модели User.
    """
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def put(self, request):
        serializer = MyUserAvatarSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        user = request.user
        default_avatar_path = 'avatar-icon.png'
        user.avatar = default_avatar_path
        user.save()
        return Response(
            {'detail': 'Аватар успешно удален.'},
            status=status.HTTP_204_NO_CONTENT
        )
