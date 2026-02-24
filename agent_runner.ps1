# PurifyAI 优化版 Agent 自动化执行脚本
# 作者：小午

param(
    [string]$TaskId = "all"
)

$ErrorActionPreference = "Continue"
$projectPath = "G:/docker/diskclean"

# 设置 UTF-8 编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  优化的 Agent 自动化执行脚本 (PowerShell 版本)" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# 切换到项目目录
Set-Location -Path $projectPath

# 任务定义
$tasks = @()

if ($TaskId -eq "all" -or $TaskId -eq "P0-verify") {
    $tasks += @{
        Id = "P0-verify"
        Name = "验证 P0-4 完成"
        Timeout = 60
        Prompt = @'
请验证 P0-4（增量清理功能）是否完整实现：

1. 后端方法：
   - load_last_cleanup_files()
   - save_last_cleanup_files()
   - recommend_incremental()

2. 前端组件：
   - agent_hub_page.py 增量清理按钮
   - CleanupPreviewCard 增量清理徽章
   - CleanupProgressWidget 保存文件列表

简要验证，告诉我"验证通过"或列出问题。
'@
    }
}

if ($TaskId -eq "all" -or $TaskId -eq "P0-5-start") {
    $tasks += @{
        Id = "P0-5-start"
        Name = "开始 P0-5 智能体页面重新设计"
        Timeout = 120
        Prompt = @'
P0-4 已完成，现在开始 P0-5：智能体页面重新设计

任务：
1. 分析当前的 agent_hub_page.py
2. 列出可以优化的布局和交互
3. 给出设计方案

先给出概要方案。
'@
    }
}

# 执行任务
$successCount = 0
$failCount = 0
$startTime = Get-Date

foreach ($task in $tasks) {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Yellow
    Write-Host "任务: [$($task.Id)] $($task.Name)" -ForegroundColor Yellow
    Write-Host "================================================================================" -ForegroundColor Yellow
    Write-Host "开始时间: $(Get-Date -Format 'HH:mm:ss')"
    Write-Host "预计超时: $($task.Timeout) 秒"
    Write-Host ""

    try {
        # 启动 claude 命令（使用 Start-Process + 等待）
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "claude"
        $psi.Arguments = @("-p", "--dangerously-skip-permissions", $task.Prompt)
        $psi.WorkingDirectory = $projectPath
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $false

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $psi
        $process.Start() | Out-Null

        # 等待完成或超时
        $process.WaitForExit($task.Timeout * 1000) | Out-Null

        if ($process.HasExited) {
            # 读取输出
            $output = $process.StandardOutput.ReadToEnd()
            $error = $process.StandardError.ReadToEnd()

            $elapsedSeconds = ((Get-Date) - $startTime).TotalSeconds - [math]::Truncate($elapsedSeconds - [math]::Truncate($elapsedSeconds))

            Write-Host "完成时间: $(Get-Date -Format 'HH:mm:ss')"
            Write-Host "返回码: $($process.ExitCode)"
            Write-Host ""

            if ($output) {
                $display = if ($output.Length -gt 500) { $output.Substring(0, 500) } else { $output }
                Write-Host "输出:" -ForegroundColor Gray
                Write-Host $display
                if ($output.Length -gt 500) {
                    Write-Host ""..." (输出已截断，共 $($output.Length) 字符)" -ForegroundColor DarkGray
                }
            }

            if ($process.ExitCode -eq 0) {
                Write-Host "" -NoNewline
                Write-Host "[OK] 完成" -ForegroundColor Green
                $successCount++
            } else {
                Write-Host "" -NoNewline
                Write-Host "[FAIL] 失败 (返回码: $($process.ExitCode))" -ForegroundColor Red
                $failCount++
            }
        } else {
            $process.Kill()
            Write-Host "完成时间: $(Get-Date -Format 'HH:mm:ss')"
            Write-Host "" -NoNewline
            Write-Host "[TIMEOUT] 超时 (超过 $($task.Timeout) 秒)" -ForegroundColor Red
            $failCount++
        }
    }
    catch {
        Write-Host "" -NoNewline
        Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }

    if ($tasks.IndexOf($task) -lt ($tasks.Count - 1)) {
        Write-Host ""
        Write-Host "等待 3 秒后继续..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 3
    }
}

# 摘要
$totalTime = ((Get-Date) - $startTime).TotalSeconds

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  执行摘要" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "总耗时: $([math]::Round($totalTime, 2)) 秒"
Write-Host "成功: $successCount"
Write-Host "失败: $failCount"
Write-Host "总计: $($tasks.Count)"

if ($successCount -eq $tasks.Count) {
    Write-Host ""
    Write-Host "[SUCCESS] 所有任务完成！" -ForegroundColor Green
} elseif ($failCount -gt 0) {
    Write-Host ""
    Write-Host "[WARNING] 有 $failCount 个任务失败" -ForegroundColor Yellow
}

Write-Host "================================================================================" -ForegroundColor Cyan
