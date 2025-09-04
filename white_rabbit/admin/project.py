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


class CompanyCategoryListFilter(admin.SimpleListFilter):
    """Custom filter to show only categories from companies the user is admin of."""

    title = "catégorie"
    parameter_name = "category"

    def lookups(self, request, model_admin):
        """Return category choices filtered by user's companies."""
        if request.user.is_superuser:
            categories = Category.objects.all().order_by("name")
        else:
            categories = Category.objects.filter(company__admins=request.user).order_by(
                "name"
            )

        return [(category.id, str(category)) for category in categories]

    def queryset(self, request, queryset):
        """Filter the queryset based on the selected category."""
        if self.value():
            return queryset.filter(category__id=self.value())
        return queryset


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
        CompanyCategoryListFilter,
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
    extra = 3
    fields = ("employee", "start_date", "end_date", "estimated_days")
    verbose_name = "Affectation d'employé"
    verbose_name_plural = "Affectations d'employés"

    def get_formset(self, request, obj=None, **kwargs):
        """Add help text for assignments"""
        formset = super().get_formset(request, obj, **kwargs)

        # Always display the help text
        formset.help_text = (
            "💡 <strong>Assignation d'employés</strong> : "
            "Vérifiez que le total des jours assignés ne dépasse pas "
            "le nombre de jours prévus du projet."
        )

        return formset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit employee choices to the same company as the forecast project"""
        if db_field.name == "employee":
            # Get the forecast project from the URL or request context
            project_id = request.resolver_match.kwargs.get("object_id")
            if project_id:
                try:
                    project = ForecastProject.objects.get(pk=project_id)
                    # Only employees from the same company as the project
                    kwargs["queryset"] = Employee.objects.filter(
                        company=project.company
                    )
                except ForecastProject.DoesNotExist:
                    kwargs["queryset"] = Employee.objects.none()
            else:
                # For new projects, show employees from all companies the user administers
                # The validation will ensure consistency when the project is saved
                if request.user.is_superuser:
                    kwargs["queryset"] = Employee.objects.all()
                else:
                    user_companies = request.user.companies.all()
                    if user_companies.exists():
                        kwargs["queryset"] = Employee.objects.filter(
                            company__in=user_companies
                        )
                    else:
                        kwargs["queryset"] = Employee.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request, obj=None):
        """Allow company admins to add assignments"""
        if request.user.is_superuser:
            return True
        # Check if user is admin of at least one company
        return request.user.companies.exists()

    def has_change_permission(self, request, obj=None):
        """Allow company admins to change assignments for their company's projects"""
        if request.user.is_superuser:
            return True
        if obj is None:
            return request.user.companies.exists()
        # obj is the parent ForecastProject, check if it belongs to a company the user administers
        return obj.company.admins.filter(pk=request.user.pk).exists()

    def has_delete_permission(self, request, obj=None):
        """Allow company admins to delete assignments for their company's projects"""
        return self.has_change_permission(request, obj)


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

    def get_form(self, request, obj=None, **kwargs):
        """Customize form to make dates required for forecast projects"""
        form = super().get_form(request, obj, **kwargs)
        # Make start_date and end_date required
        form.base_fields["start_date"].required = True
        form.base_fields["end_date"].required = True
        form.base_fields["start_date"].help_text = (
            "Date de début du projet prévisionnel (obligatoire)"
        )
        form.base_fields["end_date"].help_text = (
            "Date de fin du projet prévisionnel (obligatoire)"
        )
        return form

    exclude = ("lowercase_name", "is_forecast")
    search_fields = ["name"]
    inlines = [EmployeeForecastAssignmentInline]

    def get_queryset(self, request):
        if request.user.is_superuser:
            return ForecastProject.objects.filter(is_forecast=True)
        return ForecastProject.objects.filter(
            company__admins=request.user, is_forecast=True
        )

    def save_model(self, request, obj, form, change):
        obj.is_forecast = True
        obj.save()

    def save_related(self, request, form, formsets, change):
        """Save related objects and validate company consistency"""
        super().save_related(request, form, formsets, change)

        # Validate that all assigned employees belong to the same company as the project
        project = form.instance
        for assignment in project.employee_assignments.all():
            if assignment.employee.company != project.company:
                # Delete the invalid assignment
                assignment.delete()
                from django.contrib import messages

                messages.error(
                    request,
                    f"L'affectation de {assignment.employee.name} a été supprimée car "
                    f"cet employé appartient à l'entreprise {assignment.employee.company.name} "
                    f"alors que le projet appartient à {project.company.name}.",
                )


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
