<img src="icon.png" width="180px">

`lock` is a very simple password manager written in Python.

It uses PyNaCl library's symmetric encryption functionality to encrypt
everything stored in the database.

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/declval/lock
   ```

2. Change to the created directory:

   ```
   cd lock
   ```

3. Create a Python virtual environment and activate it (Optional):

   On Windows (cmd.exe):

   ```
   py -m venv .venv
   .venv\Scripts\activate.bat
   ```

   On Linux, macOS:

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install missing dependencies:

   ```
   pip install -r requirements.txt
   ```

5. Run the Qt Resource Compiler

   On Windows (cmd.exe):

   ```
   .venv\Lib\site-packages\PySide6\rcc -g python resources.qrc -o resources_rc.py
   ```

   On Linux, macOS:

   ```
   .venv/bin/pyside6-rcc -g python resources.qrc -o resources_rc.py
   ```

6. Run the program without arguments to launch the GUI version. For command line usage information add `-h/--help`:

   On Windows (cmd.exe):

   ```
   py lock.py
   ```

   On Linux, macOS:

   ```
   python3 lock.py
   ```

7. Run the tests (Optional):

   On Windows (cmd.exe):

   ```
   py -m unittest test_lock.py
   ```

   On Linux, macOS:

   ```
   python3 -m unittest test_lock.py
   ```
