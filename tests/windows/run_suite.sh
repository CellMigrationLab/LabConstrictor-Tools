#!/bin/bash
"$(dirname "$0")/winpy.sh" /usr/lib/wine/wine 'C:\apps\CellTracksColab\python.exe' -c "
import os,sys,runpy
os.environ['LC_TEST_PREFIX']=r'C:\apps\CellTracksColab'
os.environ['LC_TEST_EXTRA_PYTHONPATH']=r'C:\apps\CellTracksColab\CellTracksColab\src'
sys.argv=['x']; runpy.run_path(r'C:\poc\tests\windows\test_windows.py', run_name='__main__')"
