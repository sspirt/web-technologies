from html import escape

class FormBuilder:
    VALID_METHODS = {"GET", "POST"}

    def __init__(self, method: str, action: str, submit_label: str) -> None:
        self.method = self._validate_method(method)
        self.action = self._validate_non_empty(action, "action")
        self.submit_label = self._validate_non_empty(submit_label, "submit_label")
        self._elements: list[str] = []

    @classmethod
    def _validate_method(cls, method: str) -> str:
        if not isinstance(method, str):
            raise TypeError("Method must be a string")
        normalized = method.strip().upper()
        if normalized not in cls.VALID_METHODS:
            raise ValueError(f"Method must be one of: {', '.join(sorted(cls.VALID_METHODS))}")
        return normalized

    @staticmethod
    def _validate_non_empty(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        value = value.strip()
        if not value:
            raise ValueError(f"{field_name} cannot be empty")
        return value

    @staticmethod
    def _escape(value: object) -> str:
        return escape(str(value), quote=True)

    def add_text_field(self, name: str, default_value: object = "") -> None:
        name = self._validate_non_empty(name, "name")
        html = f'  <input type="text" name="{self._escape(name)}" value="{self._escape(default_value)}"/>'
        self._elements.append(html)

    def add_radio_group(self, name: str, values: list[object] | tuple[object, ...]) -> None:
        name = self._validate_non_empty(name, "name")
        if not isinstance(values, (list, tuple)):
            raise TypeError("Values must be a list or tuple")
        if not values:
            raise ValueError("Values cannot be empty")
        for value in values:
            html = f'  <input type="radio" name="{self._escape(name)}" value="{self._escape(value)}"/>'
            self._elements.append(html)

    def get_form(self) -> str:
        form_lines = [
            f'<form method="{self.method.lower()}" action="{self._escape(self.action)}">',
            *self._elements,
            f'  <input type="submit" value="{self._escape(self.submit_label)}"/>',
            '</form>'
        ]
        return "\n".join(form_lines)

if __name__ == "__main__":
    form = FormBuilder("POST", "/destination", "Send!")
    form.add_text_field("someName", "Default value")
    form.add_radio_group("someRadioName", ["A", "B"])
    print(form.get_form())