import django_filters

from reviews.models import Ingredient, Recipe


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(
        field_name='author__id',
        lookup_expr='exact'
    )
    tags = django_filters.CharFilter(method='filter_tags')
    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

    def filter_tags(self, queryset, name, value):
        tags_list = self.request.GET.getlist('tags')
        if tags_list:
            return queryset.filter(tags__slug__in=tags_list).distinct()
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        author = self.request.user
        if not author.is_authenticated:
            return queryset.none() if value else queryset
        if value:
            return queryset.filter(favorites__author=author)
        return queryset.exclude(favorites__author=author)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        author = self.request.user
        if not author.is_authenticated:
            return queryset.none() if value else queryset
        if value:
            return queryset.filter(shopping_carts__author=author)
        return queryset.exclude(shopping_carts__author=author)


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)
