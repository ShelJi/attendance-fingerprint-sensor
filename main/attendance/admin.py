from django.contrib import admin

from .models import Employee, AttendanceSession, AttendanceDevice


admin.site.register(Employee)   
admin.site.register(AttendanceSession)
admin.site.register(AttendanceDevice)