import sys

if len(sys.argv) < 2:
    print("Использование: python task_05.py <слово1> <слово2> ...")
    sys.exit(1)

words = sys.argv[1:]
max_len = max(len(word) for word in words)
longest_words = [word for word in words if len(word) == max_len]
print(f"Слова: {words}")
print(f"Максимальная длина: {max_len}")
if len(longest_words) == 1:
    print(f"Самое длинное слово: '{longest_words[0]}'")
else:
    joined = "', '".join(longest_words)
    print(f"Самые длинные слова: '{joined}'")