#!/usr/bin/env python3
"""FlakyGuard CLI — Detect, quarantine & cost-attribute flaky tests."""
import json
import os

import click
from rich.console import Console
from rich.table import Table

import engine

console = Console()
DB = os.environ.get("FLAKYGUARD_DB", "flakyguard.db")


@click.group()
@click.version_option("0.1.0")
def cli():
    """🛡️ FlakyGuard — Flaky test detection & cost attribution engine."""


@cli.command()
@click.argument("xml_path", type=click.Path(exists=True))
@click.option("--run-id", default=None, help="Custom run identifier")
def ingest(xml_path, run_id):
    """Ingest JUnit XML test results into history."""
    db = engine.init_db(DB)
    n, rid = engine.ingest(db, xml_path, run_id)
    console.print(f"[green]✓[/] Ingested {n} test results (run: {rid})")


@cli.command()
@click.option("--min-runs", default=3, help="Minimum runs to evaluate")
@click.option("--threshold", default=0.1, help="Flip rate threshold (0.0-1.0)")
@click.option("--ci-cost", default=0.008, help="CI cost per minute in USD")
@click.option("--rerun-min", default=10, help="Average rerun duration in minutes")
@click.option("--output", type=click.Choice(["table", "json"]), default="table")
def detect(min_runs, threshold, ci_cost, rerun_min, output):
    """Detect flaky tests with statistical flip-rate analysis."""
    db = engine.init_db(DB)
    results = engine.add_costs(
        engine.detect(db, min_runs, threshold), db, ci_cost, rerun_min)
    if output == "json":
        click.echo(json.dumps(results, indent=2))
        return
    if not results:
        console.print("[green]✓ No flaky tests detected![/]")
        return
    tbl = Table(title="🛡️ FlakyGuard — Flaky Test Report")
    for col in ["Test", "Flip Rate", "Runs", "Fails", "Root Cause", "Cost"]:
        tbl.add_column(col)
    total_cost = 0.0
    for r in sorted(results, key=lambda x: -x["flip_rate"]):
        c = "red" if r["flip_rate"] > 0.3 else "yellow"
        tbl.add_row(r["test"][-55:], f"[{c}]{r['flip_rate']:.0%}[/]",
                    str(r["runs"]), str(r["failures"]),
                    r["root_cause"], f"${r['cost_usd']:.2f}")
        total_cost += r["cost_usd"]
    console.print(tbl)
    console.print(f"\n💰 Monthly CI waste: [bold red]${total_cost:.2f}[/]  "
                  f"| 🔥 {len(results)} flaky tests found")


@cli.command()
@click.option("--min-runs", default=3)
@click.option("--threshold", default=0.1)
def quarantine(min_runs, threshold):
    """Generate conftest.py to auto-skip quarantined flaky tests."""
    db = engine.init_db(DB)
    results = engine.detect(db, min_runs, threshold)
    if not results:
        console.print("[green]No flaky tests to quarantine.[/]")
        return
    click.echo(engine.quarantine_code(results))
    console.print(f"\n[green]✓[/] {len(results)} tests quarantined — "
                  "pipe output to conftest.py", err=True)


@cli.command()
def stats():
    """Show ingestion statistics."""
    db = engine.init_db(DB)
    total = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    tests = db.execute("SELECT COUNT(DISTINCT name) FROM runs").fetchone()[0]
    runs = db.execute("SELECT COUNT(DISTINCT run_id) FROM runs").fetchone()[0]
    console.print(f"📊 {total} results | {tests} unique tests | {runs} CI runs")


if __name__ == "__main__":
    cli()
