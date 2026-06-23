from django.urls import path

from converter import views

urlpatterns = [
    path("", views.index, name="index"),
    path("verify/", views.verify, name="verify"),
    path("download/<uuid:pk>/", views.download, name="download"),
]
