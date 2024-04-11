import factory
from django.contrib.auth.models import User
from white_rabbit.models import Employee, Company
from datetime import datetime


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker('user_name')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Faker('company')


class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee

    user = factory.SubFactory(UserFactory)
    calendar_ical_url = factory.Faker('url')
    default_day_working_hours = 8
    min_working_hours_for_full_day = 6.0
    company = factory.SubFactory(CompanyFactory)
    start_time_tracking_from = factory.LazyFunction(datetime.now)
    end_time_tracking_on = None
    works_day_1 = True
    works_day_2 = True
    works_day_3 = True
    works_day_4 = True
    works_day_5 = True
    works_day_6 = False
    works_day_7 = False
    disabled = False
