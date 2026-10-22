from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload_document, name="upload_document"),
    path("ask/", views.ask_question, name="ask_question"),
    path("documents/<int:document_id>/delete/", views.delete_document, name="delete_document"),
]
