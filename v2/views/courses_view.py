from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from app.models import *
from v2.serializers import EnrollmentSerializer


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