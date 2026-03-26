"""Tests for api/storage.py — Supabase Storage upload_ifc."""
from __future__ import annotations

import os
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest


class TestUploadIfc:
    def test_returns_none_when_no_env(self, tmp_path):
        """Without SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY, returns None."""
        import api.storage as mod
        mod._client = None

        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}, clear=False):
            result = mod.upload_ifc(str(tmp_path / "test.ifc"), "job123")
        assert result is None

    def test_returns_none_when_file_missing(self, tmp_path):
        """Returns None when the local file does not exist."""
        import api.storage as mod
        mod._client = None

        mock_client = MagicMock()
        mod._client = mock_client
        try:
            result = mod.upload_ifc("/nonexistent/path.ifc", "job456")
            assert result is None
        finally:
            mod._client = None

    def test_uploads_and_returns_signed_url(self, tmp_path):
        """When Supabase is configured and file exists, uploads and returns URL."""
        import api.storage as mod
        mod._client = None

        ifc_file = tmp_path / "test.ifc"
        ifc_file.write_text("ISO-10303-21; ...")

        mock_bucket = MagicMock()
        mock_bucket.create_signed_url.return_value = {
            "signedURL": "https://x.supabase.co/storage/v1/object/sign/ifc-files/jobs/job789.ifc?token=abc"
        }

        mock_client = MagicMock()
        mock_client.storage.from_.return_value = mock_bucket

        # Inject the mock client directly
        mod._client = mock_client
        try:
            result = mod.upload_ifc(str(ifc_file), "job789")
            assert result is not None
            assert "sign" in result
            mock_bucket.upload.assert_called_once()
            mock_bucket.create_signed_url.assert_called_once_with("jobs/job789.ifc", expires_in=3600)
        finally:
            mod._client = None
