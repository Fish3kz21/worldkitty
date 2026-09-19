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


def build_pe(mode: str) -> bytes:
    b = Buf()

    # --- code will be patched in after we know IAT / string RVAs ---
    code_hole = b.mark("entry")
    CODE_PLACEHOLDER = 512
    b.pad(CODE_PLACEHOLDER)

    b.align4()
    b.zstr("open", "open")
    b.zstr("url", URL)
    b.zstr("wkdir", "\\WorldKitty")
    b.zstr("urlfile", "\\WORLDKITTY.url")
    b.zstr("deskfile", "\\WORLDKITTY.url")
    b.zstr("title", "WORLDKITTY")
    if mode == "setup":
        b.zstr(
            "msg",
            "Infinite Charge is installed.\r\n\r\n"
            "Desktop shortcut created.\r\n"
            "App folder: %LOCALAPPDATA%\\WorldKitty\r\n\r\n"
            "Opening the generation loop.",
        )
    else:
        b.zstr("msg", "Opening WORLDKITTY Infinite Charge.")
    b.zstr("shortcut", SHORTCUT)
    shortcut_len = len(SHORTCUT.encode("ascii"))

    b.align4()
    buf_app = b.mark("buf_app")
    b.pad(260)
    buf_desk = b.mark("buf_desk")
    b.pad(260)
    written = b.mark("written")
    b.pad(4)

    imports = {
        "kernel32.dll": [
            "ExitProcess",
            "lstrcatA",
            "CreateFileA",
            "WriteFile",
            "CloseHandle",
            "CreateDirectoryA",
        ],
        "user32.dll": ["MessageBoxA"],
        "shell32.dll": ["ShellExecuteA", "SHGetFolderPathA"],
    }

    hint_rva: dict[str, int] = {}
    for fns in imports.values():
        for fn in fns:
            b.align4()
            hint_rva[fn] = b.rva()
            b.emit(u16(0))
            b.emit(fn.encode("ascii") + b"\x00")

    dll_rva: dict[str, int] = {}
    for dll in imports:
        dll_rva[dll] = b.zstr(f"dll_{dll}", dll)

    ilt_rva: dict[str, int] = {}
    iat_rva: dict[str, int] = {}
    iat_fn: dict[str, int] = {}

    for dll, fns in imports.items():
        b.align4()
        ilt_rva[dll] = b.rva()
        for fn in fns:
            b.emit(u32(hint_rva[fn]))
        b.emit(u32(0))

        b.align4()
        iat_rva[dll] = b.rva()
        for fn in fns:
            iat_fn[fn] = b.rva()
            b.emit(u32(hint_rva[fn]))
        b.emit(u32(0))

    b.align4()
    import_dir = b.mark("import_dir")
    for dll in imports:
        b.emit(u32(ilt_rva[dll]))  # OriginalFirstThunk
        b.emit(u32(0))
        b.emit(u32(0))
        b.emit(u32(dll_rva[dll]))
        b.emit(u32(iat_rva[dll]))  # FirstThunk
    b.emit(b"\x00" * 20)

    def va(rva: int) -> int:
        return IMAGE_BASE + rva

    def push_imm32(val: int) -> bytes:
        return b"\x68" + u32(val)

    def push_imm8(val: int) -> bytes:
        return bytes([0x6A, val & 0xFF])

    def call_fn(name: str) -> bytes:
        return b"\xFF\x15" + u32(va(iat_fn[name]))

    def write_url_file(buf_rva: int) -> bytes:
        # CreateFileA(buf, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0)
        code = b""
        code += push_imm8(0)
        code += push_imm32(FILE_ATTRIBUTE_NORMAL)
        code += push_imm8(CREATE_ALWAYS)
        code += push_imm8(0)
        code += push_imm8(0)
        code += push_imm32(GENERIC_WRITE)
        code += push_imm32(va(buf_rva))
        code += call_fn("CreateFileA")
        # cmp eax, -1 / je +skip (skip length filled below)
        code += b"\x83\xF8\xFF"
        je_at = len(code)
        code += b"\x74\x00"  # placeholder
        after_je = len(code)
        # WriteFile(handle, shortcut, len, &written, 0)
        code += b"\x89\xC3"  # mov ebx, eax
        code += push_imm8(0)
        code += push_imm32(va(written))
        code += push_imm32(shortcut_len)
        code += push_imm32(va(b.labels["shortcut"]))
        code += b"\x53"  # push ebx
        code += call_fn("WriteFile")
        code += b"\x53"
        code += call_fn("CloseHandle")
        skip = len(code)
        rel = skip - after_je
        code = bytearray(code)
        code[je_at + 1] = rel
        return bytes(code)

    code = bytearray()
    # push ebp / mov ebp, esp
    code += b"\x55\x89\xE5"

    if mode == "setup":
        # SHGetFolderPathA(0, CSIDL_LOCAL_APPDATA, 0, 0, buf_app)
        code += push_imm32(va(buf_app))
        code += push_imm8(0)
        code += push_imm8(0)
        code += push_imm8(CSIDL_LOCAL_APPDATA)
        code += push_imm8(0)
        code += call_fn("SHGetFolderPathA")
        # lstrcatA(buf_app, "\\WorldKitty")
        code += push_imm32(va(b.labels["wkdir"]))
        code += push_imm32(va(buf_app))
        code += call_fn("lstrcatA")
        # CreateDirectoryA(buf_app, 0)
        code += push_imm8(0)
        code += push_imm32(va(buf_app))
        code += call_fn("CreateDirectoryA")
        # lstrcatA(buf_app, "\\WORLDKITTY.url")
        code += push_imm32(va(b.labels["urlfile"]))
        code += push_imm32(va(buf_app))
        code += call_fn("lstrcatA")
        code += write_url_file(buf_app)

        # Desktop shortcut
        code += push_imm32(va(buf_desk))
        code += push_imm8(0)
        code += push_imm8(0)
        code += push_imm8(CSIDL_DESKTOPDIRECTORY)
        code += push_imm8(0)
        code += call_fn("SHGetFolderPathA")
        code += push_imm32(va(b.labels["deskfile"]))
        code += push_imm32(va(buf_desk))
        code += call_fn("lstrcatA")
        code += write_url_file(buf_desk)

    # ShellExecuteA(0, "open", URL, 0, 0, SW_SHOWNORMAL)
    code += push_imm8(SW_SHOWNORMAL)
    code += push_imm8(0)
    code += push_imm8(0)
    code += push_imm32(va(b.labels["url"]))
    code += push_imm32(va(b.labels["open"]))
    code += push_imm8(0)
    code += call_fn("ShellExecuteA")

    # MessageBoxA(0, msg, title, MB_ICONINFORMATION)
    code += push_imm8(MB_ICONINFORMATION)
    code += push_imm32(va(b.labels["title"]))
    code += push_imm32(va(b.labels["msg"]))
    code += push_imm8(0)
    code += call_fn("MessageBoxA")

    code += push_imm8(0)
    code += call_fn("ExitProcess")

    if len(code) > CODE_PLACEHOLDER:
        raise SystemExit(f"code too large: {len(code)} > {CODE_PLACEHOLDER}")
    b.data[code_hole - SECTION_RVA : code_hole - SECTION_RVA + len(code)] = code

    raw_section = bytes(b.data)
    raw_size = align(len(raw_section), FILE_ALIGN)
    virt_size = align(len(raw_section), SECTION_ALIGN)
    size_of_image = align(SECTION_RVA + virt_size, SECTION_ALIGN)

    # DOS header + stub
    dos = bytearray(0x80)
    dos[0:2] = b"MZ"
    dos[0x3C:0x40] = u32(0x80)
    # tiny DOS stub: int 21h ah=4c
    stub = b"\x0E\x1F\xBA\x0E\x00\xB4\x09\xCD\x21\xB8\x01\x4C\xCD\x21This program cannot be run in DOS mode.\r\r\n$\x00"
    dos[0x40 : 0x40 + len(stub)] = stub

    # PE headers at 0x80
    pe = bytearray()
    pe += b"PE\x00\x00"
    pe += u16(0x14C)  # i386
    pe += u16(1)  # sections
    pe += u32(0)  # timestamp
    pe += u32(0)
    pe += u32(0)
    pe += u16(0xE0)  # optional header size
    pe += u16(0x0102)  # EXECUTABLE_IMAGE | 32BIT_MACHINE

    opt = bytearray()
    opt += u16(0x10B)  # PE32
    opt += bytes([0x0E, 0x1C])  # linker ver
    opt += u32(raw_size)  # SizeOfCode
    opt += u32(0)
    opt += u32(0)
    opt += u32(b.labels["entry"])  # AddressOfEntryPoint
    opt += u32(SECTION_RVA)  # BaseOfCode
    opt += u32(SECTION_RVA)  # BaseOfData
    opt += u32(IMAGE_BASE)
    opt += u32(SECTION_ALIGN)
    opt += u32(FILE_ALIGN)
    opt += u16(4) + u16(0)  # OS ver
    opt += u16(1) + u16(0)  # image ver
    opt += u16(4) + u16(0)  # subsystem ver
    opt += u32(0)
    opt += u32(size_of_image)
    opt += u32(HEADERS_SIZE)
    opt += u32(0)  # checksum
    opt += u16(2)  # WINDOWS_GUI
    opt += u16(0)  # DllCharacteristics = 0 (no ASLR)
    opt += u32(0x100000)  # stack reserve
    opt += u32(0x1000)
    opt += u32(0x100000)
    opt += u32(0x1000)
    opt += u32(0)
    opt += u32(16)
    dirs = [ (0, 0) ] * 16
    dirs[1] = (import_dir, 20 * (len(imports) + 1))
    for rva, size in dirs:
        opt += u32(rva) + u32(size)

    assert len(opt) == 0xE0

    sec = bytearray()
    name = b".text"
    sec += name + b"\x00" * (8 - len(name))
    sec += u32(len(raw_section))  # VirtualSize
    sec += u32(SECTION_RVA)
    sec += u32(raw_size)
    sec += u32(HEADERS_SIZE)  # PointerToRawData
    sec += u32(0) * 3
    sec += u32(0xE0000020)  # CODE | EXEC | READ | WRITE

    header = bytearray(dos) + pe + opt + sec
    assert len(header) <= HEADERS_SIZE
    header.extend(b"\x00" * (HEADERS_SIZE - len(header)))

    section = raw_section + b"\x00" * (raw_size - len(raw_section))
    pe_bytes = bytes(header + section)
    return pe_bytes


def write_exe(path: Path, mode: str) -> dict:
    raw = build_pe(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    assert raw[:2] == b"MZ"
    assert raw[0x80:0x84] == b"PE\x00\x00"
    return {"path": str(path), "bytes": len(raw), "sha256": sha, "mode": mode}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "public" / "downloads"
    if not (root / "public").exists():
        out = root / "downloads"
    setup = write_exe(out / "WorldKittySetup.exe", "setup")
    launch = write_exe(out / "WorldKitty.exe", "launch")
    meta = {
        "setup": setup,
        "launcher": launch,
        "url": URL,
    }
    (out / "checksums.json").write_text(
        __import__("json").dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    print(setup)
    print(launch)


if __name__ == "__main__":
    main()
