from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """Let customers log in with either their username or their email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        candidates = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username))
        for user in candidates:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        # Run the hasher once so response time doesn't reveal whether the account exists.
        User().set_password(password)
        return None
