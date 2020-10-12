from rest_framework.permissions import BasePermission


class PagePermission(BasePermission):
    def has_permission(self, request, view):
        if request.auth is None:
            return False

        return 'page' in request.auth
