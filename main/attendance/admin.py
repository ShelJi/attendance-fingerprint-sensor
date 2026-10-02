from django.contrib import admin

from .models import Employee, AttendanceSession, AttendanceDevice, DeviceCommand


admin.site.register(Employee)   
admin.site.register(AttendanceSession)
admin.site.register(AttendanceDevice)
admin.site.register(DeviceCommand)


