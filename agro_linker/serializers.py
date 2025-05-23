from rest_framework import serializers
from django.contrib.auth import get_user_model
from agro_linker.models.models import *


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'language', 'is_verified', 'role')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
class FarmerSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = FarmerProfile
        fields = '__all__'

class BuyerSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = BuyerProfile
        fields = '__all__'