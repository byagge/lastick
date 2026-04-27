from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered


for model in (Group, LogEntry):
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass
