from email.policy import default
from unittest.util import _MAX_LENGTH
from django.db import models
from django.utils import timezone

def employee_image_path(instance, filename):
    # Generate file path: profile_pics/employee_id/filename
    return f'profile_pics/{instance.emp_id}/{filename}'

# Create your models here.
class Emp(models.Model):
    name=models.CharField(max_length=200)
    emp_id=models.CharField(max_length=200)
    phone=models.CharField(max_length=11)
    address=models.CharField(max_length=150)
    working=models.BooleanField(default=True)
    department=models.CharField(max_length=200)
    age=models.IntegerField(default=18)
    salary=models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profile_pic = models.ImageField(upload_to=employee_image_path, default='profile_pics/default.png', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_modified = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id:  # Only set created_at for new instances
            self.created_at = timezone.now()
        self.last_modified = timezone.now()
        return super(Emp, self).save(*args, **kwargs)

    class Meta:
        ordering = ['-last_modified']  # Show most recently modified first

class Settings(models.Model):
    company_name = models.CharField(max_length=200, default="My Company")
    company_address = models.TextField(blank=True)
    company_contact = models.CharField(max_length=20, blank=True)
    company_email = models.EmailField(blank=True)
    
    # Department Settings
    department_choices = models.TextField(
        help_text="Enter department names separated by commas",
        default="Computer Science,Mechanical Engineering,Electrical Engineering,Civil Engineering"
    )
    
    # Email Settings
    enable_email_notifications = models.BooleanField(default=False)
    notification_email = models.EmailField(blank=True)
    
    # System Settings
    items_per_page = models.IntegerField(default=20)
    enable_audit_trail = models.BooleanField(default=True)
    
    # Theme Settings
    primary_color = models.CharField(max_length=7, default="#50024d")
    secondary_color = models.CharField(max_length=7, default="#0e6001")
    text_color = models.CharField(max_length=7, default="#000000")
    header_style = models.CharField(
        max_length=20,
        choices=[
            ('solid', 'Solid Color'),
            ('gradient', 'Gradient'),
            ('transparent', 'Transparent')
        ],
        default='gradient'
    )
    border_radius = models.IntegerField(default=8)
    font_size = models.CharField(
        max_length=10,
        choices=[
            ('small', 'Small'),
            ('medium', 'Medium'),
            ('large', 'Large')
        ],
        default='medium'
    )
    
    class Meta:
        verbose_name = "Settings"
        verbose_name_plural = "Settings"
    
    def __str__(self):
        return "System Settings"
    
    def get_department_list(self):
        return [dept.strip() for dept in self.department_choices.split(',')]