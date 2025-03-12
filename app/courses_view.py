import json
import random
from django.utils import timezone

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from app.models import Course, Enrollment, EnrollmentTask, Task, Attachment, Department
from django.utils.translation import gettext_lazy as _


def courses_student(request):
    if request.user.is_anonymous:
        return redirect('/login')
    if request.user.is_staff:
        return redirect('/courses_teacher')
    enrollments = Enrollment.objects.filter(student=request.user).filter(deleted=False)
    translations = {
        'courses': _("Courses"),
        'username': _("Username:"),
        'your_courses': _("Your courses"),
        'work': _("Work"),
        'no_courses_found_consider_creating_one': _("No courses found, consider creating one"),
        'enroll_to_a_course': _("Enroll to a course"),
        'total_odo': _("Total odo:"),
        'ban': _("Ban:")
    }
    context = {
        'enrollments': enrollments,
    }
    context.update(translations)
    return render(request, "courses_student.html", context)


def courses_student_tasks(request, course_id: int):
    if request.user.is_anonymous:
        return redirect('/login')
    if request.user.is_staff:
        return redirect('/courses_teacher')

    course = Course.objects.get(id=course_id)
    Task.fix_order(course)
    enrollment = Enrollment.objects.get(student=request.user, course=course)
    
    tasks = course.task_set.order_by('order').all()
    for task in tasks:
        if not EnrollmentTask.objects.filter(enrollment=enrollment, task=task).exists():
            if task.has_started():
                EnrollmentTask.objects.create(
                    enrollment=enrollment,
                    task=task,
                    minutes=0,
                )

    started_tasks_ids = [task.id for task in tasks if task.has_started()]
    enrollment_tasks = list(EnrollmentTask.objects.filter(
        enrollment=enrollment,
    ))
    enrollment_tasks = [
        et
        for et in enrollment_tasks
        if et.task.id in started_tasks_ids
    ]

    enrollment_tasks.sort(key=lambda x: x.task.order)

    translations = {
        'tasks': _("Tasks"),
        'course': _("Course:"),
        'username': _("Username:"),
        'task': _("Task"),
        'time': _("Time"),
        'progress': _("Progress"),
        'inactive': _("Inactive"),
        'no_tasks_found': _("No tasks found"),
    }

    context = {
        'course': course,
        'enrollment': enrollment,
        'enrollment_tasks': enrollment_tasks,
    }

    context.update(translations)

    return render(request, "courses_student_tasks.html", context)

def current_tasks_with_filter(request, course_id: int):
    if request.user.is_anonymous:
        return redirect('/login')
    if request.user.is_staff:
        return redirect('/courses_teacher')

    try:
        course = Course.objects.get(id=course_id, deleted=False)
    except Course.DoesNotExist:
        return redirect('/')

    try:
        enrollment = Enrollment.objects.get(student=request.user, course=course, deleted=False)
    except Enrollment.DoesNotExist:
        return redirect('/')

    Task.fix_order(course)

    tasks = Task.objects.filter(course=course, deleted=False).order_by('order')

    for task in tasks:
        if not EnrollmentTask.objects.filter(enrollment=enrollment, task=task).exists():
            if task.has_started():  # ваша логика
                EnrollmentTask.objects.create(enrollment=enrollment, task=task, minutes=0)

    enrollment_tasks = EnrollmentTask.objects.filter(enrollment=enrollment).select_related('task')

    enrollment_tasks_list = sorted(enrollment_tasks, key=lambda et: et.task.order)

    new_tasks = []
    in_progress_tasks = []
    done_not_submitted_tasks = []
    submitted_tasks = []
    overdue_tasks = []

    for_now = timezone.now()

    for et in enrollment_tasks_list:
        t = et.task

        if t.available_to and for_now > t.available_to and not et.accepted:
            overdue_tasks.append(et)
            continue

        if et.under_review or et.last_submission or et.accepted:
            submitted_tasks.append(et)
            continue

        if et.marked_as_done and not et.under_review and not et.accepted and not et.last_submission:
            done_not_submitted_tasks.append(et)
            continue

        if (et.watched or et.minutes > 0) and not et.marked_as_done and not et.accepted:
            in_progress_tasks.append(et)
            continue

        new_tasks.append(et)

    def serialize_et(et):
        return {
            "enrollment_task_id": et.id,
            "task_id": et.task.id,
            "task_name": et.task.name,
            "minutes": et.minutes,
            "marked_as_done": et.marked_as_done,
            "under_review": et.under_review,
            "accepted": et.accepted,
            "last_submission": et.last_submission.isoformat() if et.last_submission else None,
            "progress": et.progress(),  # или et.progress_num()
        }

    data = {
        "course": {
            "id": course.id,
            "name": course.name,
        },
        "new_tasks": [serialize_et(et) for et in new_tasks],
        "in_progress_tasks": [serialize_et(et) for et in in_progress_tasks],
        "done_not_submitted_tasks": [serialize_et(et) for et in done_not_submitted_tasks],
        "submitted_tasks": [serialize_et(et) for et in submitted_tasks],
        "overdue_tasks": [serialize_et(et) for et in overdue_tasks],
    }

    return JsonResponse(data, status=200)

    # return render(request, "student_dashboard.html", {
    #     "course": course,
    #     "enrollment": enrollment,
    #     "new_tasks": new_tasks,
    #     "in_progress_tasks": in_progress_tasks,
    #     "done_not_submitted_tasks": done_not_submitted_tasks,
    #     "submitted_tasks": submitted_tasks,
    #     "overdue_tasks": overdue_tasks,
    # })


