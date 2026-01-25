"""
语音识别工具 - 支持多种语音识别服务
支持本地Whisper、OpenAI API、Azure Speech Services等多种语音识别服务
"""
import logging
import subprocess
import json
import os
import asyncio
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from enum import Enum
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 尝试导入bcut-asr
try:
    from bcut_asr import BcutASR
    from bcut_asr.orm import ResultStateEnum
    BCUT_ASR_AVAILABLE = True
except ImportError:
    BCUT_ASR_AVAILABLE = False
    logger.warning("bcut-asr未安装，将跳过bcut-asr方法")

def _auto_install_bcut_asr():
    """自动安装bcut-asr"""
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # 获取安装脚本路径
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install_bcut_asr.py"
        
        if not script_path.exists():
            logger.error("安装脚本不存在，请手动安装bcut-asr")
            _show_manual_install_guide()
            return False
        
        logger.info("开始自动安装bcut-asr...")
        
        # 运行安装脚本
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=600)  # 10分钟超时
        
        if result.returncode == 0:
            logger.info("✅ bcut-asr自动安装成功")
            return True
        else:
            logger.error(f"❌ bcut-asr自动安装失败: {result.stderr}")
            _show_manual_install_guide()
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ bcut-asr安装超时")
        _show_manual_install_guide()
        return False
    except Exception as e:
        logger.error(f"❌ bcut-asr自动安装失败: {e}")
        _show_manual_install_guide()
        return False

def _show_manual_install_guide():
    """显示手动安装指导"""
    logger.info("📋 手动安装指导:")
    logger.info("1. 安装 ffmpeg:")
    logger.info("   macOS: brew install ffmpeg")
    logger.info("   Ubuntu: sudo apt install ffmpeg")
    logger.info("   Windows: winget install ffmpeg")
    logger.info("2. 安装 bcut-asr:")
    logger.info("   git clone https://github.com/SocialSisterYi/bcut-asr.git")
    logger.info("   cd bcut-asr && pip install .")
    logger.info("3. 运行手动安装脚本:")
    logger.info("   python scripts/manual_install_guide.py")

def _ensure_bcut_asr_available():
    """确保bcut-asr可用，如果不可用则尝试自动安装"""
    global BCUT_ASR_AVAILABLE
    
    if BCUT_ASR_AVAILABLE:
        return True
    
    logger.info("bcut-asr不可用")
    
    # if _auto_install_bcut_asr():
    #     # 重新尝试导入
    #     try:
    #         from bcut_asr import BcutASR
    #         from bcut_asr.orm import ResultStateEnum
    #         BCUT_ASR_AVAILABLE = True
    #         logger.info("✅ bcut-asr安装成功，现在可以使用")
    #         return True
    #     except ImportError:
    #         logger.error("❌ bcut-asr安装后仍无法导入")
    #         return False
    # else:
    #     logger.warning("⚠️ bcut-asr自动安装失败，将使用其他方法")
    #     return False


class SpeechRecognitionMethod(str, Enum):
    """语音识别方法枚举"""
    BCUT_ASR = "bcut_asr"
    WHISPER_LOCAL = "whisper_local"
    OPENAI_API = "openai_api"
    AZURE_SPEECH = "azure_speech"
    GOOGLE_SPEECH = "google_speech"
    ALIYUN_SPEECH = "aliyun_speech"


class LanguageCode(str, Enum):
    """支持的语言代码"""
    # 中文
    CHINESE_SIMPLIFIED = "zh"
    CHINESE_TRADITIONAL = "zh-TW"
    # 英文
    ENGLISH = "en"
    ENGLISH_US = "en-US"
    ENGLISH_UK = "en-GB"
    # 日文
    JAPANESE = "ja"
    # 韩文
    KOREAN = "ko"
    # 法文
    FRENCH = "fr"
    # 德文
    GERMAN = "de"
    # 西班牙文
    SPANISH = "es"
    # 俄文
    RUSSIAN = "ru"
    # 阿拉伯文
    ARABIC = "ar"
    # 葡萄牙文
    PORTUGUESE = "pt"
    # 意大利文
    ITALIAN = "it"
    # 自动检测
    AUTO = "auto"


@dataclass
class SpeechRecognitionConfig:
    """语音识别配置"""
    method: SpeechRecognitionMethod = SpeechRecognitionMethod.BCUT_ASR
    language: LanguageCode = LanguageCode.AUTO
    model: str = "base"  # Whisper模型大小
    timeout: int = 0  # 超时时间（秒），0表示无限制
    output_format: str = "srt"  # 输出格式
    enable_timestamps: bool = True  # 是否启用时间戳
    enable_punctuation: bool = True  # 是否启用标点符号
    enable_speaker_diarization: bool = False  # 是否启用说话人分离
    enable_fallback: bool = True  # 是否启用回退机制
    fallback_method: SpeechRecognitionMethod = SpeechRecognitionMethod.WHISPER_LOCAL  # 回退方法
    
    # OpenAI API 设置
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    def __post_init__(self):
        """验证配置参数"""
        # 验证方法
        if not isinstance(self.method, SpeechRecognitionMethod):
            try:
                self.method = SpeechRecognitionMethod(self.method)
            except ValueError:
                raise ValueError(f"不支持的语音识别方法: {self.method}")
        
        # 验证语言
        if not isinstance(self.language, LanguageCode):
            try:
                self.language = LanguageCode(self.language)
            except ValueError:
                raise ValueError(f"不支持的语言代码: {self.language}")
        
        # 验证模型
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if self.model not in valid_models and self.method == SpeechRecognitionMethod.WHISPER_LOCAL:
            raise ValueError(f"不支持的Whisper模型: {self.model}")
        
        # 验证超时时间
        if self.timeout < 0:
            raise ValueError("超时时间不能为负数")
        
        # 验证输出格式
        valid_formats = ["srt", "vtt", "txt", "json"]
        if self.output_format not in valid_formats:
            raise ValueError(f"不支持的输出格式: {self.output_format}")


class SpeechRecognitionError(Exception):
    """语音识别错误"""
    pass


class SpeechRecognizer:
    """语音识别器，支持多种语音识别服务"""
    
    def __init__(self, config: Optional[SpeechRecognitionConfig] = None):
        self.config = config or SpeechRecognitionConfig()
        self.available_methods = self._check_available_methods()
    
    def _check_available_methods(self) -> Dict[SpeechRecognitionMethod, bool]:
        """检查可用的语音识别方法"""
        methods = {}
        
        # 检查bcut-asr
        methods[SpeechRecognitionMethod.BCUT_ASR] = self._check_bcut_asr_availability()
        
        # 检查本地Whisper
        methods[SpeechRecognitionMethod.WHISPER_LOCAL] = self._check_whisper_availability()
        
        # 检查OpenAI API
        methods[SpeechRecognitionMethod.OPENAI_API] = self._check_openai_availability()
        
        # 检查Azure Speech Services
        methods[SpeechRecognitionMethod.AZURE_SPEECH] = self._check_azure_speech_availability()
        
        # 检查Google Speech-to-Text
        methods[SpeechRecognitionMethod.GOOGLE_SPEECH] = self._check_google_speech_availability()
        
        # 检查阿里云语音识别
        methods[SpeechRecognitionMethod.ALIYUN_SPEECH] = self._check_aliyun_speech_availability()
        
        return methods
    
    def _check_bcut_asr_availability(self) -> bool:
        """检查bcut-asr是否可用，如果不可用则尝试自动安装"""
        return BCUT_ASR_AVAILABLE
        if BCUT_ASR_AVAILABLE:
            return True
        
        # 尝试自动安装
        logger.info("bcut-asr不可用，尝试自动安装...")
        if _ensure_bcut_asr_available():
            return True
        
        logger.warning("bcut-asr不可用且自动安装失败")
        return False
    
    def _check_whisper_availability(self) -> bool:
        """检查本地Whisper是否可用 (支持 faster-whisper 和 openai-whisper)"""
        # 1. 优先检查 faster-whisper (Python包)
        try:
            import faster_whisper
            logger.info("检测到 faster-whisper 已安装")
            return True
        except ImportError:
            pass

        # 2. 检查 whisper (命令行工具)
        try:
            result = subprocess.run(['whisper', '--help'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("检测到 openai-whisper CLI 已安装")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
            
        logger.warning("本地Whisper未安装或不可用 (未检测到 faster-whisper 或 whisper CLI)")
        return False
    
    def _check_openai_availability(self) -> bool:
        """检查OpenAI API是否可用 (仅检查库是否安装)"""
        try:
            import openai
            return True
        except ImportError:
            return False
    
    def _check_azure_speech_availability(self) -> bool:
        """检查Azure Speech Services是否可用"""
        api_key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")
        return api_key is not None and region is not None
    
    def _check_google_speech_availability(self) -> bool:
        """检查Google Speech-to-Text是否可用"""
        # 检查Google Cloud凭证文件
        cred_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_file and Path(cred_file).exists():
            return True
        
        # 检查API密钥
        api_key = os.getenv("GOOGLE_SPEECH_API_KEY")
        return api_key is not None
    
    def _check_aliyun_speech_availability(self) -> bool:
        """检查阿里云语音识别是否可用"""
        access_key = os.getenv("ALIYUN_ACCESS_KEY_ID")
        secret_key = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        app_key = os.getenv("ALIYUN_SPEECH_APP_KEY")
        return access_key is not None and secret_key is not None and app_key is not None
    
    def _extract_audio_from_video(self, video_path: Path, output_dir: Path, audio_format: str = "wav", bitrate: str = "64k") -> Path:
        """
        从视频文件中提取音频
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            audio_format: 音频格式 (wav, mp3)
            bitrate: 比特率 (仅mp3有效)，默认64k
            
        Returns:
            提取的音频文件路径
        """
        try:
            # 检查ffmpeg是否可用
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise SpeechRecognitionError("ffmpeg不可用，请安装ffmpeg")
            
            # 生成音频文件路径
            audio_filename = f"{video_path.stem}_audio.{audio_format}"
            audio_path = output_dir / audio_filename
            
            # 如果音频文件已存在，直接返回
            if audio_path.exists():
                logger.info(f"音频文件已存在: {audio_path}")
                return audio_path
            
            logger.info(f"正在从视频提取音频: {video_path} -> {audio_path}")
            
            # 使用ffmpeg提取音频
            if audio_format == "mp3":
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-vn',  # 不处理视频流
                    '-acodec', 'libmp3lame',
                    '-b:a', bitrate,
                    '-y',  # 覆盖输出文件
                    str(audio_path)
                ]
            else:
                # 默认 wav (pcm_s16le)
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-vn',  # 不处理视频流
                    '-acodec', 'pcm_s16le',  # 使用PCM 16位编码
                    '-ar', '16000',  # 采样率16kHz
                    '-ac', '1',  # 单声道
                    '-y',  # 覆盖输出文件
                    str(audio_path)
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                # 如果mp3编码失败（可能是没有libmp3lame），尝试使用aac
                if audio_format == "mp3" and "Encoder (codec libmp3lame) not found" in result.stderr:
                     logger.warning("未找到libmp3lame编码器，尝试使用aac...")
                     audio_path_aac = audio_path.with_suffix(".m4a")
                     cmd = [
                        'ffmpeg',
                        '-i', str(video_path),
                        '-vn',
                        '-acodec', 'aac',
                        '-b:a', bitrate,
                        '-y',
                        str(audio_path_aac)
                     ]
                     result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                     if result.returncode == 0:
                         return audio_path_aac
                
                raise SpeechRecognitionError(f"音频提取失败: {result.stderr}")
            
            if not audio_path.exists():
                raise SpeechRecognitionError("音频提取失败，输出文件不存在")
            
            logger.info(f"音频提取成功: {audio_path}")
            return audio_path
            
        except subprocess.TimeoutExpired:
            raise SpeechRecognitionError("音频提取超时")
        except Exception as e:
            raise SpeechRecognitionError(f"音频提取失败: {e}")
    
    def _split_audio_file(self, audio_path: Path, segment_duration: int) -> List[Path]:
        """
        使用ffmpeg切分音频文件
        
        Args:
            audio_path: 音频文件路径
            segment_duration: 切分时长（秒）
            
        Returns:
            切分后的文件路径列表
        """
        try:
            output_pattern = str(audio_path.parent / f"{audio_path.stem}_%03d{audio_path.suffix}")
            
            cmd = [
                'ffmpeg',
                '-i', str(audio_path),
                '-f', 'segment',
                '-segment_time', str(segment_duration),
                '-c', 'copy',
                '-y',
                output_pattern
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode != 0:
                raise SpeechRecognitionError(f"音频切分失败: {result.stderr}")
                
            # 获取生成的片段文件
            segment_files = sorted(list(audio_path.parent.glob(f"{audio_path.stem}_*{audio_path.suffix}")))
            # 排除原始文件
            segment_files = [f for f in segment_files if f.name != audio_path.name]
            
            return segment_files
            
        except Exception as e:
            raise SpeechRecognitionError(f"音频切分失败: {e}")

    def _parse_srt_timestamp(self, timestamp: str) -> float:
        """解析SRT时间戳为秒数"""
        # 00:00:00,000
        try:
            time_parts = timestamp.replace(',', '.').split(':')
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = float(time_parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return 0.0

    def _adjust_srt_content(self, srt_content: str, time_offset: float, start_index: int) -> tuple[str, int]:
        """
        调整SRT内容的时间戳和序号
        
        Args:
            srt_content: SRT内容
            time_offset: 时间偏移量（秒）
            start_index: 起始序号
            
        Returns:
            (调整后的SRT内容, 下一个序号)
        """
        lines = srt_content.strip().split('\n')
        adjusted_lines = []
        current_index = start_index
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行
            if not line:
                i += 1
                continue
                
            # 尝试解析序号
            if line.isdigit():
                # 写入新序号
                adjusted_lines.append(str(current_index))
                current_index += 1
                
                # 下一行应该是时间戳
                if i + 1 < len(lines):
                    time_line = lines[i+1].strip()
                    if '-->' in time_line:
                        try:
                            start_str, end_str = time_line.split(' --> ')
                            start_seconds = self._parse_srt_timestamp(start_str) + time_offset
                            end_seconds = self._parse_srt_timestamp(end_str) + time_offset
                            
                            new_time_line = f"{self._format_timestamp(start_seconds)} --> {self._format_timestamp(end_seconds)}"
                            adjusted_lines.append(new_time_line)
                        except Exception:
                             adjusted_lines.append(time_line)
                        i += 2
                    else:
                        # 格式不对，直接复制
                        adjusted_lines.append(lines[i+1])
                        i += 2
                else:
                    i += 1
                
                # 后面的行是字幕内容，直到遇到空行或下一个数字
                while i < len(lines):
                    content_line = lines[i].strip()
                    if not content_line:
                        adjusted_lines.append("")
                        i += 1
                        break
                    # Check if it looks like start of new block
                    if content_line.isdigit() and i+1 < len(lines) and '-->' in lines[i+1]:
                         break
                    
                    adjusted_lines.append(lines[i])
                    i += 1
            else:
                # 不是数字开头，可能是文件头的元数据或其他，直接复制
                adjusted_lines.append(line)
                i += 1
                
        return "\n".join(adjusted_lines), current_index

    def _json_to_srt(self, json_data: Dict[str, Any]) -> str:
        """将OpenAI JSON响应转换为SRT格式"""
        if "segments" not in json_data:
            return ""
        
        segments = json_data["segments"]
        srt_parts = []
        
        for i, segment in enumerate(segments, start=1):
            start = self._format_timestamp(segment.get("start", 0))
            end = self._format_timestamp(segment.get("end", 0))
            text = segment.get("text", "").strip()
            
            srt_parts.append(f"{i}\n{start} --> {end}\n{text}\n")
            
        return "\n".join(srt_parts)

    def generate_subtitle(self, video_path: Path, output_path: Optional[Path] = None, 
                         config: Optional[SpeechRecognitionConfig] = None) -> Path:
        """
        生成字幕文件
        
        Args:
            video_path: 视频文件路径
            output_path: 输出字幕文件路径
            config: 语音识别配置
            
        Returns:
            生成的字幕文件路径
            
        Raises:
            SpeechRecognitionError: 语音识别失败
        """
        if not video_path.exists():
            raise SpeechRecognitionError(f"视频文件不存在: {video_path}")
        
        # 使用传入的配置或默认配置
        config = config or self.config
        
        # 确定输出路径
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}.{config.output_format}"
        
        # 根据配置的方法选择识别服务，支持回退机制
        try:
            if config.method == SpeechRecognitionMethod.BCUT_ASR:
                return self._generate_subtitle_bcut_asr(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.WHISPER_LOCAL:
                return self._generate_subtitle_whisper_local(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.OPENAI_API:
                return self._generate_subtitle_openai_api(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.AZURE_SPEECH:
                return self._generate_subtitle_azure_speech(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.GOOGLE_SPEECH:
                return self._generate_subtitle_google_speech(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.ALIYUN_SPEECH:
                return self._generate_subtitle_aliyun_speech(video_path, output_path, config)
            else:
                raise SpeechRecognitionError(f"不支持的语音识别方法: {config.method}")
        except SpeechRecognitionError as e:
            # 如果启用了回退机制且当前方法不是回退方法，则尝试回退
            if (config.enable_fallback and 
                config.method != config.fallback_method and 
                self.available_methods.get(config.fallback_method, False)):
                
                logger.warning(f"主方法 {config.method} 失败: {e}")
                logger.info(f"尝试回退到 {config.fallback_method}")
                
                # 创建回退配置
                fallback_config = SpeechRecognitionConfig(
                    method=config.fallback_method,
                    language=config.language,
                    model=config.model,
                    timeout=config.timeout,
                    output_format=config.output_format,
                    enable_timestamps=config.enable_timestamps,
                    enable_punctuation=config.enable_punctuation,
                    enable_speaker_diarization=config.enable_speaker_diarization,
                    enable_fallback=False  # 避免无限回退
                )
                
                return self.generate_subtitle(video_path, output_path, fallback_config)
            else:
                raise
    
    def _generate_subtitle_bcut_asr(self, video_path: Path, output_path: Path, 
                                   config: SpeechRecognitionConfig) -> Path:
        """使用bcut-asr生成字幕"""
        # 确保bcut-asr可用
        if not _ensure_bcut_asr_available():
            raise SpeechRecognitionError(
                "bcut-asr不可用且自动安装失败，请手动安装:\n"
                "1. 运行: python scripts/install_bcut_asr.py\n"
                "2. 或手动安装: git clone https://github.com/SocialSisterYi/bcut-asr.git\n"
                "3. 同时确保已安装ffmpeg:\n"
                "   macOS: brew install ffmpeg\n"
                "   Ubuntu: sudo apt install ffmpeg\n"
                "   Windows: winget install ffmpeg"
            )
        
        try:
            logger.info(f"开始使用bcut-asr生成字幕: {video_path}")
            
            # 检查视频文件是否存在
            if not video_path.exists():
                raise SpeechRecognitionError(f"视频文件不存在: {video_path}")
            
            # 检查视频文件大小
            file_size = video_path.stat().st_size
            if file_size == 0:
                raise SpeechRecognitionError(f"视频文件为空: {video_path}")
            
            # 检查文件格式，如果是视频文件需要先提取音频
            audio_path = self._extract_audio_from_video(video_path, output_path.parent)
            
            # 创建BcutASR实例，使用音频文件
            asr = BcutASR(str(audio_path))
            
            # 上传文件
            logger.info("正在上传文件到bcut-asr...")
            asr.upload()
            
            # 创建任务
            logger.info("正在创建识别任务...")
            asr.create_task()
            
            # 轮询检查结果
            logger.info("正在等待识别结果...")
            max_attempts = 60  # 最多等待5分钟（每5秒检查一次）
            attempt = 0
            
            while attempt < max_attempts:
                result = asr.result()
                
                # 判断识别成功
                if result.state == ResultStateEnum.COMPLETE:
                    logger.info("bcut-asr识别完成")
                    break
                elif result.state == ResultStateEnum.FAILED:
                    raise SpeechRecognitionError("bcut-asr识别失败")
                
                # 等待5秒后重试
                import time
                time.sleep(5)
                attempt += 1
                logger.info(f"等待识别结果... ({attempt}/{max_attempts})")
            else:
                raise SpeechRecognitionError("bcut-asr识别超时")
            
            # 解析字幕内容
            subtitle = result.parse()
            
            # 判断是否存在字幕
            if not subtitle.has_data():
                raise SpeechRecognitionError("bcut-asr未识别到有效字幕内容")
            
            # 根据输出格式保存字幕
            if config.output_format == "srt":
                subtitle_content = subtitle.to_srt()
            elif config.output_format == "json":
                subtitle_content = subtitle.to_json()
            elif config.output_format == "lrc":
                subtitle_content = subtitle.to_lrc()
            elif config.output_format == "txt":
                subtitle_content = subtitle.to_txt()
            else:
                # 默认使用srt格式
                subtitle_content = subtitle.to_srt()
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
                
            # 如果输出格式不是SRT，额外保存一份SRT文件
            if config.output_format != "srt":
                srt_path = output_path.with_suffix('.srt')
                try:
                    with open(srt_path, 'w', encoding='utf-8') as f:
                        f.write(subtitle.to_srt())
                    logger.info(f"额外保存SRT文件: {srt_path}")
                except Exception as e:
                    logger.warning(f"无法额外保存SRT文件: {e}")
            
            logger.info(f"bcut-asr字幕生成成功: {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"bcut-asr生成字幕时发生错误: {e}\n"
            error_msg += "可能的原因:\n"
            error_msg += "1. 网络连接问题\n"
            error_msg += "2. 文件格式不支持\n"
            error_msg += "3. 文件过大\n"
            error_msg += "4. bcut-asr服务暂时不可用"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _format_timestamp(self, seconds: float) -> str:
        """转换秒数为SRT时间戳格式 (HH:MM:SS,mmm)"""
        whole_seconds = int(seconds)
        milliseconds = int((seconds - whole_seconds) * 1000)
        
        hours = whole_seconds // 3600
        minutes = (whole_seconds % 3600) // 60
        seconds = whole_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def _generate_subtitle_faster_whisper(self, video_path: Path, output_path: Path, 
                                        config: SpeechRecognitionConfig) -> Path:
        """使用 faster-whisper 生成字幕"""
        try:
            from faster_whisper import WhisperModel
            import torch
        except ImportError:
            raise SpeechRecognitionError("faster-whisper 未安装")

        logger.info(f"开始使用 faster-whisper 生成字幕: {video_path}")
        
        try:
            # 确定运行设备
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            logger.info(f"使用设备: {device}, 计算类型: {compute_type}")
            
            # 加载模型
            model_size = config.model
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
            
            # 转录
            segments, info = model.transcribe(
                str(video_path), 
                beam_size=5,
                language=None if config.language == LanguageCode.AUTO else config.language,
                vad_filter=True  # 启用VAD过滤静音
            )
            
            logger.info(f"检测到语言: {info.language}, 概率: {info.language_probability:.2f}")
            
            # 生成SRT内容
            srt_lines = []
            for i, segment in enumerate(segments, start=1):
                start_time = self._format_timestamp(segment.start)
                end_time = self._format_timestamp(segment.end)
                text = segment.text.strip()
                
                srt_lines.append(f"{i}")
                srt_lines.append(f"{start_time} --> {end_time}")
                srt_lines.append(f"{text}\n")
            
            # 写入文件
            srt_content = "\n".join(srt_lines)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
                
            # 如果输出路径不是.srt结尾，额外保存一份.srt
            if output_path.suffix.lower() != ".srt":
                srt_path = output_path.with_suffix('.srt')
                try:
                    with open(srt_path, "w", encoding="utf-8") as f:
                        f.write(srt_content)
                    logger.info(f"额外保存SRT文件: {srt_path}")
                except Exception as e:
                    logger.warning(f"无法额外保存SRT文件: {e}")
                
            logger.info(f"faster-whisper 字幕生成成功: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"faster-whisper 执行失败: {e}")
            raise SpeechRecognitionError(f"faster-whisper 执行失败: {e}")

    def _generate_subtitle_whisper_local(self, video_path: Path, output_path: Path, 
                                       config: SpeechRecognitionConfig) -> Path:
        """使用本地Whisper生成字幕 (优先使用 faster-whisper)"""
        # 尝试使用 faster-whisper
        try:
            import faster_whisper
            return self._generate_subtitle_faster_whisper(video_path, output_path, config)
        except ImportError:
            pass

        # Fallback 到命令行 whisper
        if not self.available_methods[SpeechRecognitionMethod.WHISPER_LOCAL]:
            raise SpeechRecognitionError(
                "本地Whisper不可用，请安装 faster-whisper 或 openai-whisper:\n"
                "pip install faster-whisper\n"
                "或\n"
                "pip install openai-whisper"
            )
        
        try:
            logger.info(f"开始使用本地Whisper CLI生成字幕: {video_path}")
            
            # 检查视频文件是否存在
            if not video_path.exists():
                raise SpeechRecognitionError(f"视频文件不存在: {video_path}")
            
            # 检查视频文件大小
            file_size = video_path.stat().st_size
            if file_size == 0:
                raise SpeechRecognitionError(f"视频文件为空: {video_path}")
            
            # 构建whisper命令
            cmd = [
                'whisper',
                str(video_path),
                '--output_dir', str(output_path.parent),
                '--output_format', config.output_format,
                '--model', config.model
            ]
            
            # 添加语言参数
            if config.language != LanguageCode.AUTO:
                cmd.extend(['--language', config.language])
            
            # 添加超时处理
            logger.info(f"执行Whisper命令: {' '.join(cmd)}")
            
            # 根据超时配置决定是否设置超时
            if config.timeout > 0:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=config.timeout,
                    cwd=str(video_path.parent)  # 设置工作目录
                )
            else:
                # 无超时限制
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    cwd=str(video_path.parent)  # 设置工作目录
                )
            
            if result.returncode == 0:
                # 检查输出文件是否存在
                if output_path.exists():
                    logger.info(f"本地Whisper字幕生成成功: {output_path}")
                    
                    # 如果输出不是SRT，尝试转换
                    if output_path.suffix.lower() != ".srt":
                        try:
                            srt_path = output_path.with_suffix('.srt')
                            if not srt_path.exists():
                                if output_path.suffix.lower() == ".json":
                                    # 尝试从JSON转换
                                    import json
                                    with open(output_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                    
                                    # 尝试转换
                                    srt_content = self._json_to_srt(data)
                                    if srt_content:
                                        with open(srt_path, 'w', encoding='utf-8') as f:
                                            f.write(srt_content)
                                        logger.info(f"已从JSON转换并保存SRT文件: {srt_path}")
                        except Exception as e:
                            logger.warning(f"尝试转换SRT失败: {e}")
                            
                    return output_path
                else:
                    # 尝试查找其他可能的输出文件
                    possible_outputs = list(output_path.parent.glob(f"{video_path.stem}*.{config.output_format}"))
                    if possible_outputs:
                        actual_output = possible_outputs[0]
                        logger.info(f"找到Whisper输出文件: {actual_output}")
                        return actual_output
                    else:
                        raise SpeechRecognitionError(f"Whisper执行成功但未找到输出文件: {output_path}")
            else:
                error_msg = f"本地Whisper执行失败 (返回码: {result.returncode}):\n"
                if result.stderr:
                    error_msg += f"错误信息: {result.stderr}\n"
                if result.stdout:
                    error_msg += f"输出信息: {result.stdout}"
                
                # 提供具体的错误解决建议
                if "command not found" in result.stderr:
                    error_msg += "\n\n解决方案: 请安装whisper: pip install openai-whisper"
                elif "ffmpeg" in result.stderr.lower():
                    error_msg += "\n\n解决方案: 请安装ffmpeg:\n  macOS: brew install ffmpeg\n  Ubuntu: sudo apt install ffmpeg"
                elif "timeout" in result.stderr.lower():
                    error_msg += f"\n\n解决方案: 视频处理超时，请尝试使用更小的模型 (--model tiny) 或增加超时时间"
                
                logger.error(error_msg)
                raise SpeechRecognitionError(error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = f"本地Whisper执行超时（{config.timeout}秒）\n"
            error_msg += "解决方案:\n"
            error_msg += "1. 使用更小的模型: --model tiny\n"
            error_msg += "2. 增加超时时间\n"
            error_msg += "3. 检查视频文件是否损坏"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
        except FileNotFoundError:
            error_msg = "找不到whisper命令\n"
            error_msg += "解决方案:\n"
            error_msg += "1. 安装whisper: pip install openai-whisper\n"
            error_msg += "2. 确保whisper在PATH中: which whisper\n"
            error_msg += "3. 重新安装: pip uninstall openai-whisper && pip install openai-whisper"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
        except Exception as e:
            error_msg = f"本地Whisper生成字幕时发生错误: {e}\n"
            error_msg += "请检查:\n"
            error_msg += "1. 视频文件格式是否支持\n"
            error_msg += "2. 系统是否有足够的内存\n"
            error_msg += "3. 是否有足够的磁盘空间"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_openai_api(self, video_path: Path, output_path: Path, 
                                    config: SpeechRecognitionConfig) -> Path:
        """使用OpenAI API生成字幕"""
        if not self.available_methods[SpeechRecognitionMethod.OPENAI_API]:
            raise SpeechRecognitionError("OpenAI库未安装，请执行: pip install openai")
        
        api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
             raise SpeechRecognitionError("未配置OpenAI API Key，请在设置中配置或设置环境变量OPENAI_API_KEY")

        base_url = config.openai_base_url or os.getenv("OPENAI_BASE_URL")
        
        try:
            import openai
            logger.info(f"开始使用OpenAI API生成字幕: {video_path}")
            
            # 提取音频 (使用mp3格式以节省空间，48kbps)
            # OpenAI 限制 25MB
            # 48kbps 下，25MB 大约可以存储 72 分钟的音频
            # 设置切片时间为 20 分钟 (1200秒)
            audio_path = self._extract_audio_from_video(video_path, output_path.parent, audio_format="mp3", bitrate="48k")
            
            # 检查音频文件大小（OpenAI限制25MB）
            file_size = audio_path.stat().st_size
            max_size = 25 * 1024 * 1024
            
            # 初始化客户端
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            
            client = openai.OpenAI(**client_kwargs)
            
            transcript = ""
            
            # 确定模型名称
            model_name = "whisper-1"
            # 如果config.model不是本地模型的标准名称，且不为空，则使用用户配置的
            local_models = ["tiny", "base", "small", "medium", "large", "turbo"]
            if config.model and config.model not in local_models:
                 model_name = config.model
            
            # 确定response_format
            response_format = "srt"
            if config.output_format == "vtt":
                response_format = "vtt"
            elif config.output_format == "json":
                response_format = "json"
            elif config.output_format == "txt":
                response_format = "text"
            
            if file_size <= max_size:
                # 文件小于25MB，直接处理
                logger.info(f"音频文件大小 ({file_size / 1024 / 1024:.2f}MB) 未超过25MB，直接处理")
                with open(audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model=model_name, 
                        file=audio_file,
                        response_format=response_format,
                        language=None if config.language == LanguageCode.AUTO else config.language.value
                    )
                    
                    # 检查是否返回了JSON但我们想要SRT
                    if response_format == "srt":
                        content_str = str(transcript)
                        # logger.warning(content_str)
                        if content_str.strip().startswith("{") and "segments" in content_str:
                            try:
                                import json
                                data = json.loads(content_str)
                                if "segments" in data:
                                    logger.warning("OpenAI API返回了JSON格式，正在转换为SRT...")
                                    transcript = self._json_to_srt(data)
                            except Exception as e:
                                logger.warning(f"尝试转换JSON为SRT失败: {e}")
            else:
                # 文件大于25MB，需要切分
                logger.warning(f"音频文件大小 ({file_size / 1024 / 1024:.2f}MB) 超过25MB限制，开始切分...")
                
                # 切分音频 (每20分钟一段)
                segment_duration = 1200
                segment_files = self._split_audio_file(audio_path, segment_duration)
                
                logger.info(f"音频已切分为 {len(segment_files)} 个片段，开始逐个识别...")
                
                full_transcript = ""
                current_index_offset = 1
                
                for i, segment_file in enumerate(segment_files):
                    logger.info(f"正在识别片段 {i+1}/{len(segment_files)}: {segment_file.name}")
                    
                    try:
                        with open(segment_file, "rb") as audio_file:
                            segment_transcript = client.audio.transcriptions.create(
                                    model=model_name, 
                                    file=audio_file,
                                    response_format=response_format,
                                    language=None if config.language == LanguageCode.AUTO else config.language.value
                                )
                            
                            # 检查是否返回了JSON但我们想要SRT
                            if response_format == "srt":
                                content_str = str(segment_transcript)
                                # logger.warning(content_str)
                                if content_str.strip().startswith("{") and "segments" in content_str:
                                    try:
                                        import json
                                        data = json.loads(content_str)
                                        
                                        if "segments" in data:
                                            logger.warning(f"OpenAI API片段 {i+1} 返回了JSON格式，正在转换为SRT...")
                                            segment_transcript = self._json_to_srt(data)
                                    except Exception:
                                        pass

                            # 只有SRT格式才支持合并和调整时间戳
                            if response_format == "srt":
                                # 合并结果
                                time_offset = i * segment_duration
                                adjusted_srt, next_index = self._adjust_srt_content(segment_transcript, time_offset, current_index_offset)
                                full_transcript += adjusted_srt + "\n\n"
                                current_index_offset = next_index
                            else:
                                # 其他格式直接拼接（可能不完美，但暂不支持复杂合并）
                                full_transcript += str(segment_transcript) + "\n"
                        
                    except Exception as e:
                        logger.error(f"识别片段 {segment_file.name} 失败: {e}")
                        raise
                    finally:
                        # 清理片段文件
                        try:
                            if segment_file.exists():
                                os.remove(segment_file)
                        except Exception as e:
                            logger.warning(f"无法删除临时片段文件 {segment_file}: {e}")
                
                transcript = full_transcript.strip()
            
            # 写入文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(transcript))
                
            logger.info(f"OpenAI API字幕生成成功: {output_path}")

            # 如果输出格式不是SRT，额外保存一份SRT文件
            if config.output_format != "srt":
                srt_path = output_path.with_suffix('.srt')
                try:
                    srt_content = None
                    if response_format == "json":
                        try:
                            # 尝试解析JSON内容
                            import json
                            data = json.loads(str(transcript))
                            # 只有包含segments的JSON才能转换为SRT
                            if "segments" in data:
                                srt_content = self._json_to_srt(data)
                            else:
                                logger.warning("OpenAI API返回的JSON不包含segments，无法转换为SRT")
                        except Exception:
                            pass
                    elif response_format == "vtt":
                        # 尝试将VTT内容转换为SRT
                        content = str(transcript)
                        # 简单的VTT转SRT实现
                        lines = content.splitlines()
                        srt_lines = []
                        counter = 1
                        is_header = True
                        for line in lines:
                            if is_header:
                                if line.strip() == "WEBVTT":
                                    continue
                                if line.strip() == "":
                                    is_header = False
                                continue
                            
                            if "-->" in line:
                                srt_lines.append(str(counter))
                                srt_lines.append(line.replace(".", ","))
                                counter += 1
                            else:
                                srt_lines.append(line)
                        
                        srt_content = "\n".join(srt_lines)
                    
                    if srt_content:
                        with open(srt_path, 'w', encoding='utf-8') as f:
                            f.write(srt_content)
                        logger.info(f"额外保存SRT文件: {srt_path}")
                except Exception as e:
                    logger.warning(f"无法额外保存SRT文件: {e}")

            return output_path
            
        except Exception as e:
            error_msg = f"OpenAI API生成字幕时发生错误: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_azure_speech(self, video_path: Path, output_path: Path, 
                                      config: SpeechRecognitionConfig) -> Path:
        """使用Azure Speech Services生成字幕"""
        if not self.available_methods[SpeechRecognitionMethod.AZURE_SPEECH]:
            raise SpeechRecognitionError("Azure Speech Services不可用，请设置AZURE_SPEECH_KEY和AZURE_SPEECH_REGION环境变量")
        
        try:
            logger.info(f"开始使用Azure Speech Services生成字幕: {video_path}")
            
            # 这里需要实现Azure Speech Services调用
            raise SpeechRecognitionError("Azure Speech Services功能暂未实现，请使用本地Whisper")
            
        except Exception as e:
            error_msg = f"Azure Speech Services生成字幕时发生错误: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_google_speech(self, video_path: Path, output_path: Path, 
                                       config: SpeechRecognitionConfig) -> Path:
        """使用Google Speech-to-Text生成字幕"""
        if not self.available_methods[SpeechRecognitionMethod.GOOGLE_SPEECH]:
            raise SpeechRecognitionError("Google Speech-to-Text不可用，请设置GOOGLE_APPLICATION_CREDENTIALS或GOOGLE_SPEECH_API_KEY环境变量")
        
        try:
            logger.info(f"开始使用Google Speech-to-Text生成字幕: {video_path}")
            
            # 这里需要实现Google Speech-to-Text调用
            raise SpeechRecognitionError("Google Speech-to-Text功能暂未实现，请使用本地Whisper")
            
        except Exception as e:
            error_msg = f"Google Speech-to-Text生成字幕时发生错误: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_aliyun_speech(self, video_path: Path, output_path: Path, 
                                       config: SpeechRecognitionConfig) -> Path:
        """使用阿里云语音识别生成字幕"""
        if not self.available_methods[SpeechRecognitionMethod.ALIYUN_SPEECH]:
            raise SpeechRecognitionError("阿里云语音识别不可用，请设置ALIYUN_ACCESS_KEY_ID、ALIYUN_ACCESS_KEY_SECRET和ALIYUN_SPEECH_APP_KEY环境变量")
        
        try:
            logger.info(f"开始使用阿里云语音识别生成字幕: {video_path}")
            
            # 这里需要实现阿里云语音识别调用
            raise SpeechRecognitionError("阿里云语音识别功能暂未实现，请使用本地Whisper")
            
        except Exception as e:
            error_msg = f"阿里云语音识别生成字幕时发生错误: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def get_available_methods(self) -> Dict[SpeechRecognitionMethod, bool]:
        """获取可用的语音识别方法"""
        return self.available_methods.copy()
    
    def get_supported_languages(self) -> List[LanguageCode]:
        """获取支持的语言列表"""
        return list(LanguageCode)
    
    def get_whisper_models(self) -> List[str]:
        """获取可用的Whisper模型列表"""
        return ["tiny", "base", "small", "medium", "large"]


def generate_subtitle_for_video(video_path: Path, output_path: Optional[Path] = None, 
                               method: str = "auto", language: str = "auto", 
                               model: str = "base", output_format: str = "srt",
                               enable_fallback: bool = True,
                               openai_api_key: Optional[str] = None,
                               openai_base_url: Optional[str] = None) -> Path:
    """
    为视频生成字幕文件的便捷函数
    
    Args:
        video_path: 视频文件路径
        output_path: 输出字幕文件路径
        method: 生成方法 ("auto", "bcut_asr", "whisper_local", "openai_api", "azure_speech", "google_speech", "aliyun_speech")
        language: 语言代码
        model: Whisper模型大小（仅对whisper_local有效）
        output_format: 输出格式 ("srt", "vtt", "txt", "json")
        enable_fallback: 是否启用回退机制
        openai_api_key: OpenAI API Key
        openai_base_url: OpenAI Base URL
        
    Returns:
        生成的字幕文件路径
        
    Raises:
        SpeechRecognitionError: 语音识别失败
    """
    # 创建配置
    config = SpeechRecognitionConfig(
        method=SpeechRecognitionMethod(method) if method != "auto" else SpeechRecognitionMethod.BCUT_ASR,
        language=LanguageCode(language),
        model=model,
        output_format=output_format,
        enable_fallback=enable_fallback,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url
    )
    
    recognizer = SpeechRecognizer()
    
    if method == "auto":
        # 自动选择最佳方法
        available_methods = recognizer.get_available_methods()
        
        # 按优先级选择方法（bcut-asr优先，因为速度更快）
        priority_methods = [
            SpeechRecognitionMethod.WHISPER_LOCAL,
            # SpeechRecognitionMethod.BCUT_ASR,
            SpeechRecognitionMethod.OPENAI_API,
            SpeechRecognitionMethod.AZURE_SPEECH,
            SpeechRecognitionMethod.GOOGLE_SPEECH,
            SpeechRecognitionMethod.ALIYUN_SPEECH
        ]
        
        for priority_method in priority_methods:
            if available_methods.get(priority_method, False):
                config.method = priority_method
                break
        else:
            raise SpeechRecognitionError("没有可用的语音识别服务，请安装whisper或配置API密钥")
    
    return recognizer.generate_subtitle(video_path, output_path, config)


def get_available_speech_recognition_methods() -> Dict[str, bool]:
    """
    获取可用的语音识别方法
    
    Returns:
        可用方法字典
    """
    recognizer = SpeechRecognizer()
    available_methods = recognizer.get_available_methods()
    
    return {
        method.value: available 
        for method, available in available_methods.items()
    }


def get_supported_languages() -> List[str]:
    """
    获取支持的语言列表
    
    Returns:
        支持的语言代码列表
    """
    return [lang.value for lang in LanguageCode]


def get_whisper_models() -> List[str]:
    """
    获取可用的Whisper模型列表
    
    Returns:
        Whisper模型列表
    """
    return ["tiny", "base", "small", "medium", "large"]
