# 簡易POSアプリ：ローカル開発環境のセットアップ（Windows / PowerShell）
# VS Code のタスク「POS: セットアップ（初回のみ）」から実行されます。何度実行しても大丈夫です。
# 外部コマンド（pip / npm）の警告で止まらないよう Continue にし、終了コードで判定する
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$api  = Join-Path $root "api"
$web  = Join-Path $root "web"

function Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host ""; Write-Host "[エラー] $msg" -ForegroundColor Red; exit 1 }

# ---- 1. Python と Node.js の確認 ----
Step "Python と Node.js を確認しています"
$pyExe = $null; $pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $pyExe = "py"; $pyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = "python" }
if (-not $pyExe) { Fail "Python が見つかりません。https://www.python.org/downloads/ から Python 3.12 を入れてください（インストール時に「Add python.exe to PATH」にチェック）。入れた後は VS Code を再起動してください。" }
$verText = & $pyExe @pyArgs -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ($LASTEXITCODE -ne 0 -or -not $verText) { Fail "Python を実行できませんでした。python.org から Python 3.12 を入れてください（Microsoft Store の案内が出る場合も同様です）。" }
if ([version]$verText -lt [version]"3.10") { Fail "Python $verText は古いため動きません。3.10 以上（推奨 3.12）を入れてください。" }
Write-Host "  Python $verText"

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) { Fail "Node.js が見つかりません。https://nodejs.org/ から LTS 版を入れて、VS Code を再起動してください。" }
$nodeVer = (& node --version).Trim().TrimStart("v")
if ([version]$nodeVer -lt [version]"20.9.0") { Fail "Node.js $nodeVer は古いため動きません。20.9 以上（推奨 22 LTS）を入れてください。" }
Write-Host "  Node.js $nodeVer"

# ---- 2. API（FastAPI） ----
Step "API：Python の仮想環境を作ってライブラリを入れています（初回は数分かかります）"
Set-Location $api
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  & $pyExe @pyArgs -m venv .venv
  if ($LASTEXITCODE -ne 0) { Fail "仮想環境を作れませんでした。" }
}
$venvPy = Join-Path $api ".venv\Scripts\python.exe"
& $venvPy -m pip install --disable-pip-version-check -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { Fail "Python ライブラリのインストールに失敗しました。" }

if (-not (Test-Path ".env")) {
  Step "API：設定ファイル api\.env を作っています（DB はファイル型の SQLite）"
  $secret = & $venvPy -c "import secrets; print(secrets.token_urlsafe(48))"
  $lines = @(
    "APP_ENV=dev",
    "DATABASE_URL=sqlite:///./pos.db",
    "CORS_ORIGINS=http://localhost:3000",
    "JWT_SECRET=$secret",
    "JWT_ALGORITHM=HS256",
    "ACCESS_TOKEN_EXPIRE_MIN=60",
    "TAX_ROUNDING=floor"
  )
  $lines | Set-Content -Path ".env" -Encoding ascii
}

Step "API：データベースを作っています"
$firstTime = -not (Test-Path "pos.db")
& $venvPy -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Fail "データベースの作成に失敗しました。" }
if ($firstTime) {
  & $venvPy seed.py
  if ($LASTEXITCODE -ne 0) { Fail "初期データの投入に失敗しました。" }
} else {
  Write-Host "  既存のデータベースを使います（入れ直すときはタスク「POS: 初期データを入れ直す」）"
}

# ---- 3. Web（Next.js） ----
Step "Web：ライブラリを入れています（初回は数分かかります）"
Set-Location $web
if (-not (Test-Path ".env.local")) { Copy-Item ".env.example" ".env.local" }
& npm.cmd install --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { Fail "npm install に失敗しました。" }

Step "セットアップが終わりました"
Write-Host "  次は Ctrl+Shift+B（タスク「POS: すべて起動」）で起動し、http://localhost:3000 を開いてください。" -ForegroundColor Green
Write-Host "  ログイン：担当ID S001 / パスワード s001-password-2026"
