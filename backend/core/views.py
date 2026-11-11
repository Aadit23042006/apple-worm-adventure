import traceback
import hashlib
import hmac
import logging
import secrets
import uuid
from urllib.parse import quote, urlsplit
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from rest_framework import status
from rest_framework.authentication import BaseAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import *
from .ad_providers import AdProviderUnavailable, get_ad_provider
from .serializers import LoginSerializer, RegistrationSerializer


User = get_user_model()

logger = logging.getLogger(__name__)


DEFAULT_ECONOMY = {
    'levelCompletionCoins': 25,
    'doubleCoinsMultiplier': 2,
    'doubleScoreMultiplier': 2,
    'extraMoves': 5,
    'maxRewardedAdsPerDay': 10,
    'maxRevivesPerLevel': 1,
    'maxDoubleScorePerLevel': 1,
    'maxDoubleCoinsPerLevel': 1,
    'adCooldownSeconds': 30,
    'hintEnabled': True,
    'boosterEnabled': True,
    'levelCompletionScore': 100,
}


# Only these reward records represent rewarded-ad claims.
# Deterministic game rewards (for example level completion coins)
# are also stored in RewardTransaction, but must never consume
# rewarded-ad cooldowns or daily ad quotas.
REWARDED_AD_PLACEMENTS = {
    "REVIVE",
    "HINT",
    "DOUBLE_SCORE",
    "DOUBLE_COINS",
    "EXTRA_MOVES",
    "BOOSTER",
    "DAILY_REWARD",
}


# ============================================================
# ECONOMY
# ============================================================

def economy():
    stored = (
        EconomyConfig.objects
        .filter(key='default')
        .values_list('config', flat=True)
        .first()
        or {}
    )

    return {
        **DEFAULT_ECONOMY,
        **stored,
    }


# ============================================================
# USER PAYLOAD
# ============================================================

def payload(user):
    profile, _ = PlayerProfile.objects.get_or_create(
        user=user
    )

    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'coins': profile.coins,
        'total_score': profile.total_score,
        'email_verified': bool(user.is_active),
    }


# ============================================================
# AUTHENTICATION
# ============================================================

class ApiKeyOrTokenAuthentication(BaseAuthentication):
    """
    Authenticate with X-API-Key or the normal DRF token.

    Invalid/revoked API keys intentionally raise AuthenticationFailed.
    """

    def authenticate(self, request):
        raw_api_key = (
            request.headers.get("X-API-Key")
            or request.META.get("HTTP_X_API_KEY")
            or ""
        ).strip()

        if raw_api_key:
            api_key = (
                ApiKey.objects
                .select_related("user")
                .filter(
                    key_hash=digest(raw_api_key),
                    revoked_at__isnull=True,
                    user__is_active=True,
                )
                .first()
            )

            if api_key is None:
                raise AuthenticationFailed(
                    "Invalid or revoked API key."
                )

            api_key.last_used_at = timezone.now()

            api_key.save(
                update_fields=[
                    "last_used_at"
                ]
            )

            return api_key.user, api_key

        return TokenAuthentication().authenticate(request)

    def authenticate_header(self, request):
        return "Api-Key"


def auth_required(fn):
    return authentication_classes(
        [ApiKeyOrTokenAuthentication]
    )(
        permission_classes(
            [IsAuthenticated]
        )(fn)
    )


def digest(value):
    return hashlib.sha256(
        str(value).encode("utf-8")
    ).hexdigest()


# ============================================================
# EMAIL HELPERS
# ============================================================

def _frontend_base_url():
    return (
        getattr(
            settings,
            "FRONTEND_BASE_URL",
            "http://localhost:5174",
        )
        .strip()
        .rstrip("/")
    )


def _frontend_url(path, token):
    return (
        f"{_frontend_base_url()}/"
        f"{path.lstrip('/')}?"
        f"token={quote(str(token), safe='')}"
    )


