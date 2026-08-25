import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def _command_error(command: str, error: subprocess.CalledProcessError) -> str:
    detail = (error.stderr or error.stdout or "").strip()
    if detail:
        return f"{command} failed with exit code {error.returncode}: {detail}"
    return f"{command} failed with exit code {error.returncode}"


def convert_apk(apk_path: Path, zip_path: Path) -> Path:
    """Extract one Alpine APK and atomically write its ZIP."""
    apk_path = apk_path.resolve()
    zip_path = zip_path.resolve()
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=f".apk2zpk-{apk_path.stem}-", dir=zip_path.parent
    ) as temporary_directory:
        work_directory = Path(temporary_directory)
        extracted_directory = work_directory / "extracted"
        extracted_directory.mkdir()
        staged_zip = work_directory / zip_path.name

        try:
            subprocess.run(
                [
                    "apk",
                    "extract",
                    "--no-chown",
                    "--destination",
                    str(extracted_directory),
                    str(apk_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as error:
            raise RuntimeError(_command_error("apk extract", error)) from error

        if any(extracted_directory.iterdir()):
            try:
                subprocess.run(
                    ["zip", "-q", "-y", "-r", str(staged_zip), "."],
                    cwd=extracted_directory,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as error:
                raise RuntimeError(_command_error("zip", error)) from error
        else:
            # Info-ZIP treats an empty input as an error, but empty Alpine
            # metapackages still need a valid corresponding archive.
            with zipfile.ZipFile(staged_zip, "w"):
                pass

        os.replace(staged_zip, zip_path)

    return zip_path


def _positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an Alpine APK repository into a separate ZIP repository."
    )
    parser.add_argument("source", type=Path, help="APK repository to read")
    parser.add_argument("destination", type=Path, help="ZIP repository to write")
    parser.add_argument(
        "-j",
        "--jobs",
        type=_positive_integer,
        default=os.cpu_count() or 1,
        help="parallel conversion processes (default: number of CPUs)",
    )
    return parser


def run(source: Path, destination: Path, jobs: int) -> int:
    source = source.resolve()
    destination = destination.resolve()

    if not source.is_dir():
        print(f"apk2zpk: not a directory: {source}", file=sys.stderr)
        return 2

    if destination == source or source in destination.parents:
        print(
            "apk2zpk: destination must be separate from and outside the source repository",
            file=sys.stderr,
        )
        return 2

    destination.mkdir(parents=True, exist_ok=True)

    apk_paths = sorted(path for path in source.rglob("*.apk") if path.is_file())
    if not apk_paths:
        print(f"apk2zpk: no .apk files found below {source}")
        return 0

    failures: list[tuple[Path, str]] = []
    completed = 0

    print(f"apk2zpk: converting {len(apk_paths)} packages with {jobs} workers")
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(
                convert_apk,
                path,
                destination / path.relative_to(source).with_suffix(".zip"),
            ): path
            for path in apk_paths
        }
        for future in as_completed(futures):
            apk_path = futures[future]
            try:
                zip_path = future.result()
            except Exception as error:
                failures.append((apk_path, str(error)))
                print(f"apk2zpk: failed: {apk_path}: {error}", file=sys.stderr)
            else:
                completed += 1
                print(f"apk2zpk: {apk_path} -> {zip_path}")

    print(f"apk2zpk: converted {completed}/{len(apk_paths)} packages")
    if failures:
        print(f"apk2zpk: {len(failures)} package(s) failed", file=sys.stderr)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    arguments = _parser().parse_args(argv)
    raise SystemExit(run(arguments.source, arguments.destination, arguments.jobs))
