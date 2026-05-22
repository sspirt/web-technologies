import sys

def hex_color(value):
    return f"#{value:02X}{value:02X}{value:02X}"

if len(sys.argv) != 2:
    print("Использование: python task_additional_02.py <количество_строк>")
    sys.exit(1)

try:
    rows = int(sys.argv[1])
    if rows < 1:
        raise ValueError
except ValueError:
    print("Укажите положительное целое число")
    sys.exit(1)
output = [
    "<!DOCTYPE html>",
    "<html><head><meta charset='UTF-8'><title>Gradient</title>",
    "<style>body{font-family:sans-serif;margin:20px}",
    "table{border-collapse:collapse;min-width:220px}",
    "td{padding:6px 14px;border:1px solid #555}</style>",
    "</head><body>",
    "<table>",
]
for i in range(rows):
    val = int(255 * (1 - i / max(rows - 1, 1)))
    bg = hex_color(val)
    fg = "#000000" if val > 127 else "#FFFFFF"
    output.append(f"  <tr><td style='background:{bg};color:{fg}'>{i + 1}</td></tr>")
output += ["</table>", "</body></html>"]
print("Content-Type: text/html; charset=utf-8\n")
print("\n".join(output))
