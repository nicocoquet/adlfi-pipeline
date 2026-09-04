import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from service.app import (
    Settings,
    allowed_return_url,
    create_app,
    filename_without_xml,
    safe_filename,
    sign_payload,
    verify_payload,
)


def test_signed_payload_round_trip():
    token = sign_payload({"login": "nicocoquet", "exp": int(time.time()) + 60}, "secret")
    assert verify_payload(token, "secret")["login"] == "nicocoquet"


def test_signed_payload_rejects_modification():
    token = sign_payload({"exp": int(time.time()) + 60}, "secret")
    with pytest.raises(HTTPException):
        verify_payload(f"{token}x", "secret")


@pytest.mark.parametrize("filename", ["../notice.xml", "folder/notice.xml", "notice.txt", "notice.xml.exe"])
def test_safe_filename_rejects_unexpected_names(filename):
    with pytest.raises(HTTPException):
        safe_filename(filename)


def test_safe_filename_accepts_xml():
    assert safe_filename("AdlFI_86.xml") == "AdlFI_86.xml"


def test_return_url_is_limited_to_pages_url():
    pages = "https://nicocoquet.github.io/adlfi-pipeline/"
    assert allowed_return_url("https://attacker.example/", pages) == pages
    assert allowed_return_url(f"{pages}?source=github", pages) == f"{pages}?source=github"


def test_output_basename_is_case_insensitive():
    assert filename_without_xml("notice.XML") == "notice"


def test_health_endpoint():
    settings = Settings("client", "secret", "session-secret")
    client = TestClient(create_app(settings))
    assert client.get("/health").json() == {"status": "ok"}


def test_service_starts_before_github_credentials_are_configured():
    settings = Settings("", "", "session-secret")
    client = TestClient(create_app(settings))
    response = client.get("/auth/github")
    assert response.status_code == 503
    assert response.json()["detail"] == "La connexion GitHub n’est pas encore configurée."
