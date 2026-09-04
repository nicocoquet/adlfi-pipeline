from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel


GITHUB_API = "https://api.github.com"
GITHUB_ACCEPT = "application/vnd.github+json"
FILENAME_PATTERN = re.compile(r"^[^/\\\x00-\x1f]+\.xml$", re.IGNORECASE)
MAX_FILE_SIZE = 25 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    github_client_id: str
    github_client_secret: str
    session_secret: str
    repository: str = "nicocoquet/adlfi-pipeline"
    pages_url: str = "https://nicocoquet.github.io/adlfi-pipeline/"
    allowed_users: tuple[str, ...] = ("nicocoquet", "gaelle-david")

    @classmethod
    def from_environment(cls) -> "Settings":
        values = {
            "github_client_id": os.getenv("GITHUB_CLIENT_ID", ""),
            "github_client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
            "session_secret": os.getenv("SESSION_SECRET", ""),
        }
        if not values["session_secret"]:
            raise RuntimeError("Variable d’environnement manquante : SESSION_SECRET")
        users = tuple(
            item.strip()
            for item in os.getenv("ALLOWED_USERS", "nicocoquet,gaelle-david").split(",")
            if item.strip()
        )
        return cls(
            **values,
            repository=os.getenv("GITHUB_REPOSITORY", "nicocoquet/adlfi-pipeline"),
            pages_url=os.getenv("PAGES_URL", "https://nicocoquet.github.io/adlfi-pipeline/"),
            allowed_users=users,
        )


class UploadRequest(BaseModel):
    filename: str
    content: str


class SessionStore:
    """Sessions opaques et temporaires ; aucun jeton GitHub n’atteint le navigateur."""

    def __init__(self, lifetime: int = 8 * 60 * 60) -> None:
        self.lifetime = lifetime
        self._sessions: dict[str, dict[str, Any]] = {}

    def create(self, login: str, github_token: str) -> str:
        self.purge()
        key = secrets.token_urlsafe(32)
        self._sessions[key] = {
            "login": login,
            "github_token": github_token,
            "expires": int(time.time()) + self.lifetime,
        }
        return key

    def get(self, key: str) -> dict[str, Any] | None:
        session = self._sessions.get(key)
        if not session or session["expires"] <= time.time():
            self._sessions.pop(key, None)
            return None
        return session

    def delete(self, key: str) -> None:
        self._sessions.pop(key, None)

    def purge(self) -> None:
        now = time.time()
        for key in [key for key, value in self._sessions.items() if value["expires"] <= now]:
            self._sessions.pop(key, None)


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    body = _urlsafe_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _urlsafe_encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_payload(value: str, secret: str) -> dict[str, Any]:
    try:
        body, provided = value.rsplit(".", 1)
        expected = _urlsafe_encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(provided, expected):
            raise ValueError
        payload = json.loads(_urlsafe_decode(body))
        if int(payload["exp"]) <= time.time():
            raise ValueError
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Jeton invalide ou expiré.") from error


def safe_filename(filename: str) -> str:
    name = PurePath(filename).name
    if name != filename or not FILENAME_PATTERN.fullmatch(name):
        raise HTTPException(status_code=400, detail="Nom de fichier XML invalide.")
    return name


def allowed_return_url(candidate: str, pages_url: str) -> str:
    wanted = urlparse(candidate)
    allowed = urlparse(pages_url)
    if (wanted.scheme, wanted.netloc, wanted.path) != (allowed.scheme, allowed.netloc, allowed.path):
        return pages_url
    return candidate.split("#", 1)[0]


