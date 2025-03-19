from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from app.courses_view import random_string
from app.models import *
from v2.serializers import *
from django.shortcuts import get_object_or_404


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