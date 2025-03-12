from django.contrib import admin
from django.urls import path, include
from app import views, courses_view, enrollments_view, tasks_view, journal_views, students_view
from app.upload_screenshot_view import upload_screenshot
from app.upload_attachment_view import upload_attachment
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path('upload_attachment/<int:enrollment_task_id>', upload_attachment, name='upload_attachment'),
    path('login', views.login_url, name='login'),
    path('register', views.register_url, name='register'),
    path('forgot', views.forgot_url, name='register'),
    path('forgot/step2', views.forgot_step_2_url, name='register'),
    path('logout', views.logout_url, name='logout'),
    path('courses', courses_view.courses_student, name='courses_student'),
    path('courses/<int:course_id>', courses_view.courses_student_tasks, name='courses_student_tasks'),
    path('courses/<int:course_id>/filtered', courses_view.current_tasks_with_filter, name='current_tasks_with_filter'),
    path('courses_teacher', courses_view.courses_teacher, name='courses_teacher'),
    path('courses_teacher/add', courses_view.course_add, name='course_add'),
    path('courses_teacher/edit/<int:course_id>', courses_view.course_edit, name='course_add'),
    path('all_students', students_view.all_students, name='all_students'),
    path('courses_student/enroll', courses_view.enroll, name='course_enroll'),
    path('track/<int:enrollment_task_id>', enrollments_view.track, name='track'),
    path('courses_teacher/<int:course_id>', courses_view.course_teacher_view, name='course_teacher_view'),
    path('courses_teacher/<int:course_id>/tasks', tasks_view.course_tasks, name='course_tasks_view'),
    path('courses_teacher/<int:course_id>/journal', journal_views.journal, name='course_journal_view'),
    path('courses_teacher/<int:course_id>/change_code', courses_view.change_code, name='change_code'),
    path('courses_teacher/<int:course_id>/change_color', courses_view.change_color, name='change_color'),
    path('courses_teacher/<int:course_id>/delete', courses_view.delete_course, name='delete_course'),
    path('export_all', journal_views.export_all, name='export_all'),
    path('attach_files/<int:task_id>', tasks_view.attach_files, name='attach_files'),
    path('delete_attachment/<int:attachment_id>', tasks_view.delete_attachment, name='delete_attachment'),
    path('add_task/<int:course_id>', tasks_view.add_task, name='add_task'),
    path('edit_task/<int:task_id>', tasks_view.edit_task, name='edit_task'),
    path('delete_task/<int:task_id>', tasks_view.delete_task, name='delete_task'),
    path('move_task_up/<int:task_id>', tasks_view.move_task_up, name='move_task_up'),
    path('watch/<int:enrollment_task_id>', enrollments_view.watch, name='watch'),
    path('watch_by_task/<int:task_id>', enrollments_view.details_by_task, name='watch_by_task'),
    path('enrollments/<int:enrollment_id>', enrollments_view.details, name='enrollment_details'),
    path('enrollments/<int:enrollment_id>/delete', enrollments_view.delete, name='enrollment_delete'),
    path('enrollments/<int:enrollment_id>/archive', enrollments_view.archive, name='enrollment_archive'),
    path('enrollments/<int:enrollment_id>/restore', enrollments_view.restore, name='enrollment_restore'),
    path('enrollments/<int:enrollment_id>/send_email/', enrollments_view.send_email, name='enrollment_send_email'),
    path('enrollment_tasks/<int:enrollment_task_id>/ban/<int:minutes>', enrollments_view.ban, name='ban'),
    path('enrollment_tasks/<int:enrollment_task_id>/unban/<int:minutes>', enrollments_view.unban, name='unban'),
    path('enrollment_tasks/<int:enrollment_task_id>/accept/', enrollments_view.accept, name='accept'),
    path('enrollment_tasks/<int:enrollment_task_id>/note/', enrollments_view.note, name='note'),
    path('enrollment_tasks/<int:enrollment_task_id>/unaccept/', enrollments_view.unaccept, name='unaccept'),
    path('enrollment_tasks/<int:enrollment_task_id>/undone/', enrollments_view.undone, name='undone'),
    path('delete_screenshot/<int:screenshot_id>/', enrollments_view.delete_screenshot, name='delete_screenshot'),

    path('copy_task', courses_view.copy_task, name='copy_task'),
    path('remove_copy/<int:task_id>', courses_view.remove_copy, name='remove_copy'),
    path('check_with_ai/enrollment/<int:enrollment_id>', enrollments_view.check_enrollment_with_ai, name='check_enrollment_with_ai'),
    path('check_with_ai/enrollment_task/<int:enrollment_task_id>', enrollments_view.check_enrollment_task_with_ai, name='check_enrollment_task_with_ai'),
    path('check_with_ai/task/<int:task_id>', enrollments_view.check_task_with_ai, name='check_task_with_ai'),

    path('reports', journal_views.reports, name='reports_list'),

    path(settings.TEACHER_REGISTRATION_URL, views.teacher_registration, name='teacher_registration'),
    path("", views.home, name='home'),
    path('i18n/', include('django.conf.urls.i18n')),  
]

urlpatterns += i18n_patterns(
    path('upload/<int:task_id>/', upload_screenshot, name='upload_screenshot'),
    path('enrollment_tasks/<int:enrollment_task_id>/confirm_as_done/', enrollments_view.confirm_as_done, name='confirm_as_done'),
    path('enrollment_tasks/<int:enrollment_task_id>/mark_as_done/', enrollments_view.mark_as_done, name='mark_as_done'),
    path('enrollment_tasks/<int:enrollment_task_id>/send_screenshots/', enrollments_view.send_screenshots, name='send_screenshots'),
    path('enrollment_tasks/<int:enrollment_task_id>/back_to_record/', enrollments_view.back_to_record, name='back_to_record'),
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

