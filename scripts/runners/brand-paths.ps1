# brand-paths.ps1 — phân giải ĐƯỜNG cho mọi runner tin: trạm, kênh, hai trạm năng lực,
# các trình thông dịch và công cụ ngoài. MỘT nơi quyết định, mọi runner dot-source vào.
#
# LUẬT CỦA FILE NÀY: không có ổ đĩa, không có tên người dùng, không có thư mục nhà nào
# được viết sẵn làm câu trả lời. Cùng một file chạy trên Windows (PS 5.1) và macOS (pwsh 7).
# Cổng `tests/test_runners_portable.py` và `tests/test_ps1_portable.py` giữ luật đó.
#
# File này sống ở HAI chỗ và phải đúng ở cả hai:
#   · `<repo>/scripts/runners/`  — bản chuẩn từ 1.1.0, `run.ps1` tìm runner ở đây trước.
#   · `<trạm>/engine/`           — bản cũ còn trên máy chưa dọn; vẫn chạy đúng (nhánh đi lên
#                                  từ thư mục engine tới `CHANNELS.md`).
#
# THỨ TỰ PHÂN GIẢI (mọi đường, mọi OS) — một luật, không ngoại lệ:
#   biến môi trường (Windows: thêm registry User) → `<repo>/.env` (chỉ chế độ embedded)
#   → repo anh em cùng thư mục cha, nhận bằng NỘI DUNG (`pyproject.toml: name`)
#   → đường cũ trong thư mục nhà, CHỈ khi có thật, kèm một dòng WARN.
# Tên thư mục chứa repo (`Code`, `Repo`, gì cũng được) không bao giờ là một giả định.

# ── Phân giải đường, KHÔNG chạm đĩa trừ khi nói rõ ───────────────────────────

# Thư mục CODE của runner, chốt NGAY lúc dot-source. Ở đây `$PSScriptRoot` chắc chắn là thư
# mục của chính file này; đọc nó bên trong một hàm được gọi sau đó thì không còn chắc.
$script:EngineDir = $PSScriptRoot

# Gợi ý trạm từ bản chụp cấu hình (`-Config`) của runner đang dot-source file này. Bản chụp
# nằm ở `<chiến dịch>/logs/`, nên đi lên từ nó tới `CHANNELS.md` là ĐÚNG trạm mà `run.ps1`
# vừa dùng — hai bên không thể trỏ hai trạm khác nhau trong cùng một lượt.
$script:StationHint = $null
if ($Config) { $script:StationHint = [string]$Config }

