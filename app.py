from __future__ import annotations

import csv
import html
import io
import json
import time
from typing import Any

import streamlit as st

from core.features import extract_features
from core.score import score_candidate
from rank import _reasoning


st.set_page_config(page_title="Redrob Ranker", layout="wide")


def _load_candidates(uploaded_file) -> list[dict[str, Any]]:
    try:
        payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON upload: {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError("Upload must be a JSON array of candidate objects.")
    if len(payload) > 100:
        raise ValueError("Upload must contain 100 or fewer candidates.")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("Every array item must be a candidate object.")
    return payload


def _rank_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float]:
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        profile = candidate.get("profile") or {}
        score = float(score_candidate(candidate))
        features = extract_features(candidate)
        rows.append(
            {
                "candidate": candidate,
                "candidate_id": candidate_id,
                "score": score,
                "current_title": str(profile.get("current_title") or ""),
                "years_of_experience": float(profile.get("years_of_experience") or 0.0),
                "location": str(profile.get("location") or ""),
                "is_honeypot": bool(features["is_honeypot"]),
            }
        )

    rows.sort(key=lambda row: (-row["score"], row["candidate_id"]))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
        row["reasoning"] = _reasoning(row["candidate"], index)

    return rows, time.perf_counter() - started


def _submission_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["candidate_id", "rank", "score", "reasoning"])
    for row in rows[:100]:
        writer.writerow(
            [
                row["candidate_id"],
                row["rank"],
                f"{row['score']:.6f}",
                row["reasoning"],
            ]
        )
    return output.getvalue()


def _render_table(rows: list[dict[str, Any]]) -> None:
    table_rows = []
    for row in rows:
        class_name = " honeypot" if row["is_honeypot"] else ""
        table_rows.append(
            "<tr class='data-row{class_name}'>"
            "<td>{rank}</td>"
            "<td>{candidate_id}</td>"
            "<td>{score:.6f}</td>"
            "<td>{title}</td>"
            "<td>{experience:.1f}</td>"
            "<td>{location}</td>"
            "<td>{reasoning}</td>"
            "</tr>".format(
                class_name=class_name,
                rank=row["rank"],
                candidate_id=html.escape(row["candidate_id"]),
                score=row["score"],
                title=html.escape(row["current_title"]),
                experience=row["years_of_experience"],
                location=html.escape(row["location"]),
                reasoning=html.escape(row["reasoning"]),
            )
        )

    st.markdown(
        """
        <div class="rank-table-wrap">
          <table class="rank-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Candidate</th>
                <th>Score</th>
                <th>Current Title</th>
                <th>YOE</th>
                <th>Location</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
        """
        + "\n".join(table_rows)
        + """
            </tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
      :root {
        --bg: #08090b;
        --panel: #111318;
        --line: #242831;
        --text: #f4f0e8;
        --muted: #a7a09a;
        --accent: #d6ff64;
        --red-bg: #311116;
        --red-line: #80313b;
      }

      .stApp {
        background:
          linear-gradient(180deg, rgba(214, 255, 100, 0.045), rgba(8, 9, 11, 0) 280px),
          var(--bg);
        color: var(--text);
      }

      [data-testid="stHeader"] {
        background: transparent;
      }

      .block-container {
        max-width: 1480px;
        padding-top: 2.5rem;
      }

      .rr-title {
        border-bottom: 1px solid var(--line);
        margin-bottom: 1.25rem;
        padding-bottom: 1rem;
      }

      .rr-title h1 {
        color: var(--text);
        font-size: 2.1rem;
        font-weight: 650;
        letter-spacing: 0;
        margin: 0;
      }

      .rr-title p {
        color: var(--muted);
        margin: 0.35rem 0 0;
      }

      [data-testid="stFileUploader"] section {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
      }

      .metric-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1px;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--line);
        margin: 1.1rem 0;
      }

      .metric-strip div {
        background: var(--panel);
        padding: 0.9rem 1rem;
      }

      .metric-strip span {
        display: block;
        color: var(--muted);
        font-size: 0.74rem;
        text-transform: uppercase;
      }

      .metric-strip strong {
        display: block;
        color: var(--text);
        font-size: 1.2rem;
        margin-top: 0.2rem;
      }

      .rank-table-wrap {
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow-x: auto;
        background: #0c0e12;
      }

      .rank-table {
        border-collapse: collapse;
        min-width: 1180px;
        width: 100%;
      }

      .rank-table th,
      .rank-table td {
        border-bottom: 1px solid var(--line);
        padding: 0.72rem 0.78rem;
        text-align: left;
        vertical-align: top;
      }

      .rank-table th {
        background: #151821;
        color: var(--muted);
        font-size: 0.74rem;
        font-weight: 650;
        text-transform: uppercase;
      }

      .rank-table td {
        color: var(--text);
        font-size: 0.88rem;
        line-height: 1.35;
      }

      .rank-table .honeypot td {
        background: var(--red-bg);
        border-bottom-color: var(--red-line);
        color: #ffd6d9;
      }

      .stDownloadButton button {
        background: var(--accent);
        border: 0;
        border-radius: 8px;
        color: #111;
        font-weight: 700;
      }

      @media (max-width: 760px) {
        .metric-strip {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }
    </style>
    <div class="rr-title">
      <h1>Redrob Ranker</h1>
      <p>Inline scoring for small candidate batches.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


uploaded = st.file_uploader("Candidate JSON", type=["json"], accept_multiple_files=False)

if uploaded is None:
    st.stop()

try:
    candidates = _load_candidates(uploaded)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if not candidates:
    st.warning("No candidates found.")
    st.stop()

ranked_rows, elapsed = _rank_candidates(candidates)
honeypot_count = sum(1 for row in ranked_rows if row["is_honeypot"])
csv_data = _submission_csv(ranked_rows)

st.markdown(
    f"""
    <div class="metric-strip">
      <div><span>Candidates</span><strong>{len(ranked_rows)}</strong></div>
      <div><span>Honeypots</span><strong>{honeypot_count}</strong></div>
      <div><span>Top Score</span><strong>{ranked_rows[0]['score']:.4f}</strong></div>
      <div><span>Runtime</span><strong>{elapsed:.3f}s</strong></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if len(ranked_rows) < 100:
    st.warning(
        "This upload has fewer than 100 candidates, so the CSV cannot satisfy the validator's exact 100-row rule."
    )

st.download_button(
    "Download submission.csv",
    data=csv_data,
    file_name="submission.csv",
    mime="text/csv",
)

_render_table(ranked_rows)
