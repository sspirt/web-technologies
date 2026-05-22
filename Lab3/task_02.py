#!C:\WebSoft\Python\python.exe

import os
import sys
import urllib.parse

print("Content-Type: text/html; charset=utf-8\n")
query_string = os.environ.get("QUERY_STRING", "")
params = urllib.parse.parse_qs(query_string)
text = params.get("text", [""])[0].strip()
if not text:
    print("<p>No text provided</p>")
    print("<p>Please provide some text, example: ?text=one+two+three</p>")
    sys.exit(0)
words = text.split()
html = []
for i, word in enumerate(words):
    is_third_word = i % 3 == 2
    j = 0
    for char in word:
        if char.isalpha():
            j += 1
            display = char.upper() if is_third_word else char
            if j % 3 == 0:
                html.append(f"<span style='color:purple;'>{display}</span>")
            else:
                html.append(display)
        else:
            html.append(char)
    html.append("<br>")
print("<html><head><meta charset='utf-8'></head><body>")
print("".join(html))
print("</body></html>")