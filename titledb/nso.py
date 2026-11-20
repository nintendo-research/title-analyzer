
from titledb.streams import StreamIn, ParseError

from dataclasses import dataclass

import enum
import hashlib
import lz4.block
import zbic


class NSOFlags(enum.IntFlag):
    TextCompress = 1 << 0
    RoCompress = 1 << 1
    DataCompress = 1 << 2
    TextHash = 1 << 3
    RoHash = 1 << 4
    DataHash = 1 << 5
    ExecuteOnlyMemory = 1 << 6
    UseZbicCompression = 1 << 7


@dataclass
class NSOFile:
    flags: NSOFlags = NSOFlags(0)
    
    text_memory_offset: int = 0
    ro_memory_offset: int = 0
    data_memory_offset: int = 0

    text_size: int = 0
    ro_size: int = 0
    data_size: int = 0

    bss_size: int = 0
    module_id: bytes = bytes(32)
    module_name: str = ""

    embedded_offset: int = 0
    embedded_size: int = 0
    dynstr_offset: int = 0
    dynstr_size: int = 0
    dynsym_offset: int = 0
    dynsym_size: int = 0

    text_data: bytes = b""
    ro_data: bytes = b""
    data_data: bytes = b""

    def load(self, filename: str) -> None:
        with open(filename, "rb") as f:
            data = f.read()
        self.parse(data)

    def parse(
        self,
        data: bytes,
        *,
        decompress_text: bool = True,
        decompress_ro: bool = True,
        decompress_data: bool = True
    ) -> None:
        stream = StreamIn(data, "<")
        if stream.ascii(4) != "NSO0":
            raise ParseError("incorrect magic number")

        version = stream.u32()
        if version != 0:
            raise ParseError("unsupported version number")

        stream.pad(4)
        self.flags = NSOFlags(stream.u32())
        text_file_offset = stream.u32()
        self.text_memory_offset = stream.u32()
        self.text_size = stream.u32()
        module_name_offset = stream.u32()
        ro_file_offset = stream.u32()
        self.ro_memory_offset = stream.u32()
        self.ro_size = stream.u32()
        module_name_size = stream.u32()
        data_file_offset = stream.u32()
        self.data_memory_offset = stream.u32()
        self.data_size = stream.u32()
        self.bss_size = stream.u32()
        self.module_id = stream.read(32)
        text_file_size = stream.u32()
        ro_file_size = stream.u32()
        data_file_size = stream.u32()
        stream.pad(28)
        self.embedded_offset = stream.u32()
        self.embedded_size = stream.u32()
        self.dynstr_offset = stream.u32()
        self.dynstr_size = stream.u32()
        self.dynsym_offset = stream.u32()
        self.dynsym_size = stream.u32()
        text_hash = stream.read(32)
        ro_hash = stream.read(32)
        data_hash = stream.u32()

        stream.seek(module_name_offset)
        self.module_name = stream.ascii(module_name_size).rstrip("\0")

        if decompress_text:
            stream.seek(text_file_offset)
            text_data = stream.read(text_file_size)
            if self.flags & NSOFlags.TextCompress:
                text_data = self._decompress(text_data, self.text_size)
            if self.flags & NSOFlags.TextHash:
                if hashlib.sha256(text_data).digest() != text_hash:
                    raise ParseError(".text hash is invalid")
            if len(text_data) != self.text_size:
                raise ParseError(".text has unexpected size")
            self.text_data = text_data

        if decompress_ro:
            stream.seek(ro_file_offset)
            ro_data = stream.read(ro_file_size)
            if self.flags & NSOFlags.RoCompress:
                ro_data = self._decompress(ro_data, self.ro_size)
            if self.flags & NSOFlags.RoHash:
                if hashlib.sha256(ro_data).digest() != ro_hash:
                    raise ParseError(".rodata hash is invalid")
            if len(ro_data) != self.ro_size:
                raise ParseError(".rodata has unexpected size")
            self.ro_data = ro_data

        if decompress_data:
            stream.seek(data_file_offset)
            data_data = stream.read(data_file_size)
            if self.flags & NSOFlags.DataCompress:
                data_data = self._decompress(data_data, self.data_size)
            if self.flags & NSOFlags.DataHash:
                if hashlib.sha256(data_data).digest() != data_hash:
                    raise ParseError(".data hash is invalid")
            if len(data_data) != self.data_size:
                raise ParseError(".data has unexpected size")
            self.data_data = data_data

    def _decompress(self, data: bytes, size: int) -> bytes:
        if self.flags & NSOFlags.UseZbicCompression:
            return zbic.decompress(data)
        return lz4.block.decompress(data, size)
