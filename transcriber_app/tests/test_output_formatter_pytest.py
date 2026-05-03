import os
from unittest.mock import patch
from transcriber_app.infrastructure.output import LocalOutputFormatter as OutputFormatter


def test_save_output_and_transcription(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_BASE_DIR", str(tmp_path))
    with patch("transcriber_app.modules.output_formatter.APP_BASE_DIR", str(tmp_path)):
        fmt = OutputFormatter()
        out = fmt.save_output("base", "contenido", "modo")
        assert out.endswith("base_modo.md")
        assert os.path.exists(out)
        with open(out, "r", encoding="utf-8") as f:
            assert f.read() == "contenido"

        tpath = fmt.save_transcription("base", "texto trans")
        assert tpath.endswith("base.txt")
        with open(tpath, "r", encoding="utf-8") as f:
            assert f.read() == "texto trans"


def test_save_metrics(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_BASE_DIR", str(tmp_path))
    with patch("transcriber_app.modules.output_formatter.APP_BASE_DIR", str(tmp_path)):
        fmt = OutputFormatter()
        name = "metrics_test"
        summary = "# Summary\n- point 1"
        mode = "tecnico"
        fmt.save_metrics(name, summary, mode)
        metrics_path = Path(str(tmp_path)) / "outputs" / "metrics" / f"{name}_{mode}.json"
        assert metrics_path.exists()
        with open(metrics_path, "r") as f:
            data = json.load(f)
            assert data["name"] == name
            assert data["mode"] == mode
            assert "length" in data
            assert data["length"] == len(summary)