def courses_teacher(request):
    if request.user.is_anonymous:
        return redirect('/login')
    if not request.user.is_staff:
        return redirect('/courses_student')

    total_ai_screenshots = 0

    if request.user.is_superuser:
        for enrollment_task in EnrollmentTask.objects.filter(ai_ready=True):
            total_ai_screenshots += enrollment_task.ai_used_screenshots
            if enrollment_task.ai_used_screenshots == 0:
                total_ai_screenshots += 10

    all_courses = [
        course for course in Course.objects.filter(deleted=False).order_by('teacher__username', 'name')
        if course.permissions(user=request.user).read
    ]

    courses = Course.objects.filter(teacher=request.user).filter(deleted=False)
    total_minutes = sum([course.total_minutes() for course in all_courses])
    total_time_tracked = f"{total_minutes // 60} h {total_minutes % 60:02d} min"
    for course in all_courses:
        if course.color == 0:
            course.color = random.randint(1, 350)
            course.save(update_fields=['color'])

    return render(request, "courses_teacher.html", {
        "courses": courses,
        "all_courses": all_courses,
        "total_time_tracked": total_time_tracked,
        "page": "all_courses",
        "total_ai_screenshots": total_ai_screenshots,
    })


def random_string(length):
    result = ""
    for i in range(length):
        result += chr(ord('a') + random.randint(0, 25))
    return result


def enroll(request):
    if request.user.is_anonymous:
        return redirect('/login')
    if request.user.is_staff:
        return redirect('/courses_teacher')
    if request.method == 'POST':
        enrollment_code = request.POST.get('enrollment_code')
        course = Course.objects.filter(enrollment_code__iexact=enrollment_code).first()
        if course is None:
            return render(request, "enroll.html", {
                'error': 'Course not found'
            })
        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user, course=course,
            defaults={'folder_prefix': random_string(10)}
        )
        if not created and enrollment.deleted:
            enrollment.deleted = False
            enrollment.save(update_fields=['deleted'])
        return redirect('/courses')
    return render(request, "enroll.html")


def course_add(request, course_id=None):
    if request.user.is_anonymous:
        return redirect('/login')
    if not request.user.is_staff:
        return redirect('/courses_student')

    if course_id is not None:
        course = Course.objects.filter(id=course_id).first()
    else:
        course = Course(
            teacher=request.user,
            name="",
            description=""
        )

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        course.name = name
        course.description = description
        department = int(request.POST.get('department', -1))
        if department >= 0:
            course.department_id = department
            for course1 in Course.objects.exclude(id=course_id).all():
                if course1.teacher == course.teacher:
                    if course1.department is None:
                        course1.department_id = department
                        course1.save()

        if not course.enrollment_code:
            course.enrollment_code = random_string(5)
        course.save()
        return redirect('/courses_teacher')
    
    return render(
        request,
        "new_course.html",
        {
            'course': course,
            'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
            'course_id': course.id if course_id else -1,
            'departments': Department.objects.all(),
        }
    )


