#!/usr/bin/env python3
"""Build WorldKitty Windows PE32 installers without mingw.

Produces GUI subsystem executables that:
  * create %%LOCALAPPDATA%%\\WorldKitty
  * write desktop + app-folder Internet shortcuts
  * open https://worldkitty.vercel.app
  * show a branded MessageBox

Modes:
  setup  — WorldKittySetup.exe (install + launch)
  launch — WorldKitty.exe (launch only)
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

IMAGE_BASE = 0x00400000
SECTION_RVA = 0x1000
FILE_ALIGN = 0x200
SECTION_ALIGN = 0x1000
HEADERS_SIZE = 0x200
URL = "https://worldkitty.vercel.app"
SHORTCUT = (
    "[InternetShortcut]\r\n"
    "URL=https://worldkitty.vercel.app\r\n"
    "IconIndex=0\r\n"
)

CSIDL_DESKTOPDIRECTORY = 0x10
CSIDL_LOCAL_APPDATA = 0x1C
GENERIC_WRITE = 0x40000000
CREATE_ALWAYS = 2
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE = 0xFFFFFFFF
MB_ICONINFORMATION = 0x40
SW_SHOWNORMAL = 1


def align(n: int, a: int) -> int:
    return (n + a - 1) & ~(a - 1)


class Buf:
    def __init__(self) -> None:
        self.data = bytearray()
        self.labels: dict[str, int] = {}

    def rva(self) -> int:
        return SECTION_RVA + len(self.data)

    def va(self, rva: int | None = None) -> int:
        return IMAGE_BASE + (self.rva() if rva is None else rva)

    def mark(self, name: str) -> int:
        self.labels[name] = self.rva()
        return self.labels[name]

    def emit(self, raw: bytes | bytearray) -> int:
        off = self.rva()
        self.data.extend(raw)
        return off

    def pad(self, n: int) -> None:
        self.data.extend(b"\x00" * n)

    def align4(self) -> None:
        while len(self.data) % 4:
            self.data.append(0)

    def zstr(self, name: str, s: str) -> int:
        r = self.mark(name)
        self.emit(s.encode("ascii") + b"\x00")
        return r


def u16(n: int) -> bytes:
    return struct.pack("<H", n)


def u32(n: int) -> bytes:
    return struct.pack("<I", n)
