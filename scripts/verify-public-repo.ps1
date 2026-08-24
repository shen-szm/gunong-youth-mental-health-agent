[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$textExtensions = @('.py','.js','.mjs','.cjs','.ts','.tsx','.vue','.json','.md','.txt','.yml','.yaml','.toml','.ini','.cfg','.ps1','.sh','.html','.css')
$credentialAssignment = '^(?i)\s*["'']?(?<key>[A-Za-z0-9_.-]*(?:api[_-]?(?:key|secret)|access[_-]?token|client[_-]?secret|password|passwd|pwd|spark_api_password|mysql_password)[A-Za-z0-9_.-]*)["'']?\s*[:=]\s*(?<value>.+?)\s*$'
$directSecretPatterns = @(
    '(?i)-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    '(?i)https?://[^/\s]+:[^@\s]+@',
    '(?i)\bghp_[A-Za-z0-9]{20,}\b',
    '(?i)\bgithub_pat_[A-Za-z0-9_]{20,}\b',
    '(?i)\bglpat-[A-Za-z0-9_-]{20,}\b'
)

function Test-TextForCredentials([string]$content, [string]$label, [System.Collections.Generic.HashSet[string]]$findings) {
    foreach ($pattern in $directSecretPatterns) {
        if ($content -match $pattern) { [void]$findings.Add($label); return }
    }
    foreach ($line in ($content -split "`r?`n")) {
        $match = [regex]::Match($line, $credentialAssignment)
        if (-not $match.Success) { continue }
        $key = $match.Groups['key'].Value.ToLowerInvariant()
        if ($key -match 'hash|\.value$|(?:msg|ok)$' -or $key.StartsWith('.')) { continue }
        $value = $match.Groups['value'].Value.Trim().TrimEnd(',',';').Trim().Trim('"', "'")
        if (-not $value) { continue }
        if ($value -match '^(?i)(your_|example|placeholder|str\b|none$|null$|false$|true$|settings\.|self\.|payload\.|os\.|getenv\b|field\(|token_urlsafe\(|secrets\.|\$\{|\$env:)') { continue }
        if ($value -match '^[A-Za-z_][A-Za-z0-9_.]*\(.*\)$') { continue }
        if ($value.Length -ge 8) { [void]$findings.Add($label); return }
    }
}

Push-Location $repo
try {
    if (-not (Test-Path -LiteralPath (Join-Path $repo '.git'))) {
        throw 'This check must run inside the sanitized Git repository.'
    }

    $tracked = @(git ls-files)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to list tracked files.' }

    $forbiddenPath = '(?i)(^|/)(\.env($|\.)|.*\.(db|sqlite|sqlite3|log|pem|key|p12|pfx|jks|keystore|zip|7z|rar|tar|gz|sql|mp3|wav|ogg|m4a|flac|mp4|webm|mov|avi)$|uploads?|backups?|logs?|output|tmp|release-archives|\.codex-[^/]+|node_modules|venv|dist)(/|$)'
    $badPaths = @($tracked | Where-Object { $_ -match $forbiddenPath -and $_ -notmatch '(?i)\.env\.(example|sample)$' })
    $badPetPaths = @($tracked | Where-Object { $_ -match '^frontend/public/pets/' -and $_ -notmatch '^frontend/public/pets/bubu/' })
    if ($badPaths.Count -gt 0 -or $badPetPaths.Count -gt 0) {
        throw "Forbidden tracked paths:`n$(@($badPaths + $badPetPaths | Sort-Object -Unique) -join "`n")"
    }

    $assetManifest = Get-Content -LiteralPath (Join-Path $repo 'ASSET_LICENSES.md') -Raw
    $publicImages = @($tracked | Where-Object { $_ -match '^frontend/public/.+\.(png|jpg|jpeg|webp|gif|svg)$' })
    $unlicensedImages = [System.Collections.Generic.List[string]]::new()
    foreach ($relative in $publicImages) {
        $hash = (Get-FileHash -LiteralPath (Join-Path $repo $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($assetManifest -notmatch [regex]::Escape($relative) -or $assetManifest -notmatch $hash) {
            $unlicensedImages.Add($relative)
        }
    }
    if ($unlicensedImages.Count -gt 0) {
        throw "Public images missing path and SHA-256 license records:`n$($unlicensedImages -join "`n")"
    }

    $findings = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($relative in $tracked) {
        if ($textExtensions -notcontains [IO.Path]::GetExtension($relative)) { continue }
        $full = Join-Path $repo $relative
        if (Test-Path -LiteralPath $full -PathType Leaf) {
            Test-TextForCredentials (Get-Content -LiteralPath $full -Raw) "worktree:$relative" $findings
        }
    }

    $revisions = @(git rev-list --all)
    foreach ($revision in $revisions) {
        $historyFiles = @(git ls-tree -r --name-only $revision)
        $badHistoryPaths = @($historyFiles | Where-Object {
            ($_ -match $forbiddenPath -and $_ -notmatch '(?i)\.env\.(example|sample)$') -or
            ($_ -match '^frontend/public/pets/' -and $_ -notmatch '^frontend/public/pets/bubu/')
        })
        if ($badHistoryPaths.Count -gt 0) {
            throw "Forbidden paths found in history revision $($revision.Substring(0,12)):`n$($badHistoryPaths -join "`n")"
        }
        foreach ($relative in $historyFiles) {
            if ($textExtensions -notcontains [IO.Path]::GetExtension($relative)) { continue }
            $content = (git show "$revision`:$relative" 2>$null | Out-String)
            Test-TextForCredentials $content "history:$($revision.Substring(0,12)):$relative" $findings
        }
    }
    if ($findings.Count -gt 0) {
        throw "Possible credential material detected:`n$(@($findings) -join "`n")"
    }

    Write-Host "Public repository safety check passed for $($tracked.Count) tracked files and $($revisions.Count) revision(s)."
}
finally {
    Pop-Location
}
