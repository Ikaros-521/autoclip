import sys
import os
from pathlib import Path
import importlib.util

# 添加项目根目录 to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load settings module directly bypassing backend.api.v1 package init
settings_path = Path(__file__).parent.parent / "api" / "v1" / "settings.py"
settings_module = load_module_from_path("backend.api.v1.settings", settings_path)

load_settings = settings_module.load_settings
save_settings = settings_module.save_settings

def test_asr_settings():
    print("Testing ASR settings persistence...")
    
    # 1. Load current settings
    initial_settings = load_settings()
    print(f"Initial settings loaded. ASR method: {initial_settings.get('asr_method')}")
    
    # 2. Update settings with new ASR values
    new_settings = initial_settings.copy()
    new_settings['asr_method'] = 'whisper_local'
    new_settings['asr_language'] = 'en'
    new_settings['asr_model'] = 'medium'
    new_settings['asr_timeout'] = 120
    new_settings['asr_enable_speaker_diarization'] = True
    
    # 3. Save settings
    print("Saving new settings...")
    save_settings(new_settings)
    
    # 4. Load settings again and verify
    loaded_settings = load_settings()
    print(f"Loaded settings. ASR method: {loaded_settings.get('asr_method')}")
    
    assert loaded_settings['asr_method'] == 'whisper_local'
    assert loaded_settings['asr_language'] == 'en'
    assert loaded_settings['asr_model'] == 'medium'
    assert loaded_settings['asr_timeout'] == 120
    assert loaded_settings['asr_enable_speaker_diarization'] is True
    
    print("✅ ASR settings persistence test passed!")
    
    # Restore original settings
    revert_settings = loaded_settings.copy()
    revert_settings['asr_method'] = 'bcut_asr'
    revert_settings['asr_language'] = 'auto'
    save_settings(revert_settings)
    print("Restored ASR method to bcut_asr")

if __name__ == "__main__":
    test_asr_settings()
