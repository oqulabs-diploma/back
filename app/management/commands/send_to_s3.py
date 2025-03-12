from time import sleep

from django.core.management.base import BaseCommand
from app.models import Screenshot, Attachment
import boto3
from botocore.config import Config
from uuid import uuid4
from sms.settings import s3_endpoint, s3_bucket, s3_key_id, s3_application_key
import os
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)


def get_b2_resource():
    b2 = boto3.resource(service_name='s3',
                        endpoint_url=s3_endpoint,
                        aws_access_key_id=s3_key_id,
                        aws_secret_access_key=s3_application_key,
                        config=Config(
                            signature_version='s3v4'))
    return b2


class Command(BaseCommand):
    help = "Send all attachments to S3"

    def handle(self, *args, **options):
        b2 = get_b2_resource()
        bucket = b2.Bucket(s3_bucket)
        while True:
            number_of_files = 0
            for screen in Screenshot.objects.filter(sent_to_s3=False):
                filename = screen.screenshot
                if not os.path.exists(filename):
                    screen.sent_to_s3 = True
                    screen.save()
                    continue
                random_string = uuid4().hex
                extension = filename.split(".")[-1]
                key = f"{screen.enrollment_task_id}/{random_string}.{extension}"
                bucket.upload_file(Filename=filename, Key=key)
                new_url = f"{s3_endpoint}/{s3_bucket}/{key}"
                screen.screenshot = new_url
                screen.sent_to_s3 = True
                screen.s3_key = key
                screen.save()
                dir = os.path.dirname(filename)
                os.remove(filename)
                number_of_files += 1
                if not os.listdir(dir):
                    os.rmdir(dir)

            if number_of_files:
                self.stdout.write(self.style.SUCCESS(f"Sent {number_of_files} screenshots to S3"))

            number_of_files = 0

            for attachment in Attachment.objects.filter(sent_to_s3=False):
                filename = attachment.attachment
                if not os.path.exists(filename):
                    attachment.sent_to_s3 = True
                    attachment.save()
                    continue
                random_string = uuid4().hex
                base_filename = filename.split("/")[-1]
                # encode the filename to url safe string
                # base_filename = urllib.parse.quote(base_filename).replace("%", "_")
                key = f"attachments/{random_string}/{base_filename}"
                bucket.upload_file(Filename=filename, Key=key)
                new_url = f"{s3_endpoint}/{s3_bucket}/{key}"
                attachment.attachment = new_url
                attachment.sent_to_s3 = True
                attachment.s3_key = key
                attachment.save()
                dir = os.path.dirname(filename)
                os.remove(filename)
                number_of_files += 1
                if not os.listdir(dir):
                    os.rmdir(dir)

            if number_of_files:
                self.stdout.write(self.style.SUCCESS(f"Sent {number_of_files} attachments to S3"))

            sleep(5)
