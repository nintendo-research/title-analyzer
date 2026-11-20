
"""Provides a memory input stream."""

from collections.abc import Callable

import struct


Float = float


class ParseError(Exception):
    """Raised when an input stream encounters an error."""


class StreamIn:
    """
    Implements a memory input stream. Any operation that moves the stream past
    the input buffer of reads invalid values raises ParseError.
    """

    _endian: str
    _data: bytes
    _pos: int

    def __init__(self, data: bytes, endian: str):
        """Creates a new input stream with the given data and endianness."""
        self._endian = endian
        self._data = data
        self._pos = 0
    
    def set_endian(self, endian: str) -> None:
        """Changes the current endianness of the input stream."""
        self._endian = endian
        
    def get(self) -> bytes:
        """Returns the memory buffer of the input stream."""
        return self._data
    
    def size(self) -> int:
        """Returns the size of the input stream."""
        return len(self._data)
    
    def tell(self) -> int:
        """Returns the current position of the input stream."""
        return self._pos
    
    def seek(self, pos: int) -> None:
        """
        Changes the current position of the input stream. Raises ParseError if
        the stream is moved past the end of the memory buffer.
        """
        if pos > self.size():
            raise ParseError("Buffer overflow")
        self._pos = pos
    
    def skip(self, num: int) -> None:
        """Skip num bytes in the input stream."""
        self.seek(self._pos + num)
    
    def align(self, num: int) -> None:
        """Advances the current position until it is a multiple of num."""
        self.skip((num - self._pos % num) % num)
    
    def eof(self) -> bool:
        """Returns whether the stream is currently at the end of the buffer."""
        return self._pos == len(self._data)
    
    def available(self) -> int:
        """
        Returns the number of bytes between the current position and the end of
        the input buffer.
        """
        return len(self._data) - self._pos
    
    def peek(self, num: int) -> bytes:
        """
        Returns num bytes from the input buffer without advancing the position.
        """
        if self.available() < num:
            raise ParseError("Buffer overflow")
        return self._data[self._pos : self._pos + num]
        
    def read(self, num: int) -> bytes:
        """
        Returns num bytes from the input buffer and advances the current
        position.

        Note: this routine should be fast, because it is used a lot, especially
        in monitor mode.
        """
        data = self._data[self._pos : self._pos + num]
        if len(data) < num:
            raise ParseError("Buffer overflow")
        self._pos += num
        return data
        
    def readall(self) -> bytes:
        """Reads all remaining bytes from the input buffer."""
        return self.read(self.available())
        
    def pad(self, num: int, value: int = 0) -> None:
        """
        Reads num bytes from the input buffer. If any of the read bytes is
        different from value, ParseError is raised.
        """
        if self.read(num) != bytes([value]) * num:
            raise ParseError("Incorrect padding")
            
    def ascii(self, num: int) -> str:
        """
        Reads num ascii characters from the stream. Raises ParseError is any of
        the encountered characters is non-ascii.
        """
        try:
            return self.read(num).decode("ascii")
        except UnicodeDecodeError:
            raise ParseError("Failed to decode ASCII characters")
        
    def u8(self) -> int:
        "Reads an 8-bit unsigned integer from the stream."
        return self.read(1)[0]
    
    def u16(self) -> int:
        """Reads a 16-bit unsigned integer from the stream."""
        return struct.unpack(self._endian + "H", self.read(2))[0]
    
    def u32(self) -> int:
        """Reads a 32-bit unsigned integer from the stream."""
        return struct.unpack(self._endian + "I", self.read(4))[0]
    
    def u32_be(self) -> int:
        """Reads a 32-bit big-endian unsigned integer from the stream."""
        return struct.unpack(">I", self.read(4))[0]
    
    def u64(self) -> int:
        """Reads a 64-bit unsigned integer from the stream."""
        return struct.unpack(self._endian + "Q", self.read(8))[0]
    
    def s8(self) -> int:
        """Reads an 8-bit signed integer from the stream."""
        return struct.unpack("b", self.read(1))[0]
    
    def s16(self) -> int:
        """Reads a 16-bit signed integer from the stream."""
        return struct.unpack(self._endian + "h", self.read(2))[0]
    
    def s32(self) -> int:
        """Reads a 32-bit signed integer from the stream."""
        return struct.unpack(self._endian + "i", self.read(4))[0]
    
    def s64(self) -> int:
        """Reads a 64-bit signed integer from the stream."""
        return struct.unpack(self._endian + "q", self.read(8))[0]
    
    def u24(self) -> int:
        """Reads a 24-bit unsigned integer from the stream."""
        if self._endian == ">":
            return (self.u16() << 8) | self.u8()
        return self.u8() | (self.u16() << 8)
    
    def u128(self) -> int:
        """Reads a 128-bit unsigned integer from the stream."""
        if self._endian == ">":
            return (self.u64() << 64) | self.u64()
        return self.u64() | (self.u64() << 64)
    
    def float(self) -> Float:
        """Reads a 32-bit floating point value from the stream."""
        return struct.unpack(self._endian + "f", self.read(4))[0]
    
    def double(self) -> Float:
        """Reads a 64-bit floating point value from the stream."""
        return struct.unpack(self._endian + "d", self.read(8))[0]
    
    def bool(self) -> bool:
        """
        Reads an 8-bit integer from the stream and returns whether it is
        non-zero.
        """
        return bool(self.u8())
    
    def char(self) -> str:
        """Reads an 8-bit unicode character from the stream."""
        return chr(self.u8())
    
    def wchar(self) -> str:
        """Reads a 16-bit unicode character from the stream."""
        return chr(self.u16())
    
    def chars(self, num: int) -> str:
        """Reads num 8-bit unicode characters from the stream."""
        return "".join(self.repeat(self.char, num))
    
    def wchars(self, num: int) -> str:
        """Reads num 16-bit unicode characters from the stream."""
        return "".join(self.repeat(self.wchar, num))
    
    def repeat[T](self, func: Callable[[], T], count: int) -> list[T]:
        """
        Invokes func count times and aggregates the results. This method can be
        used to read a list of values from the stream.
        """
        return [func() for i in range(count)]
