import sys

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

if len(sys.argv) < 2:
    print("Использование: python task_01.py <param1> <param2> ...")
    sys.exit(1)

for param in sys.argv[1:]:
    print(f"{param} = {determine_type(param)}")

