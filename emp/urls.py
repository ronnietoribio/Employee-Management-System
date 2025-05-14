from django.contrib import admin
from django.urls import path,include
from .views import *

urlpatterns = [
    path("", admin_dashboard, name='admin_dashboard'),  # Make dashboard the default view
    path("login/", login_view, name='login'),
    path("logout/", logout_view, name='logout'),
    path("home/",emp_home),
    path("add-emp/",add_emp),
    path("delete-emp/<int:emp_id>",delete_emp),
    path("update-emp/<int:emp_id>",update_emp),
    path("do-update-emp/<int:emp_id>",do_update_emp),
    path('settings/', settings_view, name='settings'),
]
