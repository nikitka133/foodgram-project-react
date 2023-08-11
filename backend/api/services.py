import io

from django.db.models import Sum
from django.http import FileResponse
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND

from recipes.models import RecipeIngredient


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

    content_type = "text/plain"

    buffer = io.BytesIO(ingredients_list.encode("utf-8"))
    response = FileResponse(buffer, content_type=content_type)

    return response
