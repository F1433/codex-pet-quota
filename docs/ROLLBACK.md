# 卸载与重置

本项目不会修改 Codex 安装目录、登录状态或宠物素材。

## 停止并移除自启动

在项目目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop-background.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall-autostart.ps1
```

随后可以直接删除项目文件夹。

## 清除本地状态

运行后产生的脱敏缓存位于：

```text
%LOCALAPPDATA%\CodexPetQuota
```

完全退出后台程序后，可以删除这个目录。这样会清除额度快照、提醒去重记录和本机随机盐；不会影响 Codex 登录状态。

## 重新安装

重新下载项目，解压到固定目录，然后运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-autostart.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```
