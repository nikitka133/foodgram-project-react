from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

User = get_user_model()


class Recipe(models.Model):
    name = models.CharField("Рецепт", max_length=200)
    author = models.ForeignKey(
        User,
        related_name="recipes",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Автор рецепта",
    )
    text = models.TextField("Описание рецепта")
    ingredients = models.ManyToManyField(
        "Ingredient",
        through="RecipeIngredient",
        related_name="recipes",
        verbose_name="Ингредиенты",
    )
    tags = models.ManyToManyField(
        "Tag", related_name="recipes", verbose_name="Теги"
    )
    cooking_time = models.PositiveSmallIntegerField(
        "Время приготовления",
        validators=[MinValueValidator(1, message="Минимальное время 1")],
    )
    image = models.ImageField("Изображение", upload_to="img/")

    class Meta:
        ordering = ["-id"]
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField("Игридиент", max_length=200)
    measurement_unit = models.CharField("Единица измерения", max_length=200)

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class Tag(models.Model):
    name = models.CharField("Тег", unique=True, max_length=200)
    color = models.CharField(
        "HEX-код",
        unique=True,
        max_length=7,
        validators=[
            RegexValidator(
                regex="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$",
                message="Введите код в формате HEX!",
            )
        ],
    )
    slug = models.SlugField("Уникальный слаг", unique=True, max_length=200)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name="Ингредиент",
        related_name="recipe_ingredients",
    )
    amount = models.PositiveSmallIntegerField(
        "Количество",
        validators=[MinValueValidator(1, message="Минимальное количество 1")],
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"

    def __str__(self):
        return (
            f"{self.ingredient.name}, {self.ingredient.measurement_unit}"
            f" - {self.amount} "
        )


class Favourite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    recipe = models.ManyToManyField(
        Recipe,
        related_name="favorites",
        verbose_name="Избранные рецепты",
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

    def __str__(self):
        return f"Избранные рецепты у {self.user}"


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Пользователь",
    )
    recipe = models.ManyToManyField(
        Recipe,
        related_name="shopping_cart",
        verbose_name="Рецепты в корзине",
    )

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзина"

    def __str__(self):
        return f"Рецепты в корзине у {self.user}"
