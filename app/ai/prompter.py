from openai import AzureOpenAI
from openai.types import Completion

from app.models import Task, EnrollmentTask, EnrollmentTaskAiDialog

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


def reply_to_dialog(
        task: Task,
        enrollment_task: EnrollmentTask,
):
    dialog_messages = EnrollmentTaskAiDialog.objects.filter(enrollment_task=enrollment_task)
    if dialog_messages.count() == 0:
        return

    def role(enrollment_task_ai_dialog: EnrollmentTaskAiDialog):
        if enrollment_task_ai_dialog.from_ai:
            return "assistant"
        return "user"

    workload = [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": f"Course: {task.course.name}\n"
                            f"Task: {task.name} \n"
                            f"Worked time (minutes): {enrollment_task.minutes}\n"
                            f"{task.text}\n"
                },
                {
                    "type": "text",
                    "text": f"Screenshot analysis:\n"
                            f"{enrollment_task.ai_description}\n"
                },
            ]
        }
    ]
    workload += [
        {
            "role": role(enrollment_task_ai_dialog),
            "content": [
                {
                    "type": "text",
                    "text": enrollment_task_ai_dialog.text
                },
            ]
        }
        for enrollment_task_ai_dialog in dialog_messages
    ]
    completion: Completion = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        messages=workload,
    )

    note = completion.choices[0].message.content
    EnrollmentTaskAiDialog.objects.create(
        enrollment_task=enrollment_task,
        text=note,
        from_teacher=False,
        from_student=False,
        from_ai=True,
    )
    return note


def get_video_description(
        task: Task,
        enrollment_task: EnrollmentTask,
        descriptions: list[str],
) -> tuple[str, int]:
    note, score = "", None

    workload = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Course: {task.course.name}\n"
                            f"Task: {task.name} \n"
                            f"{task.text}\n"
                            f"Worked time (minutes): {enrollment_task.minutes}\n"
                },
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": ",".join(
                        [
                            f"Next screenshot: {i}"
                            for i in descriptions
                        ]
                    )
                },
            ]
        }
    ]

    chat_prompt = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": f"You are an assistant to analyze users work by their screenshots."
                            f"You will be given a task and descriptions of many screenshots in order,"
                            f"they are picked randomly from a big number."
                            f""
                            f"Give the summary of what user did and whether it "
                            f"corresponds to the given task in Russian language."
                }
            ]
        },
    ] + workload

    completion: Completion = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        messages=chat_prompt,
    )

    note = completion.choices[0].message.content

    print(completion.choices[0].message.content)

    attempts = 0

    while attempts < 5 and score is None:
        attempts += 1

        chat_prompt = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": f"You are an assistant to analyze users work by their screenshots."
                                f"You will be given a task and descriptions of many screenshots in order,"
                                f"they are picked randomly from a big number."
                                f""
                                f"Return a score from 0 to 100, where 0 is not related to the task at all,"
                                f"and 100 is a perfect match. Only one integer number is expected."
                    }
                ]
            },
        ] + workload

        completion: Completion = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            messages=chat_prompt,
        )
        result = completion.choices[0].message.content
        print("Validating score", result)

        try:
            score = int(result)
        except ValueError:
            pass

    print("OK")

    return note, score
