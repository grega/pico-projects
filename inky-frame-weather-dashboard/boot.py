import os

FILES_TO_UPDATE = ["main.py", "weather_utils.py"]
FAILURE_COUNT_FILE = "failure_count.txt"
MAX_FAILURES = 3

def read_failure_count():
    try:
        with open(FAILURE_COUNT_FILE, "r") as f:
            return int(f.read())
    except Exception:
        return 0

def write_failure_count(count):
    with open(FAILURE_COUNT_FILE, "w") as f:
        f.write(str(count))

def rollback_files():
    rolled_back = False
    for file in FILES_TO_UPDATE:
        prev_file = file + ".prev"
        if prev_file in os.listdir():
            if file in os.listdir():
                os.rename(file, file + ".bad")
            os.rename(prev_file, file)
            print(f"Rolled back {file}")
            rolled_back = True
    if rolled_back:
        write_failure_count(0)
        print("Rollback complete, failure count reset")
    return rolled_back

failure_count = read_failure_count()
if failure_count >= MAX_FAILURES:
    print(f"Boot failure count ({failure_count}) >= {MAX_FAILURES}, rolling back...")
    rollback_files()
else:
    print(f"Boot failure count: {failure_count}/{MAX_FAILURES}")

try:
    import main
except SyntaxError as e:
    print(f"Syntax error in main.py: {e}")
    write_failure_count(failure_count + 1)
    raise
except Exception as e:
    print(f"Failed to import main.py: {e}")
    write_failure_count(failure_count + 1)
    raise

