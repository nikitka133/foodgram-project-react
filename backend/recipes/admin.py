from django.contrib import admin

from .models import (
    Favourite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "author", "added_in_favorites")

    def added_in_favorites(self, obj):
        return obj.favorites.count()

    added_in_favorites.short_description = "Количество рецептов в избранных"
    readonly_fields = ("added_in_favorites",)
    list_filter = (
        "author",
        "name",
        "tags",
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "measurement_unit",
    )
    list_filter = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "color",
        "slug",
    )


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "recipes_list",
    )

    def recipes_list(self, obj):
        return ", ".join([recipe.name for recipe in obj.recipe.all()])

    recipes_list.short_description = "Рецепты"


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "recipes_count",
    )

    def recipes_count(self, obj):
        return obj.recipe.count()

    recipes_count.short_description = "Количество рецептов"


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = (
        "recipe",
        "ingredient",
        "amount",
    )
