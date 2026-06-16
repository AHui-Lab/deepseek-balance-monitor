Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "python """ & ScriptDir & "\deepseek_monitor.py""", 0, False