def _send_verification_email(
    user,
    raw_token,
):
    verification_url = _frontend_url(
        "/verify-email/",
        raw_token,
    )

    send_mail(
        subject=(
            f"Verify your "
            f"{settings.GAME_NAME} account"
        ),
        message=(
            f"Hello {user.username},\n\n"
            f"Thank you for registering for "
            f"{settings.GAME_NAME}.\n\n"
            f"Please verify your email address "
            f"by opening this link:\n\n"
            f"{verification_url}\n\n"
            f"This verification link expires "
            f"in 24 hours.\n\n"
            f"If you did not create this account, "
            f"you can safely ignore this email.\n\n"
            f"Thank you,\n"
            f"{settings.GAME_NAME} Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _send_password_reset_email(
    user,
    raw_token,
):
    reset_url = _frontend_url(
        "/reset-password/",
        raw_token,
    )

    send_mail(
        subject=(
            f"Reset your "
            f"{settings.GAME_NAME} password"
        ),
        message=(
            f"Hello {user.username},\n\n"
            f"We received a request to reset "
            f"your {settings.GAME_NAME} password.\n\n"
            f"Open the following link to choose "
            f"a new password:\n\n"
            f"{reset_url}\n\n"
            f"This reset link expires in 1 hour "
            f"and can only be used once.\n\n"
            f"If you did not request a password "
            f"reset, you can safely ignore this email.\n\n"
            f"Thank you,\n"
            f"{settings.GAME_NAME} Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# ============================================================
# PROGRESS
# ============================================================

def seed_progress(user):
    levels = (
        Level.objects
        .filter(is_active=True)
        .order_by("number")
    )

    for level in levels:
        PlayerProgress.objects.get_or_create(
            user=user,
            level=level,
            defaults={
                "unlocked": level.number == 1
            },
        )


def unlock_next(user, number):
    next_level = (
        Level.objects
        .filter(
            number=number + 1,
            is_active=True,
        )
        .first()
    )

    if next_level:
        PlayerProgress.objects.filter(
            user=user,
            level=next_level,
        ).update(
            unlocked=True
        )


# ============================================================
# WALLET
# ============================================================

def grant_coins(
    user,
    amount,
    reason,
    reference=None,
    reward_ledger=None,
):
    amount = int(amount)
    reference = reference or f"{reason}:{uuid.uuid4()}"

    with transaction.atomic():
        profile = (
            PlayerProfile.objects
            .select_for_update()
            .get(user=user)
        )

        # A wallet reference can be credited only once.
        existing_wallet = WalletTransaction.objects.filter(
            reference=reference
        ).first()

        if existing_wallet:
            if existing_wallet.user_id != user.id:
                raise ValueError("Wallet reference belongs to another user.")

            if reward_ledger:
                existing_reward = RewardTransaction.objects.filter(
                    event_id=reward_ledger["event_id"]
                ).first()

                if (
                    not existing_reward
                    or existing_reward.user_id != user.id
                ):
                    raise ValueError(
                        "Wallet and reward ledgers are inconsistent."
                    )

            return profile.coins

        # A reward event can also be granted only once.
        if reward_ledger:
            existing_reward = RewardTransaction.objects.filter(
                event_id=reward_ledger["event_id"]
            ).first()

            if existing_reward:
                if existing_reward.user_id != user.id:
                    raise ValueError(
                        "Reward event belongs to another user."
                    )

                # Do not silently repair a partial ledger by crediting again.
                raise ValueError(
                    "Reward event exists without its wallet transaction."
                )

        profile.coins = max(0, profile.coins + amount)
        profile.save(update_fields=["coins", "updated_at"])

        WalletTransaction.objects.create(
            user=user,
            amount=amount,
            balance_after=profile.coins,
            kind="CREDIT" if amount >= 0 else "DEBIT",
            reason=reason,
            reference=reference,
        )

        if reward_ledger:
            RewardTransaction.objects.create(
                user=user,
                placement=reward_ledger["placement"],
                reward_type=reward_ledger["reward_type"],
                amount=amount,
                event_id=reward_ledger["event_id"],
                status="GRANTED",
                metadata=reward_ledger.get("metadata", {}),
            )

        return profile.coins


# ============================================================
# REFRESH TOKENS
# ============================================================

def issue_refresh(user):
    raw = secrets.token_urlsafe(48)

    RefreshSession.objects.create(
        user=user,
        token_hash=digest(raw),
        expires_at=(
            timezone.now()
            + timedelta(days=30)
        ),
    )

    return raw


# ============================================================
# HEALTH
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({
        "status": "ok",
        "service": "veloop-backend",
        "game_name": settings.GAME_NAME,
        "version": "1.0.0",
    })



# ============================================================
# REGISTER
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    stage = "registration initialization"

    try:
        with transaction.atomic():
            stage = "user and profile creation"
            user = serializer.save()

            stage = "authentication token creation"
            token, _ = Token.objects.get_or_create(user=user)

            stage = "initial game progress creation"
            seed_progress(user)

            stage = "verification token generation"
            verification_token = secrets.token_urlsafe(32)

            stage = "email verification record creation"
            EmailVerification.objects.update_or_create(
                user=user,
                defaults={
                    "token_hash": digest(verification_token),
                    "expires_at": timezone.now() + timedelta(hours=24),
                    "verified_at": None,
                },
            )

            if not settings.EMAIL_VERIFICATION_REQUIRED:
                stage = "account activation"
                user.is_active = True
                user.save(update_fields=["is_active"])

                EmailVerification.objects.filter(
                    user=user
                ).update(verified_at=timezone.now())

        email_sent = False

        if settings.EMAIL_VERIFICATION_REQUIRED:
            stage = "verification email sending"

            try:
                _send_verification_email(user, verification_token)
                email_sent = True
            except Exception:
                logger.exception(
                    "AWA verification email failure for user id=%s",
                    user.id,
                )
                return Response(
                    {
                        "detail": (
                            "Account created, but the verification "
                            "email could not be sent."
                        ),
                        "email_sent": False,
                        "verification_required": True,
                    },
                    status=503,
                )

        stage = "refresh session creation"
        refresh_token = issue_refresh(user)

        stage = "user response generation"

        return Response(
            {
                "token": token.key,
                "refresh_token": refresh_token,
                "verification_token": (
                    verification_token
                    if settings.DEBUG and settings.EMAIL_VERIFICATION_REQUIRED
                    else None
                ),
                "user": payload(user),
                "verification_required": settings.EMAIL_VERIFICATION_REQUIRED,
                "email_sent": email_sent,
            },
            status=201,
        )

        except Exception as exc:
        logger.exception(
            "AWA REGISTRATION FAILURE at stage: %s | Error: %s",
            stage,
            str(exc),
        )
        traceback.print_exc()
        raise


    # --------------------------------------------------------
    # SEND EMAIL AFTER DATABASE TRANSACTION
    # --------------------------------------------------------

    email_sent = False

    if settings.EMAIL_VERIFICATION_REQUIRED:
        try:
            _send_verification_email(
                user,
                verification_token,
            )

            email_sent = True

        except Exception:
            logger.exception(
                "Failed to send verification email "
                "to user id=%s",
                user.id,
            )

            return Response(
                {
                    "detail": (
                        "Account created, but the "
                        "verification email could not "
                        "be sent. Please check the "
                        "email configuration and retry "
                        "verification."
                    ),
                    "email_sent": False,
                    "verification_required": True,
                },
                status=503,
            )

    refresh_token = issue_refresh(
        user
    )

    return Response(
        {
            "token": token.key,
            "refresh_token": refresh_token,

            # Never expose this in production.
            "verification_token": (
                verification_token
                if (
                    settings.DEBUG
                    and settings.EMAIL_VERIFICATION_REQUIRED
                )
                else None
            ),

            "user": payload(user),

            "verification_required": (
                settings.EMAIL_VERIFICATION_REQUIRED
            ),

            "email_sent": email_sent,
        },
        status=201,
    )


# ============================================================
# RESEND VERIFICATION EMAIL
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def resend_verification(request):
    """
    Safely resend a verification email.

    The endpoint intentionally returns the same generic
    response whether the account exists or not, preventing
    email-account enumeration.
    """

    email = str(
        request.data.get(
            "email",
            "",
        )
    ).strip()

    generic_response = {
        "accepted": True,
        "detail": (
            "If an unverified account exists for "
            "this email address, a verification "
            "email has been sent."
        ),
    }

    if not email:
        return Response(
            generic_response
        )

    user = (
        User.objects
        .filter(
            email__iexact=email
        )
        .first()
    )

    if not user:
        return Response(
            generic_response
        )

    if user.is_active:
        return Response(
            generic_response
        )

    raw_token = secrets.token_urlsafe(
        32
    )

    EmailVerification.objects.update_or_create(
        user=user,
        defaults={
            "token_hash": digest(
                raw_token
            ),
            "expires_at": (
                timezone.now()
                + timedelta(hours=24)
            ),
            "verified_at": None,
        },
    )

    try:
        _send_verification_email(
            user,
            raw_token,
        )

    except Exception:
        logger.exception(
            "Failed to resend verification email "
            "to user id=%s",
            user.id,
        )

    return Response(
        generic_response
    )


# ============================================================
# VERIFY EMAIL
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    raw = str(
        request.data.get(
            "token",
            "",
        )
    ).strip()

    if not raw:
        return Response(
            {
                "detail": (
                    "Verification token is required."
                )
            },
            status=400,
        )

    token_hash = digest(raw)

    with transaction.atomic():
        obj = (
            EmailVerification.objects
            .select_for_update()
            .select_related("user")
            .filter(
                token_hash=token_hash
            )
            .first()
        )

        if not obj:
            return Response(
                {
                    "detail": (
                        "Verification token "
                        "is invalid."
                    )
                },
                status=400,
            )

        # ----------------------------------------------------
        # IDEMPOTENT VERIFICATION
        # ----------------------------------------------------

        if obj.verified_at:
            if not obj.user.is_active:
                obj.user.is_active = True

                obj.user.save(
                    update_fields=[
                        "is_active"
                    ]
                )

            return Response({
                "verified": True,
                "already_verified": True,
                "detail": (
                    "Email is already verified."
                ),
            })

        # ----------------------------------------------------
        # EXPIRATION
        # ----------------------------------------------------

        if obj.expires_at <= timezone.now():
            return Response(
                {
                    "detail": (
                        "Verification token "
                        "has expired."
                    )
                },
                status=400,
            )

        obj.verified_at = timezone.now()

        obj.save(
            update_fields=[
                "verified_at"
            ]
        )

        obj.user.is_active = True

        obj.user.save(
            update_fields=[
                "is_active"
            ]
        )

    return Response({
        "verified": True,
        "already_verified": False,
        "detail": (
            "Email verified successfully."
        ),
    })


# ============================================================
# LOGIN
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(
        data=request.data
    )

    serializer.is_valid(
        raise_exception=True
    )

    username = (
        serializer.validated_data[
            "username"
        ]
        .strip()
    )

    password = serializer.validated_data[
        "password"
    ]

    # --------------------------------------------------------
    # DEVELOPMENT MODE
    # --------------------------------------------------------

    user = (
        User.objects
        .filter(
            username__iexact=username
        )
        .first()
    )

    if (
        user
        and not user.is_active
        and not settings.EMAIL_VERIFICATION_REQUIRED
        and user.check_password(password)
    ):
        user.is_active = True

        user.save(
            update_fields=[
                "is_active"
            ]
        )

    # --------------------------------------------------------
    # AUTHENTICATE
    # --------------------------------------------------------

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if not user:
        inactive = (
            User.objects
            .filter(
                username__iexact=username,
                is_active=False,
            )
            .first()
        )

        if (
            inactive
            and inactive.check_password(password)
        ):
            return Response(
                {
                    "detail": (
                        "Please verify your "
                        "email before logging in."
                    )
                },
                status=403,
            )

        return Response(
            {
                "detail": (
                    "Username or password "
                    "is incorrect."
                )
            },
            status=400,
        )

    token, _ = Token.objects.get_or_create(
        user=user
    )

    seed_progress(user)

    return Response({
        "token": token.key,
        "refresh_token": issue_refresh(user),
        "user": payload(user),
    })


# ============================================================
# REFRESH
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request):
    raw = str(
        request.data.get(
            "refresh_token",
            "",
        )
    ).strip()

    if not raw:
        return Response(
            {
                "detail": (
                    "Refresh token is required."
                )
            },
            status=400,
        )

    obj = (
        RefreshSession.objects
        .select_related("user")
        .filter(
            token_hash=digest(raw),
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            user__is_active=True,
        )
        .first()
    )

    if not obj:
        return Response(
            {
                "detail": (
                    "Refresh token invalid "
                    "or expired."
                )
            },
            status=401,
        )

    token, _ = Token.objects.get_or_create(
        user=obj.user
    )

    return Response({
        "token": token.key,
        "refresh_token": raw,
    })


# ============================================================
# LOGOUT
# ============================================================

@api_view(["POST"])
@auth_required
def logout(request):
    if isinstance(
        request.auth,
        Token,
    ):
        request.auth.delete()

    # Per-device logout: when the client identifies its own refresh
    # session, revoke only that one so logging out here does not
    # permanently end the user's other live sessions (they re-obtain
    # the shared access token via /auth/refresh/). Without a matching
    # refresh token the original behaviour is kept: revoke all.
    own_refresh = str(
        request.data.get(
            "refresh_token",
            "",
        )
        if hasattr(request.data, "get")
        else ""
    ).strip()

    active = RefreshSession.objects.filter(
        user=request.user,
        revoked_at__isnull=True,
    )

    if own_refresh:
        own = active.filter(
            token_hash=digest(own_refresh)
        )

        if own.exists():
            active = own

    active.update(
        revoked_at=timezone.now()
    )

    return Response({
        "detail": (
            "Logged out successfully."
        )
    })


# ============================================================
# CURRENT USER
# ============================================================

@api_view(["GET"])
@auth_required
def me(request):
    return Response({
        "user": payload(
            request.user
        )
    })


# ============================================================
# PASSWORD RESET REQUEST
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = str(
        request.data.get(
            "email",
            "",
        )
    ).strip()

    generic_response = {
        "accepted": True,
        "detail": (
            "If an account exists for this "
            "email address, a password reset "
            "email has been sent."
        ),
    }

    if not email:
        return Response(
            generic_response
        )

    user = (
        User.objects
        .filter(
            email__iexact=email
        )
        .first()
    )

    if not user:
        return Response(
            generic_response
        )

    # --------------------------------------------------------
    # INVALIDATE ALL PREVIOUS RESET TOKENS
    # --------------------------------------------------------

    PasswordResetToken.objects.filter(
        user=user,
        used_at__isnull=True,
    ).update(
        used_at=timezone.now()
    )

    raw = secrets.token_urlsafe(
        32
    )

    PasswordResetToken.objects.create(
        user=user,
        token_hash=digest(raw),
        expires_at=(
            timezone.now()
            + timedelta(hours=1)
        ),
    )

    try:
        _send_password_reset_email(
            user,
            raw,
        )

    except Exception:
        logger.exception(
            "Failed to send password reset email "
            "to user id=%s",
            user.id,
        )

    # Development-only convenience.
    if settings.DEBUG:
        generic_response[
            "reset_token"
        ] = raw

    return Response(
        generic_response
    )


# ============================================================
# PASSWORD RESET CONFIRM
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    raw = str(
        request.data.get(
            "token",
            "",
        )
    ).strip()

    if not raw:
        return Response(
            {
                "detail": (
                    "Reset token is required."
                )
            },
            status=400,
        )

    with transaction.atomic():
        obj = (
            PasswordResetToken.objects
            .select_for_update()
            .select_related("user")
            .filter(
                token_hash=digest(raw),
                used_at__isnull=True,
            )
            .first()
        )

        if not obj:
            return Response(
                {
                    "detail": (
                        "Reset token is invalid "
                        "or has already been used."
                    )
                },
                status=400,
            )

        if obj.expires_at <= timezone.now():
            return Response(
                {
                    "detail": (
                        "Reset token has expired."
                    )
                },
                status=400,
            )

        password = str(
            request.data.get(
                "password",
                "",
            )
        )

        if len(password) < 8:
            return Response(
                {
                    "detail": (
                        "Password must be at least "
                        "8 characters."
                    )
                },
                status=400,
            )

        try:
            validate_password(
                password,
                user=obj.user,
            )

        except ValidationError as exc:
            return Response(
                {
                    "detail": list(
                        exc.messages
                    )
                },
                status=400,
            )

        obj.user.set_password(
            password
        )

        obj.user.save(
            update_fields=[
                "password"
            ]
        )

        obj.used_at = timezone.now()

        obj.save(
            update_fields=[
                "used_at"
            ]
        )

        # Invalidate every other reset token.
        PasswordResetToken.objects.filter(
            user=obj.user,
            used_at__isnull=True,
        ).exclude(
            id=obj.id
        ).update(
            used_at=timezone.now()
        )

        # Invalidate existing login credentials.
        Token.objects.filter(
            user=obj.user
        ).delete()

        RefreshSession.objects.filter(
            user=obj.user,
            revoked_at__isnull=True,
        ).update(
            revoked_at=timezone.now()
        )

    return Response({
        "reset": True,
        "detail": (
            "Password reset successfully."
        ),
    })


# ============================================================
# LEVELS
# ============================================================

@api_view(["GET"])
@auth_required
def levels(request):
    seed_progress(
        request.user
    )

    progress = (
        PlayerProgress.objects
        .filter(
            user=request.user
        )
        .select_related("level")
        .order_by("level__number")
    )

    return Response({
        "levels": [
            {
                "number": p.level.number,
                "unlocked": p.unlocked,
                "completed": p.completed,
                "stars": p.stars,
                "best_score": p.best_score,
                "best_moves": p.best_moves,
                "objectives": level_static_config(
                    p.level.number
                )["objectives"],
            }
            for p in progress
        ],
        "count": progress.count(),
    })


# ============================================================
# DETERMINISTIC LEVEL CONFIG
# ============================================================

def level_objectives(number, size=None, apple_count=None):
    """Return deterministic, server-authoritative objectives for a level.

    Every level has at least two required objectives: collect every apple
    and reach the portal. Higher difficulty tiers add distinct objectives
    so the game has a real, data-driven multi-objective progression.
    """
    if size is None:
        size = 7 + min(3, number // 12)
    if apple_count is None:
        apple_count = min(5, 2 + (number - 1) // 12)

    difficulty = min(10, 1 + (number - 1) // 6)
    max_moves = max(
        40,
        (size * size) + (apple_count * 12) + (difficulty * 4),
    )

    objectives = [
        {
            "id": "collect_apples",
            "type": "collect_apples",
            "title": "Collect all apples",
            "required": True,
            "target": apple_count,
        },
        {
            "id": "reach_portal",
            "type": "reach_portal",
            "title": "Reach the portal",
            "required": True,
        },
    ]

    if difficulty >= 4:
        objectives.append(
            {
                "id": "move_limit",
                "type": "move_limit",
                "title": "Finish within the move limit",
                "required": True,
                "target": max_moves,
            }
        )

    if difficulty >= 7:
        objectives.append(
            {
                "id": "no_revive",
                "type": "no_revive",
                "title": "Finish without using a revive",
                "required": True,
                "target": 0,
            }
        )

    return objectives


def level_static_config(number):
    size = (
        7
        + min(
            3,
            number // 12,
        )
    )

    route = [
        {
            "r": 1,
            "c": c,
        }
        for c in range(
            1,
            size - 1,
        )
    ]

    route.extend(
        {
            "r": r,
            "c": size - 2,
        }
        for r in range(
            2,
            size - 1,
        )
    )

    used = {
        f"{p['r']}:{p['c']}"
        for p in route
    }

    count = min(
        5,
        2 + (number - 1) // 12,
    )

    apples = []

    for i in range(
        1,
        count + 1,
    ):
        idx = (
            int(
                (
                    (len(route) - 2)
                    * i
                )
                / (count + 1)
            )
            + 1
        )

        apples.append(
            dict(route[idx])
        )

    def js_hash(n):
        return (
            (
                n * 9301
                + 49297
            )
            % 233280
        ) / 233280

    target = min(
        18,
        4 + number // 3,
    )

    obstacles = []

    for i in range(
        target * 5
    ):
        if len(obstacles) >= target:
            break

        r = (
            2
            + int(
                js_hash(
                    number * 71 + i
                )
                * max(
                    1,
                    size - 3,
                )
            )
        )

        c = (
            2
            + int(
                js_hash(
                    number * 97 + i
                )
                * max(
                    1,
                    size - 3,
                )
            )
        )

        key_value = (
            f"{r}:{c}"
        )

        if (
            key_value not in used
            and not any(
                x["r"] == r
                and x["c"] == c
                for x in obstacles
            )
        ):
            obstacles.append({
                "r": r,
                "c": c,
            })

    return {
        "size": size,
        "portal": {
            "r": size - 2,
            "c": size - 2,
        },
        "apples": apples,
        "obstacles": obstacles,
        "objectives": level_objectives(
            number,
            size=size,
            apple_count=len(apples),
        ),
    }


def calculate_stars(state):
    """Calculate completion stars from authoritative server state.

    Star awards are intentionally server-authoritative. The client may display
    a predicted star count, but it can never choose the awarded value.

    3 stars: no revive and 10 moves or fewer.
    2 stars: no revive, but more than 10 moves.
    1 star: at least one revive was used.
    """
    moves = int(state.get("moves", 0))
    revives = int(state.get("revives", 0))
    star_threshold = 10

    if revives == 0 and moves <= star_threshold:
        return 3
    if revives == 0:
        return 2
    return 1


def level_revive_limit(level_number):
    """Return the authoritative revive limit for a level.

    Levels with the required ``no_revive`` objective are explicitly
    non-revivable. Other levels inherit the global economy limit unless
    their data-driven level config supplies a non-negative integer override.
    """
    cfg = level_static_config(level_number)
    objectives = cfg.get("objectives") or []

    if any(
        objective.get("type") == "no_revive"
        and objective.get("required", True)
        for objective in objectives
    ):
        return 0

    level = (
        Level.objects
        .filter(
            number=level_number,
            is_active=True,
        )
        .first()
    )

    level_config = (level.config or {}) if level else {}
    override = level_config.get("maxRevivesPerLevel")

    if isinstance(override, int) and override >= 0:
        return override

    return int(economy()["maxRevivesPerLevel"])


def evaluate_objectives(state, level_number):
    """Evaluate every required objective from authoritative game state."""
    cfg = level_static_config(level_number)
    apples = state.get("apples") or []
    worm = state.get("worm") or []
    portal = state.get("portal") or {}
    moves = int(state.get("moves", 0))
    revives = int(state.get("revives", 0))
    extra_moves = int(state.get("extraMoves", 0))

    results = []
    for objective in cfg["objectives"]:
        objective_type = objective["type"]

        if objective_type == "collect_apples":
            progress = objective["target"] - len(apples)
            completed = len(apples) == 0
            progress = max(0, min(objective["target"], progress))
        elif objective_type == "reach_portal":
            completed = bool(worm) and same_position(
                worm[0],
                portal,
            )
            progress = 1 if completed else 0
        elif objective_type == "move_limit":
            allowed_moves = objective["target"] + extra_moves
            completed = moves <= allowed_moves
            progress = min(moves, allowed_moves)
        elif objective_type == "no_revive":
            completed = revives == 0
            progress = 0 if revives else 1
        else:
            completed = False
            progress = 0

        results.append(
            {
                **objective,
                "completed": completed,
                "progress": progress,
            }
        )

    return {
        "objectives": results,
        "all_completed": all(
            item["completed"]
            for item in results
            if item.get("required", True)
        ),
    }



# ============================================================
# INITIAL STATE VALIDATION
# ============================================================

def validate_initial_state(
    data,
    level_number,
):
    ok, checked = validate_state_shape(
        data,
        level_number,
    )

    if not ok:
        return False, checked

    cfg = level_static_config(
        level_number
    )

    expected_worm = [
        {
            "r": 1,
            "c": 1,
        }
    ]

    if checked["worm"] != expected_worm:
        return (
            False,
            "Invalid initial worm position.",
        )

    if checked["apples"] != cfg["apples"]:
        return (
            False,
            "Invalid initial apple layout.",
        )

    if checked["obstacles"] != cfg["obstacles"]:
        return (
            False,
            "Invalid initial obstacle layout.",
        )

    if checked["portal"] != cfg["portal"]:
        return (
            False,
            "Invalid initial portal.",
        )

    for key in (
        "moves",
        "score",
        "revives",
        "hints",
        "boosters",
        "extraMoves",
    ):
        try:
            value = int(
                checked.get(
                    key,
                    0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            return (
                False,
                "Invalid initial game counters.",
            )

        if value != 0:
            return (
                False,
                "Invalid initial game counters.",
            )

    if (
        checked.get("failed")
        or checked.get("completed")
    ):
        return (
            False,
            "Invalid initial game status.",
        )

    return True, checked


# ============================================================
# STATE SHAPE VALIDATION
# ============================================================

def validate_state_shape(
    data,
    level_number,
):
    try:
        state = (
            data
            if isinstance(
                data,
                dict,
            )
            else {}
        )

        worm = (
            state.get("worm")
            or []
        )

        apples = (
            state.get("apples")
            or []
        )

        obstacles = (
            state.get("obstacles")
            or []
        )

        portal = (
            state.get("portal")
            or {}
        )

        if (
            not isinstance(
                worm,
                list,
            )
            or not worm
        ):
            return (
                False,
                "Invalid worm state.",
            )

        if (
            not isinstance(
                apples,
                list,
            )
            or not isinstance(
                obstacles,
                list,
            )
            or not isinstance(
                portal,
                dict,
            )
        ):
            return (
                False,
                "Malformed game state.",
            )

        cfg = level_static_config(
            level_number
        )

        size = cfg["size"]

        expected_obstacles = {
            f"{p['r']}:{p['c']}"
            for p in cfg["obstacles"]
        }

        expected_apples = {
            f"{p['r']}:{p['c']}"
            for p in cfg["apples"]
        }

        actual_obstacles = {
            f"{int(p.get('r'))}:"
            f"{int(p.get('c'))}"
            for p in obstacles
            if isinstance(
                p,
                dict,
            )
        }

        actual_apples = {
            f"{int(p.get('r'))}:"
            f"{int(p.get('c'))}"
            for p in apples
            if isinstance(
                p,
                dict,
            )
        }

        if (
            actual_obstacles
            != expected_obstacles
        ):
            return (
                False,
                "Invalid level state: Level obstacles were modified.",
            )

        if not actual_apples.issubset(
            expected_apples
        ):
            return (
                False,
                "Invalid apple state.",
            )

        if len(
            actual_apples
        ) != len(apples):
            return (
                False,
                "Invalid apple state.",
            )

        portal_key = (
            f"{int(portal.get('r'))}:"
            f"{int(portal.get('c'))}"
        )

        expected_portal = (
            f"{cfg['portal']['r']}:"
            f"{cfg['portal']['c']}"
        )

        if (
            portal_key
            != expected_portal
        ):
            return (
                False,
                "Invalid portal state.",
            )

        worm_keys = []

        for part in worm:
            if (
                not isinstance(
                    part,
                    dict,
                )
                or not isinstance(
                    part.get("r"),
                    int,
                )
                or not isinstance(
                    part.get("c"),
                    int,
                )
            ):
                return (
                    False,
                    "Invalid worm segment.",
                )

            r = part["r"]
            c = part["c"]

            if (
                r <= 0
                or c <= 0
                or r >= size - 1
                or c >= size - 1
            ):
                return (
                    False,
                    "Worm is outside the playable board.",
                )

            worm_keys.append(
                f"{r}:{c}"
            )

        if len(
            set(worm_keys)
        ) != len(worm_keys):
            return (
                False,
                "Worm contains duplicate segments.",
            )

        if any(
            k in expected_obstacles
            for k in worm_keys
        ):
            return (
                False,
                "Worm overlaps an obstacle.",
            )

        for a, b in zip(
            worm,
            worm[1:],
        ):
            if (
                abs(
                    a["r"] - b["r"]
                )
                + abs(
                    a["c"] - b["c"]
                )
                != 1
            ):
                return (
                    False,
                    "Worm segments are not contiguous.",
                )

        if any(
            k in worm_keys
            for k in actual_apples
        ):
            return (
                False,
                "Worm overlaps an apple.",
            )

        return True, state

    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        return (
            False,
            "Malformed game state.",
        )


# ============================================================
# ACHIEVEMENTS
# ============================================================

def unlock_achievement(
    user,
    code,
):
    achievement = (
        Achievement.objects
        .filter(code=code)
        .first()
    )

    if achievement:
        UserAchievement.objects.get_or_create(
            user=user,
            achievement=achievement,
        )


def update_achievements(
    user,
    level_number,
    stars,
    total_score,
):
    completed = (
        PlayerProgress.objects
        .filter(
            user=user,
            completed=True,
        )
        .count()
    )

    if level_number >= 1:
        unlock_achievement(
            user,
            "FIRST_APPLE",
        )

    if completed >= 10:
        unlock_achievement(
            user,
            "LEVEL_10",
        )

    if completed >= 25:
        unlock_achievement(
            user,
            "LEVEL_25",
        )

    if completed >= 50:
        unlock_achievement(
            user,
            "LEVEL_50",
        )

    if stars >= 3:
        unlock_achievement(
            user,
            "THREE_STARS",
        )

    if total_score >= 10000:
        unlock_achievement(
            user,
            "SCORE_10000",
        )


# ============================================================
# ACTIVE GAME
# ============================================================

@api_view(["GET"])
@auth_required
def active_game(request):
    session = (
        GameSession.objects
        .select_related("level")
        .filter(
            user=request.user,
            status="ACTIVE",
        )
        .order_by(
            "-updated_at",
            "-started_at",
        )
        .first()
    )

    if not session:
        return Response({
            "active": False,
            "session": None,
        })

    # Repair legacy sessions that persisted a failed No-Revive state
    # while their database status was still ACTIVE.
    if (
        isinstance(session.checkpoint_state, dict)
        and session.checkpoint_state.get("failed")
        and level_revive_limit(session.level.number) <= 0
    ):
        session.status = "FAILED"
        session.save(update_fields=["status", "updated_at"])
        return Response({
            "active": False,
            "session": None,
        })

    return Response({
        "active": True,
        "session": {
            "sessionId": str(
                session.id
            ),
            "level": session.level.number,
            "moves": session.moves,
            "score": session.score,
            "revives_used": (
                session.revives_used
            ),
            "state": (
                session.checkpoint_state
            ),
            "started_at": (
                session.started_at
            ),
            "updated_at": (
                session.updated_at
            ),
            "objectives": level_static_config(
                session.level.number
            )["objectives"],
        },
    })


# ============================================================
# SERVER-AUTHORITATIVE INITIAL GAME STATE
# ============================================================

def build_initial_state(level_number):
    """Build the canonical starting state on the server.

    The browser may request a level, but it is never trusted to define
    the initial board, worm, counters, or timestamps.  This keeps game
    sessions deterministic and makes POST /games/start/ safe to call with
    only a level number.
    """
    cfg = level_static_config(level_number)
    now_ms = int(timezone.now().timestamp() * 1000)
    return {
        "worm": [{"r": 1, "c": 1}],
        "apples": [dict(p) for p in cfg["apples"]],
        "obstacles": [dict(p) for p in cfg["obstacles"]],
        "portal": dict(cfg["portal"]),
        "moves": 0,
        "score": 0,
        "failed": False,
        "failedMove": None,
        "completed": False,
        "started": now_ms,
        "revives": 0,
        "hints": 0,
        "boosters": 0,
        "extraMoves": 0,
    }


# ============================================================
# START GAME
# ============================================================

@api_view(["POST"])
@auth_required
def start_game(request):
    try:
        # Accept the documented `level` field and the legacy/manual
        # `level_id` spelling so clients cannot accidentally create an
        # invalid empty state just because they used the alternate name.
        raw_level = request.data.get("level")
        if raw_level is None:
            raw_level = request.data.get("level_id", 1)
        number = int(raw_level)

    except (
        TypeError,
        ValueError,
    ):
        return Response(
            {
                "detail": (
                    "Invalid level."
                )
            },
            status=400,
        )

    level = (
        Level.objects
        .filter(
            number=number,
            is_active=True,
        )
        .first()
    )

    # Bootstrap missing player progress safely.
    # Level 1 is the only level that may be auto-unlocked here.
    # Higher levels remain locked until normal server-side progression
    # unlocks them.
    progress = None

    if level:
        progress, _ = PlayerProgress.objects.get_or_create(
            user=request.user,
            level=level,
            defaults={
                "unlocked": number == 1,
            },
        )

        # Repair an inconsistent Level 1 record without unlocking
        # any later level.
        if number == 1 and not progress.unlocked:
            progress.unlocked = True
            progress.save(
                update_fields=[
                    "unlocked",
                ]
            )

    if (
        not level
        or not progress
        or not progress.unlocked
    ):
        return Response(
            {
                "detail": (
                    "Level is locked or invalid."
                )
            },
            status=400,
        )

    # The state is server-authoritative.  If a client omits it (the normal
    # production path), generate it from the immutable level configuration.
    # If a legacy client supplies a state, validate it strictly rather than
    # trusting it.  This preserves compatibility without weakening anti-cheat.
    supplied_state = request.data.get("state")
    if supplied_state is None:
        state = build_initial_state(number)
    else:
        state = supplied_state

    valid, checked = validate_initial_state(
        state,
        number,
    )

    if not valid:
        return Response(
            {
                "detail": checked
            },
            status=400,
        )

    GameSession.objects.filter(
        user=request.user,
        level=level,
        status="ACTIVE",
    ).update(
        status="ABANDONED",
        updated_at=timezone.now(),
    )

    session = GameSession.objects.create(
        id=uuid.uuid4(),
        user=request.user,
        level=level,
        initial_state=checked,
        checkpoint_state=checked,
    )

    progress.attempts += 1

    progress.save(
        update_fields=[
            "attempts",
            "updated_at",
        ]
    )

    return Response({
        "sessionId": str(session.id),
        "level": number,
        "config": {
            **level.config,
            "objectives": level_static_config(
                number
            )["objectives"],
        },
        "objectives": level_static_config(
            number
        )["objectives"],
        # Return the exact state stored by the server.  The frontend must
        # render this state instead of reconstructing it independently.
        "state": checked,
    })


# ============================================================
# GENERIC STATE VALIDATION
# ============================================================

def validate_state(
    data,
    level_number=None,
    require_portal=False,
):
    try:
        moves = int(
            data.get(
                "moves",
                0,
            )
        )

        score = int(
            data.get(
                "score",
                0,
            )
        )

        state = (
            data.get("state")
            or {}
        )

        worm = (
            state.get("worm")
            or []
        )

        apples = (
            state.get("apples")
            or []
        )

        portal = (
            state.get("portal")
            or {}
        )

    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        return (
            False,
            "Malformed state.",
        )

    if not (
        0 <= moves <= 5000
        and 0 <= score <= 1000000
        and worm
        and isinstance(
            portal,
            dict,
        )
    ):
        return (
            False,
            "Invalid game state.",
        )

    if level_number is not None:
        ok, checked = (
            validate_state_shape(
                state,
                level_number,
            )
        )

        if not ok:
            return (
                False,
                checked,
            )

        state = checked
        apples = (
            state.get("apples")
            or []
        )

    if require_portal:
        if apples:
            return (
                False,
                (
                    "All apples must be "
                    "collected before completion."
                ),
            )

        if (
            worm[0].get("r")
            != portal.get("r")
            or worm[0].get("c")
            != portal.get("c")
        ):
            return (
                False,
                "Worm is not at the portal.",
            )

    return True, (
        moves,
        score,
        state,
    )


# ============================================================
# NORMALISE STATE
# ============================================================

def _normalise_state(state):
    state = (
        state
        if isinstance(
            state,
            dict,
        )
        else {}
    )

    return {
        "worm": [
            dict(p)
            for p in (
                state.get(
                    "worm",
                    [],
                )
                or []
            )
        ],

        "apples": [
            dict(p)
            for p in (
                state.get(
                    "apples",
                    [],
                )
                or []
            )
        ],

        "obstacles": [
            dict(p)
            for p in (
                state.get(
                    "obstacles",
                    [],
                )
                or []
            )
        ],

        "portal": dict(
            state.get(
                "portal",
                {},
            )
            or {}
        ),

        "moves": int(
            state.get(
                "moves",
                0,
            )
        ),

        "score": int(
            state.get(
                "score",
                0,
            )
        ),

        "failed": bool(
            state.get(
                "failed",
                False,
            )
        ),

        "failedMove": (
            dict(state.get("failedMove"))
            if isinstance(
                state.get("failedMove"),
                dict,
            )
            else None
        ),

        "completed": bool(
            state.get(
                "completed",
                False,
            )
        ),

        "started": int(
            state.get(
                "started",
                0,
            )
        ),

        "revives": int(
            state.get(
                "revives",
                0,
            )
        ),

        "hints": int(
            state.get(
                "hints",
                0,
            )
        ),

        "boosters": int(
            state.get(
                "boosters",
                0,
            )
        ),

        "extraMoves": int(
            state.get(
                "extraMoves",
                0,
            )
        ),
    }


# ============================================================
# MOVE VALIDATION
# ============================================================

def validate_next_move(
    previous,
    incoming,
    level_number,
    require_completion=False,
):
    ok, checked = (
        validate_state_shape(
            incoming,
            level_number,
        )
    )

    if not ok:
        return (
            False,
            checked,
        )

    prev_ok, previous_checked = (
        validate_state_shape(
            previous,
            level_number,
        )
    )

    if not prev_ok:
        return (
            False,
            "Stored checkpoint is invalid.",
        )

    prev = _normalise_state(
        previous_checked
    )

    # A failed checkpoint is terminal until a verified
    # server-side revive resets the failure state.
    if prev.get("failed"):
        return (
            False,
            "A failed game cannot accept further moves.",
        )

    cur = _normalise_state(
        checked
    )

    # --------------------------------------------------------
    # MOVE SEQUENCE
    # --------------------------------------------------------

    if (
        cur["moves"]
        != prev["moves"] + 1
    ):
        return (
            False,
            "Invalid move sequence.",
        )

    # --------------------------------------------------------
    # STATUS / SERVER-AUTHORITATIVE FAILURE
    # --------------------------------------------------------

    if cur["completed"] and not require_completion:
        return (
            False,
            "Invalid checkpoint state.",
        )

    if cur["failed"]:
        if cur["completed"]:
            return (
                False,
                "A failed game cannot be completed.",
            )

        failed_move = cur.get("failedMove")
        if not isinstance(failed_move, dict):
            return (
                False,
                "Invalid failure state.",
            )

        if (
            not isinstance(failed_move.get("r"), int)
            or not isinstance(failed_move.get("c"), int)
        ):
            return (
                False,
                "Invalid failure move.",
            )

        prev_head = prev["worm"][0]
        if (
            abs(failed_move["r"] - prev_head["r"])
            + abs(failed_move["c"] - prev_head["c"])
            != 1
        ):
            return (
                False,
                "Invalid failure move.",
            )

        cfg = level_static_config(level_number)
        size = cfg["size"]

        collision = (
            failed_move["r"] <= 0
            or failed_move["c"] <= 0
            or failed_move["r"] >= size - 1
            or failed_move["c"] >= size - 1
            or any(
                same_position(failed_move, p)
                for p in prev["obstacles"]
            )
            or any(
                same_position(failed_move, p)
                for p in prev["worm"][1:]
            )
        )

        if not collision:
            return (
                False,
                "Invalid failure state.",
            )

        if cur["worm"] != prev["worm"]:
            return (
                False,
                "Invalid failure worm state.",
            )

        if cur["apples"] != prev["apples"]:
            return (
                False,
                "Invalid failure apple state.",
            )

        if cur["score"] != prev["score"]:
            return (
                False,
                "Invalid failure score.",
            )

        return True, cur

    if cur.get("failedMove") is not None:
        return (
            False,
            "Invalid failure state.",
        )

    # --------------------------------------------------------
    # START TIMESTAMP
    # --------------------------------------------------------

    if (
        cur["started"]
        != prev["started"]
    ):
        return (
            False,
            "Game start timestamp cannot be changed.",
        )

    # --------------------------------------------------------
    # SERVER-AUTHORITATIVE REWARD COUNTERS
    #
    # These values can only change through a verified
    # server-side reward claim.
    # --------------------------------------------------------

    reward_counter_fields = (
        "revives",
        "hints",
        "boosters",
        "extraMoves",
    )

    for field in reward_counter_fields:
        if (
            cur[field]
            != prev[field]
        ):
            return (
                False,
                (
                    f"{field} can only be "
                    "changed by a verified "
                    "server reward."
                ),
            )

    # --------------------------------------------------------
    # HEAD MOVEMENT
    # --------------------------------------------------------

    prev_head = prev["worm"][0]
    cur_head = cur["worm"][0]

    if (
        abs(
            cur_head["r"]
            - prev_head["r"]
        )
        + abs(
            cur_head["c"]
            - prev_head["c"]
        )
        != 1
    ):
        return (
            False,
            "Worm moved more than one cell.",
        )

    # --------------------------------------------------------
    # WORM GROWTH
    # --------------------------------------------------------

    expected_worm = [
        cur_head
    ] + prev["worm"]

    ate = any(
        cur_head == apple
        for apple in prev["apples"]
    )

    if not ate:
        expected_worm.pop()

    if (
        cur["worm"]
        != expected_worm
    ):
        return (
            False,
            "Invalid worm movement or growth.",
        )

    # --------------------------------------------------------
    # APPLE COLLECTION
    # --------------------------------------------------------

    expected_apples = [
        apple
        for apple in prev["apples"]
        if apple != cur_head
    ]

    if (
        cur["apples"]
        != expected_apples
    ):
        return (
            False,
            "Invalid apple collection state.",
        )

    # --------------------------------------------------------
    # DETERMINISTIC SCORE
    # --------------------------------------------------------

    transition_score = (
        prev["score"]
        + (
            10
            if ate
            else 0
        )
    )

    if (
        ate
        and not expected_apples
    ):
        transition_score += 50

    expected_score = (
        transition_score
        + (
            100
            if require_completion
            else 0
        )
    )

    if (
        cur["score"]
        != expected_score
    ):
        return (
            False,
            (
                "Invalid completion score."
                if require_completion
                else "Invalid score progression."
            ),
        )

    # --------------------------------------------------------
    # COMPLETION
    # --------------------------------------------------------

    if require_completion:
        if cur["apples"]:
            return (
                False,
                (
                    "All apples must be "
                    "collected before completion."
                ),
            )

        if not same_position(
            cur["worm"][0],
            cur["portal"],
        ):
            return (
                False,
                "Worm is not at the portal.",
            )

        if not cur["completed"]:
            return (
                False,
                "Completion flag is required.",
            )

    return True, cur


def same_position(
    a,
    b,
):
    try:
        return (
            int(a.get("r", -999))
            == int(b.get("r", -998))
            and
            int(a.get("c", -999))
            == int(b.get("c", -998))
        )
    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        return False


# ============================================================
# CHECKPOINT
# ============================================================

@api_view(["POST"])
@auth_required
def checkpoint(
    request,
    session_id,
):
    with transaction.atomic():
        session = (
            GameSession.objects
            .select_for_update()
            .select_related("level")
            .filter(
                id=session_id,
                user=request.user,
                status="ACTIVE",
            )
            .first()
        )

        if not session:
            return Response(
                {
                    "detail": (
                        "Invalid session."
                    )
                },
                status=404,
            )

        state = (
            request.data.get(
                "state"
            )
            or {}
        )

        ok, checked = (
            validate_next_move(
                session.checkpoint_state,
                state,
                session.level.number,
            )
        )

        if not ok:
            return Response(
                {
                    "detail": checked
                },
                status=400,
            )

        history = list(
            session.checkpoint_history
            or []
        )

        history.append(
            session.checkpoint_state
        )

        session.checkpoint_history = (
            history[-100:]
        )

        session.moves = (
            checked["moves"]
        )

        session.score = (
            checked["score"]
        )

        session.checkpoint_state = (
            checked
        )

        # A collision permanently fails a No-Revive session.
        if (
            checked.get("failed")
            and level_revive_limit(session.level.number) <= 0
        ):
            session.status = "FAILED"

        session.save(
            update_fields=[
                "moves",
                "score",
                "checkpoint_state",
                "checkpoint_history",
                "status",
                "updated_at",
            ]
        )

    return Response({
        "ok": True,
        "sessionId": str(
            session.id
        ),
        "moves": session.moves,
        "score": session.score,
    })


# ============================================================
# UNDO
# ============================================================

@api_view(["POST"])
@auth_required
def undo_game(
    request,
    session_id,
):
    with transaction.atomic():
        session = (
            GameSession.objects
            .select_for_update()
            .filter(
                id=session_id,
                user=request.user,
                status="ACTIVE",
            )
            .first()
        )

        if not session:
            return Response(
                {
                    "detail": (
                        "Invalid session."
                    )
                },
                status=404,
            )

        history = list(
            session.checkpoint_history
            or []
        )

        if not history:
            return Response(
                {
                    "detail": (
                        "Nothing to undo."
                    )
                },
                status=409,
            )

        previous = history.pop()

        ok, checked = (
            validate_state_shape(
                previous,
                session.level.number,
            )
        )

        if not ok:
            return Response(
                {
                    "detail": (
                        "Stored undo state "
                        "is invalid."
                    )
                },
                status=409,
            )

        # ----------------------------------------------------
        # NEVER ROLL BACK SERVER-AUTHORITATIVE REWARDS
        # ----------------------------------------------------

        current = _normalise_state(
            session.checkpoint_state
            or {}
        )

        # No-Revive levels cannot escape a collision by
        # restoring an earlier checkpoint.
        if (
            current.get("failed")
            and level_revive_limit(session.level.number) <= 0
        ):
            return Response(
                {
                    "detail": (
                        "Undo is disabled after failure "
                        "on a No-Revive level."
                    )
                },
                status=409,
            )

        checked = _normalise_state(
            checked
        )

        for field in (
            "revives",
            "hints",
            "boosters",
            "extraMoves",
        ):
            checked[field] = (
                current[field]
            )

        session.checkpoint_history = (
            history
        )

        session.checkpoint_state = (
            checked
        )

        session.moves = int(
            checked.get(
                "moves",
                0,
            )
        )

        session.score = int(
            checked.get(
                "score",
                0,
            )
        )

        session.save(
            update_fields=[
                "moves",
                "score",
                "checkpoint_state",
                "checkpoint_history",
                "updated_at",
            ]
        )

    return Response({
        "ok": True,
        "sessionId": str(
            session.id
        ),
        "moves": session.moves,
        "score": session.score,
        "state": checked,
    })


# ============================================================
# COMPLETION REPLAY
# ============================================================

def _completion_replay_response(
    request,
    session,
):
    incoming = (
        request.data.get(
            "state"
        )
        or {}
    )

    if not isinstance(incoming, dict):
        return Response(
            {
                "detail": (
                    "Invalid completion payload."
                )
            },
            status=400,
        )

    # Star value is never trusted from a replay request.
    # Recalculate it from the completed server state below.

    stored_state = (
        session.checkpoint_state
        or {}
    )

    try:
        stored_normalised = (
            _normalise_state(
                stored_state
            )
        )
    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        return Response(
            {
                "detail": (
                    "Stored completion state "
                    "is invalid."
                )
            },
            status=500,
        )

    # --------------------------------------------------------
    # SERVER-AUTHORITATIVE REPLAY VALIDATION
    #
    # A replay request may contain a partial state. The client
    # must NOT be required to resend the entire canonical
    # server state.
    #
    # Every supplied replay-critical value is still validated
    # against the stored completion.
    # --------------------------------------------------------

    try:
        incoming_moves = request.data.get(
            "moves",
            incoming.get(
                "moves",
                stored_normalised["moves"],
            ),
        )

        incoming_score = request.data.get(
            "score",
            incoming.get(
                "score",
                stored_normalised["score"],
            ),
        )

        incoming_moves = int(
            incoming_moves
        )

        incoming_score = int(
            incoming_score
        )

    except (
        TypeError,
        ValueError,
    ):
        return Response(
            {
                "detail": (
                    "Invalid completion "
                    "moves or score."
                )
            },
            status=400,
        )

    if (
        incoming_moves
        != session.moves
    ):
        return Response(
            {
                "detail": (
                    "Invalid completion replay: "
                    "moves do not match the "
                    "stored completion."
                )
            },
            status=400,
        )

    if (
        incoming_score
        != session.score
    ):
        return Response(
            {
                "detail": (
                    "Invalid completion replay: "
                    "score does not match the "
                    "stored completion."
                )
            },
            status=400,
        )

    # --------------------------------------------------------
    # OPTIONAL CLIENT STATE VALIDATION
    #
    # Validate only fields explicitly supplied by the client.
    # Do not compare a partial client state with the complete
    # server state.
    # --------------------------------------------------------

    replay_state = {
        "completed": (
            incoming.get("completed")
            if "completed" in incoming
            else None
        ),
        "failed": (
            incoming.get("failed")
            if "failed" in incoming
            else None
        ),
        "moves": (
            incoming.get("moves")
            if "moves" in incoming
            else None
        ),
        "score": (
            incoming.get("score")
            if "score" in incoming
            else None
        ),
    }

    stored_replay_state = {
        "completed": stored_normalised.get(
            "completed"
        ),
        "failed": stored_normalised.get(
            "failed"
        ),
        "moves": stored_normalised.get(
            "moves"
        ),
        "score": stored_normalised.get(
            "score"
        ),
    }

    for field, value in replay_state.items():
        if value is None:
            continue

        if field in (
            "moves",
            "score",
        ):
            try:
                value = int(value)
            except (
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "detail": (
                            "Invalid completion "
                            f"{field}."
                        )
                    },
                    status=400,
                )

        if (
            value
            != stored_replay_state[field]
        ):
            return Response(
                {
                    "detail": (
                        "Invalid completion replay: "
                        f"{field} does not match "
                        "the stored completion."
                    )
                },
                status=400,
            )

    # --------------------------------------------------------
    # IDEMPOTENT REPLAY
    #
    # No wallet mutation.
    # No reward mutation.
    # No progress mutation.
    # Return the already-finalized server result.
    # --------------------------------------------------------

    return Response({
        "completed": True,
        "coins": economy()[
            "levelCompletionCoins"
        ],
        "score": session.score,
        "stars": calculate_stars(stored_normalised),
        "idempotent": True,
    })

# ============================================================
# COMPLETE GAME
# ============================================================

@api_view(["POST"])
@auth_required
def complete_game(
    request,
    session_id,
):
    with transaction.atomic():
        session = (
            GameSession.objects
            .select_for_update()
            .select_related("level")
            .filter(
                id=session_id,
                user=request.user,
            )
            .first()
        )

        if not session:
            return Response(
                {
                    "detail": (
                        "Invalid session."
                    )
                },
                status=404,
            )

        # ----------------------------------------------------
        # IDEMPOTENT COMPLETION
        # ----------------------------------------------------

        if session.status == "COMPLETED":
            return _completion_replay_response(
                request,
                session,
            )

        if session.status != "ACTIVE":
            return Response(
                {
                    "detail": (
                        "Invalid or already "
                        "used session."
                    )
                },
                status=409,
            )

        # ----------------------------------------------------
        # SERVER-AUTHORITATIVE CHECKPOINT VALIDATION
        # ----------------------------------------------------
        # The database checkpoint is always the source of truth.
        # If the client supplies a state payload, it must exactly
        # match the authoritative checkpoint. The client can never
        # replace or modify the server checkpoint.
        stored_state = _normalise_state(
            session.checkpoint_state or {}
        )
        # Permanently reject completion of a failed No-Revive attempt,
        # including legacy sessions whose database status is still ACTIVE.
        if (
            stored_state.get("failed")
            and level_revive_limit(session.level.number) <= 0
        ):
            session.status = "FAILED"
            session.save(
                update_fields=["status", "updated_at"]
            )
            return Response(
                {
                    "detail": (
                        "A failed No-Revive game cannot be completed."
                    )
                },
                status=409,
            )

        if not stored_state:
            return Response(
                {
                    "detail": (
                        "No checkpoint state is available "
                        "for completion."
                    )
                },
                status=409,
            )

        incoming_state = request.data.get(
            "state"
        )

        if incoming_state is not None:
            incoming_ok, incoming_checked = (
                validate_state_shape(
                    incoming_state,
                    session.level.number,
                )
            )

            if not incoming_ok:
                return Response(
                    {
                        "detail": (
                            "Invalid completion state: "
                            f"{incoming_checked}"
                        )
                    },
                    status=400,
                )

            incoming_normalised = _normalise_state(
                incoming_checked
            )

            if incoming_normalised != stored_state:
                return Response(
                    {
                        "detail": (
                            "Invalid completion state: "
                            "submitted state does not match "
                            "the stored checkpoint."
                        )
                    },
                    status=400,
                )

        # The server continues using ONLY the stored checkpoint.
        state = stored_state

        # ----------------------------------------------------
        # SERVER-AUTHORITATIVE FINAL COMPLETION
        # ----------------------------------------------------
        # The checkpoint is the only trusted game state.
        # Completion itself is a server-side transition:
        #   - all apples must already be collected
        #   - worm must already be at the portal
        #   - completion bonus is calculated by the server
        #   - client-supplied score/moves are ignored
        # ----------------------------------------------------

        objective_result = evaluate_objectives(
            state,
            session.level.number,
        )

        if not objective_result["all_completed"]:
            incomplete = [
                item["title"]
                for item in objective_result["objectives"]
                if item.get("required", True)
                and not item["completed"]
            ]
            return Response(
                {
                    "detail": (
                        "Required objectives are not complete: "
                        + ", ".join(incomplete)
                    ),
                    "objectives": objective_result["objectives"],
                },
                status=409,
            )

        if state["apples"]:
            return Response(
                {
                    "detail": (
                        "All apples must be collected "
                        "before completion."
                    )
                },
                status=409,
            )

        if not same_position(
            state["worm"][0],
            state["portal"],
        ):
            return Response(
                {
                    "detail": (
                        "Worm is not at the portal."
                    )
                },
                status=409,
            )

        if state["completed"]:
            return Response(
                {
                    "detail": (
                        "Completion state is already "
                        "finalized."
                    )
                },
                status=409,
            )

        moves = int(
            state["moves"]
        )

        checkpoint_score = int(
            state["score"]
        )

        completion_bonus = 100

        final_score = (
            checkpoint_score
            + completion_bonus
        )

        # Final state is generated by the server.
        state["score"] = final_score
        state["completed"] = True

        # ----------------------------------------------------
        # SERVER-AUTHORITATIVE STAR CALCULATION
        # ----------------------------------------------------
        # Never trust the client-supplied `stars` field. Stars are derived
        # solely from the authoritative checkpoint state. This prevents a
        # client from submitting stars=3 after a slow/revived completion.
        stars = calculate_stars(state)

        # ----------------------------------------------------
        # COMPLETE SESSION
        # ----------------------------------------------------

        session.moves = moves
        session.score = final_score
        session.status = "COMPLETED"
        session.completed_at = timezone.now()
        session.checkpoint_state = state

        session.save(
            update_fields=[
                "moves",
                "score",
                "status",
                "completed_at",
                "checkpoint_state",
                "updated_at",
            ]
        )

        # ----------------------------------------------------
        # PROGRESS
        # ----------------------------------------------------

        progress = (
            PlayerProgress.objects
            .select_for_update()
            .get(
                user=request.user,
                level=session.level,
            )
        )

        progress.completed = True
        progress.unlocked = True

        progress.stars = max(
            progress.stars,
            stars,
        )

        progress.best_score = max(
            progress.best_score,
            final_score,
        )

        progress.best_moves = (
            moves
            if progress.best_moves is None
            else min(
                progress.best_moves,
                moves,
            )
        )

        progress.save()

        unlock_next(
            request.user,
            session.level.number,
        )

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        profile = (
            PlayerProfile.objects
            .select_for_update()
            .filter(
                user=request.user
            )
            .first()
        )

        if profile is None:
            profile = PlayerProfile.objects.create(
                user=request.user
            )

        profile.total_score += (
            final_score
        )

        profile.save(
            update_fields=[
                "total_score",
                "updated_at",
            ]
        )

        # ----------------------------------------------------
        # LEVEL COIN REWARD
        # ----------------------------------------------------

        coins = economy()[
            "levelCompletionCoins"
        ]

        level_reward_reference = (
            f"level:"
            f"{session.level.number}:"
            f"session:{session.id}"
        )

        grant_coins(
            request.user,
            coins,
            "LEVEL_REWARD",
            level_reward_reference,
            reward_ledger={
                "event_id": f"level-completion:{session.id}",
                "placement": "LEVEL_COMPLETION",
                "reward_type": "COINS",
                "metadata": {
                    "sessionId": str(session.id),
                    "level": session.level.number,
                    "walletReference": level_reward_reference,
                    "source": "level_completion",
                },
            },
        )

        update_achievements(
            request.user,
            session.level.number,
            stars,
            profile.total_score,
        )

    return Response({
        "completed": True,
        "coins": coins,
        "score": final_score,
        "stars": stars,
        "idempotent": False,
    })


# ============================================================
# AD OPPORTUNITY
# ============================================================

@api_view(["POST"])
@auth_required
@transaction.atomic
def ad_opportunity(request):
    """Create a rewarded-ad opportunity with per-user serialization.

    Locking the authenticated user row serializes all opportunity-creation
    requests for that user. This makes the cooldown and daily-limit checks
    safe against concurrent requests with different event IDs. The unique
    event_id constraint remains the final cross-user/idempotency safeguard.
    """
    placement = str(request.data.get("placement", "")).strip().upper()
    allowed = {value for value, _ in AdOpportunity.PLACEMENTS}

    if placement not in allowed:
        return Response({"detail": "Unknown placement."}, status=400)

    event_id = str(request.data.get("eventId") or uuid.uuid4()).strip()
    if not event_id or len(event_id) > 128:
        return Response({"detail": "Invalid eventId."}, status=400)

    metadata = request.data.get("metadata") or {}
    if not isinstance(metadata, dict):
        return Response({"detail": "metadata must be an object."}, status=400)

    # Bind session-scoped opportunities to the session at creation time.
    # Also preserve compatibility with clients that send sessionId at the
    # top level rather than inside metadata.
    session_scoped_placements = {
        "REVIVE",
        "HINT",
        "BOOSTER",
        "EXTRA_MOVES",
        "DOUBLE_COINS",
        "DOUBLE_SCORE",
    }
    supplied_session_id = (
        metadata.get("sessionId")
        or request.data.get("sessionId")
    )
    if placement in session_scoped_placements and supplied_session_id:
        try:
            validated_session_id = uuid.UUID(str(supplied_session_id))
        except (ValueError, TypeError, AttributeError):
            return Response(
                {"detail": "Invalid game session binding."},
                status=409,
            )

        bound_session = (
            GameSession.objects
            .select_for_update()
            .filter(
                id=validated_session_id,
                user=request.user,
            )
            .first()
        )

        if not bound_session:
            return Response(
                {"detail": "Game session binding is not available."},
                status=409,
            )

        metadata = {
            **metadata,
            "sessionId": str(bound_session.id),
        }

    # Lock a row that always exists, even if this user has no PlayerProfile yet.
    # The lock is held until this request commits or rolls back.
    User.objects.select_for_update().get(pk=request.user.pk)

    def idempotent_response(opportunity, config):
        if opportunity.user_id != request.user.id:
            return Response({"detail": "Invalid event."}, status=400)
        if opportunity.placement != placement:
            return Response(
                {"detail": "eventId is already bound to a different placement."},
                status=409,
            )
        return Response({
            "eventId": opportunity.event_id,
            "placement": opportunity.placement,
            "status": opportunity.status,
            "provider": getattr(settings, "AD_PROVIDER", "mock"),
            "cooldownSeconds": config["adCooldownSeconds"],
            "idempotent": True,
        })

    # Recheck only after acquiring the per-user lock. A concurrent request
    # with this same event ID may have committed while this request waited.
    cfg = economy()
    existing = AdOpportunity.objects.filter(event_id=event_id).first()
    if existing:
        return idempotent_response(existing, cfg)

    # REVIVE is level-aware and must be checked before creating an opportunity.
    revive_session = None
    if placement == "REVIVE":
        revive_session_id = metadata.get("sessionId") or request.data.get("sessionId")
        if not revive_session_id:
            return Response(
                {"detail": "Revive requires an active game session."},
                status=409,
            )

        revive_session = (
            GameSession.objects.select_for_update()
            .filter(id=revive_session_id, user=request.user)
            .select_related("level")
            .first()
        )
        # A failed checkpoint is expected when a player requests a revive.
        # Keep the session ownership and ACTIVE-status checks, then enforce
        # the authoritative per-level revive limit. No-Revive levels return
        # a limit of zero and remain ineligible.
        if (
            not revive_session
            or revive_session.status != "ACTIVE"
        ):
            return Response({"detail": "Revive is not available."}, status=409)

        revive_limit = level_revive_limit(revive_session.level.number)
        if (
            revive_limit <= 0
            or revive_session.revives_used >= revive_limit
        ):
            return Response({"detail": "Revive is not available."}, status=409)

    now = timezone.now()
    profile = (
        PlayerProfile.objects.select_for_update()
        .filter(user=request.user)
        .first()
    )
    last_opportunity = (
        AdOpportunity.objects.filter(
            user=request.user,
            status__in=("OFFERED", "REQUESTED", "AD_STARTED", "AD_COMPLETED", "VERIFYING", "VERIFIED", "GRANTED"),
        )
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )

    last_claim = profile.last_reward_claim_at if profile else None
    if last_claim is None:
        last_claim = (
            RewardTransaction.objects.filter(
                user=request.user,
                status="GRANTED",
                placement__in=REWARDED_AD_PLACEMENTS,
            )
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )

    cooldown_anchor = max(
        (value for value in (last_opportunity, last_claim) if value),
        default=None,
    )
    cooldown = int(cfg["adCooldownSeconds"])
    if cooldown_anchor:
        elapsed = (now - cooldown_anchor).total_seconds()
        if elapsed < cooldown:
            remaining = max(1, int(cooldown - elapsed + 0.999))
            return Response(
                {
                    "detail": "Reward cooldown active.",
                    "cooldownSeconds": remaining,
                },
                status=429,
            )

    today = timezone.localdate()
    granted_today = RewardTransaction.objects.filter(
        user=request.user,
        status="GRANTED",
        placement__in=REWARDED_AD_PLACEMENTS,
        created_at__date=today,
    ).count()
    if granted_today >= int(cfg["maxRewardedAdsPerDay"]):
        return Response(
            {"detail": "Daily rewarded-ad limit reached."},
            status=429,
        )

    # The nested atomic block creates a savepoint. If a different user's
    # request races on the globally unique event_id, IntegrityError can be
    # handled without leaving the outer transaction unusable.
    try:
        with transaction.atomic():
            opportunity = AdOpportunity.objects.create(
                event_id=event_id,
                user=request.user,
                placement=placement,
                metadata={
                    **metadata,
                    "adLifecycle": [
                        {"state": "OFFERED", "at": timezone.now().isoformat()},
                    ],
                },
                status="OFFERED",
            )
    except IntegrityError:
        opportunity = AdOpportunity.objects.filter(event_id=event_id).first()
        if opportunity is None:
            raise
        return idempotent_response(opportunity, cfg)

    provider = str(getattr(settings, "AD_PROVIDER", "mock")).lower()
    try:
        provider_adapter = get_ad_provider()
        provider_available = bool(getattr(provider_adapter, "available", True))
    except Exception as exc:
        logger.warning("Rewarded-ad provider is unavailable: %s", exc)
        provider_available = False

    return Response({
        "eventId": opportunity.event_id,
        "placement": opportunity.placement,
        "status": opportunity.status,
        "provider": provider,
        "providerAvailable": provider_available,
        "cooldownSeconds": cfg["adCooldownSeconds"],
        "idempotent": False,
        "message": ("Ad opportunity offered." if provider_available else
                    "Rewarded ads are unavailable because no real provider is configured."),
    })


# ============================================================
# REQUEST / START REWARDED AD
# ============================================================

@api_view(["POST"])
@auth_required
@transaction.atomic
def request_ad(request, event_id):
    """Request a provider session; player input cannot complete an ad."""
    opportunity = (AdOpportunity.objects.select_for_update()
                   .filter(event_id=event_id, user=request.user).first())
    if not opportunity:
        return Response({"detail": "Unknown ad opportunity."}, status=404)
    if opportunity.status in {"REQUESTED", "AD_STARTED", "AD_COMPLETED", "VERIFYING", "VERIFIED", "GRANTED"}:
        return Response({
            "eventId": event_id,
            "status": opportunity.status,
            "provider": getattr(settings, "AD_PROVIDER", "configured"),
            "launch": (opportunity.metadata or {}).get("providerLaunch", {}),
            "idempotent": True,
        })
    if opportunity.status != "OFFERED":
        return Response({"detail": "This ad opportunity is no longer available."}, status=409)
    now = timezone.now()
    lifecycle = list((opportunity.metadata or {}).get("adLifecycle", []))
    # Record the request attempt even when no provider is configured. Keep the
    # durable opportunity OFFERED so it can be retried after provider setup.
    if not any(item.get("state") == "REQUESTED" for item in lifecycle):
        lifecycle.append({"state": "REQUESTED", "at": now.isoformat()})
    opportunity.status = "REQUESTED"
    opportunity.metadata = {
        **(opportunity.metadata or {}),
        "adLifecycle": lifecycle,
        "lastRequestAttemptAt": now.isoformat(),
    }
    opportunity.save(update_fields=["status", "metadata"])

    try:
        provider = get_ad_provider()
        launch = provider.create_ad_session(opportunity)
    except Exception as exc:
        # Provider/network failures must never be interpreted as ad completion.
        logger.warning("Rewarded-ad provider session creation failed: %s", exc)
        opportunity.status = "OFFERED"
        opportunity.metadata = {
            **(opportunity.metadata or {}),
            "lastProviderError": str(exc)[:500],
        }
        opportunity.save(update_fields=["status", "metadata"])
        return Response({"status": "AD_UNAVAILABLE", "available": False, "detail": "The rewarded-ad provider is currently unavailable."}, status=503)
    if not isinstance(launch, dict) or not launch.get("providerReference"):
        opportunity.status = "OFFERED"
        opportunity.metadata = {**(opportunity.metadata or {}), "lastProviderError": "Invalid provider ad session."}
        opportunity.save(update_fields=["status", "metadata"])
        return Response({"detail": "Provider returned an invalid ad session."}, status=502)
    launch_url = launch.get("launch", {}).get("url") if isinstance(launch.get("launch", {}), dict) else None
    if launch_url:
        parsed_launch_url = urlsplit(str(launch_url))
        if parsed_launch_url.scheme != "https" or not parsed_launch_url.netloc:
            opportunity.status = "OFFERED"
            opportunity.metadata = {**(opportunity.metadata or {}), "lastProviderError": "Provider launch URL must use HTTPS."}
            opportunity.save(update_fields=["status", "metadata"])
            return Response({"detail": "Provider launch URL must use HTTPS."}, status=502)
    now = timezone.now()
    opportunity.status = "AD_STARTED"
    opportunity.provider_reference = str(launch["providerReference"])[:128]
    lifecycle = list((opportunity.metadata or {}).get("adLifecycle", []))
    if not lifecycle or lifecycle[0].get("state") != "OFFERED":
        lifecycle.insert(0, {"state": "OFFERED", "at": opportunity.created_at.isoformat()})
    if not any(item.get("state") == "AD_STARTED" for item in lifecycle):
        lifecycle.append({"state": "AD_STARTED", "at": now.isoformat()})
    opportunity.metadata = {
        **(opportunity.metadata or {}),
        "adLifecycle": lifecycle,
        "providerLaunch": launch.get("launch", {}),
        "lastProviderError": "",
    }
    opportunity.save(update_fields=["status", "provider_reference", "metadata"])
    return Response({"eventId": event_id, "status": "AD_STARTED", "provider": getattr(provider, "name", getattr(settings, "AD_PROVIDER", "configured")), "launch": launch.get("launch", {})})


# ============================================================
# REWARDED AD STATUS
# ============================================================

@api_view(["GET"])
@auth_required
def ad_opportunity_status(request, event_id):
    opportunity = AdOpportunity.objects.filter(event_id=event_id, user=request.user).first()
    if not opportunity:
        return Response({"detail": "Unknown ad opportunity."}, status=404)
    return Response({
        "eventId": opportunity.event_id,
        "placement": opportunity.placement,
        "status": opportunity.status,
        "verified": opportunity.status in {"VERIFIED", "GRANTED"},
        "granted": opportunity.status == "GRANTED",
        "providerReference": opportunity.provider_reference if opportunity.status in {"VERIFIED", "GRANTED"} else "",
        "lifecycle": (opportunity.metadata or {}).get("adLifecycle", []),
    })


# ============================================================
# PROVIDER-FREE DEMO COMPLETION (LOCAL/STAGING ONLY)
# ============================================================

@api_view(["POST"])
@auth_required
@transaction.atomic
def provider_free_demo_complete(request, event_id):
    """Complete an explicit provider-free demo opportunity.

    This endpoint is intentionally separate from the real provider webhook.
    It is enabled only by ALLOW_PROVIDER_FREE_DEMO_ADS and marks the reward
    as a MOCKED/DEMO event in metadata. It must never be enabled for a live
    ad-monetized deployment.
    """
    if not getattr(settings, "ALLOW_PROVIDER_FREE_DEMO_ADS", False):
        return Response({"detail": "Provider-free demo rewards are disabled."}, status=404)
    opportunity = (
        AdOpportunity.objects.select_for_update()
        .filter(event_id=event_id, user=request.user)
        .first()
    )
    if not opportunity:
        return Response({"detail": "Unknown ad opportunity."}, status=404)
    if opportunity.status == "VERIFIED" or opportunity.status == "GRANTED":
        return Response({"verified": True, "status": opportunity.status, "idempotent": True})
    if opportunity.status != "AD_STARTED":
        return Response({"detail": "Demo completion requires an active demo ad session."}, status=409)
    if not str(opportunity.provider_reference).startswith("pf-demo-"):
        return Response({"detail": "This opportunity is not a provider-free demo event."}, status=409)

    now = timezone.now()
    lifecycle = list((opportunity.metadata or {}).get("adLifecycle", []))
    lifecycle.append({"state": "AD_COMPLETED", "at": now.isoformat(), "mode": "provider-free-demo"})
    lifecycle.append({"state": "VERIFYING", "at": now.isoformat(), "mode": "provider-free-demo"})
    lifecycle.append({"state": "VERIFIED", "at": now.isoformat(), "mode": "provider-free-demo"})
    opportunity.status = "VERIFIED"
    opportunity.completed_at = now
    opportunity.metadata = {
        **(opportunity.metadata or {}),
        "adLifecycle": lifecycle,
        "verificationMode": "MOCKED_PROVIDER_FREE_DEMO",
        "provider_verified": True,
    }
    opportunity.save(update_fields=["status", "completed_at", "metadata"])
    return Response({"verified": True, "status": "VERIFIED", "demo": True})


# ============================================================
# AD PROVIDER CALLBACK
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def ad_provider_callback(request):
    event_id = str(
        request.data.get(
            "eventId",
            "",
        )
    ).strip()

    provider_reference = str(
        request.data.get(
            "providerReference",
            "",
        )
    ).strip()
    event_status = str(request.data.get("eventStatus", "")).strip().upper()

    provided = str(
        request.data.get(
            "signature",
            "",
        )
    ).strip()

    if not event_id:
        return Response(
            {
                "detail": (
                    "eventId is required."
                )
            },
            status=400,
        )

    if not provider_reference:
        return Response(
            {"detail": "providerReference is required."},
            status=400,
        )
    if event_status != "COMPLETED":
        return Response(
            {"detail": "A completed rewarded-ad event is required."},
            status=400,
        )

    opportunity = (
        AdOpportunity.objects.select_for_update()
        .filter(event_id=event_id)
        .first()
    )

    if not opportunity:
        return Response(
            {
                "detail": (
                    "Unknown opportunity."
                )
            },
            status=404,
        )

    secret = getattr(
        settings,
        "AD_PROVIDER_WEBHOOK_SECRET",
        "",
    )

    if not secret:
        logger.error(
            "AD_PROVIDER_WEBHOOK_SECRET is not configured."
        )

        return Response(
            {
                "detail": (
                    "Provider webhook is not configured."
                )
            },
            status=503,
        )

    expected = hmac.new(
        secret.encode("utf-8"),
        f"{event_id}:{provider_reference}:{event_status}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not secrets.compare_digest(
        expected,
        provided,
    ):
        return Response(
            {
                "detail": (
                    "Provider verification failed."
                )
            },
            status=403,
        )

    # --------------------------------------------------------
    # IDEMPOTENT CALLBACK
    # --------------------------------------------------------

    if opportunity.status in {"VERIFIED", "GRANTED"}:
        if opportunity.provider_reference == provider_reference:
            return Response({"verified": True, "status": opportunity.status, "idempotent": True})
        return Response({"detail": "Opportunity is already verified with a different provider reference."}, status=409)

    if opportunity.status != "AD_STARTED":
        return Response({"detail": "Ad completion cannot be accepted before a provider ad session has started."}, status=409)
    if not secrets.compare_digest(opportunity.provider_reference, provider_reference):
        return Response({"detail": "Provider reference does not match the started ad session."}, status=403)

    now = timezone.now()
    lifecycle = list((opportunity.metadata or {}).get("adLifecycle", []))
    lifecycle.append({"state": "AD_COMPLETED", "at": now.isoformat()})
    opportunity.status = "AD_COMPLETED"
    opportunity.metadata = {**(opportunity.metadata or {}), "adLifecycle": lifecycle}
    opportunity.save(update_fields=["status", "metadata"])

    lifecycle.append({"state": "VERIFYING", "at": now.isoformat()})
    opportunity.status = "VERIFYING"
    opportunity.metadata = {**(opportunity.metadata or {}), "adLifecycle": lifecycle}
    opportunity.save(update_fields=["status", "metadata"])

    lifecycle.append({"state": "VERIFIED", "at": now.isoformat()})
    opportunity.status = "VERIFIED"
    opportunity.provider_reference = provider_reference
    opportunity.completed_at = now
    opportunity.metadata = {**(opportunity.metadata or {}), "adLifecycle": lifecycle, "providerVerified": True}
    opportunity.save(update_fields=["status", "provider_reference", "completed_at", "metadata"])
    return Response({"verified": True, "status": "VERIFIED", "idempotent": False})


# ============================================================
# CLAIM REWARD
# ============================================================

@api_view(["POST"])
@auth_required
@transaction.atomic
def claim_reward(request):
    event_id = str(
        request.data.get(
            "eventId",
            "",
        )
    ).strip()

    if not event_id:
        return Response(
            {
                "detail": (
                    "eventId is required."
                )
            },
            status=400,
        )

    # --------------------------------------------------------
    # LOCK OPPORTUNITY
    # --------------------------------------------------------

    opportunity = (
        AdOpportunity.objects
        .select_for_update()
        .filter(
            event_id=event_id,
            user=request.user,
        )
        .first()
    )

    if not opportunity:
        return Response(
            {
                "detail": (
                    "Unknown ad opportunity."
                )
            },
            status=404,
        )

    # --------------------------------------------------------
    # IDEMPOTENT REWARD CLAIM
    # --------------------------------------------------------

    existing = (
        RewardTransaction.objects
        .filter(
            event_id=event_id
        )
        .first()
    )

    if existing:
        if existing.user_id != request.user.id:
            return Response(
                {"detail": "Reward event belongs to another user."},
                status=409,
            )

        if opportunity.status != "GRANTED":
            lifecycle = list((opportunity.metadata or {}).get("adLifecycle", []))
            lifecycle.append({"state": "GRANTED", "at": timezone.now().isoformat()})
            opportunity.status = "GRANTED"
            opportunity.metadata = {**(opportunity.metadata or {}), "adLifecycle": lifecycle}
            opportunity.save(update_fields=["status", "metadata"])
        return Response({"granted": False, "duplicate": True, "amount": existing.amount, "transactionId": existing.id, "status": "GRANTED"})

    if opportunity.status not in {"VERIFIED", "GRANTED"}:
        return Response({"detail": "Reward is not verified by the ad provider."}, status=409)

    cfg = economy()

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    placement = (
        opportunity.placement
    )

    metadata = (
        opportunity.metadata
        or {}
    )

    # A claim cannot attach an existing opportunity to a different
    # session supplied by the client. The creation-time binding is authoritative.
    stored_session_id = metadata.get("sessionId")
    requested_session_id = request.data.get("sessionId")

    session_scoped_placements = {
        "REVIVE",
        "HINT",
        "BOOSTER",
        "EXTRA_MOVES",
        "DOUBLE_COINS",
        "DOUBLE_SCORE",
    }

    if (
        placement in session_scoped_placements
        and requested_session_id
        and (
            not stored_session_id
            or str(requested_session_id) != str(stored_session_id)
        )
    ):
        return Response(
            {
                "detail": (
                    "Reward opportunity is not bound to the supplied "
                    "game session."
                )
            },
            status=409,
        )

    # These rewards cannot be claimed without a creation-time session binding.
    if (
        placement in ("REVIVE", "DOUBLE_COINS", "DOUBLE_SCORE")
        and not stored_session_id
    ):
        return Response(
            {
                "detail": (
                    "Reward opportunity is missing its game-session binding."
                )
            },
            status=409,
        )

    session_id = stored_session_id
    session = None

    if session_id:
        try:
            validated_session_id = uuid.UUID(str(session_id))
        except (ValueError, TypeError, AttributeError):
            return Response(
                {"detail": "Reward opportunity has an invalid game-session binding."},
                status=409,
            )

        session = (
            GameSession.objects
            .select_for_update()
            .filter(
                id=validated_session_id,
                user=request.user,
            )
            .first()
        )

        if not session:
            return Response(
                {"detail": "Reward opportunity game-session binding is unavailable."},
                status=409,
            )

    if (
        placement in ("REVIVE", "HINT", "BOOSTER", "EXTRA_MOVES")
        and session
        and level_revive_limit(session.level.number) <= 0
        and isinstance(session.checkpoint_state, dict)
        and session.checkpoint_state.get("failed")
    ):
        return Response(
            {"detail": "Rewards are unavailable after failure on a No-Revive level."},
            status=409,
        )

    # --------------------------------------------------------
    # PROFILE LOCK
    # --------------------------------------------------------

    profile = (
        PlayerProfile.objects
        .select_for_update()
        .get(
            user=request.user
        )
    )

    now = timezone.now()

    # --------------------------------------------------------
    # COOLDOWN
    # --------------------------------------------------------

    last_claim = (
        profile.last_reward_claim_at
    )

    if last_claim is None:
        last_claim = (
            RewardTransaction.objects
            .filter(
                user=request.user,
                status="GRANTED",
                placement__in=REWARDED_AD_PLACEMENTS,
            )
            .order_by(
                "-created_at"
            )
            .values_list(
                "created_at",
                flat=True,
            )
            .first()
        )

    if (
        last_claim
        and last_claim
        >= now - timedelta(
            seconds=int(
                cfg[
                    "adCooldownSeconds"
                ]
            )
        )
    ):
        remaining = max(
            1,
            int(
                (
                    (
                        last_claim
                        + timedelta(
                            seconds=int(
                                cfg[
                                    "adCooldownSeconds"
                                ]
                            )
                        )
                    )
                    - now
                ).total_seconds()
            )
            + 1,
        )

        return Response(
            {
                "detail": (
                    "Reward cooldown active."
                ),
                "cooldownSeconds": remaining,
            },
            status=429,
        )

    # --------------------------------------------------------
    # DAILY LIMIT
    # --------------------------------------------------------

    today = timezone.localdate()

    granted_today = (
        RewardTransaction.objects
        .filter(
            user=request.user,
            status="GRANTED",
            placement__in=REWARDED_AD_PLACEMENTS,
            created_at__date=today,
        )
        .count()
    )

    if (
        granted_today
        >= int(
            cfg[
                "maxRewardedAdsPerDay"
            ]
        )
    ):
        return Response(
            {
                "detail": (
                    "Daily rewarded-ad "
                    "limit reached."
                )
            },
            status=429,
        )

    # --------------------------------------------------------
    # DEFAULT REWARD VALUES
    # --------------------------------------------------------

    amount = 0
    reward_type = placement
    extra = {}

    # ========================================================
    # REVIVE
    # ========================================================

    if placement == "REVIVE":
        revive_limit = (
            level_revive_limit(
                session.level.number
            )
            if session
            else 0
        )

        if (
            not session
            or session.status != "ACTIVE"
            or session.revives_used >= revive_limit
        ):
            return Response(
                {
                    "detail": (
                        "Revive is not available."
                    )
                },
                status=409,
            )

        session.revives_used += 1

        state = _normalise_state(
            session.checkpoint_state
            or {}
        )

        state["revives"] += 1
        state["failed"] = False
        state["failedMove"] = None

        session.checkpoint_state = state

        session.save(
            update_fields=[
                "revives_used",
                "checkpoint_state",
                "updated_at",
            ]
        )

        reward_type = "REVIVE"

        extra = {
            "state": state,
            "revives_used": (
                session.revives_used
            ),
        }

    # ========================================================
    # HINT
    # ========================================================

    elif placement == "HINT":
        if not cfg.get(
            "hintEnabled",
            True,
        ):
            return Response(
                {
                    "detail": (
                        "Hints are disabled."
                    )
                },
                status=409,
            )

        if session:
            state = _normalise_state(
                session.checkpoint_state
                or {}
            )

            state["hints"] += 1

            session.checkpoint_state = (
                state
            )

            session.save(
                update_fields=[
                    "checkpoint_state",
                    "updated_at",
                ]
            )

        reward_type = "HINT"

        extra = {
            "hint": (
                "Follow the safe route "
                "toward the highlighted "
                "portal."
            )
        }

    # ========================================================
    # BOOSTER
    # ========================================================

    elif placement == "BOOSTER":
        if not cfg.get(
            "boosterEnabled",
            True,
        ):
            return Response(
                {
                    "detail": (
                        "Boosters are disabled."
                    )
                },
                status=409,
            )

        if session:
            state = _normalise_state(
                session.checkpoint_state
                or {}
            )

            state["boosters"] += 1

            session.checkpoint_state = (
                state
            )

            session.save(
                update_fields=[
                    "checkpoint_state",
                    "updated_at",
                ]
            )

        reward_type = "BOOSTER"

        extra = {
            "booster": True
        }

    # ========================================================
    # EXTRA MOVES
    # ========================================================

    elif placement == "EXTRA_MOVES":
        amount = int(
            cfg[
                "extraMoves"
            ]
        )

        if amount <= 0:
            return Response(
                {
                    "detail": (
                        "Extra Moves reward "
                        "is disabled."
                    )
                },
                status=409,
            )

        if session:
            if session.status != "ACTIVE":
                return Response(
                    {
                        "detail": (
                            "Extra Moves are "
                            "only available "
                            "during an active game."
                        )
                    },
                    status=409,
                )

            state = _normalise_state(
                session.checkpoint_state
                or {}
            )

            state["extraMoves"] += (
                amount
            )

            session.checkpoint_state = (
                state
            )

            session.save(
                update_fields=[
                    "checkpoint_state",
                    "updated_at",
                ]
            )

        reward_type = "EXTRA_MOVES"

        extra = {
            "extra_moves": amount
        }

    # ========================================================
    # DAILY REWARD
    # ========================================================

    elif placement == "DAILY_REWARD":
        amount = int(
            cfg[
                "levelCompletionCoins"
            ]
        )

        reward_type = "DAILY_REWARD"

    # ========================================================
    # DOUBLE COINS
    # ========================================================

    elif placement == "DOUBLE_COINS":
        if (
            not session
            or session.status
            != "COMPLETED"
        ):
            return Response(
                {
                    "detail": (
                        "Double Coins is "
                        "available after "
                        "level completion."
                    )
                },
                status=409,
            )

        used = (
            RewardTransaction.objects
            .filter(
                user=request.user,
                placement=placement,
                metadata__sessionId=str(
                    session.id
                ),
            )
            .count()
        )

        if (
            used
            >= int(
                cfg[
                    "maxDoubleCoinsPerLevel"
                ]
            )
        ):
            return Response(
                {
                    "detail": (
                        "Double Coins already "
                        "claimed for this level."
                    )
                },
                status=409,
            )

        amount = (
            int(
                cfg[
                    "levelCompletionCoins"
                ]
            )
            * (
                int(
                    cfg[
                        "doubleCoinsMultiplier"
                    ]
                )
                - 1
            )
        )

        reward_type = "DOUBLE_COINS"

    # ========================================================
    # DOUBLE SCORE
    # ========================================================

    elif placement == "DOUBLE_SCORE":
        if (
            not session
            or session.status
            != "COMPLETED"
        ):
            return Response(
                {
                    "detail": (
                        "Double Score is "
                        "available after "
                        "level completion."
                    )
                },
                status=409,
            )

        used = (
            RewardTransaction.objects
            .filter(
                user=request.user,
                placement=placement,
                metadata__sessionId=str(
                    session.id
                ),
            )
            .count()
        )

        if (
            used
            >= int(
                cfg[
                    "maxDoubleScorePerLevel"
                ]
            )
        ):
            return Response(
                {
                    "detail": (
                        "Double Score already "
                        "claimed for this level."
                    )
                },
                status=409,
            )

        amount = (
            int(session.score)
            * (
                int(
                    cfg[
                        "doubleScoreMultiplier"
                    ]
                )
                - 1
            )
        )

        reward_type = "DOUBLE_SCORE"

        extra = {
            "score_bonus": amount
        }

        profile.total_score += (
            amount
        )

        profile.save(
            update_fields=[
                "total_score",
                "updated_at",
            ]
        )

    # ========================================================
    # UNKNOWN
    # ========================================================

    else:
        return Response(
            {
                "detail": (
                    "Unsupported reward placement."
                )
            },
            status=400,
        )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    reward_metadata = {
        **metadata,
        "provider_verified": True,
        "provider_reference": (
            opportunity.provider_reference
        ),
    }

    if session:
        reward_metadata[
            "sessionId"
        ] = str(
            session.id
        )

    # --------------------------------------------------------
    # REWARD TRANSACTION
    # --------------------------------------------------------

    reward = (
        RewardTransaction.objects.create(
            user=request.user,
            placement=placement,
            reward_type=reward_type,
            amount=amount,
            event_id=event_id,
            metadata=reward_metadata,
        )
    )

    lifecycle = list((opportunity.metadata or {}).get("adLifecycle", []))
    if not any(item.get("state") == "GRANTED" for item in lifecycle):
        lifecycle.append({"state": "GRANTED", "at": now.isoformat()})
    opportunity.status = "GRANTED"
    opportunity.metadata = {**(opportunity.metadata or {}), "adLifecycle": lifecycle}
    opportunity.save(update_fields=["status", "metadata"])

    profile.last_reward_claim_at = now

    profile.save(
        update_fields=[
            "last_reward_claim_at",
            "updated_at",
        ]
    )

    # --------------------------------------------------------
    # ONLY ACTUAL COIN REWARDS MODIFY WALLET
    #
    # EXTRA_MOVES / HINT / BOOSTER / REVIVE /
    # DOUBLE_SCORE do not accidentally become coins.
    # --------------------------------------------------------

    coin_reward_placements = {
        "DAILY_REWARD",
        "DOUBLE_COINS",
    }

    if (
        placement
        in coin_reward_placements
        and amount
    ):
        balance = grant_coins(
            request.user,
            amount,
            "AD_REWARD",
            f"ad:{event_id}",
        )

    else:
        balance = profile.coins

    return Response({
        "granted": True,
        "status": "GRANTED",
        "amount": amount,
        "balance": balance,
        "transactionId": reward.id,
        **extra,
    })


# ============================================================
# WALLET
# ============================================================

@api_view(["GET"])
@auth_required
def wallet(request):
    profile = (
        PlayerProfile.objects
        .get(
            user=request.user
        )
    )

    return Response({
        "coins": profile.coins,

        "transactions": list(
            WalletTransaction.objects
            .filter(
                user=request.user
            )
            .order_by(
                "-created_at"
            )[:100]
            .values(
                "amount",
                "balance_after",
                "kind",
                "reason",
                "reference",
                "created_at",
            )
        ),

        # Unified reward ledger: verified ad rewards and deterministic
        # level-completion rewards are both exposed to the wallet UI/API.
        "rewards": list(
            RewardTransaction.objects
            .filter(
                user=request.user
            )
            .order_by(
                "-created_at",
                "-id",
            )[:100]
            .values(
                "placement",
                "reward_type",
                "amount",
                "status",
                "event_id",
                "created_at",
            )
        ),
    })


# ============================================================
# LEADERBOARD
# ============================================================

@api_view(["GET"])
@auth_required
def leaderboard(request):
    return Response({
        "leaderboard": [
            {
                "username": (
                    profile.user.username
                ),
                "score": (
                    profile.total_score
                ),
                "coins": (
                    profile.coins
                ),
            }
            for profile in (
                PlayerProfile.objects
                .select_related("user")
                .order_by(
                    "-total_score"
                )[:25]
            )
        ]
    })


# ============================================================
# ACHIEVEMENTS
# ============================================================

@api_view(["GET"])
@auth_required
def achievements(request):
    unlocked = set(
        UserAchievement.objects
        .filter(
            user=request.user
        )
        .values_list(
            "achievement_id",
            flat=True,
        )
    )

    return Response({
        "achievements": [
            {
                "code": achievement.code,
                "title": achievement.title,
                "description": (
                    achievement.description
                ),
                "icon": achievement.icon,
                "unlocked": (
                    achievement.id
                    in unlocked
                ),
            }
            for achievement
            in Achievement.objects.all()
        ]
    })


# ============================================================
# ECONOMY CONFIG
# ============================================================

@api_view(["GET"])
@auth_required
def economy_config(request):
    return Response({
        "config": economy()
    })


# ============================================================
# ADMIN ECONOMY
# ============================================================

@api_view(["GET"])
@auth_required
def admin_economy(request):
    if not request.user.is_staff:
        return Response(
            {
                "detail": (
                    "Admin access required."
                )
            },
            status=403,
        )

    since = (
        timezone.now()
        - timedelta(days=1)
    )

    return Response({
        "adOpportunities": (
            AdOpportunity.objects
            .filter(
                created_at__gte=since
            )
            .count()
        ),

        "completedAds": (
            AdOpportunity.objects
            .filter(
                created_at__gte=since,
                status__in=("VERIFIED", "GRANTED"),
            )
            .count()
        ),

        "coinsGranted": (
            WalletTransaction.objects
            .filter(
                created_at__gte=since,
                amount__gt=0,
            )
            .aggregate(
                v=Sum("amount")
            )["v"]
            or 0
        ),

        "rewardedAds": (
            RewardTransaction.objects
            .filter(
                created_at__gte=since
            )
            .count()
        ),

        "users": (
            PlayerProfile.objects.count()
        ),
    })


# ============================================================
# API KEYS
# ============================================================

@api_view(["GET", "POST"])
@auth_required
def api_keys(request):
    if request.method == "GET":
        return Response({
            "keys": list(
                ApiKey.objects
                .filter(
                    user=request.user,
                    revoked_at__isnull=True,
                )
                .values(
                    "id",
                    "name",
                    "key_prefix",
                    "created_at",
                    "last_used_at",
                )
            )
        })

    name = str(
        request.data.get(
            "name",
            "API key",
        )
    ).strip()[:80]

    name = (
        name
        or "API key"
    )

    # --------------------------------------------------------
    # LIMIT ACTIVE KEYS
    # --------------------------------------------------------

    active_key_count = (
        ApiKey.objects
        .filter(
            user=request.user,
            revoked_at__isnull=True,
        )
        .count()
    )

    if active_key_count >= 10:
        return Response(
            {
                "detail": (
                    "Maximum of 10 active "
                    "API keys allowed."
                )
            },
            status=409,
        )

    raw = (
        "aw_"
        + secrets.token_urlsafe(32)
    )

    ApiKey.objects.create(
        user=request.user,
        name=name,
        key_prefix=raw[:12],
        key_hash=digest(raw),
    )

    return Response(
        {
            "name": name,
            "key": raw,
        },
        status=201,
    )


# ============================================================
# REVOKE API KEY
# ============================================================

@api_view(["POST"])
@auth_required
def revoke_api_key(
    request,
    key_id,
):
    updated = (
        ApiKey.objects
        .filter(
            id=key_id,
            user=request.user,
            revoked_at__isnull=True,
        )
        .update(
            revoked_at=timezone.now()
        )
    )

    return Response({
        "revoked": bool(updated)
    })
