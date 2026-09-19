# WORLDKITTY — Infinite Charge

Specialist digital energy drink site.

- Rechargeable digital can
- Generation loop that mints **Volt Credits**
- Slice of every tick tops the **World Kitty** (communal pool)
- Credits redeem for **claim tickets** on actual cans and merchandise
- **AiX++** bind plate QR
- **Windows .exe installer** (`WorldKittySetup.exe`) — PE32 desktop shortcut + launch

Live: https://worldkitty.vercel.app  
Installer: https://worldkitty.vercel.app/downloads/WorldKittySetup.exe  
GitHub: https://github.com/Fish3kz21/worldkitty

Vercel project `worldkitty` on team `fish3kz21s-projects`. GitHub Login Connection in Vercel is still required before pushes auto-deploy.

## Windows installer

Rebuild the PE on Linux/macOS/Windows:

```bash
python3 installer/build_exe.py
```

Writes `downloads/WorldKittySetup.exe` (install + shortcut) and `downloads/WorldKitty.exe` (portable launch). SHA-256 is in `downloads/checksums.json`.

Companion scripts (no PE required):
- `downloads/WorldKitty-Install.ps1`
- `downloads/WorldKitty-Install.bat`

## Run locally

```bash
python3 -m http.server 8765
```
