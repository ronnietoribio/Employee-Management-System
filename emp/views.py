from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseRedirect
from .models import Emp, Settings
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from django.views.decorators.cache import never_cache
from django.utils.cache import patch_response_headers
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse

def rate_limit_login(view_func):
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST':
            ip = request.META.get('REMOTE_ADDR')
            key = f'login_attempts_{ip}'
            attempts = cache.get(key, 0)
            
            if attempts >= 5:  # 5 attempts max
                messages.error(request, 'Too many login attempts. Please try again in 5 minutes.')
                return redirect('login')
                
            cache.set(key, attempts + 1, 300)  # 5 minutes timeout
        return view_func(request, *args, **kwargs)
    return wrapper

def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build password reset link
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Send email
            subject = "Password Reset Requested"
            email_template_name = "emp/password_reset_email.html"
            context = {
                "email": user.email,
                'reset_url': reset_url,
                'user': user,
            }
            email_message = render_to_string(email_template_name, context)
            
            send_mail(subject, email_message, 'noreply@example.com', [user.email])
            messages.success(request, 'Password reset link has been sent to your email.')
            
        except User.DoesNotExist:
            messages.error(request, 'No user found with that email address.')
        
    return render(request, 'emp/password_reset.html')

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            if request.method == "POST":
                new_password = request.POST.get("new_password")
                confirm_password = request.POST.get("confirm_password")
                
                if new_password == confirm_password:
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, 'Password has been reset successfully.')
                    return redirect('login')
                else:
                    messages.error(request, 'Passwords do not match.')
            
            return render(request, 'emp/password_reset_confirm.html')
        else:
            messages.error(request, 'Password reset link is invalid or has expired.')
            
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, 'Invalid password reset link.')
    
    return redirect('login')

