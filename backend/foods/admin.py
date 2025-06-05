from django.contrib import admin
from django.db.models import Count

from .models import Ingredient, Recipe, Tag


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'get_author_username',
        'favorites_count'
    )
    list_select_related = ('author',)

    def get_author_username(self, obj):
        return obj.author.username
    get_author_username.short_description = 'Автор (username)'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _favorites_count=Count('favorites'))
        return queryset

    def favorites_count(self, obj):
        return obj._favorites_count
    favorites_count.short_description = 'В избранном'

    search_fields = ('name', 'author__username')
    list_filter = ('tags',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit'
    )
    search_fields = ('^name',)


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag)
admin.site.register(Recipe, RecipeAdmin)
