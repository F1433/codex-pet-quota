Codex Pet Quota（独立 EXE 版）
================================

本目录可以独立运行，不需要 Python，也不依赖源码目录。

首次安装并注册 Windows 任务计划程序（登录启动、异常自动恢复）：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install-autostart.ps1

立即开启：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1

临时关闭：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1

关闭并移除 Windows 任务计划程序：
  powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall-autostart.ps1

推荐使用 start.ps1 或任务计划程序启动，使监督器独立于 Codex 进程。
也可以直接双击 CodexPetQuota.exe 临时开启。EXE 默认以监督器模式运行：
Codex 启动时启动宠物监听，Codex 退出时停止监听，监听异常退出时自动恢复。

运行日志与额度缓存：
  %LOCALAPPDATA%\CodexPetQuota

程序只在鼠标与宠物交互时，通过本机 Codex App Server 读取额度；
不会调用模型生成接口，不消耗对话 Token。
