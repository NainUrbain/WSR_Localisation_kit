param([string]$Output = "$PSScriptRoot\dist\workshop_ko\preview.png")
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$bitmap = New-Object System.Drawing.Bitmap 640,640
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = 'AntiAlias'
$graphics.TextRenderingHint = 'AntiAliasGridFit'
$navy = [System.Drawing.ColorTranslator]::FromHtml('#101d2d')
$gold = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#e1bf78'))
$white = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#f4f3ee'))
$muted = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#a4b2c3'))
$small = New-Object System.Drawing.Font 'Segoe UI',15
$title = New-Object System.Drawing.Font 'Segoe UI',62,([System.Drawing.FontStyle]::Bold)
$korean = New-Object System.Drawing.Font 'Malgun Gothic',44,([System.Drawing.FontStyle]::Bold)
$label = New-Object System.Drawing.Font 'Segoe UI',23
try {
    $graphics.Clear($navy)
    $graphics.FillRectangle($gold,48,48,72,5)
    $graphics.DrawString('WALL STREET RAIDER',$small,$muted,48,80)
    $graphics.DrawString('WSR',$title,$white,42,163)
    $graphics.DrawString(([string][char]0xd55c + [char]0xad6d + [char]0xc5b4),$korean,$gold,43,268)
    $graphics.DrawString('KOREAN LOCALIZATION',$label,$white,48,391)
    $graphics.FillRectangle($gold,48,475,544,2)
    $graphics.DrawString('Nain Urbain',$small,$muted,48,528)
    $graphics.DrawString('COMMUNITY TRANSLATION',$small,$muted,48,559)
    $bitmap.Save([IO.Path]::GetFullPath($Output),[System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $graphics.Dispose(); $bitmap.Dispose()
    foreach($resource in @($gold,$white,$muted,$small,$title,$korean,$label)) { $resource.Dispose() }
}
Write-Output $Output
