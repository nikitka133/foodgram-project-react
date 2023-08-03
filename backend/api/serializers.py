from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework.exceptions import ValidationError
from rest_framework.fields import IntegerField, SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer

from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag
from users.models import Subscribe

User = get_user_model()


class CustomUserSerializer(ModelSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        user = self.context.get("request").user
        return (
            not user.is_anonymous
            and Subscribe.objects.filter(user=user, author=obj).exists()
        )


class SubscribeSerializer(ModelSerializer):
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "recipes_count",
            "recipes",
        )
        read_only_fields = ("email", "username")

    def validate(self, data):
        author = self.instance
        user = self.context.get("request").user
        if Subscribe.objects.filter(author=author, user=user).exists():
            raise ValidationError("Вы уже подписаны!")
        if user == author:
            raise ValidationError("Нельзя подписаться на себя!")
        return data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get("request")
        limit = request.GET.get("recipes_limit")
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        serializer = RecipeShortSerializer(recipes, many=True, read_only=True)
        return serializer.data


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class RecipeGetSerializer(ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = SerializerMethodField()
    image = Base64ImageField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_ingredients(self, obj):
        ingredients = obj.ingredients.prefetch_related(
            "ingredientinrecipe_set"
        )
        result = []

        for ingredient in ingredients:
            ingredient_in_recipe = ingredient.ingredientinrecipe_set.first()

            ingredient_data = {
                "id": ingredient.id,
                "name": ingredient.name,
                "measurement_unit": ingredient.measurement_unit,
                "amount": ingredient_in_recipe.amount
                if ingredient_in_recipe
                else None,
            }

            result.append(ingredient_data)

        return result

    def get_is_favorited(self, obj):
        user = self.context.get("request").user
        return (
            not user.is_anonymous
            and user.favorites.filter(recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get("request").user
        return (
            not user.is_anonymous
            and user.shopping_cart.filter(recipe=obj).exists()
        )


class IngredientInRecipeGetSerializer(ModelSerializer):
    id = IntegerField(write_only=True)

    class Meta:
        model = IngredientInRecipe
        fields = ("id", "amount")


class RecipeCreateUpdateSerializer(ModelSerializer):
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientInRecipeGetSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def validate_ingredients(self, value):
        if not value:
            raise ValidationError(
                {"ingredients": "Нужен хотя бы один ингридиент!"}
            )

        ingredients_list = []
        for item in value:
            ingredient = get_object_or_404(Ingredient, id=item["id"])
            if ingredient in ingredients_list:
                raise ValidationError(
                    {"ingredients": "Ингридиенты не должны повторяться"}
                )
            amount = item.get("amount", 0)
            if not isinstance(amount, int) or amount <= 0:
                raise ValidationError(
                    {"amount": "Укажите количество ингридиента"}
                )
            ingredients_list.append(ingredient)

        return value

    def validate_tags(self, value):
        if not value:
            raise ValidationError({"tags": "Нужно выбрать тег"})

        unique_tags = set()
        duplicate_tags = set()

        for tag in value:
            if tag in unique_tags:
                duplicate_tags.add(tag)
            else:
                unique_tags.add(tag)

        if duplicate_tags:
            raise ValidationError(
                {
                    "tags": "Теги должны быть уникальными! Обнаружены "
                            "повторяющиеся теги: "
                    + ", ".join(duplicate_tags)
                }
            )

        return value

    @transaction.atomic
    def create_ingredients_amounts(self, ingredients, recipe):
        ingredient_objs = []
        for ingredient in ingredients:
            ingredient_obj = get_object_or_404(Ingredient, id=ingredient["id"])
            ingredient_objs.append(
                IngredientInRecipe(
                    ingredient=ingredient_obj,
                    recipe=recipe,
                    amount=ingredient["amount"],
                )
            )

        IngredientInRecipe.objects.bulk_create(ingredient_objs)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)

        self.create_ingredients_amounts(ingredients=ingredients, recipe=recipe)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")

        instance = super().update(instance, validated_data)

        instance.tags.clear()
        instance.tags.set(tags)

        instance.ingredients.clear()
        self.create_ingredients_amounts(
            recipe=instance, ingredients=ingredients
        )

        return instance

    def to_representation(self, instance):
        request = self.context.get("request")
        context = {"request": request}
        return RecipeGetSerializer(instance, context=context).data


class RecipeShortSerializer(ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
