from pathlib import Path
import argparse
import subprocess
import sys


def get_duration_seconds(file_path: Path) -> float:
    """
    Get media duration using ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")

    return float(result.stdout.strip())


def trim_mp3(input_path: Path, output_path: Path, remove_ms: int = 1500, exact: bool = False):
    """
    Remove the final remove_ms milliseconds from an MP3 file.
    """

    duration = get_duration_seconds(input_path)
    trim_seconds = remove_ms / 1000
    new_duration = duration - trim_seconds

    if new_duration <= 0:
        print(f"Skipping too-short file: {input_path.name}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if exact:
        # More accurate, but re-encodes the MP3.
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-t", str(new_duration),
            "-codec:a", "libmp3lame",
            "-q:a", "2",
            str(output_path)
        ]
    else:
        # Fast, no quality loss, but cut may be frame-aligned rather than sample-exact.
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-t", str(new_duration),
            "-c", "copy",
            str(output_path)
        ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {input_path.name}:\n{result.stderr}")

    print(f"Trimmed: {input_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Remove the last 1500 ms from every MP3 file in a directory."
    )

    parser.add_argument(
        "directory",
        help="Directory containing MP3 files"
    )

    parser.add_argument(
        "--remove-ms",
        type=int,
        default=1500,
        help="Milliseconds to remove from the end of each file. Default: 1500"
    )

    parser.add_argument(
        "--output-dir",
        default="trimmed",
        help="Output subdirectory name. Default: trimmed"
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process MP3 files in subfolders too"
    )

    parser.add_argument(
        "--exact",
        action="store_true",
        help="Use more accurate trimming by re-encoding the audio"
    )

    parser.add_argument(
        "--overwrite-originals",
        action="store_true",
        help="Replace the original MP3 files. Use with caution."
    )

    args = parser.parse_args()

    input_dir = Path(args.directory)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Invalid directory: {input_dir}")
        sys.exit(1)

    mp3_files = (
        list(input_dir.rglob("*.mp3"))
        if args.recursive
        else list(input_dir.glob("*.mp3"))
    )

    if not mp3_files:
        print("No MP3 files found.")
        return

    for mp3_file in mp3_files:
        try:
            if args.overwrite_originals:
                temp_output = mp3_file.with_suffix(".trimmed.tmp.mp3")
                trim_mp3(mp3_file, temp_output, args.remove_ms, args.exact)

                temp_output.replace(mp3_file)
                print(f"Overwrote original: {mp3_file.name}")

            else:
                relative_path = mp3_file.relative_to(input_dir)
                output_path = input_dir / args.output_dir / relative_path
                trim_mp3(mp3_file, output_path, args.remove_ms, args.exact)

        except Exception as e:
            print(f"Error processing {mp3_file.name}: {e}")


if __name__ == "__main__":
    main()