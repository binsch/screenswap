from __future__ import annotations

import sys

import click

from . import display, storage


@click.group()
def main() -> None:
    pass


@main.command()
@click.argument("name")
def save(name: str) -> None:
    """Save current monitor layout."""
    monitors = display.get_current_monitors()
    monitor_dicts = [
        {
            "hardware_id": m.hardware_id,
            "width": m.width,
            "height": m.height,
            "position_x": m.position_x,
            "position_y": m.position_y,
            "is_primary": m.is_primary,
            "refresh_rate": m.refresh_rate,
            "orientation": m.orientation,
        }
        for m in monitors
    ]
    storage.save_layout(name, monitor_dicts)
    click.echo(f"Layout '{name}' saved ({len(monitors)} monitor(s)).")


@main.command("list")
def list_layouts() -> None:
    """List saved layouts."""
    layouts = storage.list_layouts()
    if not layouts:
        click.echo("No saved layouts. Run 'screenswap save <name>' to create one.")
        return
    for name in layouts:
        click.echo(name)


@main.command()
@click.argument("name")
def load(name: str) -> None:
    """Apply a saved layout."""
    try:
        layout = storage.load_layout(name)
    except FileNotFoundError:
        click.echo(
            f"Layout '{name}' not found. Run 'screenswap list' to see saved layouts.",
            err=True,
        )
        sys.exit(1)

    try:
        warnings = display.apply_layout(layout["monitors"])
    except RuntimeError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    for warning in warnings:
        click.echo(warning)
    click.echo(f"Layout '{name}' applied.")


@main.command()
@click.argument("name")
def delete(name: str) -> None:
    """Delete a saved layout."""
    try:
        storage.delete_layout(name)
    except FileNotFoundError:
        click.echo(
            f"Layout '{name}' not found. Run 'screenswap list' to see saved layouts.",
            err=True,
        )
        sys.exit(1)
    click.echo(f"Layout '{name}' deleted.")
