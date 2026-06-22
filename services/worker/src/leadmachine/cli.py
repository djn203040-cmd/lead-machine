import typer

from . import __version__

app = typer.Typer(help="Lead Machine worker", no_args_is_help=True)


@app.command()
def hello() -> None:
    """Smoke test: confirm the worker runs."""
    typer.echo(f"lead-machine worker {__version__} — ok")


@app.command()
def health() -> None:
    """Check connectivity to Supabase (requires env)."""
    from .db import get_client

    client = get_client()
    res = client.table("leads").select("id", count="exact").limit(1).execute()
    typer.echo(f"supabase ok — leads count: {res.count}")


if __name__ == "__main__":
    app()
