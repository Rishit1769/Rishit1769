"""Pure computations for repository language and contribution data."""
from collections import Counter
from datetime import date, timedelta


def included_repositories(repos, rules):
    return [r for r in repos if r.get("owner", {}).get("login", "").lower() == rules["username"].lower()
            and (rules.get("include_forks") or not r.get("fork"))
            and (rules.get("include_archived") or not r.get("archived"))
            and not r.get("private")]


def language_totals(breakdowns):
    totals = Counter()
    for breakdown in breakdowns:
        totals.update({name: int(value) for name, value in breakdown.items() if int(value) > 0})
    return totals


def top_languages(totals, limit, colors):
    grand = sum(totals.values())
    if not grand:
        return []
    return [{"name": name, "bytes": count, "percent": count * 100 / grand,
             "color": colors.get(name) or "#94A3B8"}
            for name, count in sorted(totals.items(), key=lambda x: (-x[1], x[0]))[:limit]]


def contribution_metrics(days, today, year):
    counts = {date.fromisoformat(d["date"]): int(d["contributionCount"]) for d in days}
    def streak(end):
        n = 0
        while counts.get(end, 0) > 0:
            n += 1
            end -= timedelta(days=1)
        return n
    current_end = today if counts.get(today, 0) else today - timedelta(days=1)
    ordered = sorted(counts)
    longest = 0
    run = 0
    for day in ordered:
        run = run + 1 if counts[day] > 0 else 0
        longest = max(longest, run)
    return {"year_total": sum(v for d, v in counts.items() if d.year == year),
            "current_streak": streak(current_end), "longest_streak": longest,
            "active_days": sum(v > 0 for v in counts.values()), "period_days": len(counts)}
