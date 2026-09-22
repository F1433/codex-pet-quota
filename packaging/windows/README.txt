Codex Pet Quota（独立 EXE 版）
================================

本目录可以独立运行，不需要 Python，也不依赖源码目录。

首次安装并开启 Windows 登录自启动：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install-autostart.ps1

立即开启：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1

临时关闭：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1

关闭并取消 Windows 登录自启动：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall-autostart.ps1

也可以直接双击 CodexPetQuota.exe 开启。EXE 默认以监督器模式运行：
Codex 启动时启动宠物监听，Codex 退出时停止监听，监听异常退出时自动恢复。

运行日志与额度缓存：
  %LOCALAPPDATA%\CodexPetQuota

程序只在鼠标与宠物交互时，通过本机 Codex App Server 读取额度；
不会调用模型生成接口，不消耗对话 Token。
