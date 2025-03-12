from django.shortcuts import render
from app.models import Enrollment

def all_students(request):
    enrollments = Enrollment.objects.filter(deleted=False).select_related('student', 'course')

    students_dict = {}
    for enrollment in enrollments:
        student = enrollment.student
        if student.id not in students_dict:
            students_dict[student.id] = {
                "full_name": f"{student.first_name} {student.last_name}",
                "email": student.email,
                "courses": [],
                "enrollment_id": None  
            }
        students_dict[student.id]["courses"].append({
            "id": enrollment.course.id,
            "name": enrollment.course.name
        })
        if not students_dict[student.id]["enrollment_id"]:
            students_dict[student.id]["enrollment_id"] = enrollment.id

    students = list(students_dict.values())

    return render(request, "all_students.html", {"students": students, "page": "all_students"})
