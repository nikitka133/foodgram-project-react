from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserSerializer as DjoserUserSerialiser
from drf_extra_fields.fields import Base64ImageField
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import BooleanField, SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer
from users.models import Subscribe

User = get_user_model()


class UserSerializer(DjoserUserSerialiser):
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
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientGetSerializer(ModelSerializer):
    id = serializers.IntegerField(source="ingredient.id")
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit", read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            "id",
            "name",
            "measurement_unit",
            "amount",
        )


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class RecipeGetSerializer(ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    image = Base64ImageField()
    is_favorited = BooleanField(read_only=True, default=False)
    is_in_shopping_cart = BooleanField(read_only=True, default=False)
    ingredients = RecipeIngredientGetSerializer(
        many=True, read_only=True, source="recipe_ingredients"
    )

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


class RecipeCreateUpdateSerializer(ModelSerializer):
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientGetSerializer(many=True)
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

    def validate_cooking_time(self, value):
        if value <= 1:
            raise serializers.ValidationError(
                "Время приготовления должно быть больше 1"
            )
        return value

    def validate_ingredients(self, value):
        if not value:
            raise ValidationError(
                {"ingredients": ["Нужен хотя бы один ингредиент"]}
            )

        ingredient_ids = [item["ingredient"]["id"] for item in value]
        ingredients = Ingredient.objects.filter(id__in=ingredient_ids)

        ingredients_dict = {
            ingredient.id: ingredient for ingredient in ingredients
        }

        errors = []

        ingredients_list = []

        for item in value:
            ingredient_id = item["ingredient"]["id"]
            ingredient = ingredients_dict.get(ingredient_id)

            if not ingredient:
                errors.append({"ingredient": ["Недопустимый ингредиент"]})
            elif ingredient in ingredients_list:
                errors.append({"ingredient": ["Не должны повторятся"]})

            if int(item["amount"]) <= 0:
                errors.append({"ingredient": ["Минимальное количество 1"]})

            ingredients_list.append(ingredient)

        if errors:
            raise ValidationError(errors)

        return value

    def validate_tags(self, value):
        if not value:
            raise ValidationError({"tags": ["Нужно выбрать тег"]})

        unique_tags = set()
        duplicate_tags = set()

        for tag in value:
            if tag in unique_tags:
                duplicate_tags.add(tag)
            else:
                unique_tags.add(tag)

        if duplicate_tags:
            raise ValidationError({"tags": ["Теги должны быть уникальными!"]})

        return value

    @transaction.atomic
    def create_ingredients_amounts(self, ingredients, recipe):
        ingredient_ids = [
            ingredient["ingredient"]["id"] for ingredient in ingredients
        ]
        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)

        ingredient_objs = [
            RecipeIngredient(
                ingredient=ingredient,
                recipe=recipe,
                amount=next(
                    item["amount"]
                    for item in ingredients
                    if item["ingredient"]["id"] == ingredient.id
                ),
            )
            for ingredient in existing_ingredients
        ]

        RecipeIngredient.objects.bulk_create(ingredient_objs)

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
