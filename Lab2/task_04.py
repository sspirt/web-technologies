import sys

if len(sys.argv) != 2:
    print("Использование: python task_04.py <число>")
    sys.exit(1)

raw = sys.argv[1].lstrip("-")
if not raw.isdigit():
    print("Передайте целое число")
    sys.exit(1)

digit_sum = sum(int(digit) for digit in raw)
print(f"Число: {sys.argv[1]}")
print(f"Сумма: {digit_sum}")