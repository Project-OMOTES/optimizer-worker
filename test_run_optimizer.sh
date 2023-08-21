. .venv/bin/activate

python3 --version
PYTHONPATH="$PYTHONPATH:src/:compute-engine-sdk-python/src/" python3 test_run_optimizer.py
