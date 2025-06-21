import django_filters

from .models import Ingredient, Recipe


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(
        field_name='author__id',
        lookup_expr='exact'
    )
    tags = django_filters.CharFilter(method='filter_tags')

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

    def filter_tags(self, queryset, name, value):
        tags_list = self.request.GET.getlist('tags')
        if tags_list:
            return queryset.filter(tags__slug__in=tags_list).distinct()
        return queryset


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )
    
    class Meta:
        model = Ingredient
        fields = ('name',)
