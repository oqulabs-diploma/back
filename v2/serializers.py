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