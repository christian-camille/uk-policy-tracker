from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jwt import InvalidTokenError

from app.auth import _decode_supabase_access_token
from app.config import Settings


def make_settings() -> Settings:
    return Settings(
        SUPABASE_JWKS_URL="https://example.supabase.co/auth/v1/.well-known/jwks.json",
        SUPABASE_JWT_ISSUER="https://example.supabase.co/auth/v1",
        SUPABASE_JWT_AUDIENCE="authenticated",
    )


def test_decode_supabase_access_token_uses_signing_key_algorithm():
    settings = make_settings()
    signing_key = MagicMock()
    signing_key.key = object()
    signing_key.algorithm_name = "ES256"

    jwk_client = MagicMock()
    jwk_client.get_signing_key_from_jwt.return_value = signing_key

    with patch("app.auth._get_jwk_client", return_value=jwk_client), patch(
        "app.auth.jwt.decode", return_value={"sub": "user-123"}
    ) as decode_mock:
        claims = _decode_supabase_access_token("token-value", settings)

    assert claims == {"sub": "user-123"}
    decode_mock.assert_called_once_with(
        "token-value",
        signing_key.key,
        algorithms=["ES256"],
        audience="authenticated",
        issuer="https://example.supabase.co/auth/v1",
    )


def test_decode_supabase_access_token_falls_back_to_token_header_algorithm():
    settings = make_settings()
    signing_key = MagicMock()
    signing_key.key = object()
    signing_key.algorithm_name = None

    jwk_client = MagicMock()
    jwk_client.get_signing_key_from_jwt.return_value = signing_key

    with patch("app.auth._get_jwk_client", return_value=jwk_client), patch(
        "app.auth.jwt.get_unverified_header", return_value={"alg": "RS256"}
    ), patch("app.auth.jwt.decode", return_value={"sub": "user-123"}) as decode_mock:
        claims = _decode_supabase_access_token("token-value", settings)

    assert claims == {"sub": "user-123"}
    decode_mock.assert_called_once_with(
        "token-value",
        signing_key.key,
        algorithms=["RS256"],
        audience="authenticated",
        issuer="https://example.supabase.co/auth/v1",
    )


def test_decode_supabase_access_token_returns_401_for_invalid_token():
    settings = make_settings()
    signing_key = MagicMock()
    signing_key.key = object()
    signing_key.algorithm_name = "RS256"

    jwk_client = MagicMock()
    jwk_client.get_signing_key_from_jwt.return_value = signing_key

    with patch("app.auth._get_jwk_client", return_value=jwk_client), patch(
        "app.auth.jwt.decode", side_effect=InvalidTokenError("bad token")
    ):
        with pytest.raises(HTTPException) as exc_info:
            _decode_supabase_access_token("token-value", settings)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication token"