async def github_request(
    method: str,
    path: str,
    token: str | None = None,
    **kwargs: Any,
) -> Any:
    headers = {"Accept": GITHUB_ACCEPT, "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(method, f"{GITHUB_API}{path}", headers=headers, **kwargs)
    if response.status_code >= 400:
        message = response.json().get("message", "Erreur GitHub")
        if response.status_code == 422 and "sha" in message.lower():
            message = "Un fichier portant ce nom existe déjà dans le dépôt : renommez votre fichier."
        raise HTTPException(status_code=response.status_code, detail=message)
    return response.json() if response.content else None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    sessions = SessionStore()
    app = FastAPI(title="Interface d’indexation Pactols", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"{urlparse(settings.pages_url).scheme}://{urlparse(settings.pages_url).netloc}"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def current_session(authorization: str = Header(default="")) -> tuple[str, dict[str, Any]]:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Connexion GitHub requise.")
        key = authorization.removeprefix("Bearer ").strip()
        session = sessions.get(key)
        if not session:
            raise HTTPException(status_code=401, detail="Session expirée. Reconnectez-vous avec GitHub.")
        return key, session

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/auth/github")
    async def login(returnTo: str = Query(default="")) -> RedirectResponse:  # noqa: N803
        if not settings.github_client_id or not settings.github_client_secret:
            raise HTTPException(status_code=503, detail="La connexion GitHub n’est pas encore configurée.")
        destination = allowed_return_url(returnTo or settings.pages_url, settings.pages_url)
        state = sign_payload({"returnTo": destination, "exp": int(time.time()) + 600}, settings.session_secret)
        query = urlencode({"client_id": settings.github_client_id, "state": state})
        return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")

    @app.get("/auth/callback")
    async def callback(code: str, state: str) -> RedirectResponse:
        if not settings.github_client_id or not settings.github_client_secret:
            raise HTTPException(status_code=503, detail="La connexion GitHub n’est pas encore configurée.")
        state_payload = verify_payload(state, settings.session_secret)
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
            )
        token_data = token_response.json()
        github_token = token_data.get("access_token")
        if not github_token:
            raise HTTPException(status_code=401, detail="GitHub n’a pas autorisé la connexion.")
        user = await github_request("GET", "/user", github_token)
        login_name = user["login"]
        if login_name not in settings.allowed_users:
            raise HTTPException(status_code=403, detail="Ce compte GitHub n’est pas autorisé.")
        session_key = sessions.create(login_name, github_token)
        destination = state_payload["returnTo"]
        return RedirectResponse(f"{destination}#session={session_key}")

    @app.get("/auth/session")
    async def session(data: tuple[str, dict[str, Any]] = Depends(current_session)) -> dict[str, Any]:
        return {"user": {"login": data[1]["login"]}}

    @app.post("/auth/logout", status_code=204)
    async def logout(data: tuple[str, dict[str, Any]] = Depends(current_session)) -> None:
        sessions.delete(data[0])

    @app.post("/api/jobs")
    async def create_job(
        upload: UploadRequest,
        data: tuple[str, dict[str, Any]] = Depends(current_session),
    ) -> dict[str, str]:
        filename = safe_filename(upload.filename)
        try:
            content = base64.b64decode(upload.content, validate=True)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Contenu de fichier invalide.") from error
        if not content or len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Le fichier doit peser entre 1 octet et 25 Mo.")
        session_data = data[1]
        owner, repo = settings.repository.split("/", 1)
        result = await github_request(
            "PUT",
            f"/repos/{owner}/{repo}/contents/input/{filename}",
            session_data["github_token"],
            json={
                "message": f"input: déposer {filename} via l’interface web",
                "content": upload.content,
                "branch": "main",
            },
        )
        job = {
            "filename": filename,
            "sha": result["commit"]["sha"],
            "login": session_data["login"],
            "exp": int(time.time()) + 24 * 60 * 60,
        }
        return {"id": sign_payload(job, settings.session_secret)}

    @app.get("/api/jobs/{job_id}")
    async def job_status(
        job_id: str,
        data: tuple[str, dict[str, Any]] = Depends(current_session),
    ) -> dict[str, Any]:
        job = verify_payload(job_id, settings.session_secret)
        if job["login"] != data[1]["login"]:
            raise HTTPException(status_code=403, detail="Ce traitement appartient à un autre utilisateur.")
        owner, repo = settings.repository.split("/", 1)
        runs = await github_request(
            "GET",
            f"/repos/{owner}/{repo}/actions/workflows/enrich-pactols.yml/runs",
            data[1]["github_token"],
            params={"head_sha": job["sha"], "per_page": 1},
        )
        if not runs["workflow_runs"]:
            return {"status": "queued", "sourceName": job["filename"]}
        run = runs["workflow_runs"][0]
        if run["status"] != "completed":
            return {"status": "processing", "sourceName": job["filename"]}
        if run["conclusion"] != "success":
            return {
                "status": "failed",
                "sourceName": job["filename"],
                "message": "Le workflow GitHub a échoué. Consultez son journal pour identifier la cause.",
                "workflowUrl": run["html_url"],
            }
        base = filename_without_xml(job["filename"])
        paths = {
            "xml": f"generated/xml/{base}_enriched.xml",
            "txt": f"generated/reports/{base}_report.txt",
            "csv": f"generated/reports/{base}_report.csv",
        }
        files: dict[str, str] = {}
        try:
            for kind, path in paths.items():
                item = await github_request(
                    "GET",
                    f"/repos/{owner}/{repo}/contents/{path}",
                    data[1]["github_token"],
                    params={"ref": "main"},
                )
                files[kind] = item["download_url"]
        except HTTPException as error:
            if error.status_code != 404:
                raise
            return {
                "status": "failed",
                "sourceName": job["filename"],
                "message": "Le workflow s’est terminé sans produire les trois fichiers attendus.",
                "workflowUrl": run["html_url"],
            }
        return {"status": "completed", "sourceName": job["filename"], "files": files}

    return app


def filename_without_xml(filename: str) -> str:
    return filename[:-4] if filename.lower().endswith(".xml") else filename
