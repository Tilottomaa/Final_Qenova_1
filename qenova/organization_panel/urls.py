from django.urls import path

from . import views

urlpatterns = [


    path(
        'org-dashboard/settings/',
        views.organization_settings_view,
        name='org_settings',
    ),


]
