import os
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
import markdown
from django.views.decorators.csrf import csrf_exempt
import json
from app.management.commands.send_to_s3 import get_b2_resource
from sms.settings import s3_bucket
from app.models import Enrollment, EnrollmentTask, Course, Screenshot, Attachment, Task
from django.utils.translation import gettext_lazy as _
from django.utils.translation import activate

def track(request, enrollment_task_id: int):
    user = request.user
    if user.is_anonymous:
        return redirect("/")
    if user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is staff, not trackable'}, status=403)
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if not enrollment_task:
        return redirect("/")
    enrollment = enrollment_task.enrollment
    if not enrollment.student == user:
        return redirect("/")
    if enrollment is None:
        return redirect("/")

    instructions = markdown.markdown(enrollment_task.task.text)

    attachments = Attachment.objects.filter(enrollment_task=enrollment_task)
    for attachment in attachments:
        attachment.uploading = not attachment.attachment.startswith("http")
        attachment.filename = attachment.attachment.split("/")[-1]

    if enrollment_task.under_review:
        return render(
            request,
            "review.html",
            {
                'enrollment': enrollment,
                'enrollment_task': enrollment_task,
                'task': enrollment_task.task,
                'instructions': instructions,
                'screenshots': enrollment_task.screenshot_set.all(),
                'student_attachments': attachments,
                'is_track' : True
            }
        )

    if enrollment_task.task.copy_of:
        attachments = Attachment.objects.filter(task_id=enrollment_task.task.copy_of.id)
    else:
        attachments = Attachment.objects.filter(task_id=enrollment_task.task)
    for attachment in attachments:
        if not attachment.attachment.startswith("http"):
            if not attachment.attachment.startswith("/"):
                attachment.attachment = "/" + attachment.attachment
        attachment.filename = attachment.attachment.split("/")[-1]

    translations = {
        'back': _("Back"),
        'log_out': _("Log out"),
        'task_monitoring': _("Task Monitoring"),
        'internet_error': _("INTERNET ERROR!"),
        'course': _("Course:"),
        'task': _("Task:"),
        'student': _("Student:"),
        'this_task': _("This task:"),
        'total': _("Total:"),
        'inactive': _("Inactive"),
        'share_screen': _("Share Screen"),
        'share_camera': _("Share Camera"),
        'stop_sharing': _("Stop Sharing"),
        'instructions': _("Instructions"),
        'deadline_warning': _("You have to finish this task before the deadline:"),
        'after_deadline': _("You won't be able to submit your work after the deadline."),
        'send_images': _("Send Images"),
        
    }

    context = {
        'enrollment': enrollment,
            'enrollment_task': enrollment_task,
            'task' : enrollment_task.task,
            'instructions': instructions,
            'screenshots': enrollment_task.screenshot_set.all(),
            "attachments": attachments,
    }

    context.update(translations)

    return render(
        request,
        "student.html",
        context
    )


def set_language(request):
    if request.method == 'POST':
        language = request.POST.get('language')
        if language in ['en', 'ru', 'kk']: 
            request.session['django_language'] = language
            activate(language)
    return redirect(request.META.get('HTTP_REFERER', '/'))

def watch(request, enrollment_task_id: int):
    user = request.user
    if user.is_anonymous:
        return redirect("/")
    if not user.is_staff:
        return redirect("/")
    
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return redirect("/")
    
    enrollment = enrollment_task.enrollment
    if enrollment is None:
        return redirect("/")

    if not enrollment.course.permissions(user=request.user).read:
        return redirect("/")

    course_teacher = enrollment.course.teacher

    screenshots = enrollment_task.screenshot_set.filter(id__lte=enrollment_task.last_shared_id)
    
    attachments = Attachment.objects.filter(enrollment_task_id=enrollment_task_id)
    for attachment in attachments:
        attachment.uploading = not attachment.attachment.startswith("http")
        attachment.filename = attachment.attachment.split("/")[-1]

    if enrollment.course.permissions(user=request.user).write:
        enrollment_task.watched = True
        enrollment_task.save(update_fields=["watched"])
    
    return render(
        request,
        "watch.html",
        {
            'enrollment': enrollment,
            'enrollment_task': enrollment_task,
            'screenshots': screenshots,
            'attachments': attachments,
            'course': enrollment.course,
            'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
            'page': 'enrollments',
        }
    )


