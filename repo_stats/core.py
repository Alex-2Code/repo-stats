"""Core functionality for analyzing GitHub repositories."""

import sys
from typing import Any, Dict, List, Optional

import requests
from rich.console import Console
from rich.table import Table

console = Console()

GITHUB_API = "https://api.github.com"


def get_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "repo-stats-cli",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def fetch_repo_info(owner: str, repo: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Fetch repository information."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    response = requests.get(url, headers=get_headers(token))
    if response.status_code == 404:
        console.print(f"[red]Error: Repository {owner}/{repo} not found[/red]")
        sys.exit(1)
    elif response.status_code == 403:
        console.print("[red]Error: API rate limit exceeded. Set GITHUB_TOKEN for higher limits.[/red]")
        sys.exit(1)
    response.raise_for_status()
    return response.json()


def fetch_contributors(owner: str, repo: str, token: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch top contributors."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contributors"
    params = {"per_page": limit}
    response = requests.get(url, headers=get_headers(token), params=params)
    response.raise_for_status()
    return response.json()


def fetch_languages(owner: str, repo: str, token: Optional[str] = None) -> Dict[str, int]:
    """Fetch repository languages."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/languages"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def fetch_commit_activity(owner: str, repo: str, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch commit activity for the last year."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/stats/commit_activity"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def fetch_recent_commits(owner: str, repo: str, token: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch recent commits."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    params = {"per_page": limit}
    response = requests.get(url, headers=get_headers(token), params=params)
    response.raise_for_status()
    return response.json()


def format_number(num: int) -> str:
    """Format large numbers with K/M suffix."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def format_bytes(size: int) -> str:
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def calculate_language_percentages(languages: Dict[str, int]) -> Dict[str, float]:
    """Calculate language percentages."""
    total = sum(languages.values())
    if total == 0:
        return {}
    return {lang: (bytes_count / total) * 100 for lang, bytes_count in languages.items()}


def display_repo_info(info: Dict[str, Any]) -> None:
    """Display repository information in a table."""
    table = Table(title=f"📊 Repository: {info['full_name']}", show_header=False, border_style="blue")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    table.add_row("Description", info.get("description", "N/A"))
    table.add_row("⭐ Stars", format_number(info["stargazers_count"]))
    table.add_row("🍴 Forks", format_number(info["forks_count"]))
    table.add_row("👀 Watchers", format_number(info["subscribers_count"]))
    table.add_row("📋 Open Issues", format_number(info["open_issues_count"]))
    table.add_row("📦 Size", format_bytes(info["size"] * 1024))
    table.add_row("🌐 Language", info.get("language", "N/A"))
    table.add_row("📜 License", info.get("license", {}).get("name", "N/A") if info.get("license") else "N/A")
    table.add_row("📅 Created", info["created_at"][:10])
    table.add_row("🔄 Updated", info["updated_at"][:10])
    table.add_row("🏠 Homepage", info.get("homepage", "N/A") or "N/A")
    table.add_row("🌿 Default Branch", info["default_branch"])

    console.print(table)


def display_languages(languages: Dict[str, int]) -> None:
    """Display language breakdown."""
    if not languages:
        return

    percentages = calculate_language_percentages(languages)
    table = Table(title="💻 Languages", border_style="green")
    table.add_column("Language", style="bold")
    table.add_column("Bytes", justify="right")
    table.add_column("Percentage", justify="right")

    for lang, percentage in sorted(percentages.items(), key=lambda x: x[1], reverse=True):
        table.add_row(lang, format_number(languages[lang]), f"{percentage:.1f}%")

    console.print(table)


def display_contributors(contributors: List[Dict[str, Any]]) -> None:
    """Display top contributors."""
    if not contributors:
        return

    table = Table(title="👥 Top Contributors", border_style="yellow")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Username", style="bold")
    table.add_column("Contributions", justify="right")

    for i, contributor in enumerate(contributors[:10], 1):
        table.add_row(str(i), contributor["login"], format_number(contributor["contributions"]))

    console.print(table)


def display_recent_commits(commits: List[Dict[str, Any]]) -> None:
    """Display recent commits."""
    if not commits:
        return

    table = Table(title="📝 Recent Commits", border_style="magenta")
    table.add_column("SHA", style="dim")
    table.add_column("Message", max_width=60)
    table.add_column("Author")
    table.add_column("Date")

    for commit in commits:
        sha = commit["sha"][:7]
        message = commit["commit"]["message"].split("\n")[0][:60]
        author = commit["commit"]["author"]["name"]
        date = commit["commit"]["author"]["date"][:10]
        table.add_row(sha, message, author, date)

    console.print(table)


def generate_json_report(
    info: Dict[str, Any],
    languages: Dict[str, int],
    contributors: List[Dict[str, Any]],
    commits: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate JSON report."""
    return {
        "repository": {
            "name": info["full_name"],
            "description": info.get("description"),
            "stars": info["stargazers_count"],
            "forks": info["forks_count"],
            "watchers": info["subscribers_count"],
            "open_issues": info["open_issues_count"],
            "size_kb": info["size"],
            "language": info.get("language"),
            "license": info.get("license", {}).get("name") if info.get("license") else None,
            "created_at": info["created_at"],
            "updated_at": info["updated_at"],
            "default_branch": info["default_branch"],
            "url": info["html_url"],
        },
        "languages": calculate_language_percentages(languages),
        "top_contributors": [
            {"username": c["login"], "contributions": c["contributions"]}
            for c in contributors[:10]
        ],
        "recent_commits": [
            {
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
            }
            for c in commits[:5]
        ],
    }



def compare_repos(repo1_info: Dict[str, Any], repo2_info: Dict[str, Any]) -> None:
    """Compare two repositories side by side."""
    table = Table(title="Repository Comparison", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column(repo1_info.get("full_name", "Repo 1"), style="green")
    table.add_column(repo2_info.get("full_name", "Repo 2"), style="yellow")
    table.add_column("Difference", style="bold")
    
    metrics = [
        ("Stars", repo1_info.get("stargazers_count", 0), repo2_info.get("stargazers_count", 0)),
        ("Forks", repo1_info.get("forks_count", 0), repo2_info.get("forks_count", 0)),
        ("Open Issues", repo1_info.get("open_issues_count", 0), repo2_info.get("open_issues_count", 0)),
        ("Watchers", repo1_info.get("subscribers_count", 0), repo2_info.get("subscribers_count", 0)),
    ]
    
    for name, val1, val2 in metrics:
        diff = val1 - val2
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        style = "green" if diff > 0 else "red" if diff < 0 else "white"
        table.add_row(
            name,
            format_number(val1),
            format_number(val2),
            f"[{style}]{diff_str}[/{style}]"
        )
    
    # Add language
    table.add_row(
        "Language",
        repo1_info.get("language", "N/A"),
        repo2_info.get("language", "N/A"),
        "-"
    )
    
    # Add license
    table.add_row(
        "License",
        (repo1_info.get("license") or {}).get("spdx_id", "N/A"),
        (repo2_info.get("license") or {}).get("spdx_id", "N/A"),
        "-"
    )
    
    # Add created date
    table.add_row(
        "Created",
        repo1_info.get("created_at", "")[:10],
        repo2_info.get("created_at", "")[:10],
        "-"
    )
    
    console.print(table)


def generate_compare_json(repo1_info: Dict[str, Any], repo2_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generate JSON comparison report."""
    return {
        "comparison": {
            "repo1": {
                "name": repo1_info.get("full_name"),
                "stars": repo1_info.get("stargazers_count"),
                "forks": repo1_info.get("forks_count"),
                "issues": repo1_info.get("open_issues_count"),
                "language": repo1_info.get("language"),
            },
            "repo2": {
                "name": repo2_info.get("full_name"),
                "stars": repo2_info.get("stargazers_count"),
                "forks": repo2_info.get("forks_count"),
                "issues": repo2_info.get("open_issues_count"),
                "language": repo2_info.get("language"),
            },
            "differences": {
                "stars": repo1_info.get("stargazers_count", 0) - repo2_info.get("stargazers_count", 0),
                "forks": repo1_info.get("forks_count", 0) - repo2_info.get("forks_count", 0),
                "issues": repo1_info.get("open_issues_count", 0) - repo2_info.get("open_issues_count", 0),
            }
        }
    }


def fetch_gitlab_stats(owner: str, repo: str, token: str) -> Dict[str, Any]:
    """Fetch GitLab repository statistics."""
    base_url = "https://gitlab.com/api/v4"
    headers = {"PRIVATE-TOKEN": token}
    
    try:
        # Repo info
        resp = requests.get(f"{base_url}/projects/{owner}%2F{repo}", headers=headers)
        if resp.status_code != 200:
            return {"error": f"GitLab project not found: {resp.status_code}"}
        
        info = resp.json()
        
        # Recent commits
        commits_resp = requests.get(
            f"{base_url}/projects/{owner}%2F{repo}/repository/commits",
            headers=headers, params={"per_page": 10}
        )
        commits = commits_resp.json() if commits_resp.status_code == 200 else []
        
        return {
            "name": info.get("name"),
            "stars": info.get("star_count", 0),
            "forks": info.get("forks_count", 0),
            "open_issues": info.get("open_issues_count", 0),
            "last_push": info.get("last_pipeline_completed_at"),
            "recent_commits": [
                {"sha": c["short_id"], "message": c["title"], "author": c["author_name"], "date": c["committed_date"]}
                for c in commits[:5]
            ]
        }
    except Exception as e:
        return {"error": str(e)}
