
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.v1.settings import SettingsRequest, load_settings, save_settings
import os
import json

def test_asr_settings_persistence(tmp_path):
    # Mock settings file
    settings_file = tmp_path / "settings.json"
    
    # Mock get_settings_file_path to return our temp file
    import backend.api.v1.settings as settings_module
    original_get_path = settings_module.get_settings_file_path
    settings_module.get_settings_file_path = lambda: settings_file
    
    try:
        # Initialize settings file
        save_settings({})
        
        client = TestClient(app)
        
        # Define new ASR settings
        new_settings = {
            "asr_method": "funasr",
            "asr_language": "zh",
            "asr_model": "large",
            "asr_timeout": 300,
            "asr_output_format": "txt",
            "asr_enable_timestamps": False,
            "asr_enable_punctuation": False,
            "asr_enable_speaker_diarization": True
        }
        
        # Send update request
        response = client.post("/api/v1/settings/", json=new_settings)
        assert response.status_code == 200
        
        # Reload settings and verify
        saved = load_settings()
        
        assert saved["asr_method"] == "funasr"
        assert saved["asr_language"] == "zh"
        assert saved["asr_model"] == "large"
        assert saved["asr_timeout"] == 300
        assert saved["asr_output_format"] == "txt"
        assert saved["asr_enable_timestamps"] is False
        assert saved["asr_enable_punctuation"] is False
        assert saved["asr_enable_speaker_diarization"] is True
        
    finally:
        # Restore original function
        settings_module.get_settings_file_path = original_get_path