@csrf_exempt
def delete_screenshot(request, screenshot_id):
    if request.method != 'DELETE':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    
    screenshot = Screenshot.objects.filter(id=screenshot_id).first()
    if screenshot is None:
        return JsonResponse({'status': 'error', 'message': 'Screenshot not found'}, status=404)
    
    enrollment_task = screenshot.enrollment_task
    if not enrollment_task.enrollment.student == user and \
            not enrollment_task.enrollment.course.permissions(user=request.user).delete:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    screenshot_path = os.path.join(settings.MEDIA_ROOT, screenshot.screenshot)

    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)

    if screenshot.sent_to_s3:
        try:
            b2 = get_b2_resource()
            bucket = b2.Bucket(s3_bucket)
            key = screenshot.s3_key
            obj = bucket.Object(key)
            obj.delete()
            obj = bucket.Object("/".join(key.split("/")[:-1]))  # remove folder, too
            obj.delete()
            print("Deleted from S3")
        except Exception as e:
            print("Error deleting from S3", e)

    at_minute = screenshot.at_minute
    screenshot.delete()

    same_enrollment_task = Screenshot.objects.filter(enrollment_task=enrollment_task)
    other_screen_same_minute = same_enrollment_task.filter(at_minute=at_minute).first()
    if other_screen_same_minute is None:
        enrollment_task.minutes -= 1
        enrollment_task.save(update_fields=['minutes'])

    enrollment = enrollment_task.enrollment
    enrollment.total_minutes -= enrollment_task.enrollment.course.screenshot_interval_minutes
    enrollment.save(update_fields=['total_minutes'])

    return JsonResponse({
        'status': 'success',
        'message': 'Screenshot deleted',
        'total_time': str(enrollment.total_time),  
        'minutes_task': str(enrollment_task.total_time)  
    }, status=200)


@csrf_exempt
def accept(request, enrollment_task_id: int):
    user = request.user
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    enrollment_task.accepted = True
    enrollment_task.save(update_fields=['accepted'])
    return JsonResponse({'status': 'success', 'message': 'Task accepted'}, status=200)


@csrf_exempt
def note(request, enrollment_task_id: int):
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    note = request.body.decode("UTF-8")
    enrollment_task.note = note
    enrollment_task.save(update_fields=['note'])
    return JsonResponse({'status': 'success', 'message': 'Task accepted'}, status=200)


@csrf_exempt
def unaccept(request, enrollment_task_id: int):
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'User is not the teacher of this course'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    enrollment_task.accepted = False
    enrollment_task.save(update_fields=['accepted'])
    return JsonResponse({'status': 'success', 'message': 'Task returned to work'}, status=200)


@csrf_exempt
def undone(request, enrollment_task_id: int):
    user = request.user
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'User is not the teacher of this course'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    enrollment_task.accepted = False
    enrollment_task.marked_as_done = False
    enrollment_task.save(update_fields=['accepted', 'marked_as_done'])
    return JsonResponse({'status': 'success', 'message': 'Task returned to work'}, status=200)


