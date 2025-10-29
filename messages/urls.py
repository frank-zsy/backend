"""消息 URL 配置."""

from django.urls import path

from . import views

app_name = "messages"

urlpatterns = [
    path("", views.message_list, name="list"),
    path("<int:pk>/", views.message_detail, name="detail"),
    path("mark-read/", views.mark_read, name="mark_read"),
    path("mark-unread/", views.mark_unread, name="mark_unread"),
    path("delete/", views.delete_message, name="delete"),
    path("unread-count/", views.unread_count, name="unread_count"),
]
