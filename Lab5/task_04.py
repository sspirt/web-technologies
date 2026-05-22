import unicodedata
from collections import Counter

class LetterCounter:
    def __init__(self, text: str, case_sensitive: bool = False):
        if not isinstance(text, str):
            raise TypeError("Текст должен быть строкой")
        self.text = text
        self.case_sensitive = case_sensitive

    @staticmethod
    def _is_letter(char: str) -> bool:
        return unicodedata.category(char).startswith("L")

    def count(self) -> Counter:
        letters = (ch if self.case_sensitive else ch.lower() for ch in self.text if self._is_letter(ch))
        return Counter(letters)

    def report(self, top: int = None) -> str:
        counts = self.count()
        if not counts:
            return "Букв в тексте не найдено"
        sorted_items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        if top:
            sorted_items = sorted_items[:top]
        total_letters = sum(counts.values())
        total_unique = len(counts)
        width = max(len(k) for k, _ in sorted_items)
        lines = [
            f"Всего букв: {total_letters}, уникальных: {total_unique}",
            f"{'Буква':<{width+2}} {'Кол-во':>8}  {'Частота':>8}"
        ]
        for letter, cnt in sorted_items:
            freq = cnt / total_letters * 100
            lines.append(f"  {letter!r:<{width}}   {cnt:>6}   {freq:>6.2f}%")
        return "\n".join(lines)

def main():
    demo = "Съешь же ещё этих мягких французских булок, да выпей чаю."
    print(f"Демо-текст: {demo!r}")
    print(LetterCounter(demo).report())
    print()
    while True:
        raw = input("Введите текст (или 'выход'): ")
        if raw.lower() in ("выход", "exit", "q"):
            break
        if not raw.strip():
            print("Текст пуст")
            continue
        try:
            counter = LetterCounter(raw)
            print(counter.report())
        except TypeError as e:
            print(f"Ошибка: {e}")
        print()

if __name__ == "__main__":
    main()