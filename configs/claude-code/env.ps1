# Windows PowerShell：写入当前用户的环境变量，重开终端后生效
[Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", "https://apikl.ai", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", "sk-your-key", "User")
