#!C:\WebSoft\Python\python.exe

import os
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
print("Content-Type: text/html; charset=utf-8\n")
METHOD = os.environ.get("REQUEST_METHOD", "GET").upper()

def parse_numbers(s):
    if not s.strip():
        raise ValueError("String is empty")
    result = []
    for c in s.split():
        try:
            n = float(c)
            result.append(int(n) if n.is_integer() else n)
        except ValueError:
            raise ValueError(f"{c} is not a number")
    return result

def merge_sets(set1, set2):
    values = set(set1)
    return list(set1) + [n for n in set2 if n not in values]


def render(s1="2 2 5 3 7 2", s2="2 4 4 85", result=None, error=None):
    print(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>
    <form method="post">
        <label>Set 1:<br><input type="text" name="set1" size="40" value="{s1}"></label><br><br>
        <label>Set 2:<br><input type="text" name="set2" size="40" value="{s2}"></label><br><br>
        <input type="submit" value="Process">
    </form>""")
    if error:
        print(f"<p>Error: {error}</p>")
    elif result is not None:
        r1, r2, res = result
        print(f"<p>Set 1: {r1}</p>")
        print(f"<p>Set 2: {r2}</p>")
        print(f"<p>Result: {res}</p>")
    print("</body></html>")

if METHOD == "POST":
    try:
        length = int(os.environ.get("CONTENT_LENGTH", 0))
        body = sys.stdin.read(length) if length > 0 else ""
    except (ValueError, OSError):
        render(error="Error handling request")
        sys.exit(1)
    params = urllib.parse.parse_qs(body, keep_blank_values=True)
    raw1 = params.get("set1", [""])[0].strip()
    raw2 = params.get("set2", [""])[0].strip()
    try:
        set1 = parse_numbers(raw1)
        set2 = parse_numbers(raw2)
    except ValueError as e:
        render(raw1, raw2, error=str(e))
        sys.exit(1)
    render(raw1, raw2, result=(set1, set2, merge_sets(set1, set2)))
else:
    render()