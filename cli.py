#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import questionary
from rich import print as rprint
from rich.align import Align
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from core.features import extract_features
from validate_submission import validate_submission


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
console = Console()


def success(message: str) -> None:
    rprint(f"[bold green]✓[/] {message}")


def error(message: str) -> None:
    rprint(f"[bold red]✗[/] {message}")


def section(title: str = "") -> None:
    console.rule(Text(title, style="dim white") if title else "", style="dim white")


def banner() -> None:
    console.clear()
    art = Text(
        "\n"
        "██████╗ ███████╗██████╗ ██████╗  ██████╗ ██████╗\n"
        "██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗\n"
        "██████╔╝█████╗  ██║  ██║██████╔╝██║   ██║██████╔╝\n"
        "██╔══██╗██╔══╝  ██║  ██║██╔══██╗██║   ██║██╔══██╗\n"
        "██║  ██║███████╗██████╔╝██║  ██║╚██████╔╝██████╔╝\n"
        "╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ \n"
        "\n"
        "REDROB RANKER",
        style="bold cyan",
        justify="center",
    )
    subtitle = Text("\nIntelligent Candidate Discovery", style="dim white", justify="center")
    console.print(Panel(Align.center(Text.assemble(art, subtitle)), border_style="cyan", padding=(1, 2)))


def progress(title: str, total: int | None = None) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def dark_table(title: str) -> Table:
    return Table(title=title, header_style="bold magenta", border_style="dim white")


def run_command(args: list[str], title: str) -> bool:
    started = time.perf_counter()
    with progress(title) as bar:
        task = bar.add_task(title, total=None)
        result = subprocess.run([PYTHON, *args], cwd=ROOT, text=True, capture_output=True)
        bar.update(task, completed=1)
    if result.returncode:
        error("Command failed")
        console.print(result.stdout, end="")
        console.print(result.stderr, style="red", end="")
        return False
    success(f"Done in {time.perf_counter() - started:.2f}s")
    if result.stdout:
        console.print(result.stdout, end="")
    if result.stderr:
        console.print(result.stderr, style="yellow", end="")
    return True


