import calendar
import datetime
from typing import Iterable

from dateutil.relativedelta import relativedelta

from white_rabbit.models import Employee, Project
from white_rabbit.utils import group_events_by_day, day_distribution
from white_rabbit.typing import Event


def _event_date(event: Event) -> datetime.date:
    d = event["start_datetime"]
    return d.date() if isinstance(d, datetime.datetime) else d


def _sum_leave_days(
    events: Iterable[Event],
    employee: Employee,
    project_ids: set,
    start: datetime.date,
    end: datetime.date,
) -> float:
    in_range = [e for e in events if start <= _event_date(e) <= end]
    total = 0.0
    for _day, day_events in group_events_by_day(in_range).items():
        distribution = day_distribution(day_events, employee, group_by="project")
        for project_id, data in distribution.items():
            if project_id in project_ids:
                total += data["duration"]
    return total


def _accrual_year_start(company, reference_year: int) -> datetime.date:
    return datetime.date(reference_year, company.paid_leave_accrual_start_month, 1)


def _grace_end(accrual_start: datetime.date) -> datetime.date:
    after_two_months = accrual_start + relativedelta(months=2)
    last_day = calendar.monthrange(after_two_months.year, after_two_months.month - 1)[1]
    return datetime.date(after_two_months.year, after_two_months.month - 1, last_day)


def compute_cp_status(employee: Employee, events: Iterable[Event], today: datetime.date) -> dict:
    company = employee.company
    annual_cp = float(employee.annual_paid_leave_days)
    monthly_rate = annual_cp / 12
    accrual_month = company.paid_leave_accrual_start_month

    cp_project_ids = set(
        Project.objects.filter(company=company, leave_type="CP").values_list("pk", flat=True)
    )

    current_year_start = _accrual_year_start(company, today.year)
    if today < current_year_start:
        current_year_start = _accrual_year_start(company, today.year - 1)

    grace_end = _grace_end(current_year_start + relativedelta(years=1))
    new_year_start = current_year_start + relativedelta(years=1)
    in_grace = new_year_start <= today <= grace_end

    if in_grace:
        prev_year_start = current_year_start
        prev_year_end = new_year_start - datetime.timedelta(days=1)
        prev_accrued = annual_cp

        prev_consumed_in_period = _sum_leave_days(
            events, employee, cp_project_ids, prev_year_start, prev_year_end
        )
        prev_remaining_at_new_year = max(0.0, prev_accrued - prev_consumed_in_period)

        grace_consumed = _sum_leave_days(
            events, employee, cp_project_ids, new_year_start, today
        )
        from_prev = min(grace_consumed, prev_remaining_at_new_year)
        from_current = grace_consumed - from_prev
        prev_remaining = prev_remaining_at_new_year - from_prev

        months_into_new = (today.year - new_year_start.year) * 12 + (today.month - new_year_start.month) + 1
        current_accrued = round(min(months_into_new * monthly_rate, annual_cp), 1)
        current_remaining = round(current_accrued - from_current, 1)

        periods = [
            {
                "label": f"Année {prev_year_start.year}",
                "accrued": round(prev_accrued, 1),
                "consumed": round(prev_consumed_in_period + from_prev, 1),
                "remaining": round(prev_remaining, 1),
                "expires": grace_end,
            },
            {
                "label": f"Année {new_year_start.year}",
                "accrued": current_accrued,
                "consumed": round(from_current, 1),
                "remaining": current_remaining,
                "expires": None,
            },
        ]
    else:
        year_start = current_year_start
        new_year = year_start + relativedelta(years=1)
        prev_year_start = year_start - relativedelta(years=1)
        prev_grace_end = _grace_end(year_start)

        prev_accrued = annual_cp
        prev_consumed_in_period = _sum_leave_days(
            events, employee, cp_project_ids, prev_year_start, year_start - datetime.timedelta(days=1)
        )
        prev_remaining_at_year_start = max(0.0, prev_accrued - prev_consumed_in_period)

        grace_consumed = _sum_leave_days(
            events, employee, cp_project_ids, year_start, prev_grace_end
        )
        overflow_to_current = max(0.0, grace_consumed - prev_remaining_at_year_start)

        after_grace_start = prev_grace_end + datetime.timedelta(days=1)
        after_grace_consumed = _sum_leave_days(
            events, employee, cp_project_ids, after_grace_start, today
        )

        current_consumed = round(overflow_to_current + after_grace_consumed, 1)

        months_into_year = (today.year - year_start.year) * 12 + (today.month - year_start.month) + 1
        months_into_year = min(months_into_year, 12)
        current_accrued = round(min(months_into_year * monthly_rate, annual_cp), 1)
        current_remaining = round(current_accrued - current_consumed, 1)

        periods = [
            {
                "label": f"Année {year_start.year}",
                "accrued": current_accrued,
                "consumed": current_consumed,
                "remaining": current_remaining,
                "expires": None,
            }
        ]

    return {
        "annual_cp": round(annual_cp, 1),
        "monthly_rate": round(monthly_rate, 2),
        "accrual_start_month": accrual_month,
        "periods": periods,
    }


def compute_rtt_status(employee: Employee, events: Iterable[Event], today: datetime.date) -> dict:
    annual_rtt = float(employee.annual_rtt_days)
    if annual_rtt == 0:
        return {"configured": False, "annual_rtt": 0}

    company = employee.company
    acq_month = company.rtt_acquisition_month

    this_year_acq = datetime.date(today.year, acq_month, 1)
    if today >= this_year_acq:
        period_start = this_year_acq
        period_end = datetime.date(today.year + 1, acq_month, 1) - datetime.timedelta(days=1)
    else:
        period_start = datetime.date(today.year - 1, acq_month, 1)
        period_end = this_year_acq - datetime.timedelta(days=1)

    rtt_project_ids = set(
        Project.objects.filter(company=company, leave_type="RTT").values_list("pk", flat=True)
    )

    consumed = round(
        _sum_leave_days(events, employee, rtt_project_ids, period_start, today), 1
    )
    remaining = round(annual_rtt - consumed, 1)

    return {
        "configured": True,
        "annual_rtt": round(annual_rtt, 1),
        "period_start": period_start,
        "period_end": period_end,
        "consumed": consumed,
        "remaining": remaining,
    }


def compute_vacation_summary(
    employee: Employee, events: Iterable[Event], today: datetime.date
) -> dict:
    return {
        "cp": compute_cp_status(employee, events, today),
        "rtt": compute_rtt_status(employee, events, today),
    }
