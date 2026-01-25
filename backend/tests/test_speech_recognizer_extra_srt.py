import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys
import json

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.utils.speech_recognizer import SpeechRecognizer, SpeechRecognitionConfig, SpeechRecognitionMethod

class TestSpeechRecognizerExtraSRT:
    
    @pytest.fixture
    def recognizer(self, tmp_path):
        recognizer = SpeechRecognizer()
        # Mock extract audio to return a dummy audio path
        audio_path = tmp_path / "test_audio.mp3"
        audio_path.touch()
        recognizer._extract_audio_from_video = MagicMock(return_value=audio_path)
        return recognizer
    
    @pytest.fixture
    def mock_openai(self):
        with patch("openai.OpenAI") as mock:
            yield mock
            
    def test_openai_api_generates_extra_srt_for_vtt(self, recognizer, mock_openai, tmp_path):
        # Setup
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_path = tmp_path / "test.vtt"
        
        config = SpeechRecognitionConfig(
            method=SpeechRecognitionMethod.OPENAI_API,
            output_format="vtt",
            openai_api_key="fake-key"
        )
        
        # Mock OpenAI client response
        mock_client = mock_openai.return_value
        mock_transcript = MagicMock()
        mock_transcript.__str__.return_value = "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello world"
        mock_client.audio.transcriptions.create.return_value = mock_transcript
        
        # Execute
        result_path = recognizer.generate_subtitle(video_path, output_path, config)
        
        # Verify return path is VTT
        assert result_path == output_path
        assert result_path.exists()
        assert result_path.read_text(encoding="utf-8") == "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nHello world"
        
        # Verify SRT file exists
        srt_path = output_path.with_suffix(".srt")
        assert srt_path.exists()
        
        # Verify SRT content (simple conversion check)
        srt_content = srt_path.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:05,000" in srt_content
        assert "Hello world" in srt_content
        assert "WEBVTT" not in srt_content

    def test_openai_api_generates_extra_srt_for_json(self, recognizer, mock_openai, tmp_path):
        # Setup
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_path = tmp_path / "test.json"
        
        config = SpeechRecognitionConfig(
            method=SpeechRecognitionMethod.OPENAI_API,
            output_format="json",
            openai_api_key="fake-key"
        )
        
        # Mock OpenAI client response
        mock_client = mock_openai.return_value
        mock_transcript = MagicMock()
        # Mock JSON response with segments
        json_content = json.dumps({
            "text": "Hello world", 
            "segments": [
                {"id": 0, "start": 0.0, "end": 5.0, "text": "Hello world"}
            ]
        })
        mock_transcript.__str__.return_value = json_content
        mock_client.audio.transcriptions.create.return_value = mock_transcript
        
        # Execute
        result_path = recognizer.generate_subtitle(video_path, output_path, config)
        
        # Verify return path is JSON
        assert result_path == output_path
        assert result_path.exists()
        
        # Verify SRT file exists
        srt_path = output_path.with_suffix(".srt")
        assert srt_path.exists()
        
        # Verify SRT content
        srt_content = srt_path.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:05,000" in srt_content
        assert "Hello world" in srt_content
