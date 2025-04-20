from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging
from datetime import datetime
from .user import User

logger = logging.getLogger(__name__)
from django.core.exceptions import ValidationError

class ChatRoom(models.Model):
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message = models.DateTimeField(null=True, blank=True)
    is_group = models.BooleanField(default=False)
    name = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('chat room')
        verbose_name_plural = _('chat rooms')
        ordering = ['-last_message']
    
    def __str__(self):
        if self.is_group:
            return self.name or f"Group Chat {self.id}"
        participants = self.participants.all()
        return f"Chat between {participants[0]} and {participants[1]}"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = _('chat message')
        verbose_name_plural = _('chat messages')
    
    def __str__(self):
        return f"Message from {self.sender} in {self.room}"

