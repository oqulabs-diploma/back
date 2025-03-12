import os
import random
from PIL import Image
import io

from django.conf import settings
from django.http import (
    JsonResponse,
)

from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone

from app.models import Enrollment, EnrollmentTask, Screenshot


@csrf_exempt
def upload_screenshot(request, task_id):
    if request.user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not authenticated'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    if request.FILES.get('screenshot'):
        screenshot = request.FILES['screenshot']
        enrollment_id = request.POST.get('enrollment_id')
        enrollment = Enrollment.objects.filter(id=enrollment_id).first()
        if enrollment is None:
            return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)
        enrollment_task = EnrollmentTask.objects.filter(
            enrollment=enrollment,
            task=task_id,
        ).first()
        if enrollment_task.enrollment.student != request.user:
            return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
        if not enrollment_task:
            enrollment_task = EnrollmentTask.objects.create(
                enrollment=enrollment,
                task_id=task_id,
            )
        too_soon = False
        now = timezone.now()
        now = now.replace(second=0, microsecond=0)
        now_hour = now.hour
        now_minute = now.minute
        now_text = f"{now_hour}:{now_minute}"
        minutes_diff = 1

        if enrollment_task.last_submission:
            minutes_diff = (now - enrollment_task.last_submission).total_seconds() // 60
            if minutes_diff < 1:
                too_soon = True
            if minutes_diff > 5:
                minutes_diff = 1

        if not too_soon:
            enrollment_task.minutes += minutes_diff
            enrollment_task.last_submission = now
            enrollment_task.last_hh_mm = now_text
            enrollment_task.accepted = False
            enrollment_task.marked_as_done = False
            enrollment_task.save()
            enrollment.total_minutes += minutes_diff
            enrollment.save(update_fields=['total_minutes'])

        user_dir = os.path.join(
            settings.SCREENSHOTS_URL,
            f'{enrollment.folder_prefix}',
            f'enrollment_{enrollment_id}',
            f'task_{task_id}'
        )

        # Ensure the directory exists
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)

        img = Image.open(screenshot)

        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGB")

        output_io = io.BytesIO()
        img.save(output_io, format='JPEG', quality=70)
        random_code = random.randint(1000, 9999)

        file_name = os.path.join(
            user_dir,
            f'screen_{enrollment.total_minutes}_{random_code}.jpg'
        )

        # Replace backslashes with forward slashes for URL compatibility
        file_name_url = file_name.replace('\\', '/')

        default_storage.save(file_name, ContentFile(output_io.getvalue()))

        Screenshot.objects.create(
            enrollment=enrollment,
            enrollment_task=enrollment_task,
            screenshot=file_name_url,
            at_minute=enrollment_task.minutes,
        )

        if too_soon:
            return JsonResponse({
                'status': 'error',
                'message': 'Too soon to submit',
                'total_minutes': enrollment.total_minutes,
                'minutes_task': enrollment_task.minutes,
            }, status=200)

        return JsonResponse({
            'status': 'success',
            'total_minutes': enrollment.total_minutes,
            'minutes_task': enrollment_task.minutes,
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


