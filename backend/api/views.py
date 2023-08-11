from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipes.models import Favourite, Ingredient, Recipe, ShoppingCart, Tag

from .filters import IngredientFilter, RecipeFilter
from .paginations import CustomPagination
from .permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeGetSerializer,
    RecipeShortSerializer,
    TagSerializer,
)
from .services import get_shopping_list


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly | IsAdminOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user

        is_favourited_subquery = Favourite.objects.filter(
            user=user, recipe=OuterRef("pk")
        )
        is_in_shopping_cart_subquery = ShoppingCart.objects.filter(
            user=user, recipe=OuterRef("pk")
        )

        queryset = Recipe.objects.annotate(
            is_favorited=Exists(is_favourited_subquery),
            is_in_shopping_cart=Exists(is_in_shopping_cart_subquery),
        )
        return queryset

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeGetSerializer
        return RecipeCreateUpdateSerializer

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk):
        return self.add_or_delete_obj(request, pk, Favourite)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk):
        return self.add_or_delete_obj(request, pk, ShoppingCart)

    def add_or_delete_obj(self, request, pk, model):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == "POST":
            obj, created = model.objects.get_or_create(
                user=request.user, recipe__id=pk
            )
            if obj.recipe.filter(id=pk):
                return Response(
                    {"errors": "Already exist!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            obj.recipe.set([recipe])
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        del_count, _ = model.objects.filter(
            user=request.user, recipe__id=pk
        ).delete()
        if del_count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        response = get_shopping_list(user)
        filename = f"{user.username}_cart.txt"
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
