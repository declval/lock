import subprocess

from lock import PROGRAM_NAME

subprocess.run([
    'pyinstaller',
    '--add-data', 'Roboto-Regular.ttf;.',
    '--add-data', 'icon.png;.',
    '--add-data', 'minus-solid.svg;.',
    '--add-data', 'plus-solid.svg;.',
    '--add-data', 'stylesheet.qss;.',
    '--hidden-import', '_cffi_backend',
    '--noconsole',
    '--onefile',
    f'{PROGRAM_NAME}.py'
])