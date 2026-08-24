from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import RegisterSerializer, UserSerializer

REFRESH_COOKIE_NAME = "refresh_token"

# Section 13 of the blueprint: the refresh token lives in an httpOnly,
# Secure, SameSite=Lax cookie. It is never present in a JSON response body,
# so it can't be read by JS and can't leak into localStorage by accident.
# The access token IS returned in the body — it's short-lived and meant to
# be held in memory on the frontend, not persisted.
REFRESH_COOKIE_KWARGS = {
    "httponly": True,
    "secure": not settings.DEBUG,
    "samesite": "Lax",
    "path": "/api/auth/",
}


def _issue_tokens_response(user, status_code=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)
    response = Response(
        {
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        },
        status=status_code,
    )
    response.set_cookie(REFRESH_COOKIE_NAME, str(refresh), **REFRESH_COOKIE_KWARGS)
    return response


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _issue_tokens_response(user, status_code=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth-login"

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        user = User.objects.filter(email__iexact=email).first()

        # Deliberately generic error message whether the email exists or
        # not, so this endpoint doesn't leak which emails are registered.
        if user is None or not user.check_password(password) or not user.is_active:
            raise AuthenticationFailed("Invalid email or password.")

        return _issue_tokens_response(user)


class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_refresh:
            raise AuthenticationFailed("No refresh token cookie present.")

        try:
            refresh = RefreshToken(raw_refresh)
        except TokenError as exc:
            raise AuthenticationFailed("Refresh token invalid or expired.") from exc

        response = Response({"access": str(refresh.access_token)})

        # Rotate the refresh token on every use and blacklist the old one —
        # limits the damage window if a refresh cookie is ever stolen.
        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
            try:
                refresh.blacklist()
            except AttributeError:
                pass
            new_refresh = RefreshToken.for_user(User.objects.get(id=refresh["user_id"]))
            response.set_cookie(REFRESH_COOKIE_NAME, str(new_refresh), **REFRESH_COOKIE_KWARGS)

        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/auth/")
        return response


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
