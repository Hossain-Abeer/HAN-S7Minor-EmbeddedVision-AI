<#
.SYNOPSIS
    Renames IAI-gpt note files in the current folder.

.DESCRIPTION
    Applies two literal string replacements to every IAI-gpt-*.txt file:

      1. Removes the literal string 'phase'
      2. Inserts 'design' immediately before 'tracker-'

    Case-sensitive matching (uses -creplace).
    Use -DryRun first to preview every rename before committing.

.PARAMETER DryRun
    Print the planned renames without touching the filesystem.

.EXAMPLE
    .\IAI-gpt-rename-notes.ps1 -DryRun
    .\IAI-gpt-rename-notes.ps1
#>

param(
    [switch]$DryRun
)

# ---- configurable ----------------------------------------------------------
$InsertBeforeTracker = "design"
# ----------------------------------------------------------------------------

Get-ChildItem -Path . -Filter "IAI-gpt-*.txt" -File | ForEach-Object {
    $old = $_.Name
    $new = $old

    # Step 1 - remove literal 'phase'
    $new = $new -creplace 'phase', ''

    # Step 2 - insert 'design' before 'tracker-'
    $new = $new -creplace 'tracker-', "${InsertBeforeTracker}tracker-"

    if ($old -ne $new) {
        if ($DryRun) {
            Write-Host ("DRY RUN: {0}" -f $old)
            Write-Host ("      -> {0}" -f $new)
        }
        else {
            Rename-Item -Path $_.FullName -NewName $new -ErrorAction Stop
            Write-Host ("RENAMED: {0} -> {1}" -f $old, $new)
        }
    }
}