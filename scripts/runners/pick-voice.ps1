# pick-voice.ps1 -- chon voice profile theo SERIES va NGAY. Deterministic, khong can state.
#
# THUAN ASCII CO CHU DICH: PowerShell 5.1 doc file khong BOM theo ANSI; ky tu tieng Viet
# se vo thanh mojibake va parser chet. Da tra gia mot lan (2026-08-26).
#
#   $Profile = & "$PSScriptRoot\pick-voice.ps1" -Series 'ai-hot'
#   & "$PSScriptRoot\pick-voice.ps1" -Series 'ai-hot' -Explain        # xem vi sao chon
#   & "$PSScriptRoot\pick-voice.ps1" -Simulate 21                     # mo phong 21 ngay toi
#
# ==================================================================================
# BAI TOAN
#
# Cac giong my-voice..my-voice6 deu la giong that cua tac gia nhung khac nhau KHONG DEU.
# Khoang cach do duoc trong khong gian dac trung ngon dieu (F0 trung vi, dai F0, nhip
# noi, ti le ngung, do choi pho), z-score noi bo:
#
#            1     2     3     4     5     6
#   1(mv )  --   3.52  0.91  4.14  4.39  3.28     <-- 1 va 3 la CAP SINH DOI (0.91)
#   2(mv2) 3.52   --   3.34  4.11  4.03  2.93
#   3(mv3) 0.91  3.34   --   4.30  4.68  3.50
#   4(mv4) 4.14  4.11  4.30   --   2.14  2.68
#   5(mv5) 4.39  4.03  4.68  2.14   --   1.56     <-- 5 va 6 cung kha gan (1.56)
#   6(mv6) 3.28  2.93  3.50  2.68  1.56   --
#
# Can hai thu cung luc:
#   (a) LUAN PHIEN qua cac ngay  -- moi lan chay mot giong khac lan truoc
#   (b) TACH BACH trong cung ngay -- thu Sau co 3 video (tin nong AI 18h, tin nong
#       Data 19h, ban tin tuan AI 21h); ba video do khong duoc dung giong giong nhau
#
# CACH LAM DAU (pool + offset modulo) GIAI QUYET DUOC (a) NHUNG THUA (b): mo phong 21
# ngay ra 4 ngay hong, co ngay hai video dung DUNG MOT giong. Offset khong cuu duoc --
# pool co dinh + offset co dinh thi va cham la tat yeu.
#
# CACH LAM HIEN TAI: moi ngay, gan giong cho TAT CA series chay hom do theo mot thu tu
# co dinh; moi series duyet pool cua no theo thu tu quay (de van luan phien qua ngay) va
# lay UNG VIEN DAU TIEN cach moi giong da gan hom nay it nhat MIN_GAP. Khong con ung
# vien nao dat thi lay cai xa nhat. Khong can luu state, chay lai ra ket qua y het.
# ==================================================================================

param(
  [string]$Series,
  [datetime]$Date = (Get-Date),
  [switch]$Explain,
  [int]$Simulate = 0
)

$MIN_GAP = 2.0   # duoi nguong nay thi hai giong nghe qua giong nhau khi dat canh

$DIST = @{
  'my-voice|my-voice2'=3.52; 'my-voice|my-voice3'=0.91; 'my-voice|my-voice4'=4.14
  'my-voice|my-voice5'=4.39; 'my-voice|my-voice6'=3.28; 'my-voice2|my-voice3'=3.34
  'my-voice2|my-voice4'=4.11; 'my-voice2|my-voice5'=4.03; 'my-voice2|my-voice6'=2.93
  'my-voice3|my-voice4'=4.30; 'my-voice3|my-voice5'=4.68; 'my-voice3|my-voice6'=3.50
  'my-voice4|my-voice5'=2.14; 'my-voice4|my-voice6'=2.68; 'my-voice5|my-voice6'=1.56
}

