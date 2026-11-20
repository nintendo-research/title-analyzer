
from titledb.nso import NSOFile
from titledb.scanner import FileRecord
from titledb.serializer import Serializer

from typing import Generator

import struct


class ExecutableInfo(Serializer):
    path: str

    flags: int
    module_id: bytes
    
    nso_size: int
    text_size: int
    rodata_size: int
    data_size: int
    bss_size: int

    dynstr_size: int
    dynsym_size: int

    sead: bool
    agl: bool
    aal: bool
    xlink2: bool
    lp2: bool
    enl: bool
    eui: bool
    gsys: bool
    al: bool
    eagle: bool
    lms: bool
    nexrf: bool
    nexms: bool
    modsys: bool | None
    phive: bool | None

    sdks: list[str]

    def pending(self) -> bool:
        """
        A few metrics were added later. This method returns whether the game
        needs to be reanalyzed to cover those metrics.
        """
        return self.modsys is None or self.phive is None


class ExecutableCache(Serializer):
    # title id -> title offset -> title version -> filename
    titles: dict[int, dict[int, dict[int, dict[str, ExecutableInfo]]]]

    def add(
        self, title_id: int, title_offset: int, title_version: int,
        filename: str, info: ExecutableInfo
    ) -> None:
        title = self.titles.setdefault(title_id, {})
        offset = title.setdefault(title_offset, {})
        version = offset.setdefault(title_version, {})
        version[filename] = info

    def find(
        self, title_id: int, title_offset: int, title_version: int,
        filename: str
    ) -> ExecutableInfo | None:
        title = self.titles.get(title_id)
        if title is None:
            return None

        version = title.get(title_offset)
        if version is None:
            return None

        offset = version.get(title_version)
        if offset is None:
            return None

        return offset.get(filename)

    def contains(
        self, title_id: int, title_offset: int, title_version: int,
        filename: str
    ) -> bool:
        result = self.find(title_id, title_offset, title_version, filename)
        return result is not None

    def walk(self) -> Generator[tuple[int, int, int, str, ExecutableInfo]]:
        for title_id, title_info in self.titles.items():
            for title_offset, offset_info in title_info.items():
                for title_version, version_info in offset_info.items():
                    for filename, executable_info in version_info.items():
                        yield (
                            title_id, title_offset, title_version, filename,
                            executable_info
                        )

    def update(self, path: str) -> None:
        cache = ExecutableCache()
        cache.load(path)

        for title_id, title_info in cache.titles.items():
            for title_offset, offset_info in title_info.items():
                for title_version, version_info in offset_info.items():
                    for filename, info in version_info.items():
                        if not self.contains(
                            title_id, title_offset, title_version, filename
                        ):
                            self.add(
                                title_id, title_offset, title_version, filename,
                                info
                            )


class ExecutableAnalyzer:
    _cache: ExecutableCache
    _filename: str
    _dirty: int

    def __init__(self, filename: str):
        self._cache = ExecutableCache()
        self._cache.load_if_exists(filename)
        self._filename = filename
        self._dirty = 0

    def save(self) -> None:
        self._cache.save(self._filename)
        self._dirty = 0

    def update(self, filename: str) -> None:
        self._cache.update(filename)

    def analyze(self, record: FileRecord, reanalyze: bool) -> None:
        if not reanalyze:
            cache = self._cache.find(
                record.title_id, record.title_offset, record.title_version,
                record.filename
            )
            if cache:
                if not cache.pending():
                    return

        with open(record.path, "rb") as f:
            data = f.read()

        file = NSOFile()
        file.parse(data, decompress_text = False, decompress_data = False)

        rodata = file.ro_data
        if rodata[0] == 1:
            length = struct.unpack_from("<I", rodata, 16)[0]
            path = rodata[20 : 20 + length].decode()
        else:
            length = struct.unpack_from("<I", rodata, 4)[0]
            path = rodata[8 : 8 + length].decode()

        info = ExecutableInfo()
        info.path = path

        info.flags = file.flags
        info.module_id = file.module_id

        info.nso_size = len(data)
        info.text_size = file.text_size
        info.rodata_size = file.ro_size
        info.data_size = file.data_size

        info.bss_size = file.bss_size
        info.dynstr_size = file.dynstr_size
        info.dynsym_size = file.dynsym_size

        info.sead = b"sead::MainThread" in rodata
        info.agl = b"agl::WorkHeap" in rodata
        info.aal = b"aal::Emitter" in rodata
        info.xlink2 = b"[XLink2]" in rodata
        info.lp2 = b"Lp::Sys::ThreadHolder" in rodata
        info.enl = b"enl::TaskThread" in rodata
        info.eui = b"LetterAnimControl" in rodata
        info.gsys = b"gsys::Layer3D" in rodata

        info.al = \
            b"IsEnableFishEye" in rodata or \
            b"al::InitializeThread" in rodata or \
            b"alLightMap" in rodata
        
        info.eagle = b"libeagle" in rodata
        info.lms = b"MsgStdBn" in rodata
        info.nexrf = b"MatchmakeRefereeDDLDeclarations" in rodata
        info.nexms = b"MessagingServiceDDLDeclarations" in rodata
        info.modsys = b"ModuleSystem::moduleCalc_" in rodata
        
        info.phive = \
            b"phive::AllocDrawShape" in rodata or \
            b"Phive::Memory Stats" in rodata or \
            b"[Phive] post solve" in rodata

        embedded_data = rodata[
            file.embedded_offset : file.embedded_offset + file.embedded_size
        ]
        info.sdks = embedded_data.decode().split("\0")[:-1]

        self._cache.add(
            record.title_id, record.title_offset, record.title_version,
            record.filename, info
        )

        self._dirty += 1
        if self._dirty == 50:
            self.save()
