from django.contrib import admin

from .models import (Favourite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, Tag)


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


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "measurement_unit",
    )
    list_filter = ("name",)


class TagAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "color",
        "slug",
    )


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "recipe",
    )


class FavouriteAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "recipe",
    )


class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = (
        "recipe",
        "ingredient",
        "amount",
    )


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Favourite, FavouriteAdmin)
admin.site.register(IngredientInRecipe, IngredientInRecipeAdmin)
