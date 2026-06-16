# DeepSeek Balance Monitor

一个轻量的 DeepSeek 余额和用量监控小工具，包含：

- 桌面悬浮窗：`deepseek_monitor.py`
- 浏览器页面版：`deepseek_monitor.html`
- 月度用量抓取辅助：`update_data.py`

## 功能

- 查看 DeepSeek API 账户余额
- 显示赠送余额、充值余额和总余额
- 每 60 秒自动刷新余额
- 可选显示月度 token、请求数和费用

## 安装

需要 Python 3.10+。

```bash
git clone <your-repo-url>
cd <repo-folder>
pip install -r requirements.txt
```

## 配置 API Key

推荐使用环境变量，避免把密钥写进项目文件。

PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="sk-your-deepseek-api-key"
python deepseek_monitor.py
```

也可以复制示例配置：

```powershell
Copy-Item deepseek_config.example.json deepseek_config.json
```

然后编辑 `deepseek_config.json`，填入自己的 `api_key`。该文件已加入 `.gitignore`，不会被提交。

## 启动桌面悬浮窗

```bash
python deepseek_monitor.py
```

Windows 用户也可以双击：

```text
launch_monitor.vbs
```

## 月度用量

月度用量需要登录 DeepSeek 控制台后读取网页数据。

1. 先运行登录助手：

   ```bash
   python update_data.py --login
   ```

2. 在打开的 Chrome 窗口中登录 DeepSeek。
3. 登录完成后运行：

   ```bash
   python update_data.py
   ```

4. 回到悬浮窗中点击 `MONTHLY USAGE` 或等待自动刷新。

Windows 用户也可以双击 `login_deepseek.vbs` 打开登录窗口。

## 浏览器页面版

直接打开 `deepseek_monitor.html`，输入 DeepSeek API Key 后即可使用。浏览器版会把 key 保存在本机 `localStorage` 中，不会写入仓库文件。

## 隐私和安全

- 不要提交 `deepseek_config.json`
- 不要提交 `deepseek_usage.json`
- 不要把 API Key 写进 README、截图或 issue
- 如果曾经把 key 提交或公开过，请立即在 DeepSeek 控制台轮换密钥

## 文件说明

```text
deepseek_monitor.py          桌面悬浮窗主程序
update_data.py               月度用量抓取脚本
deepseek_tracker.py          供其他脚本记录用量的辅助模块
deepseek_monitor.html        浏览器页面版
deepseek_config.example.json 配置模板
requirements.txt             Python 依赖
launch_monitor.vbs           Windows 静默启动悬浮窗
login_deepseek.vbs           Windows 登录辅助
```
