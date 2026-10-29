# SPDX-FileCopyrightText: 2026 MSHost contributors
# SPDX-License-Identifier: GPL-2.0-or-later
param([Parameter(Mandatory = $true)][string]$AssetDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
foreach ($assetName in @('header', 'welcome')) {
    $inputImage = [System.Drawing.Image]::FromFile((Join-Path $AssetDirectory "$assetName.png"))
    $outputImage = New-Object System.Drawing.Bitmap($inputImage.Width, $inputImage.Height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $graphics = [System.Drawing.Graphics]::FromImage($outputImage)
    try {
        $graphics.DrawImage($inputImage, 0, 0, $inputImage.Width, $inputImage.Height)
        $outputImage.Save((Join-Path $AssetDirectory "$assetName.bmp"), [System.Drawing.Imaging.ImageFormat]::Bmp)
    } finally {
        $graphics.Dispose()
        $outputImage.Dispose()
        $inputImage.Dispose()
    }
}
