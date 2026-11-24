"""Small authenticated GitHub REST/GraphQL client with bounded retries."""
from __future__ import annotations

import json
import os
import random
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: int = 20, retries: int = 3):
        self.token = token if token is not None else (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"))
        self.timeout = timeout
        self.retries = retries
        self.context = ssl.create_default_context()
        if os.getenv("SSL_CERT_FILE"):
            self.context.load_verify_locations(os.environ["SSL_CERT_FILE"])

    def request(self, url: str, payload: dict | None = None, binary: bool = False):
        if not url.startswith("https://"):
            raise GitHubError("Only HTTPS URLs are accepted")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "developer-universe/1.0"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(payload).encode() if payload is not None else None
        if data:
            headers["Content-Type"] = "application/json"
        for attempt in range(self.retries + 1):
            try:
                with urlopen(Request(url, data=data, headers=headers), timeout=self.timeout, context=self.context) as response:
                    body = response.read()
                    if binary:
                        return body
                    return json.loads(body), response.headers
            except HTTPError as exc:
                retryable = exc.code in (429, 500, 502, 503, 504) or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0")
                if not retryable or attempt == self.retries:
                    raise GitHubError(f"GitHub HTTP {exc.code}: {exc.reason}") from exc
                reset = exc.headers.get("X-RateLimit-Reset")
                delay = min(30, max(1, int(reset) - int(time.time()))) if reset else min(30, 2 ** attempt + random.random())
            except (URLError, TimeoutError) as exc:
                if attempt == self.retries:
                    raise GitHubError(f"GitHub request failed: {exc}") from exc
                delay = min(30, 2 ** attempt + random.random())
            time.sleep(delay)
        raise AssertionError("unreachable")

    def rest(self, path: str, params: dict | None = None):
        if not path.startswith("/") or "//" in path:
            raise GitHubError("Invalid REST path")
        url = "https://api.github.com" + path + ("?" + urlencode(params) if params else "")
        return self.request(url)[0]

    def pages(self, path: str, params: dict | None = None):
        page = 1
        while True:
            result = self.rest(path, {**(params or {}), "per_page": 100, "page": page})
            if not isinstance(result, list):
                raise GitHubError("Expected a paginated list")
            yield from result
            if len(result) < 100:
                break
            page += 1

    def graphql(self, query: str, variables: dict | None = None):
        if not self.token:
            raise GitHubError("GITHUB_TOKEN is required for pinned repositories and contributions")
        result = self.request("https://api.github.com/graphql", {"query": query, "variables": variables or {}})[0]
        if result.get("errors"):
            raise GitHubError("GitHub GraphQL: " + "; ".join(str(e.get("message", "unknown")) for e in result["errors"]))
        if "data" not in result:
            raise GitHubError("GitHub GraphQL returned no data")
        return result["data"]