# Apply rate limiting to login view
@rate_limit_login
@never_cache
def login_view(request):
    # Prevent caching of the login page
    response = HttpResponse()
    patch_response_headers(response, cache_timeout=0)
    
    if request.user.is_authenticated:
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember-me') == 'on'
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Create session data
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['is_authenticated'] = True
            request.session['session_key'] = get_random_string(32)
            
            # Set session expiry based on remember me
            if remember_me:
                # Set session to expire in 30 days
                request.session.set_expiry(30 * 24 * 60 * 60)
            else:
                # Set session to expire in 12 hours
                request.session.set_expiry(43200)
            
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    response = render(request, 'emp/login.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@never_cache
def logout_view(request):
    if request.user.is_authenticated:
        # Clear specific session data
        session_keys = ['user_id', 'username', 'is_authenticated', 'session_key']
        for key in session_keys:
            request.session.pop(key, None)
        
        # Flush the entire session
        request.session.flush()
        
        # Clear the session cookie
        request.session.clear()
        
        # Django's built-in logout
        logout(request)
    
    # Force redirect to login with no-cache headers
    response = HttpResponseRedirect('/emp/login/')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    # Add header to prevent back/forward cache
    response['X-Frame-Options'] = 'DENY'
    return response

def session_check(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # If user is not authenticated, clear any remaining session data
            request.session.flush()
            messages.error(request, 'Please login to continue.')
            response = HttpResponseRedirect('/emp/login/')
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        return view_func(request, *args, **kwargs)
    return wrapper

# Apply session check to all protected views
@login_required(login_url='login')
@session_check
def emp_home(request):
    emps = Emp.objects.all()
    departments = get_departments()
    return render(request, "emp/home.html", {
        'emps': emps,
        'departments': departments
    })


def get_departments():
    settings = Settings.objects.first()
    if settings:
        return settings.get_department_list()
    return []

@login_required(login_url='login')
@session_check
def add_emp(request):
    if request.method == "POST":
        emp_name = request.POST.get("emp_name")
        emp_id = request.POST.get("emp_id")
        emp_phone = request.POST.get("emp_phone")
        emp_address = request.POST.get("emp_address")
        emp_working = request.POST.get("emp_working")
        emp_department = request.POST.get("emp_department")
        emp_age = request.POST.get("emp_age")
        emp_salary = request.POST.get("emp_salary")
        
        e = Emp()
        e.name = emp_name
        e.emp_id = emp_id
        e.phone = emp_phone
        e.address = emp_address
        e.department = emp_department
        e.working = emp_working == 'true'
        e.age = int(emp_age)
        e.salary = float(emp_salary)
        
        # Handle profile picture
        if request.FILES.get('profile_pic'):
            e.profile_pic = request.FILES['profile_pic']
        
        e.save()
        messages.success(request, f'Employee "{emp_name}" has been added successfully!')
        return redirect("/emp/home/")
        
    return render(request, "emp/add_emp.html", {
        'departments': get_departments()
    })

@login_required(login_url='login')
@session_check
def delete_emp(request,emp_id):
    emp=Emp.objects.get(pk=emp_id)
    name = emp.name  # Store name before deletion
    emp.delete()
    messages.success(request, f'Employee "{name}" has been deleted successfully!')
    return redirect("/emp/home/")

@login_required(login_url='login')
@session_check
def update_emp(request, emp_id):
    emp = Emp.objects.get(pk=emp_id)
    return render(request, "emp/update_emp.html", {
        'emp': emp,
        'departments': get_departments()
    })

@login_required(login_url='login')
@session_check
def do_update_emp(request, emp_id):
    if request.method == "POST":
        emp_name = request.POST.get("emp_name")
        emp_id_temp = request.POST.get("emp_id")
        emp_phone = request.POST.get("emp_phone")
        emp_address = request.POST.get("emp_address")
        emp_working = request.POST.get("emp_working")
        emp_department = request.POST.get("emp_department")
        emp_age = request.POST.get("emp_age")
        emp_salary = request.POST.get("emp_salary")

        e = Emp.objects.get(pk=emp_id)
        e.name = emp_name
        e.emp_id = emp_id_temp
        e.phone = emp_phone
        e.address = emp_address
        e.department = emp_department
        e.working = emp_working == 'true'
        e.age = int(emp_age)
        e.salary = float(emp_salary)
        
        # Handle profile picture update
        if request.FILES.get('profile_pic'):
            e.profile_pic = request.FILES['profile_pic']
        
        e.save()
        messages.success(request, f'Employee "{emp_name}" has been updated successfully!')
    return redirect("/emp/home/")

@login_required(login_url='login')
@session_check
def admin_dashboard(request):
    # Get total employees count
    total_employees = Emp.objects.count()
    
    # Get active employees count
    active_employees = Emp.objects.filter(working=True).count()
    
    # Get unique departments count
    total_departments = Emp.objects.values('department').distinct().count()
    
    # Get recent updates (count of employees modified in last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_updates = Emp.objects.filter(last_modified__gte=thirty_days_ago).count()
    
    # Get 5 most recently modified employees
    recent_employees = Emp.objects.all()[:5]  # ordering is already set in model Meta
    
    # Get departments list for filter
    departments = get_departments()
    
    context = {
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_departments': total_departments,
        'recent_updates': recent_updates,
        'recent_employees': recent_employees,
        'departments': departments,
    }
    
    return render(request, "emp/admin_dashboard.html", context)

@login_required(login_url='login')
@session_check
def settings_view(request):
    # Get or create settings instance
    settings_instance, created = Settings.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        try:
            # Company Information
            company_name = request.POST.get('company_name')
            if not company_name:
                messages.error(request, 'Company name is required!')
                return redirect('settings')
            
            settings_instance.company_name = company_name
            settings_instance.company_address = request.POST.get('company_address', '')
            settings_instance.company_contact = request.POST.get('company_contact', '')
            settings_instance.company_email = request.POST.get('company_email', '')
            
            # Department Settings
            settings_instance.department_choices = request.POST.get('department_choices', '')
            
            # Email Settings
            settings_instance.enable_email_notifications = request.POST.get('enable_email_notifications') == 'on'
            settings_instance.notification_email = request.POST.get('notification_email', '')
            
            # System Settings
            try:
                items_per_page = int(request.POST.get('items_per_page', 20))
                if not (5 <= items_per_page <= 100):
                    messages.error(request, 'Items per page must be between 5 and 100!')
                    return redirect('settings')
                settings_instance.items_per_page = items_per_page
            except ValueError:
                messages.error(request, 'Invalid value for items per page!')
                return redirect('settings')
            
            settings_instance.enable_audit_trail = request.POST.get('enable_audit_trail') == 'on'
            
            # Theme Settings
            settings_instance.primary_color = request.POST.get('primary_color', '#50024d')
            settings_instance.secondary_color = request.POST.get('secondary_color', '#0e6001')
            settings_instance.text_color = request.POST.get('text_color', '#000000')
            settings_instance.header_style = request.POST.get('header_style', 'gradient')
            settings_instance.border_radius = int(request.POST.get('border_radius', 8))
            settings_instance.font_size = request.POST.get('font_size', 'medium')
            
            settings_instance.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings')
            
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
            return redirect('settings')
    
    return render(request, 'emp/settings.html', {
        'settings': settings_instance,
        'departments': settings_instance.get_department_list(),
    })

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        terms = request.POST.get('terms')

        # Validation
        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('register')
        
        if not terms:
            messages.error(request, 'Please agree to the terms and conditions!')
            return redirect('register')

        # Create user
        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('register')

    return render(request, 'emp/register.html')
