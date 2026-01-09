"""Plot access logs: confidence/time and accuracy/time charts.

This script reads the `logs` table in the SQLite database and creates a
two-panel plot:
- top: face & PIN scores over time (markers show granted/denied)
- bottom: cumulative accuracy over time (percentage of granted attempts)

It is written with clear, beginner-friendly code and comments so you can
modify it easily.
"""

from __future__ import annotations

import sys
from pathlib import Path
import argparse
import csv
import datetime
from typing import List

# ensure project root in path when run as script
if __package__ is None:
    proj_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(proj_root))

import src.db as db
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def load_logs_from_db() -> List[dict]:
    """Load log rows from the SQLite DB and normalize them into dicts.

    Each dict contains a parsed `ts` datetime, user id, name, face score,
    pin score and the decision string.
    """
    conn = db._connect()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, user_id, name, face_score, pin_score, decision FROM logs ORDER BY timestamp")
    rows = cur.fetchall()
    conn.close()
    out = []
    for ts, uid, name, face, pin, decision in rows:
        try:
            ts_dt = datetime.datetime.fromisoformat(ts)
        except Exception:
            # If the timestamp isn't in ISO format for some reason, fallback
            ts_dt = datetime.datetime.utcnow()
        out.append({
            "ts": ts_dt,
            "user_id": uid,
            "name": name,
            "face_score": float(face),
            "pin_score": float(pin),
            "decision": decision,
        })
    return out


def plot_logs(logs: List[dict], out_path: Path | None = None, show: bool = False):
   
    if not logs:
        print("No logs to plot")
        return

    times = [r["ts"] for r in logs]
    face = [r["face_score"] for r in logs]
    pin = [r["pin_score"] for r in logs]
    decisions = [r["decision"] for r in logs]

    # compute cumulative accuracy = fraction of GRANTED or GRANTED_MARGINAL
    granted_mask = [1 if (d and d.startswith("GRANTED")) else 0 for d in decisions]
    cum_total = []
    cum_granted = []
    g = 0
    t = 0
    for v in granted_mask:
        t += 1
        g += v
        cum_total.append(t)
        cum_granted.append(g / t * 100.0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax1.plot(times, face, label="Face score", color="tab:blue")
    ax1.plot(times, pin, label="PIN score", color="tab:orange")
    # mark granted vs denied with different markers so the plot is easier
    # to read for beginners.
    for t, f, d in zip(times, face, decisions):
        marker = "o" if d and d.startswith("GRANTED") else "x"
        color = "green" if d and d.startswith("GRANTED") else "red"
        ax1.scatter(t, f, marker=marker, color=color, alpha=0.6)

    ax1.set_ylabel("Score (0-100)")
    ax1.set_title("Face & PIN scores over time")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.4)

    ax2.plot(times, cum_granted, label="Cumulative accuracy (%)", color="tab:green")
    ax2.set_ylabel("Accuracy (%)")
    ax2.set_ylim(0, 100)
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.set_xlabel("Time")

    # format x axis so dates look nice
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax2.xaxis.get_major_locator()))

    plt.tight_layout()
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_path), dpi=150)
        print(f"Saved plot to {out_path}")
    if show:
        plt.show()


def export_csv_from_db(csv_out: Path):
    """Export logs from the DB into a CSV file for external tools.

    The CSV columns are: timestamp,user_id,name,face_score,pin_score,decision
    """
    logs = load_logs_from_db()
    if not logs:
        print("No logs to export")
        return
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "user_id", "name", "face_score", "pin_score", "decision"])
        for r in logs:
            writer.writerow([r["ts"].isoformat(), r["user_id"], r["name"], r["face_score"], r["pin_score"], r["decision"]])
    print(f"Exported logs to {csv_out}")


def main():
    parser = argparse.ArgumentParser(description="Plot access logs and accuracy/confidence graphs")
    parser.add_argument("--out", help="Output image path", default="logs/access_plot.png")
    parser.add_argument("--show", help="Show plot interactively", action="store_true")
    parser.add_argument("--export-csv", help="Export log CSV path", default=None)
    args = parser.parse_args()

    db.init_db()
    logs = load_logs_from_db()
    out_path = Path(args.out)
    plot_logs(logs, out_path=out_path, show=args.show)
    if args.export_csv:
        export_csv_from_db(Path(args.export_csv))


if __name__ == "__main__":
    main()
