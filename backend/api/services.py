import io
import json
import os

from django.db import transaction
from django.db.models import Sum
from recipes.models import Ingredient, RecipeIngredient
from rest_framework import status
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND


def get_shopping_list(user):
    if not user.shopping_cart.exists():
        return Response(status=HTTP_404_NOT_FOUND)

    ingredients = (
        RecipeIngredient.objects.filter(recipe__shopping_cart__user=user)
        .values("ingredient__name", "ingredient__measurement_unit")
        .annotate(amount=Sum("amount"))
    )

    ingredients_list = "Список ингредиентов:\n"
    ingredients_list += "\n".join(
        [
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ]
    )

    buffer = io.BytesIO(ingredients_list.encode("utf-8"))

    return buffer


def import_data_from_csv():
    filename = "ingredients.json"
    current_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_path, "..", "data", filename)

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
                    Ingredient(name=name, measurement_unit=measurement_unit)
                )

        if new_data:
            with transaction.atomic():
                Ingredient.objects.bulk_create(new_data)
            return Response(
                {"message": f"Добавлено ингредиентов: {len(new_data)}"},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"message": "Нет ингредиентов для импорта"},
                status=status.HTTP_400_BAD_REQUEST,
            )
