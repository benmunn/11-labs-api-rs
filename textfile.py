import argparse
import csv
import sys
from pathlib import Path
from pathvalidate import sanitize_filename

def csv_to_text(csv_file: Path, output_path: Path, has_header: bool):
    output_path.mkdir(parents=True, exist_ok=True)
    with open(csv_file,  encoding="utf-8", newline="") as f:
        reader = csv.reader(f)

        if has_header:
            next(reader, None)
        
        for line_number, row in enumerate(reader, start=2 if has_header else 1):
            if len(row) < 2:
                continue
            filename = row[0].strip()
            text_entry = row[1].strip()
            file_clean = sanitize_filename(filename)
            if file_clean[-4:] != ".txt":
                file_clean += ".txt"
            file_out = output_path / file_clean
            
            with open(file_out, "w", encoding="utf-8") as f:
                f.write(text_entry)

def main():
    parser = argparse.ArgumentParser(
        description="Create text files based on a csv with two columns"
    )

    parser.add_argument(
        "directory",
        help="Directory containing csv file"
    )

    parser.add_argument(
        "--output-dir",
        default="text_in",
        help="Output subdirectory name. Default: text_in"
    )

    parser.add_argument(
        "--head",
        action="store_true",
        help="Skip the first row as a header."
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process files in subfolders too"
    )

    args = parser.parse_args()

    input_dir = Path(args.directory)
    has_header = args.head
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Invalid directory: {input_dir}")
        sys.exit(1)

    csv_files = (
        list(input_dir.rglob("*.csv"))
        if args.recursive
        else list(input_dir.glob("*.csv"))
    )

    if not csv_files:
        print("No CSV files found.")
        return

    for csv_file in csv_files:
        try:
            output_path = input_dir / args.output_dir
            csv_to_text(csv_file, output_path, has_header)

        except Exception as e:
            print(f"Error processing {csv_file.name}: {e}")


if __name__ == "__main__":
    main()
