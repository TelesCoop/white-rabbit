from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

from white_rabbit.admin.company import is_user_admin

from white_rabbit.models import (
    Project,
    Alias,
    Category,
    Invoice,
    ForecastProject,
    EmployeeForecastAssignment,
    Employee,
)


class InvoiceInline(admin.TabularInline):
    model = Invoice
    can_delete = True

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Invoice.objects.all()
        return Invoice.objects.filter(project__company__admins=request.user)

    def has_module_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj):
        return True


class BaseProjectAdmin(admin.ModelAdmin):
    """Base admin class for Project and ForecastProject with shared functionality."""

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit the choices of the category field to the company's."""
        if db_field.name == "category":
            project_id = request.resolver_match.kwargs.get("object_id")
            if project_id:
                project = self.model.objects.get(pk=project_id)
                kwargs["queryset"] = Category.objects.filter(
                    company=project.company
                ).order_by("name")
            else:
                kwargs["queryset"] = Category.objects.filter(
                    company__admins=request.user
                ).order_by("name")
        if db_field.name == "company":
            # Limit the company choices to the companies the user is admin of
            if not request.user.is_superuser:
                kwargs["queryset"] = request.user.companies.all().order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_permission(self, request):
        if request.user.is_anonymous:
            return False

        if request.user.is_superuser:
            return True

        # if admin of at least one company
        if is_user_admin(request.user):
            return True

        return False

    def has_module_permission(self, request):
        return self.has_permission(request)

    def has_add_permission(self, request):
        return self.has_permission(request)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return self.has_permission(request)
        if request.user.is_superuser:
            return True
        return obj.company.admins.filter(pk=request.user.pk).exists()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class AliasInline(admin.StackedInline):
    model = Alias
    can_delete = True
    verbose_name_plural = "Aliases"
    exclude = ("lowercase_name",)

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Alias.objects.all()
        return Alias.objects.filter(project__company__admins=request.user)

    def has_module_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj):
        return True


@admin.register(Project)
class ProjectAdmin(BaseProjectAdmin):
    list_display = (
        "name",
        "company",
        "category",
        "start_date",
        "end_date",
        "estimated_days_count",
        "total_sold",
        "created",
    )
    list_filter = [
        "category",
        ("estimated_days_count", admin.BooleanFieldListFilter),
    ]
    readonly_fields = ("estimated_days_count", "total_sold")
    exclude = ("lowercase_name",)
    inlines = (InvoiceInline, AliasInline)
    search_fields = ["aliases__name", "name"]
    actions = ["transform_project_to_alias", "duplicate_project"]

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(company__admins=request.user)

    def transform_project_to_alias(self, request, queryset):
        if "apply" in request.POST:
            selected_project_id = int(request.POST.get("selected_project"))

            # if some data has been filled in the alias, prevent deleting it
            project_filled_fields = [
                "estimated_days_count",
                "total_sold",
                "category",
                "start_date",
            ]
            for project_to_transform in queryset:
                if any(
                    getattr(project_to_transform, field)
                    for field in project_filled_fields
                ):
                    messages.error(
                        request,
                        f"Impossible de transformer le projet {project_to_transform.name} en alias car il contient des informations spécifiques, on risquerait de perdre des données. Supprimez toutes les informations telles que date de début, catégories, jours prévus, total vendu et recommencez.",
                    )
                    return redirect(reverse("admin:white_rabbit_project_changelist"))

            for project_to_transform in queryset:
                project_to_transform.aliases.all().update(
                    project_id=selected_project_id
                )
                Alias(
                    name=project_to_transform.name, project_id=selected_project_id
                ).save()
                project_to_transform.delete()

            # Redirect to our admin view after our update has completed
            self.message_user(
                request,
                "{} projets transformés en alias de {}".format(
                    queryset.count(), Project.objects.get(pk=selected_project_id).name
                ),
            )
            return HttpResponseRedirect(request.get_full_path())

        company = queryset.first().company
        if queryset.exclude(company=company).exists():
            messages.error(
                request,
                "Tous les projets selectionnés doivent appartenir à la même entreprise",
            )
            return

        projects = (
            Project.objects.filter(company=company)
            .exclude(name__in=queryset.values_list("name", flat=True))
            .order_by("name")
        )
        return render(
            request,
            "admin/project_to_alias_intermediate.html",
            context={"new_aliases": queryset, "projects": projects, "action": True},
        )

    transform_project_to_alias.short_description = (  # type: ignore
        "Transformer en alias d'un autre projet"
    )

    def duplicate_project(self, request, queryset):
        if len(queryset) > 1:
            messages.error(
                request,
                "Vous ne pouvez dupliquer qu'un seul projet à la fois",
            )
            return redirect(reverse("admin:white_rabbit_project_changelist"))

        project = queryset.first()
        new_project = Project(
            name=f"{project.name} copie",
            company=project.company,
            category=project.category,
            start_date=project.start_date,
            estimated_days_count=project.estimated_days_count,
            total_sold=project.total_sold,
        )
        new_project.save()
        for alias in project.aliases.all():
            Alias(name=alias.name, project=new_project).save()
        return redirect(
            reverse("admin:white_rabbit_project_change", args=(new_project.pk,))
        )

    duplicate_project.short_description = "Dupliquer le projet"  # type: ignore

    def save_model(self, request, obj, form, change):
        pass  # don't actually save the parent instance

    def save_formset(self, request, form, formset, change):
        formset.save()  # this will save the children
        form.instance.save()  # form.instance is the parent