def precompute_features() -> None:
    section("Precompute features")
    candidates = ROOT / "candidates.jsonl"
    out = ROOT / "candidate_features.npz"
    if not candidates.exists():
        error("Missing candidates.jsonl")
        return

    with candidates.open(encoding="utf-8") as handle:
        total = sum(1 for line in handle if line.strip())
    cmd = [PYTHON, "precompute.py", "--candidates", "candidates.jsonl", "--out", "candidate_features.npz"]
    process = subprocess.Popen(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output: list[str] = []

    with progress("Precomputing features", total) as bar:
        task = bar.add_task("Precomputing features", total=total)
        assert process.stdout is not None
        for line in process.stdout:
            output.append(line)
            if line.startswith("Processed "):
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    bar.update(task, completed=min(int(parts[1]), total))
        code = process.wait()
        if code == 0:
            bar.update(task, completed=total)

    if code:
        error("Precompute failed")
        console.print("".join(output), style="red", end="")
    else:
        success(f"Saved {out.name}")


def run_ranker_full() -> None:
    section("Run ranker")
    if run_command(
        ["rank.py", "--candidates", "candidates.jsonl", "--features", "candidate_features.npz", "--out", "submission.csv"],
        "Running full ranker...",
    ):
        show_submission(ROOT / "submission.csv", 10)


def run_ranker_sample() -> None:
    section("Run sample")
    if run_command(
        ["rank.py", "--candidates", "sample_candidates.json", "--out", "test_submission.csv", "--no-features"],
        "Running sample ranker...",
    ):
        show_submission(ROOT / "test_submission.csv", 10)


def validate_csv() -> None:
    section("Validate submission")
    choices = [str(path.name) for path in ROOT.glob("*.csv")]
    choices.append("Enter another path")
    selected = questionary.select("CSV file to validate:", choices=choices).ask()
    if not selected:
        return
    csv_path = Path(questionary.text("CSV path:").ask() or "") if selected == "Enter another path" else ROOT / selected
    errors = validate_submission(csv_path)
    if errors:
        body = "\n".join(f"✗ {item}" for item in errors)
        console.print(Panel(body, title="SUBMISSION INVALID", title_align="center", style="bold red", border_style="red"))
    else:
        console.print(Panel(Align.center("SUBMISSION VALID"), style="bold green", border_style="green", padding=(1, 4)))


def iter_candidates(path: Path):
    if path.suffix == ".json":
        yield from json.loads(path.read_text(encoding="utf-8"))
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def find_candidate(candidate_id: str) -> dict[str, Any] | None:
    return find_candidates([candidate_id]).get(candidate_id)


def find_candidates(candidate_ids: list[str]) -> dict[str, dict[str, Any]]:
    wanted = set(candidate_ids)
    found: dict[str, dict[str, Any]] = {}
    for path in [ROOT / "sample_candidates.json", ROOT / "candidates.jsonl"]:
        if not path.exists():
            continue
        for candidate in iter_candidates(path):
            candidate_id = str(candidate.get("candidate_id"))
            if candidate_id in wanted and candidate_id not in found:
                found[candidate_id] = candidate
                if len(found) == len(wanted):
                    return found
    return found


def score_bar(value: float, color: str, width: int = 24) -> Text:
    filled = max(0, min(width, round(value * width)))
    return Text("█" * filled, style=color) + Text("░" * (width - filled), style="dim white") + Text(f" {value:.3f}", style="white")


def candidate_panel(candidate: dict[str, Any], features: dict[str, Any]) -> Panel:
    profile = candidate.get("profile") or {}
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim white")
    grid.add_column(style="white")
    grid.add_row("candidate_id", Text(str(candidate.get("candidate_id")), style="cyan"))
    grid.add_row("current_title", str(profile.get("current_title") or ""))
    grid.add_row("location", Text(str(profile.get("location") or ""), style="dim white"))
    grid.add_row("years", str(profile.get("years_of_experience") or ""))
    if features.get("is_honeypot"):
        grid.add_row("status", Text("HONEYPOT DETECTED", style="bold red blink"))

    bars = Table.grid(padding=(0, 2))
    for name, color in [
        ("skill_match", "cyan"),
        ("career_quality", "green"),
        ("seniority_fit", "yellow"),
        ("location_score", "blue"),
        ("availability", "magenta"),
    ]:
        bars.add_row(Text(name, style=color), score_bar(float(features[name]), color))

    layout = Table.grid(expand=True)
    layout.add_row(grid)
    layout.add_row("")
    layout.add_row(bars)
    return Panel(layout, title="Candidate Inspect", border_style="dim white")


def inspect_candidate() -> None:
    section("Inspect candidate")
    candidate_id = questionary.text(
        "Candidate ID:",
        validate=lambda text: bool(re.fullmatch(r"CAND_\d{7}", text.strip())) or "Use CAND_XXXXXXX",
    ).ask()
    if not candidate_id:
        return
    candidate = find_candidate(candidate_id.strip())
    if not candidate:
        error("Candidate not found")
        return

    features = extract_features(candidate)
    console.print(candidate_panel(candidate, features))
    section("Candidate fields")
    console.print(JSON.from_data(candidate))


def last_submission() -> Path | None:
    paths = [ROOT / "submission.csv", ROOT / "test_submission.csv"]
    existing = [path for path in paths if path.exists()]
    return max(existing, key=lambda path: path.stat().st_mtime) if existing else None


def show_submission(path: Path, limit: int) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))[:limit]
    candidates = find_candidates([row["candidate_id"] for row in rows])

    table = dark_table(f"Top {limit} from {path.name}")
    table.add_column("rank", justify="right", style="bold yellow")
    table.add_column("candidate_id", style="cyan")
    table.add_column("score", style="green")
    table.add_column("current_title", style="white")
    table.add_column("location", style="dim white")
    table.add_column("reasoning", style="italic dim")
    for row in rows:
        profile = (candidates.get(row["candidate_id"]) or {}).get("profile") or {}
        table.add_row(
            row["rank"],
            row["candidate_id"],
            row["score"],
            str(profile.get("current_title") or ""),
            str(profile.get("location") or ""),
            row["reasoning"],
        )
    console.print(table)


def show_top_n() -> None:
    section("Top candidates")
    path = last_submission()
    if path is None:
        error("No submission.csv or test_submission.csv found")
        return
    value = questionary.text("N:", default="10", validate=lambda text: text.isdigit() or "Use a number").ask()
    if not value:
        return
    show_submission(path, int(value))


def main() -> None:
    banner()
    actions = {
        "1. Precompute features": precompute_features,
        "2. Run ranker (full 100K)": run_ranker_full,
        "3. Run ranker (sample)": run_ranker_sample,
        "4. Validate submission": validate_csv,
        "5. Inspect candidate by ID": inspect_candidate,
        "6. Show top N from last submission": show_top_n,
    }
    while True:
        section()
        choice = questionary.select("Redrob dev tool", choices=[*actions, "7. Exit"]).ask()
        if not choice or choice == "7. Exit":
            return
        actions[choice]()


if __name__ == "__main__":
    main()