@csrf_exempt
def change_code(request, course_id):
    if request.user.is_anonymous:
        return redirect('/login')
    course = Course.objects.get(id=course_id)
    if not course.permissions(user=request.user).write:
        return redirect("/")
    if request.method == 'POST':
        try:
            json_body = request.body.decode('utf-8')
            form = json.loads(json_body)
            code = form.get('enrollment_code')
            if len(code) < 3:
                return HttpResponse("Code too short", status=400)
            if Course.objects.filter(enrollment_code__iexact=code).exists():
                return HttpResponse("Code already in use", status=400)
            course.enrollment_code = code
            course.save(update_fields=['enrollment_code'])
            return HttpResponse("Code changed")
        except Exception as e:
            return HttpResponse("Error: " + str(e), status=400)

    return HttpResponse("Not implemented", status=400)


@csrf_exempt
def change_color(request, course_id):
    course = Course.objects.get(id=course_id)
    if not course.permissions(user=request.user).write:
        return redirect("/")
    if request.method == 'POST':
        try:
            color = random.randint(1, 350)
            course.color = color
            course.save(update_fields=['color'])
            return HttpResponse(str(color))
        except Exception as e:
            return HttpResponse("Error: " + str(e), status=400)

    return HttpResponse("Not implemented", status=400)


def copy_task(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        task = Task.objects.get(id=task_id)
        course = Course.objects.get(id=task.course.id)
        other_courses_teacher = Course.objects.filter(teacher=request.user).exclude(id=course.id)
        if not course.permissions(user=request.user).write:
            return redirect("/")
        for other_course in other_courses_teacher:
            if request.POST.get('select_course_' + str(other_course.id)) == 'on':
                print(f"Copying task {task.name} to course {other_course.name}")
                task_copy = Task.objects.filter(copy_of=task, course=other_course).first()
                if task_copy is None:
                    Task.objects.create(
                        course=other_course,
                        name=task.name,
                        text=task.text,
                        minimum_minutes=task.minimum_minutes,
                        order=task.order,
                        allow_finish_earlier=task.allow_finish_earlier,
                        require_attachments=task.require_attachments,
                        copy_of=task,
                    )
                else:
                    task_copy.name = task.name
                    task_copy.text = task.text
                    task_copy.minimum_minutes = task.minimum_minutes
                    task_copy.order = task.order
                    task_copy.allow_finish_earlier = task.allow_finish_earlier
                    task_copy.require_attachments = task.require_attachments
                    task_copy.save()

    return HttpResponseRedirect('/courses')


def remove_copy(request, task_id):
    task = Task.objects.get(id=task_id)
    if not task.course.permissions(user=request.user).write:
        return redirect("/")
    attachments = Attachment.objects.filter(task=task.copy_of)
    for attachment in attachments:
        attachment.id = None
        attachment.task = task
        attachment.save()
    task.copy_of = None
    task.save(update_fields=['copy_of'])
    return HttpResponseRedirect(f'/courses_teacher/{task.course.id}/tasks')


def delete_course(request, course_id):
    course = Course.objects.get(id=course_id)
    if not course.permissions(user=request.user).delete:
        return redirect("/")
    try:
        course.deleted = True
        course.save(update_fields=['deleted'])
        for enrollment in Enrollment.objects.filter(course=course):
            enrollment.deleted = True
            enrollment.save(update_fields=['deleted'])
        return HttpResponseRedirect('/courses_teacher')
    except Exception as e:
        return HttpResponse("Error: " + str(e), status=400)


def course_edit(request, course_id):
    return course_add(request, course_id=course_id)


def course_teacher_view(request, course_id):
    if request.user.is_anonymous:
        return redirect('/login')
    if not request.user.is_staff:
        return redirect('/courses_student')
    course = Course.objects.get(id=course_id)
    if not course.permissions(user=request.user).read:
        return redirect("/")
    enrollments = Enrollment.objects.filter(course=course)
    return render(request, "enrollments_teacher.html", {
        'course': course,
        'enrollments': enrollments,
        'courses': Course.objects.filter(teacher=request.user).filter(deleted=False),
        'page': 'enrollments',
    })
