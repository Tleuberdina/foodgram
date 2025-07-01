#Домен проекта: muyfoodgram.hopto.org

###Описание:
Учебный проект в рамках курса "Python-разработчик" от Яндекс.Практикум.
Реализует backend-часть и API приложения foodgram.
Проект «Фудграм» — сайт, на котором пользователи могут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также доступен сервис «Список покупок». Он позволяет создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

# Инструкция по развертыванию проекта в Docker

## Предварительные требования
- Установленный Docker и Docker Compose

## Шаги развертывания

1. Клонируйте репозиторий:
git clone git@github.com:Tleuberdina/foodgram.git
cd foodgram

2. Постройте и запустите контейнеры:
docker-compose up -d --build

3. Выполните миграции:
docker-compose exec web python manage.py migrate

4. Откройте проект в браузере по адресу:
http://localhost:8000/

###Технологии:

- Python 3.12.7
- Django
- Django REST Framework
- Djoser
- PostgreSQL
- GitHub Actions

###Документация проекта: http://localhost/api/docs/

###Команда для запуска теста проекта: python manage.py test

###Команда для наполнения БД данными: python manage.py import_json

###Примеры запросов/ответов проекта: 
При POST запросе на создание рецепта зарегистрированного пользователя
http://127.0.0.1:8000/api/recipes/
{
"ingredients": [
{"id": 1, "amount": 100}
],
"tags": [
1,
2,
3
],
"image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
"name": "string",
"text": "string",
"cooking_time": 1
}
ответ:
{
    "id": 26,
    "tags": [
        {
            "id": 1,
            "name": "Завтрак",
            "slug": "breakfast"
        },
        {
            "id": 2,
            "name": "Обед",
            "slug": "lunch"
        },
        {
            "id": 3,
            "name": "Ужин",
            "slug": "dinner"
        }
    ],
    "author": {
        "email": "y@yandex.ru",
        "id": 3,
        "username": "y.cat",
        "first_name": "Кот",
        "last_name": "Котович",
        "is_subscribed": false,
        "avatar": null
    },
    "ingredients": [
        {
            "id": 1,
            "name": "Молоко",
            "measurement_unit": "мл",
            "amount": 100
        }
    ],
    "is_favorited": false,
    "is_in_shopping_cart": false,
    "name": "string",
    "image": "http://127.0.0.1:8000/media/recipes/images/temp_tKwagf1.png",
    "text": "string",
    "cooking_time": 1
}
При POST запросе на регистрацию пользователя http://127.0.0.1:8000/api/users/
Copy
{
"email": "vpupkin@yandex.ru",
"username": "vasya.pupkin",
"first_name": "Вася",
"last_name": "Иванов",
"password": "Qwerty12345678910"
}
ответ:
{
"email": "vpupkin@yandex.ru",
"id": 2,
"username": "vasya.pupkin",
"first_name": "Вася",
"last_name": "Иванов"
}
###Автор проекта: Юлия Тлеубердина (https://github.com/Tleuberdina)