#!/usr/bin/env python3
import argparse
import glob
import html
import json
import os
import re
import urllib.request
from typing import Dict, List, Tuple

BASE_URL = "https://www.bibliaortodoxa.ro"
HOMEPAGE_URL = f"{BASE_URL}/"
DEFAULT_BOOK_DIR = "BibleSpoken/data/Noul-Testament/Matei"
DEFAULT_TESTAMENT = "NT"
RECIPE_FILES = [
    "BibleSpoken/data/recipe.txt",
    "BibleSpoken/data/recipe-not-cached-v2.txt",
    "BibleSpoken/data/bundled-recipe.txt",
]


def fetch_url(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8", errors="ignore")


def strip_tags(raw: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", raw)
    unescaped = html.unescape(no_tags)
    cleaned = re.sub(r"\s+", " ", unescaped).strip()
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned


def parse_testament_book_ids(homepage_html: str, testament_code: str) -> List[int]:
    options = re.findall(r'<option value="(-?\d+)">(.*?)</option>', homepage_html, re.IGNORECASE | re.DOTALL)
    testament_ids: List[int] = []
    in_nt = False
    in_vt = False
    for raw_value, raw_label in options:
        value = int(raw_value)
        label = strip_tags(raw_label).upper()

        if value < 0:
            in_nt = value == -2 or "NOUL TESTAMENT" in label
            in_vt = value == -1 or "VECHIUL TESTAMENT" in label
            continue

        if testament_code == "NT" and in_nt:
            testament_ids.append(value)
        if testament_code == "VT" and in_vt:
            testament_ids.append(value)

    if not testament_ids:
        raise RuntimeError(f"Could not parse {testament_code} book IDs from homepage")

    return testament_ids


def parse_new_testament_book_ids(homepage_html: str) -> List[int]:
    return parse_testament_book_ids(homepage_html, "NT")


def parse_old_testament_book_ids(homepage_html: str) -> List[int]:
    return parse_testament_book_ids(homepage_html, "VT")


def parse_chapter_from_filename(filename: str) -> int:
    chapter_match = re.search(r"-(\d+)---", filename)
    if chapter_match:
        return int(chapter_match.group(1))

    single_chapter_match = re.search(r"(NT|VT)\d{2}-.+---Biblia-Ortodoxa-2020\.mp3$", filename)
    if single_chapter_match:
        return 1

    raise ValueError(f"Could not parse chapter from filename: {filename}")


def parse_book_index_from_filename(filename: str) -> int:
    match = re.search(r"^(NT|VT)(\d{2})-", filename)
    if not match:
        raise ValueError(f"Could not parse testament book index from filename: {filename}")
    return int(match.group(2))


def extract_verses(chapter_html: str) -> List[str]:
    rows = re.findall(
        r"<tr\s+id=verset\d+>.*?<td[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>\s*</tr>",
        chapter_html,
        re.IGNORECASE | re.DOTALL,
    )

    verses: List[str] = []
    for row in rows:
        verse = strip_tags(row)
        if verse:
            verses.append(verse)
    return verses


def chapter_url(book_id: int, chapter: int) -> str:
    return f"{BASE_URL}/carte.php?id={book_id}&cap={chapter}"


def md_path_for_mp3_path(mp3_path: str) -> str:
    if not mp3_path.endswith(".mp3"):
        return mp3_path
    return f"{mp3_path[:-4]}.md"


def write_markdown(md_file_path: str, verses: List[str]) -> None:
    lines = [f"{idx}. {verse}" for idx, verse in enumerate(verses, start=1)]
    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_testament_from_filename(filename: str) -> str:
    match = re.search(r"^(NT|VT)\d{2}-", filename)
    if not match:
        raise ValueError(f"Could not parse testament code from filename: {filename}")
    return match.group(1)


def generate_book_markdown(
    book_dir: str,
    expected_book_index: int,
    testament_code: str,
    dry_run: bool = False,
) -> Tuple[Dict[int, bool], List[Dict[str, str]]]:
    homepage_html = fetch_url(HOMEPAGE_URL)
    testament_book_ids = parse_testament_book_ids(homepage_html, testament_code)
    if expected_book_index < 1 or expected_book_index > len(testament_book_ids):
        raise RuntimeError(f"Expected {testament_code} book index {expected_book_index} out of range")
    book_id = testament_book_ids[expected_book_index - 1]

    mp3_files = sorted(glob.glob(os.path.join(book_dir, "*.mp3")))
    chapter_success: Dict[int, bool] = {}
    failures: List[Dict[str, str]] = []

    for mp3_file in mp3_files:
        filename = os.path.basename(mp3_file)

        try:
            parsed_testament_code = parse_testament_from_filename(filename)
            if parsed_testament_code != testament_code:
                raise RuntimeError(
                    f"Testament code mismatch: expected {testament_code}, found {parsed_testament_code}"
                )
            parsed_book_index = parse_book_index_from_filename(filename)
            if parsed_book_index != expected_book_index:
                raise RuntimeError(
                    f"Book index mismatch: expected {testament_code}{expected_book_index:02d}, "
                    f"found {parsed_testament_code}{parsed_book_index:02d}"
                )
            chapter = parse_chapter_from_filename(filename)
            url = chapter_url(book_id, chapter)
            html_payload = fetch_url(url)
            verses = extract_verses(html_payload)

            if not verses:
                raise RuntimeError("No verses extracted")

            chapter_success[chapter] = True

            if not dry_run:
                write_markdown(md_path_for_mp3_path(mp3_file), verses)

        except Exception as exc:
            chapter = None
            try:
                chapter = parse_chapter_from_filename(filename)
            except Exception:
                pass
            if chapter is not None:
                chapter_success[chapter] = False
            failures.append(
                {
                    "file": mp3_file,
                    "chapter": str(chapter) if chapter is not None else "unknown",
                    "error": str(exc),
                }
            )

    return chapter_success, failures


def update_recipe_file(
    recipe_path: str,
    chapter_success: Dict[int, bool],
    book_name: str,
    testament_folder: str,
    dry_run: bool = False,
) -> Dict[str, int]:
    with open(recipe_path, "r", encoding="utf-8") as f:
        recipe = json.load(f)

    touched = 0
    with_text = 0
    without_text = 0

    for step in recipe.get("steps", []):
        for path_mapping in step.get("paths", []):
            reference_path = path_mapping.get("referencePath", "")

            if f"/{testament_folder}/{book_name}/" not in reference_path or not reference_path.endswith(".mp3"):
                continue

            chapter = parse_chapter_from_filename(os.path.basename(reference_path))
            has_text = bool(chapter_success.get(chapter, False))
            path_mapping["hasText"] = has_text

            touched += 1
            if has_text:
                with_text += 1
            else:
                without_text += 1

    if not dry_run:
        with open(recipe_path, "w", encoding="utf-8") as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return {
        "entriesTouched": touched,
        "entriesWithText": with_text,
        "entriesWithoutText": without_text,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Bible book markdown and recipe metadata")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files")
    parser.add_argument(
        "--testament",
        choices=["NT", "VT"],
        default=DEFAULT_TESTAMENT,
        help="Book testament code from file names",
    )
    parser.add_argument(
        "--book-dir",
        default=DEFAULT_BOOK_DIR,
        help="Book folder with mp3 chapters (example: BibleSpoken/data/Noul-Testament/Matei or BibleSpoken/data/Vechiul-Testament/Facerea)",
    )
    parser.add_argument(
        "--book-index",
        type=int,
        default=1,
        help="Book index encoded in file names (example: 1 for NT01/VT01, 2 for NT02/VT02)",
    )
    parser.add_argument(
        "--report-path",
        default="BibleSpoken/data/matei-text-report.json",
        help="Path to write summary report JSON",
    )
    args = parser.parse_args()

    book_name = os.path.basename(args.book_dir.rstrip("/"))
    testament_folder = "Noul-Testament" if args.testament == "NT" else "Vechiul-Testament"

    chapter_success, failures = generate_book_markdown(
        book_dir=args.book_dir,
        expected_book_index=args.book_index,
        testament_code=args.testament,
        dry_run=args.dry_run,
    )

    recipe_stats = {}
    for recipe_path in RECIPE_FILES:
        recipe_stats[recipe_path] = update_recipe_file(
            recipe_path,
            chapter_success,
            book_name=book_name,
            testament_folder=testament_folder,
            dry_run=args.dry_run,
        )

    report = {
        "testament": args.testament,
        "book": book_name,
        "chaptersProcessed": len(chapter_success),
        "chaptersWithText": sum(1 for ok in chapter_success.values() if ok),
        "chaptersWithoutText": sum(1 for ok in chapter_success.values() if not ok),
        "failures": failures,
        "recipes": recipe_stats,
    }

    if not args.dry_run:
        os.makedirs(os.path.dirname(args.report_path), exist_ok=True)
        with open(args.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
