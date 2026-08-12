#!/usr/bin/env python3
"""Pull contribution numbers off the GitHub GraphQL API into activity.json.

Runs in CI. The calendar comes back as one entry per day for a rolling year,
which is enough to derive both streaks locally; lifetime commits need one
query per year since the account was created, because contributionsCollection
only ever covers a window.

Needs GITHUB_TOKEN in the environment. The default Actions token sees public
contributions; private ones need a PAT with read:user, and the owner has to
switch on "Include private contributions on my profile".
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

API = "https://api.github.com/graphql"
LOGIN = os.environ.get("GITHUB_LOGIN", "flinlabs")
TOKEN = os.environ.get("GITHUB_TOKEN")

PROFILE = """
query($login: String!) {
  user(login: $login) {
    createdAt
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""

WINDOW = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def query(doc, **variables):
    if not TOKEN:
        sys.exit("fetch_activity: GITHUB_TOKEN is not set")
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": doc, "variables": variables}).encode(),
        headers={"Authorization": "bearer %s" % TOKEN,
                 "Content-Type": "application/json",
                 "User-Agent": "flinlabs-profile"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("fetch_activity: %s %s\n%s" % (e.code, e.reason, e.read().decode()[:400]))
    if "errors" in payload:
        sys.exit("fetch_activity: %s" % json.dumps(payload["errors"])[:400])
    return payload["data"]


def streaks(days):
    """(current, longest) run lengths over days sorted oldest first.

    Today is excluded from breaking a streak: a day with nothing on it yet is
    still in progress, so an active streak that stops at yesterday counts.
    """
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    current = 0
    today = date.today().isoformat()
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        elif d["date"] != today:
            break
    return current, longest


def main():
    profile = query(PROFILE, login=LOGIN)["user"]
    created = datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00"))
    stars = sum(n["stargazerCount"] for n in profile["repositories"]["nodes"])

    today = datetime.now(created.tzinfo)
    year = query(WINDOW, login=LOGIN,
                 **{"from": (today - timedelta(days=365)).isoformat(), "to": today.isoformat()})
    coll = year["user"]["contributionsCollection"]

    days = [{"date": d["date"], "count": d["contributionCount"]}
            for w in coll["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    current, longest = streaks(days)

    # lifetime commits: one window per calendar year since sign-up
    commits = 0
    start = created
    while start < today:
        end = min(start + timedelta(days=364), today)
        c = query(WINDOW, login=LOGIN, **{"from": start.isoformat(), "to": end.isoformat()})
        commits += c["user"]["contributionsCollection"]["totalCommitContributions"]
        start = end + timedelta(seconds=1)

    active = [d for d in days if d["count"] > 0]
    busiest = max(days, key=lambda d: d["count"]) if days else {"date": "", "count": 0}

    out = {
        "login": LOGIN,
        "current_streak": current,
        "longest_streak": longest,
        "year_contributions": coll["contributionCalendar"]["totalContributions"],
        "total_commits": commits,
        "prs": coll["totalPullRequestContributions"],
        "repos": profile["repositories"]["totalCount"],
        "stars": stars,
        "busiest_date": busiest["date"],
        "busiest_count": busiest["count"],
        "active_days": len(active),
        "since": created.date().isoformat(),
        "updated": date.today().isoformat(),
    }
    dest = sys.argv[1] if len(sys.argv) > 1 else "activity.json"
    with open(dest, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
