@echo off
title Voice Intake - Creare snapshot ZIP
cd /d "%~dp0.."
python -c "
import zipfile, os, pathlib, re, datetime
base = pathlib.Path('.')
skip_dirs = {'__pycache__', '.git', '_backup_v025', 'recordings', 'logs', 'loguri', 'temp_audio', 'uploads', 'data', 'cases', 'dosare', 'date'}
skip_exts = {'.pyc', '.pyo', '.log', '.tmp'}
includes = ['_app', '_launcher', '_tools', 'static', 'templates', 'requirements.txt', 'launch_tray.py', '.env.example']
existing = [f.name for f in base.glob('VoiceIntake_v0.0.4.*.zip')]
nums = [int(re.search(r'v0\.0\.4\.(\d+)', n).group(1)) for n in existing if re.search(r'v0\.0\.4\.(\d+)', n)]
next_n = max(nums)+1 if nums else 1
import re
zip_name = f'VoiceIntake_v0.0.4.{next_n}_USB.zip'
count = 0
with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
    for inc in includes:
        p = base / inc
        if not p.exists(): continue
        if p.is_file(): zf.write(p, inc); count += 1; continue
        for fpath in sorted(p.rglob('*')):
            if fpath.is_dir(): continue
            if any(s in skip_dirs for s in fpath.parts): continue
            if fpath.suffix in skip_exts: continue
            zf.write(fpath, str(fpath.relative_to(base))); count += 1
size = os.path.getsize(zip_name)/1024/1024
print(f'  Creat: {zip_name}  ({count} fisiere, {size:.1f} MB)')
"
echo.
pause
