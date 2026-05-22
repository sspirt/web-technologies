import sys

def generate_table(rows):
    lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='UTF-8'><title>Table</title></head>",
        "<body>",
        "<table border='1' cellpadding='6' cellspacing='0'>",
        "  <tr><th>Number</th></tr>",
    ]
    for i in range(1, rows + 1):
        lines.append(f"  <tr><td>{i}</td></tr>")
    lines += ["</table>", "</body></html>"]
    return "\n".join(lines)

if len(sys.argv) != 2:
    print("Использование: python task_02.py <количество_строк>")
    sys.exit(1)

try:
    rows = int(sys.argv[1])
    if rows <= 0:
        raise ValueError
except ValueError:
    print("Укажите положительное целое число")
    sys.exit(1)
print("Content-Type: text/html; charset=utf-8\n")
print(generate_table(rows))