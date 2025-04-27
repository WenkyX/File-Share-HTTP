import base64

def svg_to_data_uri(svg_string):
    return "data:image/svg+xml;base64," + base64.b64encode(svg_string.encode("utf-8")).decode("utf-8")

with open("python/share_script/icons_510303.svg", "r", encoding="utf-8") as f:
    FOLDER_SVG = f.read()

with open("python/share_script/unknown.svg", "r", encoding="utf-8") as f:
    FILE_SVG = f.read()


FOLDER_ICON = svg_to_data_uri(FOLDER_SVG)
FILE_ICON = svg_to_data_uri(FILE_SVG)

print(FOLDER_ICON)
# print(FILE_ICON)