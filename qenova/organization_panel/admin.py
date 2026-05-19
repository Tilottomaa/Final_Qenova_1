from django.contrib import admin
from .models import (
    BehaviorMonitoring,
    QueueReport,
)

admin.site.register(QueueReport)
admin.site.register(BehaviorMonitoring)
