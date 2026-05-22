#!C:\WebSoft\Python\python.exe

import os
import sys
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')
print("Content-type:text/html; charset=utf-8\n")
METHOD = os.environ.get("REQUEST_METHOD", "GET").upper()

def render(s="раз два три четыре", result=None, error=None):
    print(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>
    <form method="post">
        <label>String:<br><input type="text" name="string" size="40" value="{s}"></label><br><br>
        <input type="submit" value="Process">
    </form>""")
    if error:
        print(f"<p>Error: {error}</p>")
    elif result is not None:
        s0, s = result
        print(f"<p>String: {s0}</p>")
        print(f"<p>Result: {s}</p>")
    print("</body></html>")

if METHOD == "POST":
    try:
        length = int(os.environ.get("CONTENT_LENGTH", 0))
        body = sys.stdin.read(length) if length > 0 else ""
    except (ValueError, OSError):
        render(error="Error handling request")
        sys.exit(1)
    params = urllib.parse.parse_qs(body, keep_blank_values=True)
    s = params.get("string", [""])[0].strip()
    render(s, (s, " ".join(reversed(s.split()))))
else:
    render()