class EmployeeForecastAssignmentInline(admin.TabularInline):
    model = EmployeeForecastAssignment
    extra = 1
    autocomplete_fields = ["employee"]
    fields = ("employee", "start_date", "end_date", "estimated_days")
    verbose_name = "Affectation d'employé"
    verbose_name_plural = "Affectations d'employés"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit employee choices to the same company as the forecast project"""
        if db_field.name == "employee":
            forecast_project = getattr(request, "_obj_", None)
            company = getattr(forecast_project, "company", None)
            if company:
                kwargs["queryset"] = Employee.objects.filter(company=company)
            else:
                user_employee = getattr(request.user, "employee", None)
                company = getattr(user_employee, "company", None)
                if company:
                    kwargs["queryset"] = Employee.objects.filter(company=company)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    search_fields = ["user__first_name", "user__last_name", "user__username"]


@admin.register(ForecastProject)
class ForecastProjectAdmin(BaseProjectAdmin):
    list_display = (
        "name",
        "company",
        "category",
        "start_date",
        "end_date",
        "estimated_days_count",
        "total_sold",
        "created",
    )
    list_filter = [
        "category",
        "start_date",
        "end_date",
    ]
    fields = (
        "name",
        "company",
        "category",
        "notes",
        "start_date",
        "end_date",
        "estimated_days_count",
        "total_sold",
    )
    exclude = ("lowercase_name", "is_forecast")
    search_fields = ["name"]

    def get_queryset(self, request):
        if request.user.is_superuser:
            return ForecastProject.objects.filter(is_forecast=True)
        return ForecastProject.objects.filter(
            company__admins=request.user, is_forecast=True
        )

    def save_model(self, request, obj, form, change):
        obj.is_forecast = True
        obj.save()


@admin.register(EmployeeForecastAssignment)
class EmployeeForecastAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "forecast_project",
        "start_date",
        "end_date",
        "estimated_days",
    )
    list_filter = ("start_date", "end_date", "forecast_project__company")
    search_fields = [
        "employee__user__first_name",
        "employee__user__last_name",
        "forecast_project__name",
    ]
    autocomplete_fields = ["employee", "forecast_project"]
    fields = (
        "employee",
        "forecast_project",
        "start_date",
        "end_date",
        "estimated_days",
    )

    def get_queryset(self, request):
        if request.user.is_superuser:
            return EmployeeForecastAssignment.objects.all()
        return EmployeeForecastAssignment.objects.filter(
            forecast_project__company__admins=request.user
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit choices to the user's company"""
        if db_field.name == "employee":
            if not request.user.is_superuser:
                kwargs["queryset"] = Employee.objects.filter(
                    company__admins=request.user
                )
        elif db_field.name == "forecast_project":
            if not request.user.is_superuser:
                kwargs["queryset"] = ForecastProject.objects.filter(
                    company__admins=request.user, is_forecast=True
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_permission(self, request):
        if request.user.is_anonymous:
            return False
        if request.user.is_superuser:
            return True
        return is_user_admin(request.user)

    def has_module_permission(self, request):
        return self.has_permission(request)

    def has_add_permission(self, request):
        return self.has_permission(request)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return self.has_permission(request)
        if request.user.is_superuser:
            return True
        return obj.forecast_project.company.admins.filter(pk=request.user.pk).exists()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "company")
    search_fields = ["name"]

    def get_queryset(self, request):
        if request.user.is_superuser:
            return Category.objects.all()
        return Category.objects.filter(company__admins=request.user)

    def has_permission(self, request):
        if request.user.is_anonymous:
            return False

        if request.user.is_superuser or is_user_admin(request.user):
            return True

        return False

    def has_module_permission(self, request):
        return self.has_permission(request)

    def has_add_permission(self, request):
        return self.has_permission(request)

    def has_change_permission(self, request, obj: Category = None):
        if obj is None:
            return self.has_permission(request)
        if request.user.is_superuser:
            return True
        return obj.company.admins.filter(pk=request.user.pk).exists()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)
