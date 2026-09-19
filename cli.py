#!/usr/bin/env python3
"""Standalone macOS lookup and CSV export.

Examples:
    python3 cli.py --list-dicts
    python3 cli.py --dict 现代汉语规范词典 学习
    python3 cli.py --dict Oxford --parts definitions apple
    python3 cli.py --file words.txt --output definitions.csv

The preset is chosen by dictionary name unless --profile is supplied.
"""

import argparse
import csv
import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)

def main():
    parser = argparse.ArgumentParser(
        description="Look up words in macOS dictionaries"
    )
    parser.add_argument("words", nargs="*", help="Words to look up")
    parser.add_argument("--file", "-f", help="Read words from file (one per line)")
    parser.add_argument("--stdin", action="store_true", help="Read words from stdin")
    parser.add_argument("--output", "-o", help="Write CSV to file (default: stdout)")
    parser.add_argument(
        "--parts", "-p", default="pos,definitions,examples",
        help="Comma-separated parts to include: pinyin,pronunciation,pos,definitions,examples,usage_notes"
    )
    parser.add_argument("--raw", action="store_true", help="Print raw text (macOS only)")
    parser.add_argument("--list-dicts", action="store_true", help="List available dictionaries")
    parser.add_argument("--dict", "-d", help="Select specific macOS dictionary by partial name")
    parser.add_argument(
        "--profile", default=None,
        help="Optional parsing preset ID; otherwise chosen by dictionary name."
    )

    args = parser.parse_args()
    parts = set(args.parts.split(","))

    from profiles import BUILTIN_PROFILES
    all_profiles = BUILTIN_PROFILES
    from profiles import default_profile_id_for_dict
    profile_id = args.profile or default_profile_id_for_dict(args.dict)
    profile = all_profiles.get(profile_id)
    if profile is None:
        print(f"Unknown profile '{args.profile}'. Available: "
              f"{', '.join(sorted(all_profiles))}", file=sys.stderr)
        sys.exit(1)

    # --- List dicts mode ---
    if args.list_dicts:
        _list_dicts()
        return

    # --- Gather words ---
    words = list(args.words) if args.words else []
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w and not w.startswith("#"):
                    words.append(w)
    if args.stdin:
        for line in sys.stdin:
            w = line.strip()
            if w:
                words.append(w)

    if not words:
        parser.print_help()
        sys.exit(1)

    # --- Raw mode (macOS only) ---
    if args.raw:
        from dict_lookup import MacOSDictionary
        d = MacOSDictionary()
        if args.dict:
            d.select_dictionary(args.dict)
        for word in words:
            result = d.lookup(word)
            print(f"=== {word} ===")
            print(result or "[Not found]")
            print()
        return

    # --- Formatted lookup ---
    from dict_lookup import MacOSDictionary
    macos_dict = MacOSDictionary()
    macos_dict.select_dictionary(args.dict or None)
    from formatter import format_macos_entry
    from convert import to_simplified, to_traditional

    out_file = (
        open(args.output, "w", encoding="utf-8-sig", newline="")
        if args.output else sys.stdout
    )

    writer = csv.writer(out_file)
    header = ["Word"]
    if macos_dict:
        header.append("macOS Definition")
    writer.writerow(header)

    for word in words:
        row = [word]

        if macos_dict:
            # Convert the typed word to the script this profile's
            # dictionary expects, falling back to the word as typed.
            # (Same logic as lookup.lookup_macos — keep in sync.)
            conversion = profile.get("input_conversion", "none")
            if conversion == "simplified":
                query = to_simplified(word)
            elif conversion == "traditional":
                query = to_traditional(word)
            else:
                query = word
            raw = macos_dict.lookup(query)
            if not raw and query != word:
                query = word
                raw = macos_dict.lookup(word)
            if raw:
                row.append(format_macos_entry(query, raw, parts, profile))
            else:
                row.append("")

        writer.writerow(row)

    if args.output:
        out_file.close()
        print(f"Wrote {len(words)} entries to {args.output}", file=sys.stderr)


def _list_dicts():
    try:
        from dict_lookup import MacOSDictionary
        d = MacOSDictionary()
        dicts = d.list_dictionaries()
        if dicts:
            print("macOS Dictionaries:")
            kw = ["汉语", "漢語", "Chinese", "國語", "中文", "辭典", "词典"]
            for name, short in sorted(dicts):
                mark = " ✓" if any(k in name for k in kw) else ""
                print(f"  {name} ({short}){mark}")
        else:
            print("No downloaded dictionaries found, or macOS dictionary discovery is unavailable.")
    except Exception as e:
        print(f"macOS: unavailable ({e})")



if __name__ == "__main__":
    main()
