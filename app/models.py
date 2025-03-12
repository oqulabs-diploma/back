from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from app.email_task import send_email
from django.utils import timezone
from django.db.models import Sum


@dataclass
class Permission:
    read: bool
    write: bool
    delete: bool


cached_permissions = {}


class Department(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    color = models.IntegerField(default=0)  # up to 359

    def __str__(self):
        return self.name


class Course(models.Model):
    teacher = models.ForeignKey('auth.User', on_delete=models.DO_NOTHING, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    max_screenshots_per_user = models.PositiveIntegerField(default=60*15)  # 15 hours, 180 MB
    screenshot_interval_minutes = models.PositiveIntegerField(default=1)
    enrollment_code = models.CharField(max_length=30, unique=True, blank=True, null=True)
    deleted = models.BooleanField(default=False)
    color = models.IntegerField(default=0)  # up to 359
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING, null=True, blank=True)

    def permissions(self, user: User, expire=60 * 5) -> Permission:
        now = datetime.now()
        key = f"{self.id}-{user.id}"
        if key in cached_permissions:
            permission, time = cached_permissions[f"{self.id}-{user.id}"]
            if (now - time).seconds < expire:
                return permission

        permission = Permission(read=False, write=False, delete=False)
        if user is None or not user.is_authenticated:
            permission = Permission(read=False, write=False, delete=False)
        elif user.is_superuser:
            permission = Permission(read=True, write=True, delete=True)
        elif not user.is_staff:
            permission = Permission(read=False, write=False, delete=False)
        elif user == self.teacher:
            permission = Permission(read=True, write=True, delete=True)
        elif self.coursesupervisor_set.filter(user=user).exists():
            course_supervisor = self.coursesupervisor_set.get(user=user)
            permission = Permission(
                read=course_supervisor.read,
                write=course_supervisor.write,
                delete=course_supervisor.delete,
            )
        cached_permissions[key] = (permission, now)
        return permission

    def tasks_number(self):
        return self.task_set.count()

    def enrolled_students(self):
        return self.enrollment_set.filter(deleted=False).count()

    def total_minutes(self, tasks=None):
        if tasks is None:
            tasks = self.task_set.all()
        return sum([task.total_minutes() for task in tasks])

    def total_time(self, tasks=None):
        total_mins = self.total_minutes(tasks=tasks)
        return f"{total_mins // 60} h {total_mins % 60:02d} min"

    def tasks_count(self):
        return self.task_set.count()

    def __str__(self):
        return f"{self.name}, department: {self.department}"

    class Meta:
        ordering = ['-id']


class CourseSupervisor(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    read = models.BooleanField(default=True)
    write = models.BooleanField(default=True)
    delete = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.course.name} - {self.user.username}: R-{self.read} W-{self.write} D-{self.delete}"


class TaskType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Task(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    text = models.TextField()
    minimum_minutes = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    allow_finish_earlier = models.BooleanField(default=False)  # TODO: add to UI
    require_attachments = models.BooleanField(default=False)  # TODO: add to UI
    task_type = models.ForeignKey(TaskType, on_delete=models.DO_NOTHING, null=True, blank=True)
    copy_of = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    available_from = models.DateTimeField(blank=True, null=True)
    available_to = models.DateTimeField(blank=True, null=True)
    deleted = models.BooleanField(default=False)
    ai_screenshots_count = models.PositiveIntegerField(default=10)

    @classmethod
    def fix_order(cls, course: Course):
        course_id = course.id
        # tasks = cls.objects.filter(course_id=course_id).order_by('order')
        # for i, task in enumerate(tasks):
        #     task.order = i+1
        #     task.save(update_fields=['order'])
        tasks = list(cls.objects.filter(course=course).order_by('order'))
        for i, task in enumerate(tasks):
            task.order = i + 1
        cls.objects.bulk_update(tasks, ['order'])

    def is_active_right_now(self):
        if self.deleted:
            return False
        now = timezone.now()
        if self.available_from is not None and now < self.available_from:
            return False
        if self.available_to is not None and now > self.available_to:
            return False
        return True

    def __str__(self):
        return f"{self.course.name} - {self.name}"

    def minimum_time(self):
        return f"{self.minimum_minutes // 60} h {self.minimum_minutes % 60:02d} min"

    class Meta:
        ordering = ['order']

    def total_minutes(self):
        return self.enrollmenttask_set.aggregate(total_minutes=Sum('minutes'))['total_minutes'] or 0

    def watched(self) -> bool:
        return self.enrollmenttask_set.filter(watched=False).filter(last_shared_id__gt=0).count() == 0

    def has_started(self):
        if self.deleted:
            return False
        if self.available_from is None:
            return True

        return timezone.now() > self.available_from


class Enrollment(models.Model):
    student = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    total_minutes = models.PositiveIntegerField(default=0)
    total_ban_minutes = models.PositiveIntegerField(default=0)
    folder_prefix = models.CharField(max_length=100, blank=True, null=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.username} - {self.course.name}: {self.total_minutes} minutes"

    def total_minutes_func(self, tasks=None):
        enrollment_tasks = EnrollmentTask.objects.filter(enrollment=self)
        if tasks is not None:
            enrollment_tasks = enrollment_tasks.filter(task__in=tasks)
        return enrollment_tasks.aggregate(
            total_minutes=Sum('minutes')
        )['total_minutes'] or 0

    def worked_tasks(self):
        return self.enrollmenttask_set.count()

    def completed_tasks(self):
        return self.enrollmenttask_set.filter(accepted=True).count()

    def total_time(self):
        total_minutes = self.total_minutes_func()  # - self.total_ban_minutes
        return f"{total_minutes // 60} h {total_minutes % 60:02d} min"

    def total_time_ban(self):
        return f"{self.total_ban_minutes // 60} h {self.total_ban_minutes % 60:02d} min"

    def needs_attention(self):
        marked_as_done = self.enrollmenttask_set.filter(accepted=False, marked_as_done=True).count()
        return marked_as_done > 0

    def progress_num(self):
        if self.total_minutes == 0:
            return 0
        worked_minutes = self.total_minutes - self.total_ban_minutes
        required_minutes = sum([task.minimum_minutes for task in self.course.task_set.all()])
        if required_minutes == 0:
            return 0
        progress = worked_minutes / required_minutes
        progress = max(0, min(1, progress)) * 100
        return int(progress)

    def check_with_ai(self):
        for enrollment_task in self.enrollmenttask_set.filter(ai_request=False):
            enrollment_task.ai_request = True
            enrollment_task.save(update_fields=['ai_request'])

    def send_email(self, text):
        text = f"""
Dear {self.student.first_name},

You have a message from OquLabs:

## {text}

Best regards,
OquLabs
                """
        send_email(
            name=self.student.first_name,
            email=self.student.email,
            subject="Message from OquLabs",
            text=text,
        )


class EnrollmentTask(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    minutes = models.PositiveIntegerField(default=0)
    last_hh_mm = models.CharField(max_length=10, default="00:00")
    last_submission = models.DateTimeField(null=True, blank=True)
    ban_minutes = models.PositiveIntegerField(default=0)
    last_shared_id = models.PositiveIntegerField(default=0)
    marked_as_done = models.BooleanField(blank=True, default=False)
    under_review = models.BooleanField(blank=True, default=False)
    accepted = models.BooleanField(default=False)
    score = models.PositiveIntegerField(default=100)
    watched = models.BooleanField(default=False)
    note = models.CharField(max_length=50, default="", blank=True)
    ai_note = models.TextField(default="", blank=True)
    ai_ready = models.BooleanField(default=False)
    ai_request = models.BooleanField(default=False)
    ai_score = models.PositiveIntegerField(default=0)
    ai_description = models.TextField(default="", blank=True)
    ai_used_screenshots = models.PositiveIntegerField(default=0)

    def __str__(self):
        done = "Done" if self.marked_as_done else "Not done"
        result = f"{self.enrollment} - {self.task.name}: {self.minutes} minutes - {done}"
        if self.ai_ready:
            result += f" - AI: {self.ai_note[:20]}"
        return result

    def total_time(self):
        minutes = self.minutes - self.ban_minutes
        return f"{minutes // 60} h {minutes % 60:02d} min"

    def total_time_ban(self):
        return f"{self.ban_minutes // 60} h {self.ban_minutes % 60:02d} min"

    def progress_num(self):
        worked_minutes = self.minutes - self.ban_minutes
        if self.task.minimum_minutes == 0:
            return 0
        progress = worked_minutes / self.task.minimum_minutes
        progress = max(0, min(1, progress)) * 100
        return int(progress)

    def ai_eligible(self) -> bool:
        return self.progress_num() > 95

    def progress(self):
        if self.accepted:
            return "Accepted"
        if self.marked_as_done:
            return "Done"
        if self.under_review:
            return "Under review"
        if self.minutes == 0:
            return "Not started"
        worked_minutes = self.minutes - self.ban_minutes
        if self.task.minimum_minutes == 0:
            return str(worked_minutes) + " min"
        progress = worked_minutes / self.task.minimum_minutes
        progress = max(0, min(1, progress))
        return f"{progress * 100:.0f}%"

    class Meta:
        ordering = ['id']


class EnrollmentTaskAiDialog(models.Model):
    enrollment_task = models.ForeignKey(EnrollmentTask, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    from_student = models.BooleanField(default=False)
    from_teacher = models.BooleanField(default=False)
    from_ai = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.enrollment_task} - {self.created_at} - {self.text[:20]}"

    class Meta:
        ordering = ['id']


class Attachment(models.Model):
    enrollment_task = models.ForeignKey(EnrollmentTask, on_delete=models.CASCADE, null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    attachment = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_to_s3 = models.BooleanField(default=False)
    s3_key = models.CharField(max_length=1000, blank=True, null=True)

    def __str__(self):
        return f"{self.enrollment_task} - {self.created_at}"


class Screenshot(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, db_index=True)
    enrollment_task = models.ForeignKey(EnrollmentTask, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    screenshot = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    at_minute = models.PositiveIntegerField(default=0)
    sent_to_s3 = models.BooleanField(default=False)
    s3_key = models.CharField(max_length=1000, blank=True, null=True)
    ai_comment = models.TextField(default="", blank=True)
    ai_ready = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        try:
            return f"{self.enrollment} - {self.enrollment_task.task.name} - {self.created_at}"
        except AttributeError:
            return f"{self.enrollment} - {self.created_at}"

    def time(self):
        return f"{self.at_minute // 60}:{self.at_minute % 60:02d}"

    class Meta:
        ordering = ['id']


class Notification(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    text = models.CharField(max_length=1000)
    link = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    emailed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.text}"


class EnrollmentTaskMessage(models.Model):
    enrollment_task = models.ForeignKey(EnrollmentTask, on_delete=models.CASCADE)
    text = models.CharField(max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)
    from_student = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.enrollment_task} - {self.created_at} - {self.text[:20]}"


class ForgotPassword(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.token}"

    def send_email(self):
        text = f"""
Hello {self.user.first_name},

You have requested to reset your password. Please use this token to reset password:

## {self.token}

If you did not request this, please ignore this email.

Best regards,
OquLabs
        """
        send_email(
            name=self.user.first_name,
            email=self.user.email,
            subject="Password reset token",
            text=text,
        )