function Get-Gap($a, $b) {
  # Tra $null khi CHUA DO khoang cach cap nay. KHONG tra 0 va KHONG de roi vao
  # $null ngam: PowerShell ep $null thanh 0 trong so sanh so, nen "chua do" se bi
  # doc thanh "giong het nhau" -> canh bao gia keu moi ngay. Mot cong bao dong sai
  # moi ngay la mot cong se bi phot lo dung luc no bao that.
  if ($a -eq $b) { return 0.0 }
  $k = "$a|$b"
  if ($DIST.ContainsKey($k)) { return $DIST[$k] }
  $k2 = "$b|$a"
  if ($DIST.ContainsKey($k2)) { return $DIST[$k2] }
  return $null
}

# Pool moi brand -- de moi thuong hieu co mot ho giong rieng.
# offset chi con lam moc quay, khong con phai ganh viec tach bach cung ngay.
# GHIM MOT GIONG MOI SERIES -- Duc quyet 31/08/2026 sau khi nghe bo A/B.
# VI SAO bo luan phien: render CUNG mot cau qua 7 profile ra RMS -20.3..-30.2 dB
# (chenh 9.9 dB) va toc do 3.78..4.28 tu/giay (chenh 13%). Luan phien theo ngay
# = doi ca do to lan nhip doc giua cac ngay, dung trieu chung "luc to luc nho"
# va "luc nhanh luc cham" ma Duc phan anh. Am luong nay da duoc chuan hoa o tang
# engine (mcp_server.normalize_rms), nhung NHIP DOC thi khong chuan duoc -- no
# nam trong clip mau. Nen ghim la cach duy nhat cho nhip on dinh.
#
# Muon bat lai luan phien: dien them giong vao pool. NHUNG phai cat lai clip mau
# sao cho toc do lech <10% va ref_text du dau cau -- neu khong se lap lai dung
# cai benh vua chua xong.
$POOL = @{
  'ai-hot'      = @{ pool = @('my-voice-2208'); offset = 0 }   # Daily Hot AI 6PM
  'ai-weekly'   = @{ pool = @('my-voice2');     offset = 0 }   # ban tin tuan AI
  'data-hot'    = @{ pool = @('my-voice');      offset = 0 }   # Daily Hot Data 7PM
  'data-weekly' = @{ pool = @('my-voice4');     offset = 0 }   # ban tin tuan Data
  'repo-weekly' = @{ pool = @('my-voice6');     offset = 0 }   # Weekly Repo Sunday
}

# Thu tu gan CO DINH -- weekly duoc chon truoc vi no la video chu luc cua tuan;
# cac ban daily thich nghi theo. Thu tu nay chi can khong doi, khong can trung
# thu tu phat hanh.
$ORDER = @('ai-weekly','data-weekly','repo-weekly','ai-hot','data-hot')

function Get-RunsOn([datetime]$d) {
  $r = @('ai-hot','data-hot')                              # chay hang ngay
  switch ($d.DayOfWeek) {
    'Friday'   { $r += 'ai-weekly' }
    'Saturday' { $r += 'data-weekly' }
    'Sunday'   { $r += 'repo-weekly' }
  }
  return $r
}

