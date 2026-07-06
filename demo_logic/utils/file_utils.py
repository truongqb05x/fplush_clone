# file_utils.py

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return [l.strip() for l in f if l.strip()]
    except:
        return []

def write_file(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")

def append_file(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
