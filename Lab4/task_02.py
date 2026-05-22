from task_01 import FormBuilder
from urllib.parse import parse_qs

class SafeFormBuilder(FormBuilder):
    def __init__(self, method: str, action: str, submit_label: str, params: dict[str, object] | None = None) -> None:
        super().__init__(method, action, submit_label)
        self.params = self._normalize_params(params or {})

    @staticmethod
    def _normalize_params(params: dict[str, object]) -> dict[str, str]:
        if not isinstance(params, dict):
            raise TypeError("Params must be a dictionary")
        normalized: dict[str, str] = {}
        for key, value in params.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Every parameter name must be a non-empty string")
            if isinstance(value, (list, tuple)):
                normalized[key] = str(value[0]) if value else ""
            else:
                normalized[key] = str(value)
        return normalized

    @classmethod
    def from_query_string(cls, method: str, action: str, submit_label: str, query_string: str) -> SafeFormBuilder:
        if not isinstance(query_string, str):
            raise TypeError("query_string must be a string")
        parsed = {key: values[0] if values else "" for key, values in parse_qs(query_string, keep_blank_values=True).items()}
        return cls(method, action, submit_label, parsed)

    def add_text_field(self, name: str, default_value: object = "") -> None:
        restored_value = self.params.get(name, default_value)
        super().add_text_field(name, restored_value)

    def add_radio_group(self, name: str, values: list[object] | tuple[object, ...]) -> None:
        name = self._validate_non_empty(name, "name")
        if not isinstance(values, (list, tuple)):
            raise TypeError("Values must be a list or tuple")
        if not values:
            raise ValueError("Values cannot be empty")
        selected_value = self.params.get(name)
        for value in values:
            checked = ' checked="checked"' if selected_value is not None and str(value) == selected_value else ""
            html = f'  <input type="radio" name="{self._escape(name)}" value="{self._escape(value)}"{checked}/>'
            self._elements.append(html)

if __name__ == "__main__":
    form = SafeFormBuilder.from_query_string("GET", "/destination", "Send!", "someName=ABC&someRadioName=B")
    form.add_text_field("someName", "Default value")
    form.add_radio_group("someRadioName", ["A", "B"])
    print(form.get_form())