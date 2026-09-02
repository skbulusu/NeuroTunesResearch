"""
NeuroTunes Research API — official Python SDK
=============================================

A thin, dependency-light client for the versioned ``/api/v1`` NeuroTunes
Research API. Designed for ML researchers and music therapists who want to
generate physiologically-informed therapeutic music, run IRB/consent-gated
studies, submit RLHF feedback, and export de-identified training data from
scripts or notebooks.

Only dependency: ``requests`` (``pip install requests``).

Quick start
-----------
>>> from neurotunes_sdk import NeuroTunesClient
>>> nt = NeuroTunesClient("https://your-host", api_key="nt_live_...")
>>> nt.health()
{'api_version': 'v1', 'status': 'ok', ...}
>>> result = nt.generate(age=34, therapy_goal="relaxation", stress_level=7)
>>> for track in result["tracks"]:
...     print(track["track_id"], track["audio_url"])

IRB / consent-gated generation (patent Claim 3)
-----------------------------------------------
>>> result = nt.generate_irb(
...     patient={"age": 34, "therapy_goal": "sleep", "stress_level": 6},
...     consent_verified=True,
...     consent_reference="IRB-2026-0142",
... )

The server rejects consent-gated generation with an :class:`NeuroTunesError`
(HTTP 403) unless ``consent_verified`` is true.
"""

from __future__ import annotations

import io
from typing import Any, Dict, Optional

try:
    import requests
except ImportError as exc:  # pragma: no cover - clear guidance if missing
    raise ImportError(
        "The NeuroTunes SDK requires the 'requests' package. "
        "Install it with: pip install requests"
    ) from exc

__all__ = ["NeuroTunesClient", "NeuroTunesError"]
__version__ = "1.0.0"


class NeuroTunesError(RuntimeError):
    """Raised when the API returns a non-success response.

    Attributes:
        status_code: HTTP status code returned by the API.
        error: Short machine-readable error code (e.g. ``"unauthorized"``).
        message: Human-readable description.
        payload: Full decoded JSON body (when available).
    """

    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        if isinstance(payload, dict):
            self.error = payload.get("error", "error")
            self.message = payload.get("message", "")
        else:
            self.error = "error"
            self.message = str(payload)
        super().__init__(f"[{status_code}] {self.error}: {self.message}")


