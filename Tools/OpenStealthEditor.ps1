param([switch]$WithTools)
$projectRoot=Split-Path -Parent $PSScriptRoot
$editor='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$arguments=@((Join-Path $projectRoot 'StealthShooter.uproject'),'-NoSplash')
if($WithTools){
    $arguments+='-EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities,EditorToolset'
    $arguments+='-ExecCmds="py '+(Join-Path $PSScriptRoot 'editor_bridge.py').Replace('\','/')+'"'
}
Start-Process -FilePath $editor -ArgumentList $arguments -WindowStyle Normal
