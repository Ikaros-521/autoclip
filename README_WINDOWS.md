# AutoClip Windows 一键部署指南

本指南将帮助你在 Windows 环境下部署和迁移 AutoClip 系统。

## 目录结构要求

为了实现“解压即用”的便携性，请确保目录结构如下：

```
autoclip/
  ├── start_autoclip.bat      # 启动脚本
  ├── stop_autoclip.bat       # 停止脚本
  ├── backend/                # 后端代码
  ├── frontend/               # 前端代码
  ├── tools/
  │   ├── redis/              # Redis 目录 (需要手动放置)
  │   │   └── redis-server.exe
  │   └── ffmpeg/             # FFmpeg 目录 (可选，推荐)
  │       └── bin/
  │           └── ffmpeg.exe
  ├── venv/                   # Python 虚拟环境 (自动生成)
  └── ...
```

## 首次安装准备

在运行启动脚本之前，你需要准备以下环境：

1.  **安装 Python**: 建议安装 Python 3.10 或更高版本，并勾选 "Add Python to PATH"。
2.  **安装 Node.js**: 用于运行前端服务。
3.  **配置 Redis (重要)**:
    *   由于 Windows 没有官方 Redis，为了便携性，请下载 Windows 版本的 Redis。
    *   推荐下载: [Redis-x64-3.0.504.zip](https://github.com/microsoftarchive/redis/releases) (虽然较旧但足够稳定且免安装) 或其他 Windows 构建版本。
    *   在项目根目录下创建一个 `tools` 文件夹。
    *   在 `tools` 下创建一个 `redis` 文件夹。
    *   将下载的 Redis 解压到 `tools/redis/` 目录中，确保 `redis-server.exe` 位于 `tools/redis/redis-server.exe`。
4.  **配置 FFmpeg (推荐)**:
    *   虽然脚本会尝试自动安装 FFmpeg，但为了保证稳定性，建议手动下载。
    *   下载 [FFmpeg Windows build](https://www.gyan.dev/ffmpeg/builds/) (例如 `ffmpeg-git-full.7z`)。
    *   解压后，将其中的 `bin` 文件夹放到 `tools/ffmpeg/` 下。
    *   最终路径应为: `tools/ffmpeg/bin/ffmpeg.exe`。

## 启动系统

双击运行 `start_autoclip.bat`。

脚本会自动执行以下操作：
1.  检查 Python 和 Node.js 环境。
2.  自动创建 Python 虚拟环境 (`venv`) 并安装依赖 (首次运行可能需要几分钟)。
3.  启动 Redis 服务。
4.  启动 Celery 任务队列 (使用 `solo` 模式以兼容 Windows)。
5.  启动后端 API 服务。
6.  安装前端依赖并启动前端服务。
7.  自动打开浏览器访问系统。

## 停止系统

双击运行 `stop_autoclip.bat`。

此脚本会根据窗口标题和端口尝试关闭所有相关服务。

## 迁移指南

如果你需要将配置好的 AutoClip 发送给其他人使用：

1.  运行 `stop_autoclip.bat` 停止所有服务。
2.  **可选**: 删除 `venv` 文件夹和 `frontend/node_modules` 文件夹以减小压缩包体积（接收方首次启动时会自动重新安装，但需要联网）。
    *   如果不删除，接收方的文件路径必须与你的一致，否则 `venv` 可能会失效。**建议删除 `venv` 让对方重新生成。**
3.  确保 `tools/redis` 里面包含 Redis 可执行文件。
4.  将整个 `autoclip` 文件夹压缩为 `.zip` 或 `.7z`。
5.  接收方解压后，直接运行 `start_autoclip.bat` 即可。

## 常见问题

*   **Celery 启动失败**: 确保脚本中使用了 `--pool=solo` 参数。
*   **依赖安装失败**: 请检查网络连接，或尝试配置国内镜像源。
*   **端口占用**: 默认使用 8000 (后端), 3000 (前端), 6379 (Redis)。如果端口被占用，脚本可能会报错，请先关闭占用端口的程序。
