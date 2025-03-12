import os

from django.conf import settings
from django.http import (
    HttpResponseRedirect,
    JsonResponse,
)

from app.models import (
    Attachment
)
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from app.models import (
    EnrollmentTask,
)


@csrf_exempt
def upload_attachment(request, enrollment_task_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    attachments = request.FILES.getlist('file')

    enrollment_task = EnrollmentTask.objects.get(id=enrollment_task_id)
    if request.user != enrollment_task.enrollment.student:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    for file in attachments:
        print("File size", file.size)
        if file.size > 20 * 1024 * 1024:
            return JsonResponse({'status': 'error', 'message': 'File is too big'}, status=400)

        attachment = Attachment.objects.create(
            enrollment_task=enrollment_task,
        )

        user_dir = os.path.join(
            settings.ATTACHMENTS_URL
        )

        file_name = os.path.join(
            user_dir,
            f'a_{enrollment_task_id}/{file.name}'
        )

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        with default_storage.open(file_name, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        attachment.attachment = file_name
        attachment.save()

        print(f"Attachment created: {attachment}")
        return HttpResponseRedirect(f'/track/{enrollment_task_id}')

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
