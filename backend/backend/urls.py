from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from foods.views import (FavoriteView, IngredientViewSet, RecipeViewSet,
                         ShoppingCartView, SubscribeView, TagViewSet,
                         short_link_redirect)
from rest_framework.routers import DefaultRouter
from users.views import (MyUserAvatarViewSet, MyUserProfileViewSet,
                         MyUserViewSet)

router = DefaultRouter()
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/subscriptions/',
         SubscribeView.as_view(),
         name='subscriptions'),
    path('api/users/<int:id>/subscribe/',
         SubscribeView.as_view(),
         name='subscribe'),
    path('api/users/favorites/', FavoriteView.as_view(), name='favorites'),
    path('api/users/shopping_carts/',
         ShoppingCartView.as_view(),
         name='shopping_carts'),
    path('api/recipes/<int:id>/favorite/',
         FavoriteView.as_view(),
         name='favorite'),
    path('api/recipes/<int:id>/shopping_cart/',
         ShoppingCartView.as_view(),
         name='shopping_cart'),
    path('api/users/', MyUserViewSet.as_view(), name='users_list'),
    path('api/users/<int:id>/', MyUserProfileViewSet.as_view(
        {'get': 'retrieve'}), name='users_profile'),
    path('api/users/me/avatar/', MyUserAvatarViewSet.as_view(
        {'put': 'put',
         'delete': 'delete'})),
    path('api/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/', include(router.urls)),
    path('s/<str:short_code>/', short_link_redirect, name='short-link-redirect'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
