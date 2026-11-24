"""Collect a complete, real snapshot; callers write only after this succeeds."""
from datetime import date, timedelta
from urllib.parse import quote

from .github_client import GitHubClient, GitHubError
from .statistics import included_repositories, language_totals, top_languages, contribution_metrics


GRAPHQL = """query Universe($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) { nodes { ... on Repository {
      name description url stargazerCount forkCount updatedAt
      primaryLanguage { name color }
    } } }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount color } } }
    }
  }
}"""


def recent_pushes(client, username, limit):
    events = client.pages(f"/users/{quote(username)}/events/public")
    latest = {}
    for event in events:
        repo = event.get("repo") or {}
        name = repo.get("name", "").casefold()
        if event.get("type") != "PushEvent" or not name or not event.get("created_at"):
            continue
        key = repo.get("id") or name
        if key not in latest or event["created_at"] > latest[key]["created_at"]:
            latest[key] = event
    ordered = sorted(latest.values(), key=lambda event: event["created_at"], reverse=True)
    unique = {}
    for event in ordered:
        unique.setdefault(event["repo"]["name"].casefold(), event)
    return list(unique.values())[:max(0, min(limit, 6))]


def collect_public_preview(client: GitHubClient, config: dict, today: date | None = None):
    """Create an honest first-render preview when local GraphQL auth is unavailable.

    This never claims to know pins or contribution counts. Scheduled production runs
    always use ``collect`` instead.
    """
    today = today or date.today()
    username = config["username"]
    profile = client.rest(f"/users/{quote(username)}")
    public_repos = included_repositories(
        client.pages(f"/users/{quote(username)}/repos", {"type": "owner", "sort": "full_name"}),
        {"username": username, "include_forks": True, "include_archived": True},
    )
    public_stars = sum(repo["stargazers_count"] for repo in public_repos)
    repos = included_repositories(public_repos, {**config["repositories"], "username": username})
    breakdowns = [client.rest(f"/repos/{quote(username)}/{quote(repo['name'])}/languages") for repo in repos]
    # GitHub Linguist is GitHub's public language-color source.
    linguist = client.request("https://raw.githubusercontent.com/github-linguist/linguist/master/lib/linguist/languages.yml", binary=True).decode()
    import re
    colors = {}
    current = None
    for line in linguist.splitlines():
        if line and not line.startswith(" ") and line.endswith(":"):
            current = line[:-1]
        elif current and (match := re.match(r"^  color: ['\"]?(#[0-9a-fA-F]{6})", line)):
            colors[current] = match.group(1)
    pushes = recent_pushes(client, username, config["max_comets"])
    avatar = client.request(profile["avatar_url"], binary=True)
    if not avatar or len(avatar) > 2_000_000:
        raise GitHubError("Avatar is empty or too large")
    return {"profile": profile, "public_stars": public_stars, "repos": repos, "pinned": [],
            "languages": top_languages(language_totals(breakdowns), config["max_planets"], colors),
            "days": [], "metrics": {}, "pushes": pushes,
            "avatar": avatar, "as_of": today.isoformat(), "authenticated": False}


def collect(client: GitHubClient, config: dict, today: date | None = None):
    today = today or date.today()
    username = config["username"]
    if not username.replace("-", "").isalnum():
        raise ValueError("Invalid GitHub username")
    profile = client.rest(f"/users/{quote(username)}")
    public_repos = included_repositories(
        client.pages(f"/users/{quote(username)}/repos", {"type": "owner", "sort": "full_name"}),
        {"username": username, "include_forks": True, "include_archived": True},
    )
    public_stars = sum(repo["stargazers_count"] for repo in public_repos)
    repos = included_repositories(public_repos, {**config["repositories"], "username": username})
    breakdowns = []
    colors = {}
    for repo in repos:
        breakdowns.append(client.rest(f"/repos/{quote(username)}/{quote(repo['name'])}/languages"))
    # Resolve every displayed language color from GitHub GraphQL, not a local palette.
    ids = [r["node_id"] for r in repos if r.get("node_id")]
    for offset in range(0, len(ids), 100):
        colors_result = client.graphql("query Colors($ids: [ID!]!) { nodes(ids: $ids) { ... on Repository { languages(first: 100) { nodes { name color } } } } }", {"ids": ids[offset:offset+100]})
        for node in colors_result.get("nodes", []):
            for language in (node or {}).get("languages", {}).get("nodes", []):
                if language and language.get("color"):
                    colors[language["name"]] = language["color"]
    start = today - timedelta(days=config["heatmap_weeks"] * 7 - 1)
    # The current year can predate the heatmap window; request from Jan 1 for a true year total.
    query_start = min(start, date(today.year, 1, 1))
    gql = client.graphql(GRAPHQL, {"login": username, "from": query_start.isoformat() + "T00:00:00Z", "to": today.isoformat() + "T23:59:59Z"})
    user = gql.get("user")
    if not user:
        raise GitHubError("GitHub user missing from GraphQL response")
    pinned = [node for node in user["pinnedItems"]["nodes"] if node]
    days = [day for week in user["contributionsCollection"]["contributionCalendar"]["weeks"] for day in week["contributionDays"]
            if query_start <= date.fromisoformat(day["date"]) <= today]
    if not days:
        raise GitHubError("Contribution calendar is empty")
    pushes = recent_pushes(client, username, config["max_comets"])
    avatar = client.request(profile["avatar_url"], binary=True)
    if not avatar or len(avatar) > 2_000_000:
        raise GitHubError("Avatar is empty or too large")
    totals = language_totals(breakdowns)
    # Pinned repository language colors are another authoritative GitHub source.
    for item in pinned:
        lang = item.get("primaryLanguage") or {}
        if lang.get("name") and lang.get("color"):
            colors[lang["name"]] = lang["color"]
    languages = top_languages(totals, config["max_planets"], colors)
    return {"profile": profile, "public_stars": public_stars, "repos": repos, "pinned": pinned, "languages": languages,
            "days": [d for d in days if date.fromisoformat(d["date"]) >= start],
            "metrics": contribution_metrics(days, today, today.year), "pushes": pushes,
            "avatar": avatar, "as_of": today.isoformat(), "authenticated": True}