function Get-Assignment([datetime]$d) {
  $runs = Get-RunsOn $d
  $out  = @{}
  foreach ($s in $ORDER) {
    if ($runs -notcontains $s) { continue }
    # CHU Y: KHONG dat ten bien la $pool. PowerShell KHONG phan biet hoa thuong, nen
    # `$pool = ...` se ghi de luon bang $POOL o scope script -> vong lap sau index vao
    # mang ten giong va tra null. Da tra gia dung loi nay 2026-08-26.
    $cfg = $POOL[$s]; $plist = $cfg.pool; $n = $plist.Count
    # Pool GHIM (1 giong): lay thang. Khong chay may do khoang cach vi (a) khong
    # co gi de chon, (b) giong moi chua co trong bang $DIST se tra $null va
    # PowerShell ep $null thanh 0 -- so sanh van "chay" nhung vo nghia.
    if ($n -eq 1) { $out[$s] = $plist[0]; continue }
    $start = ([int]$d.DayOfYear + [int]$cfg.offset) % $n
    $taken = @($out.Values)
    $best = $null; $bestGap = -1.0
    for ($i = 0; $i -lt $n; $i++) {
      $c = $plist[($start + $i) % $n]
      $gap = 99.0
      foreach ($t in $taken) {
        $g = Get-Gap $c $t
        if ($null -eq $g) { continue }          # chua do thi khong ket luan
        if ($g -lt $gap) { $gap = $g }
      }
      if ($gap -ge $MIN_GAP) { $best = $c; $bestGap = $gap; break }   # dat nguong -> lay ngay
      if ($gap -gt $bestGap) { $best = $c; $bestGap = $gap }          # giu cai xa nhat lam du phong
    }
    $out[$s] = $best
  }
  return $out
}

if ($Simulate -gt 0) {
  "{0,-13} {1,-52} {2}" -f 'ngay', 'phat hanh hom do', 'cap gan nhat'
  "-" * 92
  $bad = 0
  0..($Simulate - 1) | ForEach-Object {
    $d = (Get-Date).AddDays($_); $a = Get-Assignment $d
    $ks = @($a.Keys); $worst = 99.0; $wp = ''; $unk = 0
    for ($i = 0; $i -lt $ks.Count; $i++) { for ($j = $i + 1; $j -lt $ks.Count; $j++) {
      $g = Get-Gap $a[$ks[$i]] $a[$ks[$j]]
      if ($null -eq $g) { $unk++; continue }
      if ($g -lt $worst) { $worst = $g; $wp = "$($a[$ks[$i]])/$($a[$ks[$j]])" } } }
    $lst = ($ks | ForEach-Object { "$_=$($a[$_])" }) -join ' '
    $flag = if ($worst -lt $MIN_GAP) { $script:bad++; " HONG: $wp d=$worst" }
            elseif ($worst -eq 99.0) { " (khong cap nao do duoc: $unk cap chua co trong bang)" }
            elseif ($unk -gt 0)      { " d_min=$worst (+$unk cap chua do)" }
            else                     { " d_min=$worst" }
    "{0,-13} {1,-52} {2}" -f $d.ToString('MM-dd ddd'), $lst, $flag
  }
  ""
  if ($bad -eq 0) { "OK: $Simulate ngay, khong ngay nao co hai video giong nhau qua muc" }
  else { "CANH BAO: $bad / $Simulate ngay co van de" }
  return
}

if (-not $Series) { Write-Error "pick-voice: thieu -Series hoac -Simulate"; return 'my-voice' }
if (-not $POOL.ContainsKey($Series)) {
  # Fail-safe: khong bao gio tra chuoi rong -- pipeline nhan chuoi rong se roi ve
  # default mutable, dung cai ta dang tranh.
  Write-Error "pick-voice: khong biet series '$Series'. Co: $($POOL.Keys -join ', ')"
  return 'my-voice'
}

$asg = Get-Assignment $Date
$pick = $asg[$Series]
if (-not $pick) {
  # Series khong nam trong lich cua ngay do (vd chay tay ban tin tuan vao thu Ba).
  # Van phai tra mot giong hop le: dung moc quay cua chinh series do.
  $cfg = $POOL[$Series]
  $pick = $cfg.pool[(([int]$Date.DayOfYear + [int]$cfg.offset) % $cfg.pool.Count)]
}

if ($Explain) {
  $others = ($asg.Keys | Where-Object { $_ -ne $Series } | ForEach-Object { "$_=$($asg[$_])" }) -join ' '
  Write-Output ("series={0} ngay={1} -> {2}   (cung ngay: {3})" -f $Series, $Date.ToString('yyyy-MM-dd'), $pick, $others)
} else {
  Write-Output $pick
}
