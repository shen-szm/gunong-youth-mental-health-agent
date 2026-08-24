[CmdletBinding()]
param(
    [switch]$Publish,
    [string]$PythonExecutable = 'python'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$archiveRoot = Join-Path (Split-Path -Parent $repo) 'gunong-release-archives'
Push-Location $repo
try {
    $branch = (git branch --show-current).Trim()
    if ($branch -ne 'main') { throw "Release requires main; current branch is $branch." }
    if (@(git status --porcelain).Count -ne 0) { throw 'Release requires a clean worktree.' }
    git diff --check HEAD
    if ($LASTEXITCODE -ne 0) { throw 'git diff --check failed.' }

    $version = (Get-Content -LiteralPath (Join-Path $repo 'VERSION') -Raw).Trim()
    if ($version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') { throw "Invalid VERSION: $version" }
    $packageVersion = (Get-Content -LiteralPath (Join-Path $repo 'frontend/package.json') -Raw | ConvertFrom-Json).version
    if ($packageVersion -ne $version) { throw "frontend/package.json is $packageVersion but VERSION is $version." }
    $config = Get-Content -LiteralPath (Join-Path $repo 'backend/config.py') -Raw
    if ($config -notmatch ('RELEASE_VERSION:\s*str\s*=\s*["'']' + [regex]::Escape($version) + '["'']')) {
        throw 'backend/config.py release version does not match VERSION.'
    }

    & (Join-Path $repo 'scripts/verify-public-repo.ps1')

    Push-Location (Join-Path $repo 'frontend')
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
        npm audit --audit-level=moderate
        if ($LASTEXITCODE -ne 0) { throw 'npm audit failed.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        $frontendTests = @(Get-ChildItem -LiteralPath 'tests' -Filter '*.test.mjs' | Select-Object -ExpandProperty FullName)
        node --test $frontendTests
        if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }
    }
    finally { Pop-Location }

    Push-Location (Join-Path $repo 'backend')
    try {
        & $PythonExecutable -m unittest discover -s tests -p 'test_*.py' -v
        if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
    }
    finally { Pop-Location }

    $tag = "v$version"
    $existingTag = git tag --list $tag
    $headCommit = (git rev-parse HEAD).Trim()
    if ($existingTag) {
        $tagCommit = (git rev-list -n 1 $tag).Trim()
        if ($tagCommit -ne $headCommit) { throw "$tag points to $tagCommit, not tested HEAD $headCommit." }
    } else {
        git tag -a $tag -m "Release $tag"
    }

    $versionDir = Join-Path $archiveRoot $tag
    $zip = Join-Path $versionDir "gunong-youth-mental-health-agent-$tag.zip"
    if (Test-Path -LiteralPath $zip) { throw "Immutable release snapshot already exists: $zip" }
    New-Item -ItemType Directory -Path $versionDir -Force | Out-Null
    git archive --format=zip --output=$zip $tag
    if ($LASTEXITCODE -ne 0) { throw 'git archive failed.' }
    $hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    $commit = $headCommit
    $manifest = [ordered]@{
        version = $version
        tag = $tag
        commit = $commit
        created_at = (Get-Date).ToUniversalTime().ToString('o')
        archive = [IO.Path]::GetFileName($zip)
        sha256 = $hash
    } | ConvertTo-Json
    Set-Content -LiteralPath (Join-Path $versionDir 'manifest.json') -Value $manifest -Encoding utf8
    Set-Content -LiteralPath (Join-Path $versionDir 'SHA256SUMS.txt') -Value "$hash  $([IO.Path]::GetFileName($zip))" -Encoding ascii
    foreach ($snapshotFile in @($zip, (Join-Path $versionDir 'manifest.json'), (Join-Path $versionDir 'SHA256SUMS.txt'))) {
        (Get-Item -LiteralPath $snapshotFile).IsReadOnly = $true
    }

    if ($Publish) {
        $remoteNames = @(git remote)
        foreach ($required in @('github','gitee')) {
            if ($remoteNames -notcontains $required) { throw "Missing required remote: $required" }
        }
        $expectedRepository = 'gunong-youth-mental-health-agent'
        $githubUrl = (git remote get-url --push github).Trim()
        $giteeUrl = (git remote get-url --push gitee).Trim()
        if ($githubUrl -notmatch ('^(https://github\.com/|git@github\.com:|ssh://git@github\.com/).+/' + $expectedRepository + '(?:\.git)?$')) {
            throw "GitHub remote is not an approved github.com repository: $githubUrl"
        }
        if ($giteeUrl -notmatch ('^(https://gitee\.com/|git@gitee\.com:|ssh://git@gitee\.com/).+/' + $expectedRepository + '(?:\.git)?$')) {
            throw "Gitee remote is not an approved gitee.com repository: $giteeUrl"
        }
        git push github main $tag
        if ($LASTEXITCODE -ne 0) { throw 'GitHub push failed; Gitee was not attempted.' }
        git push gitee main $tag
        if ($LASTEXITCODE -ne 0) { throw 'Gitee push failed. GitHub already contains this release; retry after fixing Gitee access.' }
    }

    Write-Host "Release snapshot ready: $zip"
    Write-Host "SHA256: $hash"
}
finally {
    Pop-Location
}
