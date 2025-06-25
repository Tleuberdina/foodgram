from rest_framework.pagination import PageNumberPagination
from users.constants import PAGE_SIZE


class CustomLimitPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = PAGE_SIZE
