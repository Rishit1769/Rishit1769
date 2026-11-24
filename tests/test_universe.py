import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

from scripts.data import collect
from scripts.github_client import GitHubClient, GitHubError
from scripts.main import generate, render_readme, ROOT
from scripts.statistics import included_repositories, language_totals, top_languages, contribution_metrics
from scripts.svg import esc, solar


CONFIG = json.loads((ROOT / "data/config.json").read_text())


def fixture():
    return {
        "profile": {"name": "Rishit Singh", "location": "Mumbai, India", "followers": 2, "public_repos": 2},
        "repos": [{"name": "alpha", "language": "Python", "stargazers_count": 3},
                  {"name": "beta", "language": None, "stargazers_count": 1}],
        "pinned": [{"name": "alpha", "description": "A < test & project", "url": "https://github.com/rishit1769/alpha",
                    "stargazerCount": 3, "forkCount": 1, "primaryLanguage": {"name": "Python", "color": "#3572A5"}},
                   {"name": "beta", "description": None, "url": "https://github.com/rishit1769/beta",
                    "stargazerCount": 1, "forkCount": 0, "primaryLanguage": None}],
        "languages": [{"name": "Python", "bytes": 75, "percent": 75.0, "color": "#3572A5"}],
        "days": [{"date": "2026-11-23", "contributionCount": 2}, {"date": "2026-11-24", "contributionCount": 0}],
        "metrics": {"year_total": 2, "current_streak": 1, "longest_streak": 1, "active_days": 1, "period_days": 2},
        "pushes": [{"type": "PushEvent", "repo": {"name": "rishit1769/alpha"}}],
        "avatar": b"\xff\xd8\xff\xe0fakejpeg", "as_of": "2026-11-24",
    }


class StatisticsTests(unittest.TestCase):
    def test_languages_by_bytes(self):
        totals = language_totals([{"Python": 3, "C": 1}, {"Python": 6}])
        result = top_languages(totals, 2, {"Python": "#123456"})
        self.assertEqual([x["percent"] for x in result], [90, 10])

    def test_repository_rules(self):
        repos = [{"owner": {"login": "rishit1769"}, "fork": False, "archived": False},
                 {"owner": {"login": "rishit1769"}, "fork": True},
                 {"owner": {"login": "other"}}]
        self.assertEqual(len(included_repositories(repos, {"username": "rishit1769"})), 1)

    def test_streak_dates(self):
        days = [{"date": f"2026-01-{i:02d}", "contributionCount": n} for i, n in enumerate([1, 1, 0, 1, 1, 1, 0], 1)]
        result = contribution_metrics(days, date(2026, 1, 7), 2026)
        self.assertEqual(result["current_streak"], 3)
        self.assertEqual(result["longest_streak"], 3)
        self.assertEqual(result["year_total"], 5)


class ClientTests(unittest.TestCase):
    def test_pagination(self):
        class Client(GitHubClient):
            def rest(self, path, params=None):
                return list(range(100)) if params["page"] == 1 else [101]
        self.assertEqual(len(list(Client().pages("/test"))), 101)

    def test_graphql_needs_auth(self):
        with self.assertRaises(GitHubError):
            GitHubClient(token="").graphql("query { viewer { login } }")

    def test_http_failure(self):
        with self.assertRaises(GitHubError):
            GitHubClient(retries=0).rest("invalid")

    def test_collection_preserves_pinned_order(self):
        class Client:
            def rest(self, path, params=None):
                if path.startswith("/users/") and path.endswith("/events/public"):
                    return []
                if path.startswith("/users/"):
                    return {"avatar_url": "https://avatars.githubusercontent.com/u/1", "name": "Rishit"}
                if path.endswith("/languages"):
                    return {"Python": 10}
                raise AssertionError(path)

            def pages(self, path, params=None):
                return iter([{"name": "repo", "node_id": "R_1", "language": "Python",
                              "owner": {"login": "rishit1769"}, "fork": False, "archived": False}])

            def graphql(self, query, variables):
                if "query Colors" in query:
                    return {"nodes": [{"languages": {"nodes": [{"name": "Python", "color": "#3572A5"}]}}]}
                return {"user": {"pinnedItems": {"nodes": [{"name": "second"}, {"name": "first"}]},
                                 "contributionsCollection": {"contributionCalendar": {"weeks": [
                                     {"contributionDays": [{"date": "2026-11-24", "contributionCount": 1}]}]}}}}

            def request(self, url, binary=False):
                return b"\xff\xd8avatar"

        result = collect(Client(), CONFIG, date(2026, 11, 24))
        self.assertEqual([p["name"] for p in result["pinned"]], ["second", "first"])
        self.assertEqual(result["languages"][0]["color"], "#3572A5")


class RenderTests(unittest.TestCase):
    def test_xml_and_escaping(self):
        self.assertEqual(esc('<&"'), '&lt;&amp;&quot;')
        ET.fromstring(solar(fixture(), CONFIG))

    def test_determinism_and_links(self):
        snap = fixture()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            out_a = generate(snap, CONFIG, Path(a))
            out_b = generate(snap, CONFIG, Path(b))
            self.assertEqual({p.relative_to(a): v for p, v in out_a.items()}, {p.relative_to(b): v for p, v in out_b.items()})
            self.assertIn('](https://github.com/rishit1769/alpha)', out_a[Path(a) / "README.md"])
            self.assertLess(out_a[Path(a) / "README.md"].find('assets/moons/01.svg'), out_a[Path(a) / "README.md"].find('assets/moons/02.svg'))
            for path, content in out_a.items():
                self.assertNotIn("GITHUB_TOKEN", content)
                if path.suffix == ".svg":
                    ET.fromstring(content)

    def test_empty_pins(self):
        snap = fixture()
        snap["pinned"] = []
        self.assertIn("No repositories are currently pinned", render_readme(snap, CONFIG))


if __name__ == "__main__":
    unittest.main()
