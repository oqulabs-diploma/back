from rest_framework import serializers
from app.models import *

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password")

    def validate_email(self, value):
        """Убедиться, что пользователь с таким email ещё не зарегистрирован."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def create(self, validated_data):
        """Создание пользователя, username = email."""
        user = User(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            username=validated_data['email'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
    
class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for the Enrollment model."""
    student_username = serializers.CharField(source='student.username', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'student',
            'student_username',
            'course',
            'course_name',
            'total_minutes',
            'total_ban_minutes',
            'folder_prefix',
            'deleted',
        ]

class EnrollmentTaskSerializer(serializers.ModelSerializer):
    """Serializer for the EnrollmentTask model."""
    enrollment_id = serializers.PrimaryKeyRelatedField(source='enrollment.id', read_only=True)
    task_id = serializers.PrimaryKeyRelatedField(source='task.id', read_only=True)
    task_name = serializers.CharField(source='task.name', read_only=True)

    class Meta:
        model = EnrollmentTask
        fields = [
            'id',
            'enrollment_id',
            'task_id',
            'task_name',
            'minutes',
            'last_hh_mm',
            'last_submission',
            'ban_minutes',
            'last_shared_id',
            'marked_as_done',
            'under_review',
            'accepted',
            'score',
            'watched',
            'note',
            'ai_note',
            'ai_ready',
            'ai_request',
            'ai_score',
            'ai_description',
            'ai_used_screenshots',
        ]

class CourseSerializer(serializers.ModelSerializer):
    """Serializer for the Course model."""
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'teacher',
            'teacher_username',
            'name',
            'description',
            'max_screenshots_per_user',
            'screenshot_interval_minutes',
            'enrollment_code',
            'deleted',
            'color',
            'department',
            'department_name',
        ]
