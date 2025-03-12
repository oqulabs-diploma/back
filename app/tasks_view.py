import os

from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from app.management.commands.send_to_s3 import get_b2_resource
from app.models import Course, Task, Attachment, TaskType
from sms import settings
from sms.settings import s3_bucket


def course_tasks(request, course_id):
    course = Course.objects.get(id=course_id)
    if not course.permissions(user=request.user).read:
        return redirect("/")
    Task.fix_order(course)
    tasks = course.task_set.order_by('order').all()
    return render(
        request,
        "tasks_teacher.html",
        {
            'course': course,
            'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
            'other_courses': Course.objects.filter(teacher=request.user).exclude(id=course_id).filter(deleted=False),
            'tasks': tasks,
            'page': 'tasks',
        }
    )


def delete_attachment(request, attachment_id):
    attachment = Attachment.objects.get(id=attachment_id)
    redirect_to = '/'

    # this is for task, hence for teachers
    if attachment.task is not None:
        if not attachment.task.course.permissions(user=request.user).delete:
            return redirect("/")
        task_id = attachment.task.id
        redirect_to = f'/edit_task/{task_id}'

    # this is for enrollment task, hence for students
    if attachment.enrollment_task is not None:
        if request.user != attachment.enrollment_task.enrollment.student:
            return redirect("/")
        enrollment_task_id = attachment.enrollment_task.id
        redirect_to = f'/track/{enrollment_task_id}'

    if attachment.sent_to_s3:
        try:
            b2 = get_b2_resource()
            bucket = b2.Bucket(s3_bucket)
            key = attachment.s3_key
            obj = bucket.Object(key)
            obj.delete()
            print("Deleted from S3")
        except Exception as e:
            print("Error deleting from S3", e)

    try:
        os.remove(attachment.attachment)
    except FileNotFoundError:
        pass
    attachment.delete()
    return redirect(redirect_to)


def attach_files(request, task_id):
    task = Task.objects.get(id=task_id)
    if not task.course.permissions(user=request.user).write:
        return redirect("/")

    if request.method == 'POST':
        attachments = request.FILES.getlist('file')
        for file in attachments:
            print(file)
            attachment = Attachment.objects.create(
                task=task,
            )
            user_dir = os.path.join(
                settings.ATTACHMENTS_URL
            )
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)

            file_name = os.path.join(
                user_dir,
                str(task.id),
                file.name,
            )

            if not os.path.exists(os.path.dirname(file_name)):
                os.makedirs(os.path.dirname(file_name))

            with default_storage.open(file_name, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # Update the attachment model with the relative file path
            attachment.attachment = file_name
            attachment.save()

        return redirect(f'/edit_task/{task.id}')

    return redirect("/")


def add_task(request, course_id):
    course = Course.objects.get(id=course_id)
    if request.method == 'POST':
        name = request.POST.get('task_name')
        text = request.POST.get('task_text')
        minutes = request.POST.get('task_minutes')
        task_id = int(request.POST.get('task_id'))
        require_attachments = bool(request.POST.get('is_attached'))
        available_from = request.POST.get('available_from')
        if available_from == "":
            available_from = None
        available_to = request.POST.get('available_to')
        if available_to == "":
            available_to = None
        
        # Get task type if selected
        task_type_id = request.POST.get('task_type')
        task_type = None
        if task_type_id:
            task_type = TaskType.objects.get(id=task_type_id)

        if task_id == -1:
            Task.objects.create(
                course=course,
                name=name,
                text=text,
                minimum_minutes=minutes,
                order=course.task_set.count()+1,
                require_attachments=require_attachments,
                available_from=available_from,
                available_to=available_to,
                task_type=task_type,
            )
        else:
            task = Task.objects.get(id=task_id)
            task.name = name
            task.text = text
            task.minimum_minutes = minutes
            task.require_attachments = require_attachments
            task.available_from = available_from
            task.available_to = available_to
            task.task_type = task_type
            task.save()

            for copy in Task.objects.filter(copy_of=task):
                copy.name = name
                copy.text = text
                copy.minimum_minutes = minutes
                copy.require_attachments = require_attachments
                copy.task_type = task_type
                copy.save()

        return redirect(f'/courses_teacher/{course_id}/tasks')

    task = Task(
        course=course,
        name="",
        text="",
        minimum_minutes=60,
        order=course.task_set.count(),
        require_attachments=False,
        available_from=timezone.now(),
        available_to=timezone.now() + timezone.timedelta(days=7),
    )
    return render(
        request,
        "add_task.html",
        {
            'course': course,
            'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
            'task': task,
            'task_id': -1,
            'task_types': TaskType.objects.all().order_by('name'),
        }
    )


def edit_task(request, task_id):
    task = Task.objects.get(id=task_id)
    attachments = Attachment.objects.filter(task=task)
    for attachment in attachments:
        if not attachment.attachment.startswith("http"):
            attachment.uploading = not attachment.attachment.startswith("/")
        attachment.filename = os.path.basename(attachment.attachment)
    return render(
        request,
        "add_task.html",
        {
            'course': task.course,
            'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
            'task': task,
            'task_id': task_id,
            'attachments': attachments,
            'task_types': TaskType.objects.all().order_by('name'),
        }
    )


def delete_task(request, task_id):
    task = Task.objects.get(id=task_id)
    course_id = task.course.id
    task.delete()
    return redirect(f'/courses_teacher/{course_id}/tasks')


def move_task_up(request, task_id):
    task = Task.objects.get(id=task_id)
    course_id = task.course.id
    tasks = list(task.course.task_set.all())
    previous_task = None
    for i in range(len(tasks)):
        if tasks[i].id == task_id and i > 0:
            previous_task = tasks[i - 1]

    if previous_task is not None:
        task.order, previous_task.order = previous_task.order, task.order
        task.save()
        previous_task.save()

    return redirect(f'/courses_teacher/{course_id}/tasks')