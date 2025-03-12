from django.contrib import admin
from app.models import (
    Course,
    Enrollment,
    EnrollmentTask,
    EnrollmentTaskAiDialog,
    Screenshot,
    Attachment,
    TaskType,
    Task,
    CourseSupervisor,
    Department,    
)

admin.site.register(Course)
admin.site.register(Task)
admin.site.register(TaskType)
admin.site.register(Enrollment)
admin.site.register(EnrollmentTask)
admin.site.register(EnrollmentTaskAiDialog)
admin.site.register(Screenshot)
admin.site.register(Attachment)
admin.site.register(CourseSupervisor)
admin.site.register(Department)
