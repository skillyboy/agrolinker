from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
from django.contrib.auth.models import Group


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location')
    # Add other configurations as needed

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'farmer', 'category', 'created_at')
    # Add other configurations as needed

# Register other models similarly
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ChatMessage)
admin.site.register(Notification)

# Unregister Group if you don't need it
# admin.site.unregister(Group)