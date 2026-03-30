from ..serializers import UserRegistrationSerializer
from .base import BaseCreateAPIView


class UserRegistrationView(BaseCreateAPIView):
    serializer_class = UserRegistrationSerializer
    success_message = "User registered successfully."
