from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_superuser


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user
