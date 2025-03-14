# cafe/auth_backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class PhoneOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try to find a user by phone number first
        try:
            user_profile = UserProfile.objects.get(phone_number=username)
            user = user_profile.user
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except UserProfile.DoesNotExist:
            # If no phone number match, try username
            try:
                user = User.objects.get(username=username)
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
            except User.DoesNotExist:
                return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None