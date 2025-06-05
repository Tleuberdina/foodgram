import json

from django.core.management.base import BaseCommand

from foods.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт ингредиентов из JSON файла'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Путь к JSON файлу')

    def handle(self, *args, **kwargs):
        json_file_path = kwargs['json_file']
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f"Файл не найден: {json_file_path}")
            return
        except json.JSONDecodeError as e:
            self.stderr.write(f"Ошибка разбора JSON: {e}")
            return

        for item in data:
            name = item.get('name')
            measurement_unit = item.get('measurement_unit')
            if name and measurement_unit:
                Ingredient.objects.update_or_create(
                    name=name,
                    defaults={'measurement_unit': measurement_unit}
                )
                self.stdout.write(f"Обработан ингредиент: {name}")
            else:
                self.stderr.write(f"Некорректный объект: {item}")

        self.stdout.write(self.style.SUCCESS('Импорт завершен'))
