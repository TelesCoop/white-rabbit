import datetime


def user_is_staff(request):
    return {
        "user_is_staff": request.user.is_staff,
        "current_month": datetime.date.today().strftime("%m-%Y"),
    }
