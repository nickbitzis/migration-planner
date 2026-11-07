from migplan.__main__ import main


def test_plan_command_writes_exports_and_step_summary(tmp_path, capsys):
    summary = tmp_path / "summary.md"
    assert main(["plan", "--out", str(tmp_path / "out"), "--summary", str(summary), "--gate"]) == 0
    for f in ("waves.csv", "migration-plan.md", "plan.json"):
        assert (tmp_path / "out" / f).stat().st_size > 1000
    text = summary.read_text()
    assert "### Wave plan comparison" in text and "Graph partitioning" in text and "baseline" in text
    assert "Wave plan comparison" in capsys.readouterr().out


def test_estate_command_writes_csv(tmp_path):
    assert main(["estate", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "flows.csv").read_text().count("\n") > 6000
    assert (tmp_path / "applications.csv").read_text().count("\n") == 251
