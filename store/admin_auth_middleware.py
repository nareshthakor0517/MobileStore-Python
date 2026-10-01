from django.shortcuts import redirect
from django.urls import reverse

class AdminAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # allow login & logout
        if path.startswith("/admin-login/") or path.startswith("/admin-logout/"):
            return self.get_response(request)

        # protect admin pages
        if path.startswith("/admin-panel/") or path.startswith("/admin/"):
            if not request.session.get("admin_id"):
                return redirect("admin_login")

        return self.get_response(request)