class NeuroTunesClient:
    """Client for the NeuroTunes Research API (``/api/v1``).

    Args:
        base_url: Root URL of the NeuroTunes deployment, e.g.
            ``"https://neurotunes.example.org"``. A trailing ``/api/v1`` is
            appended automatically; do not include it yourself.
        api_key: Your ``nt_live_...`` API key. Required for all data
            endpoints; optional for :meth:`health` / :meth:`version`.
        timeout: Per-request timeout in seconds (default 60).
        session: Optional pre-configured ``requests.Session`` (advanced).
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        session: Optional["requests.Session"] = None,
    ):
        base_url = base_url.rstrip("/")
        if base_url.endswith("/api/v1"):
            base_url = base_url[: -len("/api/v1")]
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.api_key = api_key
        self.timeout = timeout
        self._session = session or requests.Session()

    # ---- internal helpers -------------------------------------------------
    def _headers(self, auth: bool = True) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if auth:
            if not self.api_key:
                raise NeuroTunesError(
                    401, {"error": "unauthorized", "message": "No API key configured."}
                )
            headers["X-API-Key"] = self.api_key
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        stream: bool = False,
    ):
        url = f"{self.api_base}{path}"
        headers = self._headers(auth=auth)
        if json is not None:
            headers["Content-Type"] = "application/json"
        resp = self._session.request(
            method,
            url,
            headers=headers,
            json=json,
            params=params,
            timeout=self.timeout,
            stream=stream,
        )
        if stream:
            if resp.status_code >= 400:
                raise NeuroTunesError(resp.status_code, _safe_json(resp))
            return resp
        body = _safe_json(resp)
        if resp.status_code >= 400:
            raise NeuroTunesError(resp.status_code, body)
        return body

    # ---- status (public) --------------------------------------------------
    def version(self) -> Dict[str, Any]:
        """Return API name and version (no key required)."""
        return self._request("GET", "/version", auth=False)

    def health(self) -> Dict[str, Any]:
        """Return health of the API, ML server and database (no key required)."""
        return self._request("GET", "/health", auth=False)

    def me(self) -> Dict[str, Any]:
        """Describe the calling API key: id, name, scopes, rate limit."""
        return self._request("GET", "/me")

    # ---- generation -------------------------------------------------------
    def generate(self, **patient_data: Any) -> Dict[str, Any]:
        """Generate therapeutic music (scope: ``generate``).

        Pass patient inputs as keyword arguments, e.g. ``age``,
        ``therapy_goal``, ``stress_level``, ``sleep_quality``,
        ``energy_levels``, ``mood``, ``diagnosis``, ``gender``.
        """
        return self._request("POST", "/generate", json=patient_data)

    def generate_irb(
        self,
        patient: Dict[str, Any],
        consent_verified: bool,
        consent_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate under verified IRB / informed consent (patent Claim 3).

        Requires the ``generate`` scope. The server rejects the request with a
        403 :class:`NeuroTunesError` unless ``consent_verified`` is ``True``.

        Args:
            patient: Patient input dict (same fields as :meth:`generate`).
            consent_verified: Must be ``True`` for music to be generated.
            consent_reference: Optional IRB / study identifier to record.
        """
        payload = dict(patient)
        consent: Dict[str, Any] = {"consent_verified": bool(consent_verified)}
        if consent_reference is not None:
            consent["consent_reference"] = consent_reference
        payload["consent"] = consent
        return self._request("POST", "/generate_irb", json=payload)

    # ---- feedback ---------------------------------------------------------
    def submit_feedback(self, generation_log_id: int, **ratings: Any) -> Dict[str, Any]:
        """Submit RLHF feedback for a generated track (scope: ``feedback``).

        Args:
            generation_log_id: The ``log_id`` of the generation being rated.
            **ratings: e.g. ``overall_rating``, ``effectiveness_rating``,
                ``enjoyment_rating`` (1-5), ``reported_feeling`` (str).
        """
        payload = {"generation_log_id": generation_log_id, **ratings}
        return self._request("POST", "/feedback", json=payload)

    # ---- sessions ---------------------------------------------------------
    def list_sessions(self, limit: int = 100) -> Dict[str, Any]:
        """List persisted therapy sessions (scope: ``sessions``)."""
        return self._request("GET", "/sessions", params={"limit": limit})

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Fetch one session with its generations (scope: ``sessions``)."""
        return self._request("GET", f"/sessions/{session_id}")

    # ---- research ---------------------------------------------------------
    def research_training_data(self, limit: int = 1000) -> Dict[str, Any]:
        """Export aggregate, de-identified RLHF training data (scope: ``read``)."""
        return self._request("GET", "/research/training-data", params={"limit": limit})

    def download(self, filename: str) -> bytes:
        """Download a generated MIDI/audio file as bytes (scope: ``read``)."""
        resp = self._request("GET", f"/download/{filename}", stream=True)
        buf = io.BytesIO()
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                buf.write(chunk)
        return buf.getvalue()

    def download_to(self, filename: str, dest_path: str) -> str:
        """Download a generated file and write it to ``dest_path``. Returns the path."""
        data = self.download(filename)
        with open(dest_path, "wb") as fh:
            fh.write(data)
        return dest_path


def _safe_json(resp: "requests.Response") -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"error": "non_json_response", "message": resp.text[:500]}


if __name__ == "__main__":  # pragma: no cover - simple smoke/demo
    import argparse

    parser = argparse.ArgumentParser(description="NeuroTunes SDK quick demo")
    parser.add_argument("base_url", help="e.g. https://neurotunes.example.org")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--goal", default="relaxation")
    args = parser.parse_args()

    client = NeuroTunesClient(args.base_url, api_key=args.api_key)
    print("version:", client.version())
    print("health :", client.health())
    if args.api_key:
        print("me     :", client.me())
        result = client.generate(therapy_goal=args.goal, stress_level=7, age=34)
        print("tracks :", [t.get("track_id") for t in result.get("tracks", [])])
