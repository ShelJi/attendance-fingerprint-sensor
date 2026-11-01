import time

from django.core.management.base import BaseCommand
from attendance.push import dispatch_push


class Command(BaseCommand):
    help = "Deliver admin and personal staff attendance pushes and check Expo receipts. Run one worker continuously."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process pending pushes once, then exit.")

    def handle(self, *args, **options):
        try:
            while True:
                dispatch_push()
                if options["once"]:
                    return
                time.sleep(5)
        except KeyboardInterrupt:
            return
