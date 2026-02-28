from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('c/<uuid:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('api/conversations/', views.get_conversations, name='get_conversations'),
    path('api/conversations/new/', views.new_conversation, name='new_conversation'),
    path('api/conversations/<uuid:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    path('api/conversations/<uuid:conversation_id>/messages/', views.send_message, name='send_message'),
]
