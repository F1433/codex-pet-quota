# Codex 宠物周额度伴随条

一个面向 Windows Codex 桌面客户端的轻量伴随程序：鼠标悬停或拖动官方宠物时，在宠物上方短暂显示 Codex 每周剩余额度与相对重置时间。

> 本项目是社区工具，并非 OpenAI 官方项目。它不会修改 Codex 安装文件，也不会调用模型生成接口。

![白色胶囊条预览](docs/pill-preview.png)

## 功能

- 悬停宠物约 0.1 秒或左键拖动时显示，移开约 0.35 秒后隐藏。
- 拖动期间按鼠标位移约 60 FPS 跟随，不等待最终坐标落盘。
- 只显示 `limitId=codex` 的每周额度，不混入五小时或模型专用额度。
- 30 秒内重复交互复用缓存；没有宠物交互时不查询额度。
- `pythonw.exe` 无控制台运行、单实例保护、Windows 登录自启动与异常自动恢复。
- 监督进程绑定 Codex 桌面生命周期：Codex 启动时拉起监听，退出时停止，重新启动后自动恢复。
- 高 DPI 圆角白色胶囊条，不抢焦点、不挡住宠物操作。

## 使用条件

- Windows 10 或 Windows 11。
- 已安装并登录 Codex 桌面客户端，且已经开启官方宠物。
- Python 3.9 或更高版本，安装时包含 Tk（Windows 官方 Python 默认包含）。
- Codex CLI/App Server 可用。程序会先查找 `PATH` 中的 `codex.exe`，再查找 Codex 桌面客户端的本地 CLI。

验证 Python：

```powershell
python --version
python -m tkinter
```

第二条命令能打开一个 Tk 测试窗口即表示环境正常。

## 下载与首次安装

### 方法一：下载 ZIP

1. 点击 GitHub 页面右上方 **Code → Download ZIP**。
2. 解压到一个长期不移动的位置，例如 `D:\Tools\codex-pet-quota`。
3. 在解压目录空白处按住 Shift 并右键，选择“在终端中打开”。
4. 依次运行：

```powershell
python -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Once
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-autostart.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

### 方法二：使用 Git

```powershell
git clone https://github.com/F1433/codex-pet-quota.git
cd codex-pet-quota
python -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-autostart.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

安装登录启动项后会立即启动一个轻量监督进程；以后每次登录 Windows 也会静默启动。监督进程检测到 Codex 桌面端后才拉起宠物监听，Codex 退出时停止监听，重新启动 Codex 后自动恢复，不需要手动运行。

## 日常使用

1. 打开 Codex 桌面客户端并开启宠物。
2. 将鼠标停在宠物上约 0.1 秒，或按住左键拖动宠物。
3. 宠物上方会显示类似 `周剩余 66%｜6天后重置` 的白色胶囊条。

监督进程和后台监听启动时都不会读取额度。第一次有效宠物交互才会连接官方 Codex App Server；持续悬停时最多每 30 秒刷新一次。

## 管理命令

```powershell
# 启动无控制台 Codex 生命周期监督
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1

# 读取一次脱敏额度结果
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Once

# 只检查 Codex 窗口，不读取额度
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -DiagnoseWindows

# 停止监督进程和宠物监听
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop-background.ps1

# 移除 Windows 登录自启动
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall-autostart.ps1
```

如果移动了项目文件夹，需要先移除旧启动项，再在新目录重新运行 `install-autostart.ps1`。

## 隐私与安全边界

- App Server RPC 白名单只有 `initialize`、`account/read` 和 `account/rateLimits/read`。
- 明确拒绝 `turn/start` 等生成调用，因此额度读取不会启动模型推理。
- 不保存令牌、Cookie、邮箱或原始账户响应。
- 本地仅保存加盐后的账户作用域、额度快照和提醒去重状态，目录为 `%LOCALAPPDATA%\CodexPetQuota`。
- 同一目录下的 `watchdog.log` 只记录监督进程启停、Codex 检测和子进程退出码，用于排障，不包含令牌或账户响应。
- 优先只读 Codex 写入的 `.codex-global-state.json` 获取宠物位置；官方状态缺失时才在内存分析光标附近 112×112 像素，不保存截图。

## 故障排查

- **额度条不出现**：确认 Codex 正在运行、宠物已经开启，然后执行 `run.ps1 -DiagnoseWindows`。
- **提示找不到 Python**：安装 Python 3.9+，安装时勾选“Add Python to PATH”。
- **提示找不到 Codex CLI**：更新或重新启动最新版 Codex 桌面客户端。
- **移动项目后无法自启动**：执行 `uninstall-autostart.ps1`，再从新目录执行 `install-autostart.ps1`。
- **重启 Codex 后不显示**：确认 `watchdog.log` 中出现 `Codex desktop detected` 和 `quota watcher started`；也可重新执行 `install-autostart.ps1` 修复旧版启动项。
- **需要完全重置**：参考 [卸载与重置](docs/ROLLBACK.md)。

更多实现细节见 [实施状态](docs/IMPLEMENTATION_STATUS.md) 和 [详细实现方案](Codex宠物额度显示-详细实现方案.md)。

## 许可证

[MIT License](LICENSE)
