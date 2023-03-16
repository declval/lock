import subprocess

from lock import PROGRAM_NAME

subprocess.run([
    'pyinstaller',
    '--hidden-import', '_cffi_backend',
    '--icon', 'icon.png',
    '--noconsole',
    '--onefile',
    f'{PROGRAM_NAME}.py'
])