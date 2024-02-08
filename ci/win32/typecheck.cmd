REM script to run mypy type checker on this source tree.
pushd .
cd /D "%~dp0"
cd ..\..\
call .\venv\Scripts\activate
set PYTHONPATH=.\src\grow_worker;%$PYTHONPATH%
python -m mypy ./src/grow_worker ./unit_test/
popd