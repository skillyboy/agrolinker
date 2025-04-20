from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.http import JsonResponse
from ninja import Router

router = Router(tags=["WhatsApp"])

def send_whatsapp_message(request: HttpRequest, message: str):
    """
    Send a WhatsApp message to the user
    """
    user = get_object_or_404(User, id=request.user.id)
    user.send_whatsapp_message(message)
    return JsonResponse({"message": "WhatsApp message sent successfully"})  

def send_whatsapp_message_to_all(request: HttpRequest, message: str):
    """
    Send a WhatsApp message to all users
    """
    users = User.objects.all()
    for user in users:
        send_whatsapp_message(request, message)
    return JsonResponse({"message": "WhatsApp message sent to all users successfully"})

def send_whatsapp_message_to_user(request: HttpRequest, message: str, user: User):
    """
    Send a WhatsApp message to a specific user
    """ 
    user.send_whatsapp_message(message)
    return JsonResponse({"message": "WhatsApp message sent to user successfully"})

def send_whatsapp_message_to_all_except_user(request: HttpRequest, message: str, user: User):
    """
    Send a WhatsApp message to all users except a specific user
    """ 
    users = User.objects.all()
    for user in users:
        if user != user:
            send_whatsapp_message(request, message)
    return JsonResponse({"message": "WhatsApp message sent to all users except user successfully"})
