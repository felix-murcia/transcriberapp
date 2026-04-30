import pytest
from unittest.mock import MagicMock, patch
from transcriber_app.modules.transcriber_cli import Transcriber


@pytest.fixture
def mock_groq_api():
    with patch("transcriber_app.modules.ai.groq.transcriber.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "simulated transcription from groq"}
        mock_post.return_value = mock_response

        import transcriber_app.modules.ai.groq.transcriber as gt
        with patch.object(gt.GroqTranscriber, "transcribe", return_value=("simulated transcription from groq", {"time": 0.5})):
            yield mock_post


def test_transcribe_returns_text(mock_groq_api, monkeypatch):
    t = Transcriber()
    out = t.transcribe("audios/ejemplo.mp3")
    assert "simulated transcription from groq" in out
