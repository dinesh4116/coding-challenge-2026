from app.cli import main


def test_cli_on_demo(capsys):
    assert main(["data/demo_campaigns.csv"]) == 0
    out = capsys.readouterr().out
    assert "Total alerts fired over 180 days" in out and "Naive ±30%" in out


def test_cli_bad_file(tmp_path, capsys):
    p = tmp_path / "x.csv"
    p.write_text("campaign_id,date,spend\nA,bad,1\n")
    assert main([str(p)]) == 2
