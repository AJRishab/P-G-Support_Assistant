"""
One-off converter: Kaggle "Cosmetics datasets" (kingabzpro) CSV -> products.json entries.

Usage:
    python convert_cosmetics_csv.py path/to/cosmetics.csv --limit 50

If your CSV's headers differ from what's expected, this script prints the real headers
it found so you can fix COLUMN_ALIASES below and re-run - no guessing silently.
"""
import csv
import json
import re
import argparse
import sys
from pathlib import Path

SKIN_TYPE_COLUMNS = ["Combination", "Dry", "Normal", "Oily", "Sensitive"]

COLUMN_ALIASES = {
    "label": ["label", "Label", "\ufeffLabel"],
    "brand": ["Brand"],
    "name": ["Name", "Product", "Product Name"],
    "price": ["Price"],
    "rank": ["Rank", "Rating"],
    "ingredients": ["Ingredients"],
}

INGREDIENT_DELIMITER = ","  # change to ";" if your CSV separates ingredients that way


def find_column(headers_lower_map, aliases):
    for alias in aliases:
        if alias.lower() in headers_lower_map:
            return headers_lower_map[alias.lower()]
    return None


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--limit", type=int, default=50, help="Max rows to convert, top by Rank")
    parser.add_argument("--products-json", default="server/src/config/products.json")
    args = parser.parse_args()

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers_lower_map = {h.lower(): h for h in reader.fieldnames}

        col = {key: find_column(headers_lower_map, aliases) for key, aliases in COLUMN_ALIASES.items()}
        missing = [k for k in ("label", "brand", "name", "ingredients") if col[k] is None]
        if missing:
            print(f"ERROR: couldn't find columns for {missing}.")
            print(f"Actual headers in your CSV: {reader.fieldnames}")
            print("Update COLUMN_ALIASES at the top of this script to match, then re-run.")
            sys.exit(1)

        skin_col = {st: find_column(headers_lower_map, [st]) for st in SKIN_TYPE_COLUMNS}
        missing_skin = [st for st, v in skin_col.items() if v is None]
        if missing_skin:
            print(f"WARNING: skin-type columns not found for {missing_skin} - those flags will be skipped.")

        rows = list(reader)

    def row_rank(r):
        if col["rank"] and r.get(col["rank"]):
            try:
                return float(r[col["rank"]])
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    rows.sort(key=row_rank, reverse=True)
    rows = rows[: args.limit]

    converted = []
    for r in rows:
        name = (r.get(col["name"]) or "").strip()
        brand = (r.get(col["brand"]) or "").strip()
        label = (r.get(col["label"]) or "").strip()
        ingredients_raw = (r.get(col["ingredients"]) or "").strip()
        ingredients = [i.strip() for i in ingredients_raw.split(INGREDIENT_DELIMITER) if i.strip()]

        if not name or not ingredients:
            continue  # skip incomplete rows rather than guessing at missing data

        skin_types = [
            st for st, colname in skin_col.items()
            if colname and str(r.get(colname, "0")).strip() in ("1", "1.0", "True", "true")
        ]

        entry = {
            "id": slugify(f"{brand}-{name}"),
            "name": name,
            "brand": brand,
            "category": "Skincare",
            "ingredients": ingredients,
            "purpose": f"{label} for {', '.join(skin_types)} skin" if skin_types else (label or "Skincare product"),
            "safety_warnings": "",  # not present in source data - left blank rather than invented
            "where_to_buy": "",     # not present in source data
            "skin_types": skin_types,
        }
        if col["rank"] and r.get(col["rank"]):
            entry["rank"] = row_rank(r)
        if col["price"] and r.get(col["price"]):
            entry["price"] = r[col["price"]]

        converted.append(entry)

    products_path = Path(args.products_json)
    existing = {"products": []}
    if products_path.exists():
        with open(products_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Replaces any prior Skincare entries (including the old single Olay one) - keeps
    # Tide/Pampers/Gillette untouched.
    existing["products"] = [p for p in existing["products"] if p.get("category") != "Skincare"] + converted

    with open(products_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    print(f"Wrote {len(converted)} skincare products into {products_path} ({len(existing['products']) - len(converted)} other entries kept as-is).")


if __name__ == "__main__":
    main()