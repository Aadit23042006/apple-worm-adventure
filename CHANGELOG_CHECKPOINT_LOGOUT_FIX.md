# Change log (this session)
- backend/core/views.py — logout: per-device refresh revocation (backward compatible).
- frontend/src/App.tsx — signout: send refresh_token, skipRefresh.
- backend/core/tests_multi_device_logout.py — NEW, 6 regression tests.
- EVIDENCE/FINAL_REGRESSION/** — NEW report, e2e script, screenshots.
- CHECKPOINT_AUTH_FIX.md — addendum below.

- frontend/src/App.tsx — session restore no longer clears stored access/refresh tokens for transient API/network failures; definitive auth expiry remains event-driven.
- SESSION_RESTORE_TRANSIENT_ERROR_FIX.md — documents the additional targeted correction and its verification limits.
- EVIDENCE/FINAL_REGRESSION/CHATGPT_REVIEW_SESSION.md — records review scope, checks run, and outstanding evidence gaps.
