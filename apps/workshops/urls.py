from django.urls import path
from .api import (
    MyWorkshopsView,
    WorkshopEmployeesView,
    AllWorkshopsView,
    WorkshopMastersView,
    AddWorkshopMasterView,
    RemoveWorkshopMasterView,
    MasterWorkshopsStatsView,
    ExtrusionReportView,
    NeutralBatchesListView,
    PackagingReportView,
)

urlpatterns = [
    path('api/my-workshops/', MyWorkshopsView.as_view()),
    path('api/employees/', WorkshopEmployeesView.as_view()),
    path('api/all/', AllWorkshopsView.as_view()),
    path('api/masters/', WorkshopMastersView.as_view()),
    path('api/add-master/', AddWorkshopMasterView.as_view()),
    path('api/remove-master/', RemoveWorkshopMasterView.as_view()),
    path('api/master-stats/', MasterWorkshopsStatsView.as_view()),
    # Новый workflow
    path('api/extrusion/report/', ExtrusionReportView.as_view()),
    path('api/neutral-batches/', NeutralBatchesListView.as_view()),
    path('api/packaging/report/', PackagingReportView.as_view()),
] 