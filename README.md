# Panasonic Matter AC CLI

A modern, human-friendly Python CLI wrapper for `chip-tool` to control Matter-enabled Panasonic Air Conditioners.

## 🌟 Features
- **Simplicity**: Use `panasonic-ac on bedroom` instead of complex `chip-tool` hexadecimal strings.
- **Aliases**: Map Node IDs to names (e.g., `chaitanya-bedroom`, `living-room`).
- **Real-time Status**: Beautifully formatted reports showing power state, current room temperature, and target temperature.
- **Multi-Admin Support**: Works simultaneously with your Panasonic MirAIe app, Google Home, or Apple Home.
- **Global Installation**: Install once and run `panasonic-ac` from any directory.

## 📋 Prerequisites
1. **Linux**: Tested on Ubuntu/Debian.
2. **chip-tool**: The official Matter reference controller.
   ```bash
   sudo snap install chip-tool
   ```

## 🛠️ Setup & Pairing

### 1. Initial Wi-Fi Setup
Before using this tool, your AC **must already be connected to your Wi-Fi network** using the official Panasonic **MirAIe app**.

### 2. Identify your AC's Pairing Code
Locate the Matter QR sticker on your AC unit. You will need the **11-digit numeric setup code**.

### 3. Pair the AC with the CLI
Once the AC is on your Wi-Fi, simply run:
```bash
panasonic-ac pair <11-DIGIT-CODE> --name <ALIAS>
# Example: panasonic-ac pair 1234-567-8901 --name bedroom
```

## ⌨️ Usage

| Command | Description |
| :--- | :--- |
| `panasonic-ac on bedroom` | Turn AC ON |
| `panasonic-ac off bedroom` | Turn AC OFF |
| `panasonic-ac status bedroom` | View full status report (Power, Room Temp, Target) |
| `panasonic-ac set bedroom 24` | Set target temperature to 24°C |
| `panasonic-ac fan bedroom 5` | Set fan mode (1:Low, 2:Med, 3:High, 5:Auto) |
| `panasonic-ac temp bedroom` | Quick read of the room temperature sensor |
| `panasonic-ac identify bedroom` | Make the AC beep/flash to identify it |
| `panasonic-ac list` | Show all saved AC aliases |

## 🔄 Updates
To get the latest version of the tool:
```bash
uv tool upgrade panasonic-ac
```
