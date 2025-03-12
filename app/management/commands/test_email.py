from time import sleep

from django.core.management.base import BaseCommand
from app.email_task import send_email
from uuid import uuid4
import os

class Command(BaseCommand):
    help = "Test email send to timurbakibayev@gmail.com"

    def handle(self, *args, **options):
        text = f"""
Hello Timur,

### this is a test email from Django.

* This is a list item
* This is another list item

Thanks,
Django
        """
        send_email(
            name="Timur",
            email="timurbakibayev@gmail.com",
            subject=f"Test email {uuid4()}",
            text=text,
        )
        self.stdout.write(self.style.SUCCESS(f"Sent an email, please check"))


