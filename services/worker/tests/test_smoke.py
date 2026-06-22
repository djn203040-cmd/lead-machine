from typer.testing import CliRunner

from leadmachine.cli import app

runner = CliRunner()


def test_hello_runs() -> None:
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert "ok" in result.stdout
