def deduplicate(arr, seen=None):
    if seen is None:
        seen = set()
    result = []
    for element in arr:
        if isinstance(element, list):
            result.append(deduplicate(element, seen))
        else:
            if element not in seen:
                seen.add(element)
                result.append(element)
    return result

array = [
    [100, 1, 2, 100, 3],
    [2, 4, 100, [5, 5, 6, 1]],
    [7, 8, [9, 7, [100, 3, 10]]]
]
print(f"Исходный: {array}")
print(f"Результат: {deduplicate(array)}")
