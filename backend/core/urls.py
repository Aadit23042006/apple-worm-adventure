from django.urls import path

from .views import (
    # ------------------------------------------------------------
    # HEALTH
    # ------------------------------------------------------------
    health,

    # ------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------
    register,
    login,
    refresh,
    logout,
    me,

    # ------------------------------------------------------------
    # EMAIL VERIFICATION
    # ------------------------------------------------------------
    verify_email,
    resend_verification,

    # ------------------------------------------------------------
    # PASSWORD RESET
    # ------------------------------------------------------------
    password_reset_request,
    password_reset_confirm,

    # ------------------------------------------------------------
    # LEVELS / PROGRESSION
    # ------------------------------------------------------------
    levels,

    # ------------------------------------------------------------
    # GAME SESSIONS
    # ------------------------------------------------------------
    start_game,
    active_game,
    checkpoint,
    undo_game,
    complete_game,

    # ------------------------------------------------------------
    # ECONOMY / REWARDED ADS
    # ------------------------------------------------------------
    ad_opportunity,
    request_ad,
    ad_opportunity_status,
    ad_provider_callback,
    provider_free_demo_complete,
    claim_reward,
    wallet,
    economy_config,

    # ------------------------------------------------------------
    # LEADERBOARD
    # ------------------------------------------------------------
    leaderboard,

    # ------------------------------------------------------------
    # ACHIEVEMENTS
    # ------------------------------------------------------------
    achievements,

    # ------------------------------------------------------------
    # ADMIN / ECONOMY
    # ------------------------------------------------------------
    admin_economy,

    # ------------------------------------------------------------
    # API KEY MANAGEMENT
    # ------------------------------------------------------------
    api_keys,
    revoke_api_key,
)


urlpatterns = [

    # ============================================================
    # HEALTH
    # ============================================================

    path(
        "health/",
        health,
        name="health",
    ),


    # ============================================================
    # AUTHENTICATION
    # ============================================================

    # Register a new account
    path(
        "auth/register/",
        register,
        name="auth-register",
    ),

    # Login
    path(
        "auth/login/",
        login,
        name="auth-login",
    ),

    # Refresh access token
    path(
        "auth/refresh/",
        refresh,
        name="auth-refresh",
    ),

    # Logout / revoke refresh session
    path(
        "auth/logout/",
        logout,
        name="auth-logout",
    ),

    # Current authenticated user
    path(
        "auth/me/",
        me,
        name="auth-me",
    ),


    # ============================================================
    # EMAIL VERIFICATION
    # ============================================================

    # Verify email using token
    #
    # POST:
    # {
    #     "token": "..."
    # }
    path(
        "auth/verify-email/",
        verify_email,
        name="auth-verify-email",
    ),

    # Resend verification email
    #
    # POST:
    # {
    #     "email": "user@example.com"
    # }
    #
    # Response is intentionally generic so that the endpoint
    # does not reveal whether an email address exists.
    path(
        "auth/resend-verification/",
        resend_verification,
        name="auth-resend-verification",
    ),


    # ============================================================
    # PASSWORD RESET
    # ============================================================

    # Request password reset email
    #
    # POST:
    # {
    #     "email": "user@example.com"
    # }
    path(
        "auth/password-reset/request/",
        password_reset_request,
        name="password-reset-request",
    ),

    # Confirm password reset
    #
    # POST:
    # {
    #     "token": "...",
    #     "password": "..."
    # }
    path(
        "auth/password-reset/confirm/",
        password_reset_confirm,
        name="password-reset-confirm",
    ),


    # ============================================================
    # LEVELS / PROGRESSION
    # ============================================================

    path(
        "levels/",
        levels,
        name="levels",
    ),


    # ============================================================
    # GAME SESSIONS
    # ============================================================

    # Start a new game session
    path(
        "games/start/",
        start_game,
        name="games-start",
    ),

    # Get current active game session
    path(
        "games/active/",
        active_game,
        name="games-active",
    ),

    # Save/checkpoint game state
    path(
        "games/<uuid:session_id>/checkpoint/",
        checkpoint,
        name="games-checkpoint",
    ),

    # Undo the latest move
    path(
        "games/<uuid:session_id>/undo/",
        undo_game,
        name="games-undo",
    ),

    # Complete game session
    path(
        "games/<uuid:session_id>/complete/",
        complete_game,
        name="games-complete",
    ),


    # ============================================================
    # ECONOMY / REWARDED ADS
    # ============================================================

    # Create a rewarded-ad opportunity
    path(
        "economy/ad-opportunity/",
        ad_opportunity,
        name="economy-ad-opportunity",
    ),

    # Request a real provider ad session; cannot complete an ad from client input.
    path(
        "economy/ad-opportunity/<str:event_id>/request/",
        request_ad,
        name="economy-ad-request",
    ),
    path(
        "economy/ad-opportunity/<str:event_id>/status/",
        ad_opportunity_status,
        name="economy-ad-status",
    ),
    path(
        "economy/ad-opportunity/<str:event_id>/provider-free-complete/",
        provider_free_demo_complete,
        name="provider-free-demo-complete",
    ),

    # Provider callback / verification webhook
    #
    # This endpoint is authenticated using the configured
    # provider webhook secret/signature rather than a player JWT.
    path(
        "economy/ad-provider-callback/",
        ad_provider_callback,
        name="economy-ad-provider-callback",
    ),

    # Claim a verified reward
    path(
        "economy/claim-reward/",
        claim_reward,
        name="economy-claim-reward",
    ),

    # Current player wallet
    path(
        "economy/wallet/",
        wallet,
        name="economy-wallet",
    ),

    # Public/economy configuration
    path(
        "economy/config/",
        economy_config,
        name="economy-config",
    ),


    # ============================================================
    # LEADERBOARD
    # ============================================================

    path(
        "leaderboard/",
        leaderboard,
        name="leaderboard",
    ),


    # ============================================================
    # ACHIEVEMENTS
    # ============================================================

    path(
        "achievements/",
        achievements,
        name="achievements",
    ),


    # ============================================================
    # ADMIN / ECONOMY
    # ============================================================

    path(
        "admin/economy/",
        admin_economy,
        name="admin-economy",
    ),


    # ============================================================
    # API KEY MANAGEMENT
    # ============================================================

    # GET:
    #   List active API keys
    #
    # POST:
    #   Create a new API key
    path(
        "api-keys/",
        api_keys,
        name="api-keys",
    ),

    # POST:
    #   Revoke an API key
    path(
        "api-keys/<int:key_id>/revoke/",
        revoke_api_key,
        name="api-key-revoke",
    ),
]