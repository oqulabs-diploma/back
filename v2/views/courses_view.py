from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
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