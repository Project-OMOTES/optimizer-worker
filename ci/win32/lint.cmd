rem Short script to run linting
rem @echo off

pushd .
cd /D "%~dp0"
cd ..\..\
flake8 .\src\grow_worker
popd
