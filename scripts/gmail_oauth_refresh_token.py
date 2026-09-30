#!/usr/bin/env python3
"""Obtain a Google OAuth refresh token for Gmail readonly access.

Run locally (browser required). Does NOT print or commit secrets into the repo —
you paste the resulting values into backend/.env yourself.

Prerequisites:
  1. Google Cloud Console → APIs & Services → enable Gmail API
  2. Create OAuth client (Desktop app recommended)
  3. Download client JSON or copy Client ID + Client Secret

Usage:
  python scripts/gmail_oauth_refresh_token.py \\
    --client-id YOUR_CLIENT_ID \\
    --client-secret YOUR_CLIENT_SECRET

  # Or with a downloaded client secrets JSON:
  python scripts/gmail_oauth_refresh_token.py --client-secrets ./client_secret.json

Then set in backend/.env:
  GMAIL_MODE=oauth
  GOOGLE_CLIENT_ID=...
  GOOGLE_CLIENT_SECRET=...
  GOOGLE_REFRESH_TOKEN=...

Scope: https://www.googleapis.com/auth/gmail.readonly
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
REDIRECT_URI = "http://127.0.0.1:8765/oauth2callback"


def load_from_secrets_file(path: str) -> tuple[str, str]:
    data = json.loads(open(path, encoding="utf-8").read())
    block = data.get("installed") or data.get("web") or data
    return block["client_id"], block["client_secret"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret")
    parser.add_argument("--client-secrets", help="Path to Google OAuth client JSON")
    args = parser.parse_args()

    if args.client_secrets:
        client_id, client_secret = load_from_secrets_file(args.client_secrets)
    else:
        client_id = args.client_id
        client_secret = args.client_secret
    if not client_id or not client_secret:
        print("Provide --client-id and --client-secret, or --client-secrets", file=sys.stderr)
        return 2

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    code_holder: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/oauth2callback":
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            if "error" in qs:
                code_holder["error"] = qs["error"][0]
                body = b"OAuth error — you can close this tab."
            else:
                code_holder["code"] = qs.get("code", [""])[0]
                body = b"Authorization received. You can close this tab and return to the terminal."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 8765), Handler)
    print("Opening browser for Google consent…")
    print(auth_url)
    webbrowser.open(auth_url)
    print("Waiting for redirect on", REDIRECT_URI, "…")
    while "code" not in code_holder and "error" not in code_holder:
        server.handle_request()
    server.server_close()

    if "error" in code_holder:
        print("OAuth failed:", code_holder["error"], file=sys.stderr)
        return 1

    token_body = urllib.parse.urlencode(
        {
            "code": code_holder["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())

    refresh = payload.get("refresh_token")
    if not refresh:
        print(
            "No refresh_token in response. Revoke prior grants at "
            "https://myaccount.google.com/permissions and re-run with prompt=consent.",
            file=sys.stderr,
        )
        print(json.dumps({k: v for k, v in payload.items() if k != "access_token"}, indent=2))
        return 1

    print("\nSuccess. Add these to backend/.env (do not commit):\n")
    print("GMAIL_MODE=oauth")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={refresh}")
    print("\nThen restart the API and check GET /inbox/gmail/status (connected=true).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
