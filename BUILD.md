# Compiling repo2md

Convert the Python script into a standalone binary executable using PyInstaller.

## Requirements

- Python 3.8 or higher
- pip package manager

## Steps

1. Install PyInstaller:

```bash
pip3 install -U pyinstaller
```

2. Create the binary executable:

```bash
pyinstaller --onefile repo2md.py
```

3. Install the binary executable by using the provided script:

```bash
bash install.sh
```

4. Run the binary executable:

```bash
repo2md
```