@csrf_exempt
def back_to_record(request, enrollment_task_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.student == user:
        return JsonResponse({'status': 'error', 'message': 'User is not the student of this enrollment'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    enrollment_task.under_review = False
    enrollment_task.save(update_fields=['under_review'])
    return JsonResponse({'status': 'success', 'message': 'Task marked as done'}, status=200)


@csrf_exempt
def mark_as_done(request, enrollment_task_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.student == user:
        return JsonResponse({'status': 'error', 'message': 'User is not the student of this enrollment'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    enrollment_task.under_review = True
    enrollment_task.save(update_fields=['under_review'])
    return JsonResponse({'status': 'success', 'message': 'Task marked as done'}, status=200)


@csrf_exempt
def confirm_as_done(request, enrollment_task_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.student == user:
        return JsonResponse({'status': 'error', 'message': 'User is not the student of this enrollment'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    if not enrollment_task.task.allow_finish_earlier and enrollment_task.minutes < enrollment_task.task.minimum_minutes:
        return JsonResponse({'status': 'error', 'message': f'Please work more and then submit. Complete: {enrollment_task.progress_num()}%'}, status=400)
    if not enrollment_task.task.is_active_right_now():
        return JsonResponse({
            'status': 'error',
            'message': f'Deadline has passed. You can not submit anymore. Ask your teacher for more time.'},
            status=400
        )
    enrollment_task.marked_as_done = True
    enrollment_task.under_review = False

    screenshots = Screenshot.objects.filter(enrollment_task_id=enrollment_task.id).order_by('-id')
    last_id = screenshots.first().id if screenshots else 0
    enrollment_task.last_shared_id = last_id
    enrollment_task.save(update_fields=['marked_as_done', 'last_shared_id'])
    return JsonResponse({'status': 'success', 'message': 'Task marked as done'}, status=200)


@csrf_exempt
def send_screenshots(request, enrollment_task_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)

    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)

    enrollment = enrollment_task.enrollment
    if enrollment.student != user:
        return JsonResponse({'status': 'error', 'message': 'User is not the student of this enrollment'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    try:
        screenshots = Screenshot.objects.filter(enrollment_task_id=enrollment_task.id).order_by('-id')
        for screen in screenshots:
            screen.is_sent = True
            screen.save()

        last_id = screenshots.first().id if screenshots else 0
        if last_id:
            enrollment_task.last_shared_id = last_id
            enrollment_task.watched = False
            enrollment_task.save(update_fields=['last_shared_id', 'watched'])
            return JsonResponse({'status': 'success', 'message': 'Task marked as done'}, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': 'lastScreenshotId not provided'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)


def ban(request, enrollment_task_id: int, minutes: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    enrollment = enrollment_task.enrollment
    if not enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'User is not the teacher of this course'}, status=403)
    enrollment_task.ban_minutes += minutes
    enrollment_task.save(update_fields=['ban_minutes'])
    enrollment.total_ban_minutes += minutes
    enrollment.save(update_fields=['total_ban_minutes'])
    return JsonResponse({'status': 'success', 'message': 'Ban set'}, status=200)


def unban(request, enrollment_task_id: int, minutes: int):
    return ban(request, enrollment_task_id, -minutes)


@csrf_exempt
def check_enrollment_with_ai(request, enrollment_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment = Enrollment.objects.filter(id=enrollment_id).first()
    if enrollment is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)
    if not enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    enrollment.check_with_ai()
    return JsonResponse({'status': 'ok', 'message': 'AI check started'}, status=200)


@csrf_exempt
def check_enrollment_task_with_ai(request, enrollment_task_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment_task = EnrollmentTask.objects.filter(id=enrollment_task_id).first()
    if enrollment_task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    if not enrollment_task.enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    enrollment_task.ai_request = True
    enrollment_task.save(update_fields=['ai_request'])
    return JsonResponse({'status': 'ok', 'message': 'AI check started'}, status=200)


@csrf_exempt
def check_task_with_ai(request, task_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    task = Task.objects.filter(id=task_id).first()
    if task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_task_id'}, status=400)
    for enrollment_task in task.enrollmenttask_set.all():
        enrollment_task.ai_request = True
        enrollment_task.save(update_fields=['ai_request'])
    return JsonResponse({'status': 'ok', 'message': 'AI check started'}, status=200)


@csrf_exempt
def send_email(request, enrollment_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment = Enrollment.objects.filter(id=enrollment_id).first()
    if not enrollment.course.permissions(user=request.user).write:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    if enrollment is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)
    body = json.loads(request.body.decode("UTF-8"))
    print("Will send email to", enrollment.student.email)
    print("Text:", body["text"])
    enrollment.send_email(body["text"])
    return JsonResponse({'status': 'ok', 'message': 'Email sent'}, status=200)


def delete(request, enrollment_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment = Enrollment.objects.filter(id=enrollment_id).first()
    if not enrollment.course.permissions(user=request.user).delete:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    if enrollment is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)
    enrollment.delete()
    return JsonResponse({'status': 'ok', 'message': 'User is deleted'}, status=200)

def archive(request, enrollment_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment = Enrollment.objects.filter(id=enrollment_id).first()
    if not enrollment.course.permissions(user=request.user).delete:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    if enrollment is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)
    enrollment.deleted = True
    enrollment.save(update_fields=['deleted'])
    return JsonResponse({'status': 'ok', 'message': 'User is archived'}, status=200)

def restore(request, enrollment_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment = Enrollment.objects.filter(id=enrollment_id).first()
    if not enrollment.course.permissions(user=request.user).delete:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    if enrollment is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)
    enrollment.deleted = False
    enrollment.save(update_fields=['deleted'])
    return JsonResponse({'status': 'ok', 'message': 'User is archived'}, status=200)

def details(request, enrollment_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    enrollment = Enrollment.objects.filter(id=enrollment_id).first()
    if not enrollment.course.permissions(user=request.user).read:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    if enrollment is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)

    enrollment_tasks = list(EnrollmentTask.objects.filter(
        enrollment=enrollment
    ))
    # sort by task order
    enrollment_tasks.sort(key=lambda x: x.task.order)

    return render(
        request,
        "enrollment_details.html",
        {
            'course': enrollment.course,
            'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
            'enrollment': enrollment,
            'enrollment_tasks': enrollment_tasks,
            'page': 'enrollments',
        }
    )


def details_by_task(request, task_id: int):
    user = request.user
    if user.is_anonymous:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=400)
    if not user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'User is not staff'}, status=403)
    task = Task.objects.filter(id=task_id).first()
    if task is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid enrollment_id'}, status=400)
    if not task.course.permissions(user=request.user).read:
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)

    enrollment_tasks = list(EnrollmentTask.objects.filter(
        task=task,
        enrollment__deleted=False
    ))
    # sort by task order
    enrollment_tasks.sort(key=lambda x: x.task.order)

    return render(
        request,
        "teacher_watch_by_task.html",
        {
            'task': task,
            'course': task.course,
            'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
            'enrollment_tasks': enrollment_tasks,
            'page': 'tasks'
        }
    )
