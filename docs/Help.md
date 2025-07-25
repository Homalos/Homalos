模式1：研究，目的：信息收集和深入理解

\[MODE: RESEARCH]

模式2：创新，目的：头脑风暴潜在方法

\[MODE: INNOVATE]

模式3：规划，目的：创建详尽的技术规范

\[MODE: PLAN]

模式4：执行，目的：准确实施模式3中规划的内容

\[MODE: EXECUTE]

模式5：审查，目的：无情地验证实施与计划的符合程度

\[MODE: REVIEW]



只有在明确信号时才能转换模式：

* “ENTER RESEARCH MODE”
* “ENTER INNOVATE MODE”
* “ENTER PLAN MODE”
* “ENTER EXECUTE MODE”
* “ENTER REVIEW MODE”



#### 按交易日+合约分表

taskkill /F /IM python.exe

powershell "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000' -TimeoutSec 5; Write-Host 'Web服务正常，状态码:' $response.StatusCode } catch { Write-Host 'Web服务连接失败:' $\_.Exception.Message }"

powershell "try { $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/strategies' -Method GET; Write-Host 'API响应正常:'; $response | ConvertTo-Json } catch { Write-Host 'API调用失败:' $\_.Exception.Message }"

powershell "try { $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/system/status' -Method GET; Write-Host 'System Status API响应:'; $response | ConvertTo-Json -Depth 3 } catch { Write-Host 'System Status API调用失败:' $\_.Exception.Message }"

curl -s "http://127.0.0.1:8000/api/v1/strategies" | python -c "import sys, json; data=json.load(sys.stdin); print('当前策略状态:'); \[print(f'  - {k}: {v\["strategy\_name"]} ({v\["status"]})') for k,v in data\['data']\['strategies'].items()]"

timeout 10 \&\& curl -s -o nul -w "%{http\_code}" http://127.0.0.1:8000/

curl -s -o nul -w "%{http\_code}" http://127.0.0.1:8000/static/css/app.css

curl -s http://127.0.0.1:8000/api/v1/system/status

curl -s http://127.0.0.1:8000/api/v1/strategies/discover

curl -s http://127.0.0.1:8000/api/v1/strategies

powershell "Get-Content log\\homalos\_20250711.log -Tail 80"

Invoke-WebRequest -Uri "http://localhost:8001/api/v1/strategies/98bccd20-61a0-4728-8af8-04c6d25a94e9/start"

Invoke-WebRequest -Uri "http://localhost:8001/api/v1/strategies" -Method GET 

```bash
git rm --cached -r .vercel
git rm --cached logs/debug.log
git commit -m "Stop tracking debug.log"
```

sqlite3 data/market_data.db "SELECT symbol, datetime, last_price, volume FROM tick_data ORDER BY datetime DESC LIMIT 5;"

netstat -ano | findstr :8000 

taskkill /F /PID 11968

```
# 1. 获取远程仓库最新分支信息
git fetch origin

# 2. 查看所有分支（包括远程）
git branch -a   # 远程分支会显示为 `remotes/origin/分支名`

# 3. 创建并切换到远程分支的本地副本（例如切换到远程的 feature/new 分支）
git checkout -b feature/new origin/feature/new

# 或使用 switch 命令（Git 2.23+）
git switch -c feature/new origin/feature/new
```