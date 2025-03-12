import concurrent.futures
from time import sleep
import random
from django.core.management.base import BaseCommand
from app.models import EnrollmentTask, Screenshot, EnrollmentTaskAiDialog
from app.ai.image_loader import get_image_description
from app.ai.prompter import get_video_description, reply_to_dialog

from openai import AzureOpenAI
from sms.settings import (
    OPENAI_ENDPOINT,
    OPENAI_API_KEY,
    OPENAI_DEPLOYMENT,
    OPENAI_API_VERSION,
)

client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT,
    api_key=OPENAI_API_KEY,
    api_version=OPENAI_API_VERSION,
)


class Command(BaseCommand):
    help = "Send screenshots to Azure AI"

    def handle(self, *args, **options):
        if OPENAI_API_KEY == "":
            self.stdout.write(self.style.ERROR("OPENAI_API_KEY is empty"))
            return

        completion = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "Hello, world! This is a ping message to check services."
                        }
                    ]
                },
            ],
        )
        print(completion.choices[0].message.content)

        while True:
            number_of_taks = 0

            for enrollment_task in EnrollmentTask.objects.filter(ai_request=True).filter(ai_ready=False):
                try:
                    task = enrollment_task.task
                    if enrollment_task.ai_eligible():
                        screenshots = Screenshot.objects.filter(enrollment_task=enrollment_task).filter(sent_to_s3=True)
                        if screenshots.count() < task.ai_screenshots_count + 3:
                            continue
                        screenshot_urls = [
                            screenshot.screenshot
                            for screenshot in screenshots
                            if screenshot.sent_to_s3
                        ]
                        additional = int(task.ai_screenshots_count * enrollment_task.minutes / 120)
                        additional = min(additional, 20)
                        selected_screenshots = random.sample(
                            screenshot_urls,
                            task.ai_screenshots_count + additional
                        )
                        selected_screenshots += screenshot_urls[-3:]

                        def process_image(url):
                            return get_image_description(url)

                        descriptions = []

                        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                            futures = [
                                executor.submit(process_image, screen)
                                for screen in selected_screenshots
                            ]
                            for future in concurrent.futures.as_completed(futures):
                                try:
                                    descriptions.append(future.result())
                                except Exception as e:
                                    print(f"Error processing image: {e}")

                        if len(descriptions) < task.ai_screenshots_count:
                            self.stdout.write(
                                self.style.ERROR(f"Failed to process {enrollment_task.id}: only {len(descriptions)} "
                                                 f"descriptions were generated"))
                            continue

                        note, score = get_video_description(
                            task,
                            enrollment_task,
                            descriptions,
                        )
                        enrollment_task.ai_description = ",".join(
                            [
                                f"Next screenshot: {i}"
                                for i in descriptions
                            ]
                        )
                        enrollment_task.ai_used_screenshots = len(descriptions)
                        enrollment_task.ai_ready = True
                        enrollment_task.ai_note = note
                        enrollment_task.ai_score = score
                        enrollment_task.save(update_fields=[
                            "ai_ready",
                            "ai_note",
                            "ai_score",
                            "ai_description",
                            "ai_used_screenshots",
                        ])

                        EnrollmentTaskAiDialog.objects.create(
                            enrollment_task=enrollment_task,
                            text=note,
                            from_ai=True,
                        )

                        EnrollmentTaskAiDialog.objects.create(
                            enrollment_task=enrollment_task,
                            text="Напиши очень коротко",
                            from_teacher=True,
                        )

                        reply_to_dialog(task, enrollment_task)

                        number_of_taks += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to process {enrollment_task.id}: {e}, let's wait a minute"))
                    sleep(60)

            if number_of_taks:
                self.stdout.write(self.style.SUCCESS(f"Sent {number_of_taks} tasks to Azure"))

            sleep(5)
