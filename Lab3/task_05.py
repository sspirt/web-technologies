#!C:\WebSoft\Python\python.exe

import sys

def process_element(element):
    if isinstance(element, list):
        return [process_element(e) for e in element]
    if isinstance(element, int):
        return element * 2
    if isinstance(element, float):
        return round(element, 2)
    if isinstance(element, str):
        return element.upper()
    return element

def flat_rows(arr, path=""):
    rows = []
    for i, element in enumerate(arr):
        cur = f"{path}[{i}]"
        if isinstance(element, list):
            rows += flat_rows(element, cur)
        else:
            rows.append((cur, element))
    return rows

sys.stdout.reconfigure(encoding="utf-8")
print("Content-type: text/html; charset=utf-8\n")
array = [
    [1, "hello", 3.1434],
    [45, 5.12984, "abc"],
    ["x = 35", 2.2295, 9]
]
try:
    result = [process_element(e) for e in array]
except Exception as e:
    print(f"<p>Error: {e}</p>")
    sys.exit(1)
orig_rows = flat_rows(array)
proc_rows = flat_rows(result)
print("""<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>
<table border="1" cellpadding="6">
<tr><th>Индекс</th><th>Original</th><th>Result</th></tr>""")
for (i, orig), (_, proc) in zip(orig_rows, proc_rows):
    print(f"<tr><td>{i}</td><td>{orig!r}</td><td>{proc!r}</td></tr>")
print("</table></body></html>")

