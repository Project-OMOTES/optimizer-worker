call .\venv\Scripts\activate
mkdir .\temp\input_files
mkdir .\temp\output_files


set PYTHONPATH=.\src\;%$PYTHONPATH%
set INPUT_FILES_DIR=.\temp\input_files
set OUTPUT_FILES_DIR=.\temp\output_files
python -m optimizer_worker.main
