from rest_framework.permissions import BasePermission


class PagePermission(BasePermission):
    def has_permission(self, request, view):
        if request.auth is None:
            return False
        page = request.auth.get('page')
        return page is not None and page.is_enable
