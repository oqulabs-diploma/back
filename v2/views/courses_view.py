from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from app.courses_view import random_string
from app.models import *
from v2.serializers import *
from django.shortcuts import get_object_or_404
import random

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def courses_student(request):
    """API endpoint for students to get their enrolled courses."""
    
    if request.user.is_staff:
        return Response({"redirect": "/courses_teacher"}, status=status.HTTP_302_FOUND)
    
    enrollments = Enrollment.objects.filter(student=request.user, deleted=False)
    serialized_enrollments = EnrollmentSerializer(enrollments, many=True).data
    
    return Response({
        "enrollments": serialized_enrollments,
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def courses_student_tasks(request, course_id: int):
    """API endpoint for students to get their tasks in a course."""
    
    course = get_object_or_404(Course, id=course_id)
    
    if request.user.is_staff:
        return Response({"redirect": "/courses_teacher"}, status=status.HTTP_302_FOUND)
    
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
    
    Task.fix_order(course)
    
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
    enrollment_tasks = list(EnrollmentTask.objects.filter(enrollment=enrollment))
    enrollment_tasks = [
        et for et in enrollment_tasks if et.task.id in started_tasks_ids
    ]
    enrollment_tasks.sort(key=lambda x: x.task.order)
    

    return Response({
        "course": course.name,
        "enrollment": enrollment.id,
        "enrollment_tasks": EnrollmentTaskSerializer(enrollment_tasks, many=True).data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def courses_teacher(request):
    """API endpoint for teachers to view their courses."""
    if not request.user.is_staff:
        return Response({"redirect": "/courses_student"}, status=status.HTTP_302_FOUND)

    total_ai_screenshots = 0
    
    if request.user.is_superuser:
        for enrollment_task in EnrollmentTask.objects.filter(ai_ready=True):
            total_ai_screenshots += enrollment_task.ai_used_screenshots or 0
            if enrollment_task.ai_used_screenshots == 0:
                total_ai_screenshots += 10

    all_courses = [
        course for course in Course.objects.filter(deleted=False).order_by('teacher__username', 'name')
        if course.permissions(user=request.user).read
    ]

    courses = Course.objects.filter(teacher=request.user, deleted=False)

    total_minutes = sum([course.total_minutes() for course in all_courses])
    total_time_tracked = f"{total_minutes // 60} h {total_minutes % 60:02d} min"

    for course in all_courses:
        if course.color == 0:
            course.color = random.randint(1, 350)
            course.save(update_fields=['color'])

    return Response({
        "courses": CourseSerializer(courses, many=True).data,
        "all_courses": CourseSerializer(all_courses, many=True).data,
        "total_time_tracked": total_time_tracked,
        "total_ai_screenshots": total_ai_screenshots,
    }, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def course_add(request, course_id=None):
    """API endpoint to add or update a course."""
    
    if not request.user.is_staff:
        return Response({"redirect": "/courses_student"}, status=status.HTTP_302_FOUND)
    
    if course_id is not None:
        course = get_object_or_404(Course, id=course_id)
    else:
        course = Course(teacher=request.user, name="", description="")
    
    if request.method == 'POST':
        name = request.data.get('name', course.name)
        description = request.data.get('description', course.description)
        department_id = request.data.get('department', -1)
        
        course.name = name
        course.description = description
        
        if department_id is not None and int(department_id) >= 0:
            course.department_id = department_id
            for other_course in Course.objects.exclude(id=course.id).filter(teacher=course.teacher):
                if other_course.department is None:
                    other_course.department_id = department_id
                    other_course.save()
        
        if not course.enrollment_code:
            course.enrollment_code = random_string(5)
        
        course.save()
        return Response(CourseSerializer(course).data, status=status.HTTP_200_OK)
    
    return Response({
        "course": CourseSerializer(course).data,
        "courses": CourseSerializer(Course.objects.filter(teacher=request.user, deleted=False), many=True).data,
        "course_id": course.id if course_id else -1,
        "departments": list(Department.objects.values()),
    }, status=status.HTTP_200_OK)