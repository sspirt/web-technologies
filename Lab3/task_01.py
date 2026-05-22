#!C:\WebSoft\Python\python.exe

import urllib.parse
import os
import sys

print("Content-Type: text/html; charset=utf-8\n")
query_string = os.environ.get("QUERY_STRING", "")
params = urllib.parse.parse_qs(query_string)
raw = params.get("cities", [""])[0]
if not raw.strip():
    print("<p>No cities provided.</p>")
    print("<p>Example:?cities=Minsk,Moscow</p>")
    sys.exit(0)
cities = [city.strip() for city in raw.split(",") if city.strip()]
if not cities:
    print("<p>No cities provided.</p>")
    sys.exit(0)
unique_cities = sorted(set(cities), key=lambda city: city.lower())
print("<html><head><meta charset='utf-8'><title>Cities</title></head><body>")
print(f"<p>Number of unique cities: {len(unique_cities)}</p>")
print("<ol>")
for city in unique_cities:
    print(f"<li>{city}</li>")
print("</ol></body></html>")
