#!C:\WebSoft\Python\python.exe
import os
import urllib.parse

def determine_type(value):
    try:
        int(value)
        return "int"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        pass
    return "string"

query_string = os.environ.get("QUERY_STRING", "")
params = urllib.parse.parse_qs(query_string, keep_blank_values=True)
print("Content-Type: text/html; charset=utf-8\n")
print("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>GET-request</title>
<style>
  body { font-family: sans-serif; margin: 20px; }
  table { border-collapse: collapse; }
  th, td { border: 1px solid #aaa; padding: 8px 14px; }
  th { background: #eee; }
</style>
</head><body>""")
if not params:
    print("<p>No parameters provided. Example: <code>?x=42&y=3.14&z=hello</code></p>")
else:
    print("<table><tr><th>Parameter</th><th>Value</th><th>Type</th></tr>")
    for key, values in params.items():
        for value in values:
            t = determine_type(value)
            print(f"  <tr><td>{key}</td><td>{value}</td><td>{t}</td></tr>")
    print("</table>")
print("</body></html>")