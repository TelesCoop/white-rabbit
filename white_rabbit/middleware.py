from django.shortcuts import redirect


def is_acceptable_path(request_path: str):
    return request_path.startswith("/admin/login")


def only_logged_in_users(get_response):
    def middleware(request):
        if request.user.is_anonymous and not is_acceptable_path(request.path):
            print(f"anonymous user, request.path={request.path}")
            return redirect("/admin/login/")

        return get_response(request)

    return middleware
