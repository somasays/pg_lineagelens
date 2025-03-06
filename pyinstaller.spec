# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import site
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get pip-installed site packages
site_packages = site.getsitepackages()

# Get pipenv virtual environment site-packages (only if running inside pipenv)
if os.environ.get('PIPENV_ACTIVE') == '1':
    venv_path = os.environ.get('VIRTUAL_ENV')
    if venv_path:
        if sys.platform == 'win32':
            venv_site_packages = os.path.join(venv_path, 'Lib', 'site-packages')
        else:
            venv_site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
        site_packages.append(venv_site_packages)

block_cipher = None

# Add data files (templates, static files, etc.)
datas = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
]

# Add icon files for different platforms
if sys.platform == 'win32':
    icon_file = 'packaging/windows/pg_lineage.ico'
elif sys.platform == 'darwin':
    icon_file = 'packaging/macos/pg_lineage.icns'
else:
    icon_file = 'packaging/linux/pg_lineage.png'

# Add hidden imports
hiddenimports = [
    'sqlparse',
    'networkx',
    'matplotlib',
    'pandas',
    'psycopg2',
    'waitress',
    'flask_session',
]

# Add all networkx algorithms modules
hiddenimports.extend(collect_submodules('networkx.algorithms'))

# Add all matplotlib modules
hiddenimports.extend(collect_submodules('matplotlib'))

# Add pandas modules
hiddenimports.extend(collect_submodules('pandas'))

a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pg_lineage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for windowed application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pg_lineage',
)

# For macOS
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='PostgreSQL Data Lineage.app',
        icon='packaging/macos/pg_lineage.icns',
        bundle_identifier='com.pglineage',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHumanReadableCopyright': '© 2024 PostgreSQL Data Lineage',
            'CFBundleName': 'PostgreSQL Data Lineage',
            'CFBundleDisplayName': 'PostgreSQL Data Lineage',
            'CFBundleExecutable': 'pg_lineage',
            'LSBackgroundOnly': False,
            'LSEnvironment': {'PYTHONOPTIMIZE': '1'},
        },
    )