function Resolve-Home {
  <#
    Mở `~` ở ĐẦU một chuỗi đường. PowerShell KHÔNG tự mở `~` khi chuỗi đi qua
    `Join-Path`/`Test-Path` dưới dạng biến; để nguyên thì đường `~/...` lặng lẽ thành một
    thư mục tên `~` cạnh cwd.
  #>
  param([string]$P)
  if (-not $P) { return $P }
  if ($P -eq '~') { return $HOME }
  if ($P.StartsWith('~/') -or $P.StartsWith('~\')) {
    return (Join-Path $HOME $P.Substring(2))
  }
  return $P
}

function Write-PathWarn {
  # Đường lùi cũ vẫn dùng được nhưng phải NÓI RA: im lặng là cách hai máy lệch nhau.
  param([string]$Msg)
  Write-Host ('WARN: ' + $Msg)
}

function Get-StudioRepo {
  <#
    Gốc bản clone `agent-marketing-studio`. Thứ tự: thư mục CHA của `scripts/runners` (khi
    file này nằm trong repo) -> MARKETING_STUDIO_HOME. Nhận bằng NỘI DUNG
    (`scripts/pipeline/campaign_cfg.py`), không bằng tên thư mục.
    Bản trong trạm cũ (`<trạm>/engine`) không suy ra được repo từ vị trí -> chỉ còn biến.
  #>
  $ung = @()
  $cha = Split-Path (Split-Path $script:EngineDir -Parent) -Parent
  if ($cha) { $ung += $cha }
  $h = [Environment]::GetEnvironmentVariable('MARKETING_STUDIO_HOME')
  if ($h) { $ung += (Resolve-Home $h) }
  foreach ($c in $ung) {
    $moc = Join-Path $c (Join-Path 'scripts' (Join-Path 'pipeline' 'campaign_cfg.py'))
    if ($c -and (Test-Path -LiteralPath $moc)) { return $c }
  }
  return $null
}
$script:RepoRoot = Get-StudioRepo

function Read-JsonFile {
  param([string]$Path)
  if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  try { return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}

function Get-StudioLocal {
  # `<repo>/studio.local.json` (lựa chọn chế độ cài, gitignore) — $null khi chưa có.
  if (-not $script:RepoRoot) { return $null }
  return (Read-JsonFile (Join-Path $script:RepoRoot 'studio.local.json'))
}

$script:DotEnvCache = $null
function Get-RepoDotEnv {
  <#
    `<repo>/.env` thành bảng băm — CHỈ khi `studio.local.json: mode = embedded`, cùng luật
    với `studio_paths.env_file()`: chế độ `separate` không bao giờ tự nạp một file lạ trong
    repo. Định dạng tối giản `TEN=giá trị`, bỏ dòng `#`, bỏ `export `, gỡ một lớp nháy.
  #>
  if ($null -ne $script:DotEnvCache) { return $script:DotEnvCache }
  $h = @{}
  $lc = Get-StudioLocal
  if ($lc -and ([string]$lc.mode) -eq 'embedded') {
    $f = Join-Path $script:RepoRoot '.env'
    if (Test-Path -LiteralPath $f -PathType Leaf) {
      foreach ($dong in (Get-Content -LiteralPath $f -Encoding UTF8)) {
        $d = ([string]$dong).Trim()
        if (-not $d -or $d.StartsWith('#') -or -not $d.Contains('=')) { continue }
        if ($d.StartsWith('export ')) { $d = $d.Substring(7) }
        $i = $d.IndexOf('=')
        $ten = $d.Substring(0, $i).Trim(); $gia = $d.Substring($i + 1).Trim()
        if ($gia.Length -ge 2 -and $gia[0] -eq $gia[$gia.Length - 1] -and ($gia[0] -eq '"' -or $gia[0] -eq "'")) {
          $gia = $gia.Substring(1, $gia.Length - 2)
        }
        if ($ten) { $h[$ten] = $gia }
      }
    }
  }
  $script:DotEnvCache = $h
  return $h
}

function Get-EnvVar {
  <#
    Đọc một biến cấu hình. Thứ tự: tiến trình -> (Windows) REGISTRY phạm vi User
    -> `<repo>/.env` (chỉ embedded).

    Vì sao có nấc registry: biến được `setx` ở phạm vi User; tiến trình khởi động TRƯỚC lần
    `setx` đó không có biến, và khi đó mọi nấc sau sẽ lặng lẽ rơi xuống đường lùi.
    macOS: không có registry; biến đến từ plist launchd hoặc `<repo>/.env`.
    Đây là chỗ DUY NHẤT được đọc registry — cổng `test_runners_portable` giữ điều đó.
  #>
  param([Parameter(Mandatory)][string]$Name)
  $v = [Environment]::GetEnvironmentVariable($Name)
  if (-not $v -and $env:OS -eq 'Windows_NT') { $v = [Environment]::GetEnvironmentVariable($Name, 'User') }
  if (-not $v) {
    $e = Get-RepoDotEnv
    if ($e.ContainsKey($Name)) { $v = [string]$e[$Name] }
  }
  return $v
}

function Test-IsPathValue {
  # Giá trị trông như ĐƯỜNG DẪN (tuyệt đối, `~`, ổ đĩa Windows) — cùng luật `studio_paths.la_duong_dan`.
  param([string]$V)
  if (-not $V) { return $false }
  $t = $V.Trim()
  return ($t.StartsWith('/') -or $t.StartsWith('~') -or ($t -match '^[A-Za-z]:[\\/]'))
}

function Find-SiblingRepo {
  # Bản clone `<Package>` cùng thư mục cha (nhận bằng `pyproject.toml: name`) -> đường, hoặc $null.
  param([Parameter(Mandatory)][string]$Package)
  if (-not $script:RepoRoot) { return $null }
  $cha = Split-Path $script:RepoRoot -Parent
  if (-not $cha -or -not (Test-Path -LiteralPath $cha)) { return $null }
  $mau = '(?m)^\s*name\s*=\s*["' + "'" + ']' + [regex]::Escape($Package) + '["' + "'" + ']'
  $ung = @(Join-Path $cha $Package)
  $ung += @(Get-ChildItem -LiteralPath $cha -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne $Package -and -not $_.Name.StartsWith('.') } |
    Sort-Object Name | ForEach-Object { $_.FullName })
  $goc = [System.IO.Path]::GetFullPath($script:RepoRoot)
  foreach ($d in $ung) {
    if ([System.IO.Path]::GetFullPath($d) -eq $goc) { continue }
    $pp = Join-Path $d 'pyproject.toml'
    if (-not (Test-Path -LiteralPath $pp -PathType Leaf)) { continue }
    $noi = ''
    try { $noi = Get-Content -LiteralPath $pp -Raw -Encoding UTF8 } catch { continue }
    if ($noi -match $mau) { return $d }
  }
  return $null
}

function Find-SiblingStation {
  <#
    Trạm của một repo ANH EM nằm cùng thư mục cha với repo này — nhận bằng NỘI DUNG
    (`pyproject.toml` có `name = "<Package>"`), không bằng tên thư mục. Trạm của nó:
    `studio.local.json: station_path` -> `<repo anh em>/workspace`. Không thấy -> $null.
    BẢN SONG SINH của `studio_paths.repo_anh_em` + `tram_cua_repo` (PS không gọi được Python
    mà không tốn một tiến trình); cổng `test_runner_brand_paths.py` so hai bản trên cùng cây giả.
  #>
  param([Parameter(Mandatory)][string]$Package)
  $d = Find-SiblingRepo $Package
  if (-not $d) { return $null }
  $q = Join-Path $d 'workspace'
  $lc = Read-JsonFile (Join-Path $d 'studio.local.json')
  if ($lc -and $lc.station_path) {
    $q = Resolve-Home ([string]$lc.station_path)
    if (-not [System.IO.Path]::IsPathRooted($q)) { $q = Join-Path $d $q }
  }
  if (Test-Path -LiteralPath $q -PathType Container) { return [System.IO.Path]::GetFullPath($q) }
  return $null
}

function Find-UpToChannels {
  # Đi LÊN từ một thư mục tới thư mục có `CHANNELS.md` (dấu nhận trạm). Không thấy -> $null.
  param([string]$Start)
  $d = $Start
  while ($d) {
    if (Test-Path -LiteralPath (Join-Path $d 'CHANNELS.md')) { return $d }
    $cha = Split-Path $d -Parent
    if ($cha -eq $d) { break }
    $d = $cha
  }
  return $null
}

function Get-StationRoot {
  <#
    Gốc trạm marketing. Thứ tự:
      1. (bản cũ trong trạm) đi LÊN từ thư mục engine tới `CHANNELS.md`
      2. đi LÊN từ bản chụp `-Config` (nằm trong `<chiến dịch>/logs/`)
      3. MARKETING_STUDIO_DATA
      4. `<repo>/studio.local.json: station_path`
      5. `<repo>/workspace` (chế độ embedded) khi có `CHANNELS.md`
      6. thư mục cũ `.marketing` trong thư mục nhà — chỉ khi có thật, kèm WARN
    Không thấy gì -> NÉM, nêu tên biến. Đoán một thư mục là tạo ra một trạm thứ hai.

    Nấc 1–2 quan trọng nhất: `run.ps1` cũng đi lên từ thư mục chiến dịch, nên runner và
    `run.ps1` không bao giờ trỏ HAI trạm khác nhau trong cùng một lượt. Bản trong repo bỏ
    qua nấc 1: đi lên từ `<repo>/scripts/runners` thì có thể vấp một `CHANNELS.md` lạc ở
    thư mục cha nào đó.
  #>
  if (-not $script:RepoRoot) {
    $t = Find-UpToChannels $script:EngineDir
    if ($t) { return $t }
  }
  if ($script:StationHint) {
    $t = Find-UpToChannels (Split-Path $script:StationHint -Parent)
    if ($t) { return $t }
  }
  $v = Get-EnvVar 'MARKETING_STUDIO_DATA'
  if ($v) { return (Resolve-Home $v) }
  $lc = Get-StudioLocal
  if ($lc -and $lc.station_path) {
    $sp = Resolve-Home ([string]$lc.station_path)
    if (-not [System.IO.Path]::IsPathRooted($sp)) { $sp = Join-Path $script:RepoRoot $sp }
    return $sp
  }
  if ($script:RepoRoot) {
    $ws = Join-Path $script:RepoRoot 'workspace'
    if (Test-Path -LiteralPath (Join-Path $ws 'CHANNELS.md')) { return $ws }
  }
  $cu = Join-Path $HOME '.marketing'
  if (Test-Path -LiteralPath (Join-Path $cu 'CHANNELS.md')) {
    Write-PathWarn ('tram lay theo duong cu ' + $cu + ' - dat MARKETING_STUDIO_DATA cho ro rang.')
    return $cu
  }
  throw 'Get-StationRoot: khong xac dinh duoc tram. Dat MARKETING_STUDIO_DATA (hoac cai che do embedded: <repo>/workspace).'
}

function Get-VoiceStation {
  <#
    Gốc trạm giọng. Thứ tự: VOICE_STATION -> thư mục CHA của OMNIVOICE_DIR (tên cũ, trỏ
    engine) -> `studio.local.json: voice_station` -> repo anh em `agent-voice-studio`
    -> thư mục cũ trong thư mục nhà (chỉ khi có thật, WARN) -> $null.

    Hàm này chỉ GHÉP đường; phần fail-closed nằm ở `Find-OmniVoicePython`, nơi thực sự cần
    một trình thông dịch chạy được.
  #>
  $v = Get-EnvVar 'VOICE_STATION'
  if ($v) { return (Resolve-Home $v) }
  $v = Get-EnvVar 'OMNIVOICE_DIR'
  if ($v) { return (Split-Path (Resolve-Home $v) -Parent) }
  $lc = Get-StudioLocal
  if ($lc -and $lc.voice_station) { return (Resolve-Home ([string]$lc.voice_station)) }
  $v = Find-SiblingStation 'agent-voice-studio'
  if ($v) { return $v }
  foreach ($ten in @('.voice', '.tts')) {
    $cu = Join-Path $HOME $ten
    if (Test-Path -LiteralPath $cu) {
      Write-PathWarn ('tram giong lay theo duong cu ' + $cu + ' - dat VOICE_STATION.')
      return $cu
    }
  }
  return $null
}

function Get-VideoStation {
  # Gốc trạm video: VIDEO_STATION -> VIDEO_ROOT (tên cũ) -> `studio.local.json: video_station`
  # -> repo anh em `agent-video-studio` -> thư mục cũ (chỉ khi có thật, WARN) -> $null.
  $v = Get-EnvVar 'VIDEO_STATION'
  if ($v) { return (Resolve-Home $v) }
  $v = Get-EnvVar 'VIDEO_ROOT'
  if ($v) { return (Resolve-Home $v) }
  $lc = Get-StudioLocal
  if ($lc -and $lc.video_station) { return (Resolve-Home ([string]$lc.video_station)) }
  $v = Find-SiblingStation 'agent-video-studio'
  if ($v) { return $v }
  $cu = Join-Path $HOME '.video'
  if (Test-Path -LiteralPath $cu) {
    Write-PathWarn ('tram video lay theo duong cu ' + $cu + ' - dat VIDEO_STATION.')
    return $cu
  }
  return $null
}

function Find-Python {
  # CHÉP NGUYÊN giữa các .ps1 của repo (PS 5.1 không có module chung); cổng
  # tests/test_ps1_portable.py giữ mọi bản giống hệt nhau. Thứ tự dò:
  #   MARKETING_STUDIO_PY -> <repo>/.venv -> python -> python3 -> py
  # Mỗi ứng viên phải CHẠY được và tự khai là Python 3.10+: trên Windows `python3` có
  # thể là stub của Microsoft Store — Get-Command thấy, chạy thì hỏng.
  param([string]$Repo)
  $chay = {
    param([string]$exe)
    # Chuyen huong luong loi cua LENH NGOAI duoi `Stop`: PS 5.1 boc tung dong stderr thanh
    # NativeCommandError, va dong DAU TIEN da la loi ket thuc. Mot Python CHAY DUOC nhung
    # in canh bao luc khoi dong (wrapper .cmd, shim pyenv/conda, mot .pth in ra) bi loai
    # OAN -> exit 2; pwsh 7 thi khong -> cung mot file, hai hanh vi (review P1, N1).
    # Ha ve `Continue` trong chinh scriptblock nay: goi bang `&` nen bien la CUC BO, khong
    # ro ri ra ngoai. Ket qua that van doc tu $LASTEXITCODE — noi loi la te hon chet.
    # Test: tests/test_find_python.py
    $ErrorActionPreference = 'Continue'
    try {
      $ra = @(& $exe -c 'import sys;print(sys.version_info[:2])' 2>$null)
      if ($LASTEXITCODE -ne 0) { return $false }
      # Dong CUOI chu khong phai ca stdout: `[string](@(...))` noi moi dong bang dau cach,
      # nen mot loi chao in truoc dong phien ban lam regex neo truot.
      $v = ''
      foreach ($d in $ra) { $t = ([string]$d).Trim(); if ($t) { $v = $t } }
      $m = [regex]::Match($v, '^\((\d+), (\d+)\)$')
      return ($m.Success -and [int]$m.Groups[1].Value -eq 3 -and [int]$m.Groups[2].Value -ge 10)
    } catch { return $false }
  }
  if ($env:MARKETING_STUDIO_PY) {
    if (& $chay $env:MARKETING_STUDIO_PY) { return $env:MARKETING_STUDIO_PY }
    Write-Host ('Find-Python: MARKETING_STUDIO_PY=' + $env:MARKETING_STUDIO_PY + ' khong chay duoc Python 3.10+ -> DUNG.')
    return $null
  }
  $ung = @()
  if ($Repo) {
    foreach ($con in @('Scripts', 'bin')) {
      $thu = Join-Path (Join-Path $Repo '.venv') $con
      if (Test-Path $thu) {
        $ung += @(Get-ChildItem -Path $thu -Filter 'python*' -File -ErrorAction SilentlyContinue |
          Where-Object { $_.BaseName -eq 'python' -or $_.BaseName -eq 'python3' } |
          Sort-Object Name | ForEach-Object { $_.FullName })
      }
    }
  }
  $ung += @('python', 'python3', 'py')
  foreach ($u in $ung) {
    if (& $chay $u) { return $u }
  }
  Write-Host 'Find-Python: khong thay Python 3.10+ (MARKETING_STUDIO_PY, .venv, python, python3, py) -> DUNG.'
  return $null
}

function Get-VenvPythonFiles {
  <#
    Trình thông dịch trong một venv, hai OS: `<venv>/Scripts/*` (Windows) rồi `<venv>/bin/*`
    (macOS/Linux), chỉ tên gốc `python`/`python3`. Không viết đuôi file: tên chương trình
    khác nhau giữa hai OS, còn tên gốc thì không.
  #>
  param([string]$Venv)
  $ra = @()
  if (-not $Venv) { return $ra }
  foreach ($con in @('Scripts', 'bin')) {
    $d = Join-Path $Venv $con
    if (Test-Path -LiteralPath $d) {
      $ra += @(Get-ChildItem -LiteralPath $d -File -ErrorAction SilentlyContinue |
        Where-Object { $_.BaseName -match '^python3?$' } |
        Sort-Object Name | ForEach-Object { $_.FullName })
    }
  }
  return $ra
}

function Find-OmniVoicePython {
  <#
    Python CỦA TRẠM GIỌNG — không phải python hệ thống. Nó là cái duy nhất có
    `voice_studio`/`video_studio`/torch và các gói của `requirements-runners.txt`.

    Thứ tự (cùng `scripts/lib/voice.py: python_exe`): OMNIVOICE_PY -> `station.json: venv`
    của trạm giọng -> `<trạm giọng>/omnivoice/.venv` -> `.venv` của repo anh em
    `agent-video-studio`, rồi `agent-voice-studio` (bố cục "giọng cài chung venv video").

    FAIL-CLOSED: không tìm ra thì NÉM, kèm tên biến cần đặt. Đường lùi về `python` trần ở
    đây là kiểu hỏng đắt nhất — pipeline chạy tiếp 10 phút rồi chết ở `import torch`.
  #>
  param([string]$VoiceStation)
  if (-not $VoiceStation) { $VoiceStation = Get-VoiceStation }
  $thu = @()
  $bien = Get-EnvVar 'OMNIVOICE_PY'
  if ($bien) { $thu += (Resolve-Home $bien) }
  if ($VoiceStation) {
    $j = Read-JsonFile (Join-Path $VoiceStation 'station.json')
    if ($j -and $j.venv) {
      $v = Resolve-Home ([string]$j.venv)
      if (-not [System.IO.Path]::IsPathRooted($v)) { $v = Join-Path $VoiceStation $v }
      $thu += @(Get-VenvPythonFiles $v)
    }
    $thu += @(Get-VenvPythonFiles (Join-Path (Join-Path $VoiceStation 'omnivoice') '.venv'))
  }
  foreach ($ten in @('agent-video-studio', 'agent-voice-studio')) {
    $r = Find-SiblingRepo $ten
    if ($r) { $thu += @(Get-VenvPythonFiles (Join-Path $r '.venv')) }
  }
  foreach ($t in $thu) { if ($t -and (Test-Path $t -PathType Leaf)) { return $t } }
  throw ("Find-OmniVoicePython: khong thay python cua tram giong. Da thu: " +
         (($thu | Where-Object { $_ }) -join ' | ') + ". Dat OMNIVOICE_PY hoac VOICE_STATION.")
}

function Find-Ffmpeg {
  <#
    ffmpeg: FFMPEG_DIR -> PATH. Trả về đường CHẠY ĐƯỢC để gọi bằng `& (Find-Ffmpeg)`.
    Không qua `cmd /c` (chỉ có trên Windows, và che mã thoát thật sau đường ống).
  #>
  $dir = Get-EnvVar 'FFMPEG_DIR'
  if ($dir) {
    $f = @(Get-ChildItem -LiteralPath (Resolve-Home $dir) -File -ErrorAction SilentlyContinue |
      Where-Object { $_.BaseName -eq 'ffmpeg' } | Sort-Object Name)
    if ($f.Count -gt 0) { return $f[0].FullName }
  }
  $c = Get-Command 'ffmpeg' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($c) { return $c.Source }
  throw "Find-Ffmpeg: khong thay ffmpeg (FFMPEG_DIR hoac PATH)."
}

function Find-Last30Days {
  <#
    Script nghiên cứu `last30days` (plugin Claude). Thứ tự:
      L30_SCRIPT -> `<CLAUDE_CONFIG_DIR | ~/.claude>/plugins/marketplaces/*/skills/last30days/
      scripts/last30days.py` -> `.../plugins/cache/*/last30days/<bản mới nhất>/skills/...`.
    Không thấy -> $null; runner DỪNG trước `claude -p` và nêu tên biến L30_SCRIPT.
    Cài plugin là việc của lớp cài đặt máy; repo này chỉ TÌM và KIỂM (`doctor`).
  #>
  $v = Get-EnvVar 'L30_SCRIPT'
  if ($v) { return (Resolve-Home $v) }
  $goc = Get-EnvVar 'CLAUDE_CONFIG_DIR'
  if ($goc) { $goc = Resolve-Home $goc } else { $goc = Join-Path $HOME '.claude' }
  $plug = Join-Path $goc 'plugins'
  $duoi = Join-Path 'skills' (Join-Path 'last30days' (Join-Path 'scripts' 'last30days.py'))
  $mk = Join-Path $plug 'marketplaces'
  if (Test-Path -LiteralPath $mk) {
    foreach ($d in (Get-ChildItem -LiteralPath $mk -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
      $p = Join-Path $d.FullName $duoi
      if (Test-Path -LiteralPath $p -PathType Leaf) { return $p }
    }
  }
  $ca = Join-Path $plug 'cache'
  if (Test-Path -LiteralPath $ca) {
    $ds = @()
    foreach ($d in (Get-ChildItem -LiteralPath $ca -Directory -ErrorAction SilentlyContinue)) {
      $l = Join-Path $d.FullName 'last30days'
      if (-not (Test-Path -LiteralPath $l)) { continue }
      foreach ($b in (Get-ChildItem -LiteralPath $l -Directory -ErrorAction SilentlyContinue)) {
        $p = Join-Path $b.FullName $duoi
        if (Test-Path -LiteralPath $p -PathType Leaf) {
          $ver = $null; try { $ver = [version]$b.Name } catch { $ver = [version]'0.0' }
          $ds += [pscustomobject]@{ ver = $ver; path = $p }
        }
      }
    }
    $moi = $ds | Sort-Object ver -Descending | Select-Object -First 1
    if ($moi) { return $moi.path }
  }
  return $null
}

function Get-BgmCatalog {
  <#
    Thư viện nhạc nền (`bgm-library.json` + `<style>.mp3`) -> @{ dir; lib; available;
    missing; text }. `text` là danh sách đưa cho AI chọn — CHỈ gồm style CÓ mp3: để AI chọn
    một style không có file là để engine giọng ném `FileNotFoundError` ở bước dựng, sau khi
    đã tốn `claude -p` và TTS. Style thiếu mp3 nằm ở `missing` để runner báo WARN.
  #>
  param([string]$Dir)
  $r = [pscustomobject]@{ dir = $Dir; lib = $null; available = @(); missing = @(); text = '' }
  if (-not $Dir) { return $r }
  $r.lib = Read-JsonFile (Join-Path $Dir 'bgm-library.json')
  if (-not $r.lib) { return $r }
  $co = @(); $thieu = @(); $dong = @()
  foreach ($s in @($r.lib.styles)) {
    if (-not $s -or -not $s.name) { continue }
    $ten = [string]$s.name
    if (Test-Path -LiteralPath (Join-Path $Dir ($ten + '.mp3')) -PathType Leaf) {
      $co += $ten
      $dong += "- $($s.name) (BPM $($s.bpm), $($s.mood)): $($s.use)"
    } else { $thieu += $ten }
  }
  $r.available = $co; $r.missing = $thieu; $r.text = ($dong -join "`n")
  return $r
}

function Resolve-ForcedBgm {
  <#
    Khoá `bgm` của cấu hình: vắng/null = AI chọn · "" = TẮT · tên style/đường file = ÉP.
    -> @{ forced; path; ok }. Ép mà không ra file -> ok=$false: runner DỪNG trước `claude -p`
    (kiểm sớm, rẻ) thay vì tắt nhạc im lặng hay chết ở bước dựng.
  #>
  param($Cfg, [string]$Dir, [string]$BrandDir)
  $r = [pscustomobject]@{ forced = $false; path = ''; ok = $true }
  if (-not $Cfg -or $null -eq $Cfg.bgm) { return $r }
  $r.forced = $true
  $b = [string]$Cfg.bgm
  if (-not $b) { return $r }
  $ung = @()
  if ($Dir) { $ung += (Join-Path $Dir ($b + '.mp3')) }
  if ($BrandDir) { $ung += (Join-Path $BrandDir $b) }
  $ung += (Resolve-Home $b)
  foreach ($u in $ung) { if ($u -and (Test-Path -LiteralPath $u -PathType Leaf)) { $r.path = $u; return $r } }
  $r.ok = $false
  return $r
}

function Read-BgmPick {
  # Trường `bgm` AI ghi trong JSON của lượt chạy. Không đọc được -> '' (không phải lỗi).
  param([string]$JsonPath)
  try { return [string]((Get-Content -LiteralPath $JsonPath -Raw -Encoding UTF8 | ConvertFrom-Json).bgm) } catch { return '' }
}

function Select-Bgm {
  <#
    -> đường mp3 sẽ trộn, hoặc '' (tắt nhạc). Ép (Resolve-ForcedBgm) thắng. Không ép: lựa
    chọn của AI nếu style đó CÓ mp3 -> `default` của thư viện nếu có mp3 -> style có mp3 đầu
    tiên -> tắt. Không bao giờ trả một style thiếu file.
  #>
  param($Forced, $Catalog, [string]$Pick)
  if ($Forced -and $Forced.forced) { return [string]$Forced.path }
  $names = @($Catalog.available)
  if (-not ($Pick -and ($names -contains $Pick))) {
    $Pick = ''
    if ($Catalog.lib -and ($names -contains [string]$Catalog.lib.default)) { $Pick = [string]$Catalog.lib.default }
    elseif ($names.Count -gt 0) { $Pick = [string]$names[0] }
  }
  if ($Pick) { return (Join-Path $Catalog.dir ($Pick + '.mp3')) }
  return ''
}

function Get-GitAuthorArgs {
  <#
    Đối số `-c` cho commit của bot vào repo web. Danh tính KHÔNG viết trong mã (repo public):
      · `git_author` (channel.yml brand / campaign.md) dạng "Tên <email>" -> dùng nguyên;
      · không khai -> tên "<site_name> Bot" và email = danh tính git của máy (không ép).
  #>
  param($Cfg)
  $ga = if ($Cfg) { [string]$Cfg.git_author } else { '' }
  $m = [regex]::Match($ga, '^\s*(.+?)\s*<([^<>\s]+)>\s*$')
  if ($m.Success) { return @('-c', ('user.name=' + $m.Groups[1].Value), '-c', ('user.email=' + $m.Groups[2].Value)) }
  $ten = if ($Cfg -and $Cfg.site_name) { ([string]$Cfg.site_name) + ' Bot' } else { 'Studio Bot' }
  return @('-c', ('user.name=' + $ten))
}

# ── Biến dùng chung, tính MỘT lần khi runner dot-source file này ─────────────
# `$script:` trong file được dot-source = phạm vi script của NGƯỜI GỌI, nên runner thấy
# chúng dưới tên trần `$Station`, `$Engine`, `$VoiceStation`, `$VideoStation`.
#
# `$Engine` = thư mục CODE của runner (chính thư mục chứa file này), KHÔNG phải
# `<trạm>/engine`. PowerShell không phân biệt hoa thường: runner đặt `$engine = $PSScriptRoot`
# rồi dot-source file này, nên gán `$script:Engine` ở đây là GHI ĐÈ biến của runner. Trỏ nó
# về trạm thì bản runner trong repo sẽ âm thầm gọi script của bản cũ trong trạm.
$script:Station      = Get-StationRoot
$script:Engine       = $script:EngineDir
$script:VoiceStation = Get-VoiceStation
$script:VideoStation = Get-VideoStation
# Đẩy HAI trạm đã phân giải xuống mọi tiến trình con (`video-studio`, `voice-studio`,
# bộ dựng bản tin): runner và Python phải phân giải trạm MỘT kiểu.
if ($script:VoiceStation) { $env:VOICE_STATION = $script:VoiceStation }
if ($script:VideoStation) { $env:VIDEO_STATION = $script:VideoStation }

function Get-BrandDir {
  param([Parameter(Mandatory)][string]$Brand)

  $tram = if ($script:Station) { $script:Station } else { Get-StationRoot }
  $map  = @{ 'ai' = 'ai-news'; 'data' = 'data-news'; 'repo' = (Join-Path 'ai-news' 'hot-repo') }

  if (-not $map.ContainsKey($Brand)) {
    throw "Get-BrandDir: brand '$Brand' chua duoc khai trong bang anh xa (ai|data|repo)."
  }
  $moi = Join-Path $tram $map[$Brand]
  if (Test-Path $moi) { $script:BrandSrc = 'NEW'; return $moi }

  # FAIL-CLOSED thay cho đường lùi.
  #
  # Trước 07/09/2026 chỗ này rơi về một thư mục kênh trong engine dùng chung khi không
  # thấy `brand.json`. Hai lý do bỏ:
  #   1. Thư mục lùi ĐÃ KHÔNG CÒN — nội dung kênh dời sang trạm 05/09. Rơi về đó chỉ
  #      tạo ra một đường dẫn chết, rồi runner báo "missing brand.json" ở tận bước sau, xa
  #      chỗ hỏng thật.
  #   2. Tín hiệu là sự tồn tại của `brand.json` — mà chính file đó đang bị gộp vào
  #      `channel.yml` + `brand.md`. Giữ nguyên thì xoá `brand.json` là cả 5 pipeline lặng
  #      lẽ tụt về đường chết.
  #
  # Dừng ngay và nói rõ thiếu gì, tốt hơn chạy tiếp 10 phút rồi hỏng vì lý do khác.
  throw "Get-BrandDir: khong thay thu muc kenh cho brand '$Brand': $moi"
}

function Get-Cfg {
  <#
    Trả về đối tượng cấu hình cho runner. MỘT nơi quyết định đọc từ đâu, 4 runner gọi vào.

    · Có -Config  -> đọc BẢN CHỤP do `campaign_cfg.py` sinh từ `campaign.md`.
    · Không có    -> đọc `brand.json` như trước, KHÔNG đổi một hành vi nào.

    Vì sao an toàn: bản chụp đã được đối chiếu với `brand.json` trên ĐÚNG bộ khoá mà từng
    runner thật sự đọc (14 khoá daily · 11 weekly · 10 repo) — tất cả trùng khớp, kể cả
    hai khoá có đường lùi trong code (`bgm_vol` -> '0.10', `fb_text_post` vắng ≡ $false).
    Nên nhánh -Config là no-op chứng minh được, không phải hy vọng.

    FAIL-CLOSED: khai -Config mà file không có thì DỪNG, tuyệt đối không lặng lẽ quay về
    `brand.json`. Rơi về im lặng nghĩa là người sửa `campaign.md` xong thấy sản phẩm không
    đổi và không hiểu vì sao — kiểu hỏng đắt nhất.
  #>
  param([string]$Config, [Parameter(Mandatory)][string]$BrandDir)

  if ($Config) {
    if (-not (Test-Path $Config)) { throw "Get-Cfg: khong thay ban chup cau hinh: $Config" }
    $script:CfgSrc = 'CONFIG'
    $c = Get-Content $Config -Raw -Encoding UTF8 | ConvertFrom-Json
  } else {
    $bj = Join-Path $BrandDir 'brand.json'
    if (-not (Test-Path $bj)) { throw "Get-Cfg: khong thay $bj" }
    $script:CfgSrc = 'BRAND.JSON'
    $c = Get-Content $bj -Raw -Encoding UTF8 | ConvertFrom-Json
  }
  # Runner đưa `repo` cho Python và git; hai bên đó KHÔNG hiểu `~` hay `${TÊN}`, nên để nguyên
  # là tạo ra một thư mục tên `~` cạnh thư mục hiện hành mà không ai báo.
  # `repo` theo CÙNG luật `studio_paths.duong_repo_web` (bản chụp của `campaign_cfg.py` đã
  # nở sẵn thành đường tuyệt đối; nhánh này phục vụ đường cũ brand.json):
  #   `${TÊN}` -> Get-EnvVar (biến chưa đặt thì DỪNG, nêu tên) · `~` -> thư mục nhà ·
  #   tương đối -> theo THƯ MỤC CHA chứa các repo (cha của bản clone này).
  if ($c.repo -and ([string]$c.repo).Contains('${')) {
    $r = [string]$c.repo
    foreach ($m in [regex]::Matches($r, '\$\{([A-Za-z_][A-Za-z0-9_]*)\}')) {
      $g = Get-EnvVar $m.Groups[1].Value
      if (-not $g) { throw ("Get-Cfg: repo = '" + $r + "' can bien " + $m.Groups[1].Value + " nhung bien chua dat (env hoac <repo>/.env).") }
      $r = $r.Replace($m.Value, $g)
    }
    if ([System.IO.Path]::IsPathRooted($r)) { $r = [System.IO.Path]::GetFullPath($r) }
    $c.repo = $r
  }
  if ($c.repo -and ([string]$c.repo).StartsWith('~')) {
    $c.repo = [System.IO.Path]::GetFullPath((Resolve-Home ([string]$c.repo)))
  }
  if ($c.repo -and -not [System.IO.Path]::IsPathRooted([string]$c.repo)) {
    if (-not $script:RepoRoot) { throw ("Get-Cfg: repo = '" + $c.repo + "' la duong TUONG DOI nhung khong xac dinh duoc repo (dat MARKETING_STUDIO_HOME) - hoac viet duong tuyet doi / `${TEN_BIEN}.") }
    $c.repo = [System.IO.Path]::GetFullPath((Join-Path (Split-Path $script:RepoRoot -Parent) ([string]$c.repo)))
  }
  return $c
}

function Test-Cadence {
  <#
    Hôm nay có phải ngày chạy của chiến dịch không — lịch "N ngày/lần" nằm TRONG runner.

    Trên Windows nhịp do Task Scheduler giữ (`-EveryDays 2`), nên hàm này chỉ xác nhận lại.
    launchd trên macOS không có nhịp đó: nó gọi MỖI NGÀY, và không có hàm này thì mỗi kênh
    ra bài gấp đôi, hai kênh lệch nhịp (AI / Data) chạy chồng lên nhau.

    Đọc `runtime.cadence_days` + `runtime.cadence_anchor` (yyyy-MM-dd) của campaign.md qua bản
    chụp. Thiếu một trong hai, hoặc days <= 1 -> $null = không chặn (weekly, repo, truyện).
    -> $null | @{ run; days; anchor; offset }
  #>
  param([Parameter(Mandatory)][string]$Date, $Cfg)
  if (-not $Cfg) { return $null }
  $n = 0
  try { $n = [int]$Cfg.cadence_days } catch { $n = 0 }
  $moc = [string]$Cfg.cadence_anchor
  if ($n -le 1 -or -not $moc) { return $null }
  $ci = [System.Globalization.CultureInfo]::InvariantCulture
  $d0 = [datetime]::ParseExact($moc, 'yyyy-MM-dd', $ci)
  $d  = [datetime]::ParseExact($Date, 'yyyy-MM-dd', $ci)
  $lech = ([int][math]::Round(($d - $d0).TotalDays)) % $n
  if ($lech -lt 0) { $lech += $n }
  return [pscustomobject]@{ run = ($lech -eq 0); days = $n; anchor = $moc; offset = $lech }
}

function Invoke-VideoStudio {
  <#
    Gọi `video-studio` (hợp đồng CLI của repo agent-video-studio) bằng python của trạm giọng —
    nơi cài `video_studio` cạnh `voice_studio`. Gọi `python -m video_studio` chứ không gọi
    `video-studio.exe`: tên launcher khác nhau giữa Windows (`Scripts\*.exe`) và macOS
    (`bin/*`), còn python thì Find-OmniVoicePython đã dò đúng cho cả hai.

    Không qua `cmd /c` (chỉ có trên Windows, và che mã thoát thật sau đường ống). Mọi dòng ra
    (tiến độ ở stderr + dòng JSON kết quả ở stdout) đi qua -OnLine để vào log của runner; dòng
    JSON CUỐI là kết quả theo hợp đồng CLI của repo agent-video-studio (§2).
    -> @{ code; result }   code: 0 ok · 1 engine/render hỏng · 2 gọi/spec sai · 3 thiếu trạm/công cụ
  #>
  param([Parameter(Mandatory)][string]$Python, [Parameter(Mandatory)][string[]]$Arguments,
        [scriptblock]$OnLine)
  $ErrorActionPreference = 'Continue'
  $cuoi = $null
  & $Python -m video_studio @Arguments 2>&1 | ForEach-Object {
    $s = Format-NativeLine $_
    if ($null -eq $s) { return }
    if ($OnLine) { & $OnLine $s }
    $t = $s.Trim()
    if ($t.StartsWith('{') -and $t.EndsWith('}')) { $cuoi = $t }
  }
  $code = $LASTEXITCODE
  $res = $null
  if ($cuoi) { try { $res = $cuoi | ConvertFrom-Json } catch { $res = $null } }
  return [pscustomobject]@{ code = $code; result = $res }
}

function Invoke-AgentCall {
  <#
    Bước nghiên cứu của runner tin đi qua `scripts/pipeline/agent_call.py --engine order` —
    chuỗi engine theo `order` trong `<trạm>/_agent-call/engines.json`, KHÔNG gọi `claude -p` thô.

    P1-21 (Mac mini 01/10/2026): Hot Data 19:00 gọi `claude -p` thô, chung hạn mức với phiên
    Claude tương tác cùng tài khoản ⇒ "hit your session limit" ×3, abort, không đăng — trong
    khi `order` xếp agy đứng đầu và agy chạy được. Lớp agent_call lo: thứ tự engine, hết hạn
    mức (mã 4 + resets_at), lỗi tạm (thử lại rồi lùi), cổng artifact (`-Expect`).

    Prompt đi qua TỆP tạm (`--prompt-file`), không qua đường ống: PS 5.1 đẩy chuỗi vào stdin
    của lệnh ngoài bằng bảng mã console, tiếng Việt vỡ trên máy Windows chưa đặt UTF-8.
    -Tools là tập trừu tượng của agent_call (`web,read,write,shell:<lệnh>`), map sang cờ từng
    engine. Mọi dòng ra đi qua -OnLine để vào log của runner.
    -> @{ code; result }   code: 0 xong + artifact đạt · 1 lỗi engine (đã lùi hết chuỗi) ·
                           2 cấu hình sai · 3 thiếu CLI/đăng nhập · 4 MỌI engine hết hạn mức
  #>
  param([Parameter(Mandatory)][string]$Python, [Parameter(Mandatory)][string]$Prompt,
        [Parameter(Mandatory)][string[]]$Expect, [string]$Tools = 'web,read,write',
        [string]$Cwd, [int]$Timeout = 2700, [switch]$NoContentGate, [scriptblock]$OnLine)
  $ErrorActionPreference = 'Continue'
  $ac = Join-Path (Join-Path (Join-Path $script:RepoRoot 'scripts') 'pipeline') 'agent_call.py'
  $tmp = [System.IO.Path]::GetTempFileName()
  [System.IO.File]::WriteAllText($tmp, $Prompt, (New-Object System.Text.UTF8Encoding $false))
  $doi = @($ac, '--engine', 'order', '--prompt-file', $tmp, '--tools', $Tools,
           '--timeout', [string]$Timeout, '--json')
  foreach ($e in $Expect) { $doi += @('--expect', $e) }
  if ($Cwd) { $doi += @('--cwd', $Cwd) }
  if ($NoContentGate) { $doi += '--no-content-gate' }
  $cuoi = $null
  try {
    & $Python @doi 2>&1 | ForEach-Object {
      $s = Format-NativeLine $_
      if ($null -eq $s) { return }
      if ($OnLine) { & $OnLine $s }
      $t = $s.Trim()
      if ($t.StartsWith('{') -and $t.EndsWith('}')) { $cuoi = $t }
    }
    $code = $LASTEXITCODE
  } finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
  }
  $res = $null
  if ($cuoi) { try { $res = $cuoi | ConvertFrom-Json } catch { $res = $null } }
  return [pscustomobject]@{ code = $code; result = $res }
}

function Format-NativeLine {
  <#
    Một phần tử của `lệnh-ngoài 2>&1` -> chuỗi để ghi log, hoặc $null nếu là dòng trống.

    PS 5.1 bọc từng dòng stderr thành ErrorRecord; dòng stderr RỖNG (thanh tiến độ của
    tqdm/transformers xuống dòng) ép `[string]` ra đúng chữ
    "System.Management.Automation.RemoteException" — log và tin Telegram đầy chữ đó. Bản cũ
    đi qua `cmd /c ... 2>&1` nên cmd trộn stderr thành chữ thường trước khi PS thấy.
  #>
  param($Item)
  if ($Item -is [System.Management.Automation.ErrorRecord]) {
    $s = [string]$Item.Exception.Message
    if (-not $s) { $s = [string]$Item.TargetObject }
  } else { $s = [string]$Item }
  if ($null -eq $s -or $s.Trim() -eq '' -or $s -eq 'System.Management.Automation.RemoteException') { return $null }
  return $s
}

function Invoke-TopstoryRender {
  <#
    Bước "dựng video" của hai runner deep-dive (Daily Hot, Weekly Repo): ghép spec rồi gọi
    `video-studio render --project topstory`. Một chỗ cho cả hai runner — hai bản chép sớm muộn
    lệch nhau.

    Thương hiệu, giọng, nhạc nền đi TRONG spec, không qua biến môi trường. Biến cũ bị gỡ khỏi
    tiến trình trước khi gọi: `NEWS_BGM`/`VOICE_BGM` còn sót (từ runner cũ, từ một phiên shell)
    làm bước ghép tiếng của engine trộn nhạc thêm một lần NỮA ngoài khối `bgm` của spec.
    `TOPSTORY_ACCENTS` thì GIỮ: template topstory của video-studio 0.1.0 vẫn đọc màu từ đó.

    -BgmPath nằm trong thư viện -BgmDir -> spec mang TÊN style và VOICE_BGM_DIR trỏ thư viện
    (đúng hợp đồng); file ngoài thư viện (khoá `bgm` ép một file riêng của kênh) -> spec mang
    đường dẫn file, engine giọng nhận cả hai. Rỗng -> "none".
    -> @{ code; result; spec }
  #>
  param([Parameter(Mandatory)][string]$Python, [Parameter(Mandatory)][string]$JsonPath,
        [Parameter(Mandatory)][string]$ConfigFile, [Parameter(Mandatory)][string]$Date,
        [Parameter(Mandatory)][string]$OutDir, [string]$VoiceProfile = '', [string]$BgmPath = '',
        [string]$BgmDir = '', [string]$BgmVol = '', [scriptblock]$OnLine)
  $ErrorActionPreference = 'Continue'
  Remove-Item Env:TOPSTORY_BRAND_A, Env:TOPSTORY_BRAND_B, Env:TOPSTORY_KICKER, Env:TOPSTORY_SITE,
              Env:NEWS_BGM, Env:NEWS_BGM_VOL, Env:VOICE_BGM, Env:VOICE_BGM_VOL -ErrorAction SilentlyContinue
  $env:HF_HUB_OFFLINE = '1'; $env:TRANSFORMERS_OFFLINE = '1'; $env:PYTHONIOENCODING = 'utf-8'
  $style = 'none'
  if ($BgmPath -and (Test-Path $BgmPath)) {
    $ten = [System.IO.Path]::GetFileNameWithoutExtension($BgmPath)
    if ($BgmDir -and ((Join-Path $BgmDir ($ten + '.mp3')) -eq $BgmPath)) { $style = $ten; $env:VOICE_BGM_DIR = $BgmDir }
    else { $style = $BgmPath }
  }
  $spec = Join-Path $OutDir ($Date + '-spec.json')
  # Mảng đối số dựng CÓ ĐIỀU KIỆN: PS 5.1 bỏ mất chuỗi rỗng khi truyền cho lệnh ngoài, nên
  # `--profile ''` thành `--profile --bgm ...` và argparse chết vì thiếu giá trị.
  $a = @((Join-Path $script:EngineDir 'topstory_spec.py'), '--top', $JsonPath, '--config', $ConfigFile,
         '--date', $Date, '--bgm', $style, '--out', $spec)
  if ($VoiceProfile) { $a += @('--profile', $VoiceProfile) }
  if ($BgmVol)  { $a += @('--bgm-volume', $BgmVol) }
  & $Python @a 2>&1 | ForEach-Object { $s = Format-NativeLine $_; if ($OnLine -and $null -ne $s) { & $OnLine $s } }
  if ($LASTEXITCODE -ne 0) { return [pscustomobject]@{ code = 2; result = $null; spec = $spec } }
  $r = Invoke-VideoStudio -Python $Python -OnLine $OnLine `
         -Arguments @('render', '--project', 'topstory', '--input', $spec, '--out', $OutDir, '--json')
  return [pscustomobject]@{ code = $r.code; result = $r.result; spec = $spec }
}

function Invoke-RenderPreflight {
  <#
    Rào render (P1-24): `video-studio probe` — render THẬT một trang 320x180 dài 0,5 s, không tài
    nguyên ngoài (vài giây trên máy khoẻ) — đặt TRƯỚC bước nghiên cứu (agent) và TTS.

    Mac mini 02/10/2026: Hot AI 18:00 hỏng sau 42 phút ở `page.goto … Navigation timeout` frame 0
    — môi trường macOS kẹt, mọi project đều hỏng, khởi động lại máy là hết. Không có rào này thì
    lượt chạy đốt agent + TTS + 40 phút rồi mới biết.

    Trần phần RENDER của phép thử: 30 s; đặt `RENDER_PROBE_TIMEOUT` (giây) để đổi — đặt 1 là cách
    GIẢ LẬP máy kẹt khi nghiệm thu (đúng nhánh kẹt, đúng tin ❌). Trước đó probe LÀM ẤM npx +
    Chromium ngoài trần đó (thường vài giây; lần đầu sau nâng bản ghim có thể vài phút, mỗi bước
    trần 600 s ⇒ mã 3) — runner không đặt trần ngoài cho preflight, wrapper của job là trần cuối.
    -> mã thoát cho runner (DỪNG khi khác 0, không thử lại):
       0 đi tiếp · 5 môi trường render KẸT (`RENDER_STUCK`) — khởi động lại máy ·
       1 phép thử hỏng kiểu khác (đuôi log nói vì sao) · 2 cấu hình sai (probe trả JSON lỗi, vd
       `HYPERFRAMES_VERSION=latest`) · 3 thiếu công cụ (npx/Node, Chromium, gói `video_studio`).
       Chỉ `RENDER_STUCK` mới là mã 5 — mã 5 nghĩa là "khởi động lại máy", nói câu đó cho một
       lỗi cấu hình là chỉ sai hướng (review 02/10).
       video-studio cũ (< 0.2.5): mã 2 mà KHÔNG có dòng JSON (lệnh lạ) ⇒ nhắc rồi đi tiếp.

    THANG TỰ CHỮA (P1-25, video-studio ≥ 0.2.7 `probe --heal`): lần đầu kẹt thì video-studio chụp
    gói chẩn đoán vào -DiagDir (`<log>/render-stuck/<giờ>/`), giết Chrome/HyperFrames mồ côi, xoá
    profile tạm cũ > 1 h, chờ 60 s → probe lại, chờ 600 s → probe cuối; qua ⇒ 0 (dòng
    `RENDER_HEAL=recovered`), hết thang mới 5. Nhịp chờ: `RENDER_HEAL_WAITS` (vd `1,1` khi giả lập
    trên máy nghiệm thu); `RENDER_HEAL=0` tắt thang. video-studio 0.2.5/0.2.6 không biết `--heal`
    ⇒ nhắc một dòng rồi probe như cũ (không thang).
  #>
  param([Parameter(Mandatory)][string]$Python, [scriptblock]$OnLine, [string]$DiagDir = '')
  $cb = $OnLine
  $ghi = { param($l) if ($cb) { & $cb $l } }.GetNewClosure()
  $t = 30
  $bien = Get-EnvVar 'RENDER_PROBE_TIMEOUT'
  if ($bien -match '^\d+$' -and [int]$bien -ge 1) { $t = [int]$bien }
  $thang = ((Get-EnvVar 'RENDER_HEAL') -ne '0')
  $cho = '60,600'
  $bienCho = Get-EnvVar 'RENDER_HEAL_WAITS'
  if ($bienCho -match '^\d+(,\d+)*$') { $cho = $bienCho }
  $goc = @('probe', '--timeout', [string]$t, '--json')
  $doi = $goc
  if ($thang) {
    $doi = $goc + @('--heal', '--heal-waits', $cho)
    if ($DiagDir) { $doi += @('--diag-dir', $DiagDir) }
    & $ghi ('Render preflight: video-studio probe (tran ' + $t + 's, ket thi tu chua: cho ' + $cho + 's) ...')
  } else {
    & $ghi ('Render preflight: video-studio probe (tran ' + $t + 's, RENDER_HEAL=0 - khong tu chua) ...')
  }
  # Gom dòng ra rồi mới ghi: video-studio cũ in nguyên bảng trợ giúp (~18 dòng) khi gặp lệnh lạ —
  # mã 2 chỉ cần một dòng nhắc, không cần dồn bảng đó vào log và đuôi tin Telegram.
  $dong = New-Object System.Collections.Generic.List[string]
  $r = Invoke-VideoStudio -Python $Python -OnLine { param($l) $dong.Add([string]$l) }.GetNewClosure() `
         -Arguments $doi
  if ($thang -and $r.code -eq 2 -and (($dong -join "`n") -match 'unrecognized arguments: --heal')) {
    # video-studio 0.2.5/0.2.6: argparse từ chối `--heal` (mã 2 KÈM JSON "tham số không hợp lệ") —
    # không phải cấu hình sai. Probe lại đúng như bản cũ, không có thang.
    & $ghi 'WARN: video-studio < 0.2.7 chua co probe --heal (thang tu chua render ket) - probe nhu cu. Nang video-studio.'
    $dong.Clear()
    $r = Invoke-VideoStudio -Python $Python -OnLine { param($l) $dong.Add([string]$l) }.GetNewClosure() `
           -Arguments $goc
  }
  $cu = ($r.code -eq 2 -and -not $r.result)          # lệnh lạ của video-studio cũ: không JSON
  if (-not $cu) { foreach ($l in $dong) { & $ghi ('probe: ' + $l) } }
  $err = ''
  if ($r.result -and $r.result.error) { $err = [string]$r.result.error }
  $diag = ''
  if ($r.result -and $r.result.diag) { $diag = [string]$r.result.diag }
  if ($r.result -and $r.result.heal -and $r.result.heal.diag) { $diag = [string]$r.result.heal.diag }
  $khongModule = (-not $r.result) -and (($dong -join "`n") -match 'No module named')
  if ($r.code -eq 0) {
    if ($r.result -and $r.result.heal) {
      & $ghi ('WARN: moi truong render KET luc dau, DA TU CHUA (lan ' + $r.result.heal.step + ') - chay tiep. Goi chan doan: ' + $diag)
    }
    & $ghi 'RENDER_PREFLIGHT=ok'; return 0
  }
  if ($r.code -eq 1 -and $err -like 'RENDER_STUCK*') {
    $them = ''
    if ($diag) { $them = ' Goi chan doan: ' + $diag }
    # Dấu ASCII, không so chữ tiếng Việt trong `$err`: dòng ra của lệnh native đi qua bảng mã
    # console — PS 5.1 chưa đặt UTF-8 thì chữ có dấu đã vỡ trước khi tới đây.
    if (($dong -join "`n") -match 'RENDER_HEAL=failed') {
      & $ghi ('ERROR: moi truong render ket - da tu chua (giet Chrome mo coi, xoa profile tam, thu lai) van ket - khoi dong lai may roi chay lai.' + $them)
    } else {
      & $ghi ('ERROR: moi truong render ket (HyperFrames khong mo duoc trang) - khoi dong lai may roi chay lai.' + $them)
    }
    & $ghi 'RENDER_PREFLIGHT=stuck'
    return 5
  }
  if ($r.code -eq 3 -or $khongModule) {
    & $ghi ('ERROR: thieu cong cu render (npx/Node, Chromium hoac goi video_studio trong venv tram giong): ' + $err + ' - chay video-studio doctor.')
    & $ghi 'RENDER_PREFLIGHT=missing'
    return 3
  }
  if ($cu) { & $ghi 'WARN: video-studio chua co lenh probe (can >= 0.2.5) - bo qua phep thu render.'; & $ghi 'RENDER_PREFLIGHT=skipped'; return 0 }
  if ($r.code -eq 2) {
    & $ghi ('ERROR: cau hinh render sai (video-studio probe ma 2): ' + $err + ' - sua cau hinh, chay lai vo ich.')
    & $ghi 'RENDER_PREFLIGHT=config'
    return 2
  }
  & $ghi ('ERROR: phep thu render hong truoc buoc ton kem (ma ' + $r.code + '): ' + $err + ' - chay video-studio doctor --hf.')
  & $ghi 'RENDER_PREFLIGHT=failed'
  return 1
}

function Invoke-LogRotate {
  <#
    Xoay vòng log NGAY TRONG lượt chạy (SUBTASK-WIN-RUNTIME-3 §4): Đức gỡ job dọn tuần trên Mac, nên
    đầu mỗi lượt tin/truyện gọi `scripts/lib/log_rotate.py` — xoá `*.log` quá 60 ngày, cắt file trên
    5 MB (giữ 1 MB cuối, không đụng file vừa ghi trong 1 h), xoá thư mục con quá hạn của -OldDirs
    (gói chẩn đoán `render-stuck/<giờ>/`). Luôn kèm `<trạm>/logs/launchd` (log stdout/stderr của
    launchd — chỉ có trên Mac; thư mục không có thì bỏ qua).
    KHÔNG BAO GIỜ làm hỏng lượt chạy: lỗi gì cũng chỉ thành một dòng WARN. -> không trả gì.
  #>
  param([Parameter(Mandatory)][string]$Python, [string[]]$Dirs = @(), [string[]]$OldDirs = @(),
        [scriptblock]$OnLine)
  $ErrorActionPreference = 'Continue'
  $lr = Join-Path (Join-Path (Join-Path $script:RepoRoot 'scripts') 'lib') 'log_rotate.py'
  $tat = @($Dirs | Where-Object { $_ })
  if ($script:Station) { $tat += (Join-Path (Join-Path $script:Station 'logs') 'launchd') }
  $doi = @($lr)
  foreach ($d in $tat) { $doi += @('--dir', $d) }
  foreach ($d in @($OldDirs | Where-Object { $_ })) { $doi += @('--old-dirs', $d) }
  try {
    & $Python @doi 2>&1 | ForEach-Object {
      $l = Format-NativeLine $_
      if ($null -ne $l -and $OnLine) { & $OnLine $l }
    }
  } catch {
    if ($OnLine) { & $OnLine ('WARN: xoay vong log loi - ' + $_.Exception.Message) }
  }
}

function Get-VideoStudioCodeText {
  param([int]$Code)
  switch ($Code) {
    0 { 'ok' }
    1 { 'engine/render hong (thu lai duoc)' }
    2 { 'goi sai / spec sai (sua cau hinh, KHONG thu lai)' }
    3 { 'thieu tram/cong cu (cai dat, KHONG thu lai)' }
    default { 'ma la' }
  }
}

function Set-SecretEnv {
  <#
    Nạp CON TRỎ bí mật (đường dẫn tới file bí mật, không bao giờ là bí mật) vào tiến trình.

    Windows: đọc THẲNG REGISTRY (phạm vi User) và đè giá trị tiến trình — tiến trình khởi
    động TRƯỚC lần `setx` gần nhất sẽ không có biến, và khi đó code lùi về đường cũ.
    Mọi OS: biến còn rỗng thì lấy từ `<repo>/.env` (chỉ chế độ embedded), và CHỈ nhận giá
    trị có hình dạng đường dẫn — cùng luật với `studio_paths.hook_env()`: `.env` không phải
    kênh để đẩy thứ tuỳ ý vào môi trường của một script đăng bài.
    macOS/launchd: biến đã nằm trong plist; hàm này không ném — thiếu biến phải hỏng ở chỗ
    dùng nó, với thông điệp nói rõ thiếu cái gì.

    Dùng `$env:OS -eq 'Windows_NT'` chứ không phải `$IsWindows`: PS 5.1 không có `$IsWindows`.
  #>
  $ten = @('YT_TOKEN_PATH', 'YT_CLIENT_SECRET', 'FB_CONFIG', 'EMAIL_CONFIG')
  if ($env:OS -eq 'Windows_NT') {
    foreach ($t in $ten) {
      $v = [Environment]::GetEnvironmentVariable($t, 'User')
      if ($v) { Set-Item -Path ("env:" + $t) -Value $v }
    }
  }
  $e = Get-RepoDotEnv
  foreach ($t in $ten) {
    if ([Environment]::GetEnvironmentVariable($t)) { continue }
    if ($e.ContainsKey($t) -and (Test-IsPathValue ([string]$e[$t]))) {
      Set-Item -Path ("env:" + $t) -Value (Resolve-Home ([string]$e[$t]).Trim())
    }
  }
}
