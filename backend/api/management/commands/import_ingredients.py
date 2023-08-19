import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Import ingredients data from JSON file"

    def handle(self, *args, **options):
        filename = "ingredients.json"
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        file_path = os.path.join(project_root, "data", filename)

        with open(file_path, "r", encoding="UTF-8") as f:
            data = json.load(f)
            new_data = []

            for item in data:
                name = item["name"]
                measurement_unit = item["measurement_unit"]

                if not Ingredient.objects.filter(
                    name=name, measurement_unit=measurement_unit
                ).exists():
                    new_data.append(
                        Ingredient(
                            name=name, measurement_unit=measurement_unit
                        )
                    )

            if new_data:
                with transaction.atomic():
                    Ingredient.objects.bulk_create(new_data)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Добавлено ингредиентов: {len(new_data)}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("Нет ингредиентов для импорта")
                )
