import sys

if len(sys.argv) != 2:
    print("Использование: python task_additional_02.py <имя_файла>", file=sys.stderr)
    sys.exit(1)
filename = sys.argv[1]
try:
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()
except FileNotFoundError:
    print(f"Ошибка: файл «{filename}» не найден", file=sys.stderr)
    sys.exit(1)
except PermissionError:
    print(f"Ошибка: нет прав для чтения «{filename}»", file=sys.stderr)
    sys.exit(1)
except UnicodeDecodeError:
    print(f"Ошибка: не удалось прочитать «{filename}» как UTF-8", file=sys.stderr)
    sys.exit(1)
sorted_lines = sorted(lines, key=lambda s: s.lower())
try:
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(sorted_lines)
except PermissionError:
    print(f"Ошибка: нет прав для записи в «{filename}»", file=sys.stderr)
    sys.exit(1)
