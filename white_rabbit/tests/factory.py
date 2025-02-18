from datetime import datetime, timedelta
import factory
from django.contrib.auth.models import User
from white_rabbit.models import Employee, Company, Project, Invoice


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Faker("company")
    daily_employee_cost = 200
    profitability_threshold = 400
    daily_market_price = 600


class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee

    user = factory.SubFactory(UserFactory)
    calendar_ical_url = factory.Faker("url")
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


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    company = factory.SubFactory(CompanyFactory)
    name = factory.Faker("company")
    start_date = factory.LazyAttribute(lambda a: datetime(2022, 1, 1))
    end_date = factory.LazyAttribute(lambda a: datetime.now())

    @factory.post_generation
    def days_and_sold(self: Project, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            days_count, amount = extracted
            InvoiceFactory.create(project=self, amount=amount, days_count=days_count)
            self.save()


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    project = factory.SubFactory(ProjectFactory)
    number = factory.Faker("random_int")
    amount = factory.Faker("random_int", min=1000, max=10000)
    days_count = factory.Faker("random_int", min=1, max=20)
    date = factory.LazyAttribute(lambda a: datetime.now())


class EventFactory(factory.DictFactory):
    project_id = factory.Faker("random_int")
    project_name = factory.Faker("company")
    name = factory.Faker("company")
    subproject_name = None
    duration = 1.0
    start_datetime = factory.LazyAttribute(lambda a: datetime.now())
    end_datetime = factory.LazyAttribute(
        lambda a: datetime.now() + timedelta(hours=a.duration)
    )
    category = factory.Faker("word")
