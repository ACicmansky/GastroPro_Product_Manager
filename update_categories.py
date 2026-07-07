import json

prefix = "Tovary a kategórie > "

try:
    with open("categories.json", "r", encoding="utf-8") as f:
        data1 = json.load(f)
    for item in data1:
        if "newCategory" in item and not item["newCategory"].startswith(prefix):
            item["newCategory"] = prefix + item["newCategory"]
    with open("categories.json", "w", encoding="utf-8") as f:
        json.dump(data1, f, indent=2, ensure_ascii=False)
    print("categories.json updated")
except Exception as e:
    print(f"Error updating categories.json: {e}")

try:
    with open("categories_with_parameters.json", "r", encoding="utf-8") as f:
        data2 = json.load(f)
    for item in data2:
        if "kategoria" in item and not item["kategoria"].startswith(prefix):
            item["kategoria"] = prefix + item["kategoria"]
    with open("categories_with_parameters.json", "w", encoding="utf-8") as f:
        json.dump(data2, f, indent=4, ensure_ascii=False)
    print("categories_with_parameters.json updated")
except Exception as e:
    print(f"Error updating categories_with_parameters.json: {e}")
