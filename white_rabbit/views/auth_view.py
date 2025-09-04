from django.contrib.auth.views import LoginView


class MyLoginView(LoginView):
    template_name = "admin/login.html"
