from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion


def create_accounts(apps, schema_editor):
    Employee = apps.get_model("attendance", "Employee")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    database = schema_editor.connection.alias
    for employee in Employee.objects.using(database).all():
        if User.objects.using(database).filter(username=employee.employee_id).exists():
            raise RuntimeError(f"Employee {employee.employee_id}: username already exists. Resolve the collision before migrating; existing accounts are never claimed or reset.")
        user = User.objects.using(database).create(
            username=employee.employee_id, password=make_password(employee.employee_id),
        )
        employee.user_id = user.pk
        employee.save(using=database, update_fields=["user"])


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0004_devicecommand"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name="employee", name="user",
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="employee", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(create_accounts),
        migrations.AlterField(
            model_name="employee", name="user",
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="employee", to=settings.AUTH_USER_MODEL),
        ),
    ]
