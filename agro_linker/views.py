"""
Authentication API endpoints for Agro Linker.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from agro_linker.models import *
from agro_linker.serializers import *
from django.shortcuts import render

User = get_user_model()



def index(request):
    return render(request, 'index.html')


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password):
        user = self.create_user(phone, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class AuthViewSet(viewsets.ViewSet):
    """
    Authentication operations for all user types.
    """
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Base user registration endpoint.
        """
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='register/farmer')
    def register_farmer(self, request):
        """
        Specialized farmer registration with profile creation.
        """
        user_serializer = UserSerializer(data=request.data.get('user', {}))
        farmer_serializer = FarmerSerializer(data=request.data.get('farmer', {}))
        
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        user = user_serializer.save(role='FARMER')
        farmer_data = {**farmer_serializer.initial_data, 'user': user.id}
        farmer_serializer = FarmerSerializer(data=farmer_data)
        
        if farmer_serializer.is_valid():
            farmer_serializer.save()
            return Response({
                'user': user_serializer.data,
                'farmer': farmer_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(farmer_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='register/buyer')
    def register_buyer(self, request):
        """
        Buyer registration endpoint.
        """
        serializer = BuyerSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(role='BUYER')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        JWT token authentication.
        """
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        
        if not user:
            return Response(
                {'detail': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        """
        Blacklist refresh token on logout.
        """
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(
                {'detail': 'Invalid token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )