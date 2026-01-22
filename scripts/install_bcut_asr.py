#!/usr/bin/env python3
"""
自动安装 bcut-asr 模块
"""
import os
import sys
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def check_bcut_asr_installed():
    """检查 bcut-asr 是否已安装"""
    try:
        import bcut_asr
        from bcut_asr import BcutASR
        from bcut_asr.orm import ResultStateEnum
        logger.info("✅ bcut-asr 已安装")
        return True
    except ImportError:
        logger.info("❌ bcut-asr 未安装")
        return False

def check_ffmpeg_installed():
    """检查 ffmpeg 是否已安装"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ ffmpeg 已安装")
            return True
        else:
            logger.warning("❌ ffmpeg 未正确安装")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.warning("❌ ffmpeg 未安装")
        return False

def install_ffmpeg():
    """安装 ffmpeg"""
    logger.info("开始安装 ffmpeg...")
    
    system = sys.platform.lower()
    
    try:
        if system == "darwin":  # macOS
            logger.info("检测到 macOS 系统，使用 Homebrew 安装 ffmpeg")
            result = subprocess.run(['brew', 'install', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("✅ ffmpeg 安装成功")
                return True
            else:
                logger.error(f"❌ ffmpeg 安装失败: {result.stderr}")
                return False
                
        elif system == "linux":
            logger.info("检测到 Linux 系统，使用 apt 安装 ffmpeg")
            result = subprocess.run(['sudo', 'apt', 'update'], 
                                  capture_output=True, text=True, timeout=60)
            result = subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("✅ ffmpeg 安装成功")
                return True
            else:
                logger.error(f"❌ ffmpeg 安装失败: {result.stderr}")
                return False
                
        elif system == "win32":
            logger.info("检测到 Windows 系统，使用 winget 安装 ffmpeg")
            result = subprocess.run(['winget', 'install', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("✅ ffmpeg 安装成功")
                return True
            else:
                logger.error(f"❌ ffmpeg 安装失败: {result.stderr}")
                logger.info("请手动安装 ffmpeg: https://ffmpeg.org/download.html")
                return False
        else:
            logger.error(f"❌ 不支持的操作系统: {system}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ ffmpeg 安装超时")
        return False
    except Exception as e:
        logger.error(f"❌ ffmpeg 安装失败: {e}")
        return False

def install_bcut_asr():
    """安装 bcut-asr"""
    logger.info("开始安装 bcut-asr...")
    
    # 确定项目根目录和 tools 目录
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    tools_dir = project_root / "tools"
    tools_dir.mkdir(exist_ok=True)
    
    bcut_asr_path = tools_dir / "bcut-asr"
    
    try:
        # 尝试多种方式克隆仓库
        clone_success = False
        
        if bcut_asr_path.exists():
            logger.info(f"bcut-asr 目录已存在: {bcut_asr_path}")
            # 这里可以添加 git pull 更新逻辑，或者直接认为已克隆
            if (bcut_asr_path / ".git").exists():
                 logger.info("检测到 git 仓库，尝试更新...")
                 try:
                     subprocess.run(['git', 'pull'], cwd=bcut_asr_path, capture_output=True, timeout=30)
                 except:
                     pass # 忽略更新失败
                 clone_success = True
            else:
                 # 目录存在但不是git仓库？可能是之前的残留或非git下载
                 logger.warning("目录存在但可能不完整，尝试继续安装...")
                 clone_success = True 
        else:
            # 方式1: 优先使用 wget.la 代理克隆
            logger.info("正在克隆 bcut-asr 仓库 (wget.la 代理)...")
            result = subprocess.run([
                'git', 'clone',
                'https://wget.la/https://github.com/SocialSisterYi/bcut-asr.git',
                str(bcut_asr_path)
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("✅ 仓库克隆成功 (wget.la 代理)")
                clone_success = True
            else:
                logger.warning(f"wget.la 代理克隆失败: {result.stderr}")
                
                # 方式2: 尝试直接 HTTPS 克隆
                logger.info("尝试直接 HTTPS 克隆...")
                result = subprocess.run([
                    'git', 'clone', 
                    'https://github.com/SocialSisterYi/bcut-asr.git',
                    str(bcut_asr_path)
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    logger.info("✅ 仓库克隆成功 (HTTPS)")
                    clone_success = True
                else:
                    logger.warning(f"HTTPS 克隆失败: {result.stderr}")
                
                    # 方式3: 使用 SSH
                    logger.info("尝试使用 SSH 克隆...")
                    result = subprocess.run([
                        'git', 'clone', 
                        'git@github.com:SocialSisterYi/bcut-asr.git',
                        str(bcut_asr_path)
                    ], capture_output=True, text=True, timeout=120)
                    
                    if result.returncode == 0:
                        logger.info("✅ 仓库克隆成功 (SSH)")
                        clone_success = True
                    else:
                        logger.warning(f"SSH 克隆失败: {result.stderr}")
        
        if not clone_success:
            logger.error("❌ 所有克隆方式都失败")
            logger.info("请检查:")
            logger.info("  1. 网络连接是否正常")
            logger.info("  2. 是否能够访问 GitHub")
            logger.info("  3. 防火墙设置")
            return False
        
        # 检查是否有 poetry
        try:
            subprocess.run(['poetry', '--version'], 
                         capture_output=True, text=True, timeout=10)
            has_poetry = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            has_poetry = False
        
        if has_poetry:
            # 使用 poetry 安装
            logger.info("使用 poetry 安装 bcut-asr...")
            result = subprocess.run([
                'poetry', 'lock'
            ], cwd=bcut_asr_path, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.warning(f"poetry lock 失败: {result.stderr}")
                logger.info("尝试使用 pip 安装...")
                return install_bcut_asr_with_pip(bcut_asr_path)
            
            result = subprocess.run([
                'poetry', 'build', '-f', 'wheel'
            ], cwd=bcut_asr_path, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.warning(f"poetry build 失败: {result.stderr}")
                logger.info("尝试使用 pip 安装...")
                return install_bcut_asr_with_pip(bcut_asr_path)
            
            # 查找生成的 wheel 文件
            dist_path = bcut_asr_path / "dist"
            wheel_files = list(dist_path.glob("*.whl"))
            
            if not wheel_files:
                logger.warning("未找到 wheel 文件，尝试使用 pip 安装...")
                return install_bcut_asr_with_pip(bcut_asr_path)
            
            wheel_file = wheel_files[0]
            logger.info(f"找到 wheel 文件: {wheel_file}")
            
            # 安装 wheel 文件
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', str(wheel_file)
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("✅ bcut-asr 安装成功")
                return True
            else:
                logger.error(f"❌ bcut-asr 安装失败: {result.stderr}")
                return False
        else:
            # 使用 pip 安装
            logger.info("poetry 未安装，使用 pip 安装...")
            return install_bcut_asr_with_pip(bcut_asr_path)
            
    except subprocess.TimeoutExpired:
        logger.error("❌ bcut-asr 安装超时")
        return False
    except Exception as e:
        logger.error(f"❌ bcut-asr 安装失败: {e}")
        return False

def install_bcut_asr_with_pip(bcut_asr_path):
    """使用 pip 安装 bcut-asr"""
    try:
        logger.info("使用 pip 从源码安装 bcut-asr...")
        # 第一次尝试：默认源
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', str(bcut_asr_path)
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("✅ bcut-asr 安装成功")
            return True
        
        logger.warning(f"默认源安装失败: {result.stderr}")
        logger.info("尝试使用清华镜像源安装...")
        
        # 第二次尝试：清华源
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', str(bcut_asr_path),
            '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info("✅ bcut-asr 安装成功 (镜像源)")
            return True
        else:
            logger.error(f"❌ bcut-asr 安装失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ pip 安装失败: {e}")
        return False

def install_dependencies():
    """安装所有依赖"""
    logger.info("开始安装 bcut-asr 相关依赖...")
    
    # 检查并安装 ffmpeg
    if not check_ffmpeg_installed():
        logger.info("ffmpeg 未安装，开始安装...")
        if not install_ffmpeg():
            logger.warning("⚠️ ffmpeg 安装失败，请手动安装")
            logger.info("安装指南:")
            logger.info("  macOS: brew install ffmpeg")
            logger.info("  Ubuntu: sudo apt install ffmpeg")
            logger.info("  Windows: winget install ffmpeg")
    
    # 检查并安装 bcut-asr
    if not check_bcut_asr_installed():
        logger.info("bcut-asr 未安装，开始安装...")
        if not install_bcut_asr():
            logger.error("❌ bcut-asr 安装失败")
            return False
    
    logger.info("🎉 所有依赖安装完成！")
    return True

def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("开始自动安装 bcut-asr 依赖...")
    
    success = install_dependencies()
    
    if success:
        logger.info("✅ 安装完成！现在可以使用 bcut-asr 进行语音识别了")
        return True
    else:
        logger.error("❌ 安装失败，请检查网络连接和系统权限")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
