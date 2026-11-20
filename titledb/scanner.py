
from dataclasses import dataclass

import enum
import os
import string


class FileType(enum.Enum):
    Unrecognized = enum.auto()
    Main = enum.auto()
    MainNpdm = enum.auto()
    Sdk = enum.auto()
    Subsdk = enum.auto()
    Rtld = enum.auto()


@dataclass
class FileRecord:
    title_id: int
    title_version: int
    title_offset: int
    filename: str
    path: str
    type: FileType


class FolderScanner:
    _records: list[FileRecord]

    def __init__(self):
        self._records = []

    def scan(self, path: str) -> list[FileRecord]:
        self._records = []
        for folder_name in os.listdir(path):
            title_id = folder_name
            if "_" in title_id:
                title_id = title_id.split("_")[0]

            if len(title_id) != 16 or \
               any(char not in string.hexdigits for char in title_id):
                print(f"Skipping unrecognized folder: {folder_name}")
                continue
            
            title_path = os.path.join(path, folder_name)
            self._scan_title(title_path, int(title_id, 16))
        return self._records

    def _scan_title(self, path: str, title_id: int) -> None:
        for version in os.listdir(path):
            if not version.startswith("v") or not version[1:].isdecimal():
                print(f"Skipping unrecognized folder: {version}")
                return
            
            version_path = os.path.join(path, version)
            self._scan_title_version(version_path, title_id, int(version[1:]))

    def _scan_title_version(
        self, path: str, title_id: int, title_version: int
    ) -> None:
        names = os.listdir(path)
        if "main" in names:
            self._scan_files(path, title_id, title_version)
        else:
            for offset in names:
                offset_path = os.path.join(path, offset)
                self._scan_files(
                    offset_path, title_id, title_version, int(offset)
                )

    def _scan_files(
        self, path: str, title_id: int, title_version: int,
        title_offset: int = 0
    ) -> None:
        for filename in os.listdir(path):
            type = self._derive_file_type(filename)

            if type == FileType.Unrecognized:
                print(f"Skipping unrecognized file: {filename}")
                continue

            record = FileRecord(
                title_id = title_id,
                title_version = title_version,
                title_offset = title_offset,
                filename = filename,
                path = os.path.join(path, filename),
                type = type
            )
            self._records.append(record)

    def _derive_file_type(self, filename: str) -> FileType:
        if filename == "main": return FileType.Main
        elif filename == "main.npdm": return FileType.MainNpdm
        elif filename == "sdk": return FileType.Sdk
        elif filename.startswith("subsdk") and filename[6:].isdecimal():
            return FileType.Subsdk
        elif filename == "rtld": return FileType.Rtld
        return FileType.Unrecognized
