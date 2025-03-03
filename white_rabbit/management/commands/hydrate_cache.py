from django.core.management import BaseCommand

from white_rabbit.hydrate_cache import hydrate_cache


class Command(BaseCommand):
    def handle(self, *args, **options):
        hydrate_cache()
