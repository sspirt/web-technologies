COLORS = {1: "red", 2: "blue", 3: "green", 4: "purple"}

def get_color(level):
    return COLORS.get(level, "goldenrod")

STRUCTURE = {
    "Animals": {
        "Mammals": {
            "Predators": {
                "Felines": {
                    "Lion": "Panthera leo",
                    "Tiger": "Panthera tigris",
                },
                "Canines": {
                    "Wolf": "Canis lupus",
                }
            },
            "Rodents": {
                "Mice": {
                    "House mouse": "Mus musculus",
                    "Brown rat": "Rattus rattus",
                }
            }
        },
        "Birds": {
            "Passerines": {
                "Sparrows": {
                    "House sparrow": "Passer domesticus",
                }
            }
        }
    },
    "Plants": {
        "Flowering": {
            "Rosales": {
                "Rosaceae": {
                    "Dog rose": "Rosa canina",
                    "Apple tree": "Malus domestica",
                }
            }
        }
    }
}

def render(node, level=1):
    color = get_color(level)
    html = "<ul style=\"list-style-type:disc;\">"
    if isinstance(node, dict):
        for key, value in node.items():
            html += f"<li style=\"color:{color};font-weight:bold\">Level {level}: {key}"
            html += render(value, level + 1)
            html += "</li>"
    else:
        html += f"<li style=\"color:{color}\">{node}</li>"
    html += "</ul>"
    return html

output = [
    "<!DOCTYPE html>",
    "<html><head><meta charset=\"UTF-8\">",
    "<title>Struct</title>",
    "<style>body{font-family:sans-serif;margin:20px}</style>",
    "</head><body>",
    render(STRUCTURE),
    "</body></html>",
]
print("Content-Type: text/html; charset=utf-8\n")
print("\n".join(output))