from rest_framework.permissions import BasePermission


class OnlyAuthor(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.author == request.user


class IsSelfOrReadOnly(BasePermission):
    """
    Для /users/me/ — только текущий пользователь может получить данные.
    """
    def has_permission(self, request, view):
        if view.action == 'retrieve':
            return request.user and request.user.is_authenticated
        return True


class IsSelfForPasswordChange(BasePermission):
    """
    Для /users/set_password/ — только текущий пользователь может менять пароль.
    """
    def has_permission(self, request, view):
        user_id = view.kwargs.get('pk') or view.request.data.get('user_id')
        return (request.user and request.user.is_authenticated
                and str(request.user.id) == str(user_id))
