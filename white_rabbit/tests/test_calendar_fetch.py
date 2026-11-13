import io
from contextlib import redirect_stdout
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase

from white_rabbit.constants import CALENDAR_REQUEST_TIMEOUT
from white_rabbit.events import get_events_by_url
from white_rabbit.hydrate_cache import hydrate_cache
from white_rabbit.tests.factory import EmployeeFactory

CALENDAR_URL = "https://calendar.example.org/secret-token/calendar.ics"


class TestUnresponsiveCalendarServer(TestCase):
    """A calendar server that never answers must fail fast instead of blocking."""

    def setUp(self):
        cache.clear()
        self.employee = EmployeeFactory(calendar_ical_url=CALENDAR_URL)
        self.timeouts_sent = []

    def send_and_time_out(self, adapter, request, **kwargs):
        self.timeouts_sent.append(kwargs.get("timeout"))
        raise requests.exceptions.ConnectTimeout(request=request)

    def test_hydrate_cache_reports_the_host_and_keeps_the_cache(self):
        output = io.StringIO()
        with patch.object(
            requests.adapters.HTTPAdapter, "send", autospec=True
        ) as send, redirect_stdout(output):
            send.side_effect = self.send_and_time_out
            hydrate_cache()

        self.assertEqual(self.timeouts_sent, [CALENDAR_REQUEST_TIMEOUT])
        self.assertIn(
            "Could not fetch calendar from calendar.example.org: ConnectTimeout",
            output.getvalue(),
        )
        self.assertNotIn("secret-token", output.getvalue())
        self.assertIsNone(cache.get(str(self.employee.id)))

    def test_get_events_by_url_raises_instead_of_hanging(self):
        with patch.object(
            requests.adapters.HTTPAdapter, "send", autospec=True
        ) as send:
            send.side_effect = self.send_and_time_out
            with self.assertRaises(requests.exceptions.ConnectTimeout):
                get_events_by_url(CALENDAR_URL, self.employee)

        self.assertEqual(self.timeouts_sent, [CALENDAR_REQUEST_TIMEOUT])
