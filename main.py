
from titledb.executable import ExecutableAnalyzer
from titledb.scanner import FileRecord, FileType, FolderScanner

import os
import sys
import urllib3


class Program:
    _executables: ExecutableAnalyzer
    
    def __init__(self):
        if not os.path.exists("data"):
            os.mkdir("data")
        
        self._executables = ExecutableAnalyzer("data/executables.json")

    def main(self, path: str, reanalyze: bool) -> None:
        if not os.path.isdir(path):
            print(f"{path} is not a folder or does not exist")
            return

        files = self._scan_folders(path)
        for i, file in enumerate(files):
            print(f"Processing file {i + 1} / {len(files)}: {file.path}")
            self._analyze_file(file, reanalyze)
        
        self._executables.save()

    def _scan_folders(self, path: str) -> list[FileRecord]:
        scanner = FolderScanner()
        return scanner.scan(path)

    def _collect_title_ids(self, files: list[FileRecord]) -> list[int]:
        title_ids = []
        for file in files:
            if file.title_id not in title_ids:
                title_ids.append(file.title_id)
        return title_ids

    def _analyze_file(self, file: FileRecord, reanalyze: bool) -> None:
        if file.type in [
            FileType.Main, FileType.Sdk, FileType.Subsdk, FileType.Rtld
        ]:
            self._executables.analyze(file, reanalyze)


def print_usage(message: str) -> None:
    print(message)
    print()
    print(f"Usage: python3 {sys.argv[0]} <path> (reanalyze)")


def main() -> None:
    if len(sys.argv) not in [2, 3]:
        print_usage("Incorrect number of arguments provided.")
        return

    if len(sys.argv) == 3 and sys.argv[2] != "reanalyze":
        print_usage("Second argument must be 'reanalyze' if provided")
        return

    urllib3.disable_warnings()

    program = Program()
    program.main(sys.argv[1], len(sys.argv) == 3)


if __name__ == "__main__":
    main()
