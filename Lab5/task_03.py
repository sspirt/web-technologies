from typing import Any

class Flattener:
    ATOMIC = (str, bytes, bytearray)

    def __init__(self, data: Any):
        self.data = data

    def flatten(self) -> list:
        return list(self._iter(self.data))

    def flatten_unique(self) -> list:
        seen = []
        result = []
        for item in self._iter(self.data):
            try:
                if item not in seen:
                    seen.append(item)
                    result.append(item)
            except TypeError:
                result.append(item)
        return result

    def _iter(self, obj: Any):
        if isinstance(obj, self.ATOMIC):
            yield obj
        else:
            try:
                it = iter(obj)
            except TypeError:
                yield obj
                return
            for element in it:
                yield from self._iter(element)


def demo():
    examples = [
        ([1, [2, [3, 4]], 5, [2, 3]], "Вложенные числа"),
        (([1, "a", (2, "b")], [[1, "a"], 3]), "Смешанные типы"),
        ({"a": 1, "b": [2, 3]}, "Словарь"),
        ([1, None, [None, 2, None], 1], "None-значения"),
        ([[[[[[42]]]]]], "Глубокая вложенность"),
    ]
    for data, label in examples:
        f = Flattener(data)
        flat = f.flatten()
        unique = f.flatten_unique()
        print(f"\n[{label}]")
        print(f"Исходное: {data}")
        print(f"Плоское: {flat}")
        print(f"Без дубликатов: {unique}")

def main():
    demo()
    print("\nВведите Python-выражение (список, кортеж и т.д.)")
    while True:
        raw = input("Выражение (или 'выход'): ").strip()
        if raw.lower() in ("выход", "exit", "q"):
            break
        if not raw:
            continue
        try:
            data = eval(raw, {"__builtins__": {}})
        except Exception as e:
            print(f"Ошибка разбора выражения: {e}")
            continue
        try:
            f = Flattener(data)
            print(f"Плоское: {f.flatten()}")
            print(f"Без дубликатов: {f.flatten_unique()}")
        except Exception as e:
            print(f"Ошибка обработки: {e}")
        print()

if __name__ == "__main__":
    main()
