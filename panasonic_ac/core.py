import json
import os
import re
import subprocess
import shutil
from typing import Optional, Dict, Any

CONFIG_DIR = os.path.expanduser("~/.config/panasonic-ac")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CHIP_TOOL = "chip-tool"
DEFAULT_ENDPOINT = 1

def check_chip_tool():
    """Verify that chip-tool is installed and accessible."""
    if not shutil.which(CHIP_TOOL):
        return False
    return True

def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"aliases": {}}

def save_config(config: Dict[str, Any]):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def resolve_id(identifier: str) -> str:
    config = load_config()
    # Ensure it's returned as string for chip-tool
    return str(config["aliases"].get(identifier, identifier))

def run_chip_tool(args: list[str]) -> str:
    try:
        result = subprocess.run(
            [CHIP_TOOL] + args,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError("chip-tool command timed out after 60s.")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.output or str(e)
        raise RuntimeError(f"Error running chip-tool: {error_msg}")

def get_next_node_id() -> int:
    config = load_config()
    existing_ids = list(config["aliases"].values())
    if not existing_ids:
        return 100001 # Start from a larger number
    
    try:
        max_id = max(int(node_id) for node_id in existing_ids)
        return max_id + 1
    except (ValueError, TypeError):
        return 100001

def decode_manual_code(code: str):
    """Decodes an 11-digit Manual Pairing Code into PIN and Short Discriminator."""
    code = re.sub(r"\D", "", code)
    if len(code) != 11:
        raise ValueError("Manual code must be exactly 11 digits.")

    d1 = int(code[0])
    d2_6 = int(code[1:6])
    d7_10 = int(code[6:10])
    
    # Extract Discriminator (Short version)
    discriminator_high = d1 & 0x3
    discriminator_low = d2_6 >> 14
    short_discriminator = (discriminator_high << 2) | discriminator_low
    
    # Extract Passcode
    passcode_low = d2_6 & 0x3FFF
    passcode_high = d7_10
    passcode = (passcode_high << 14) | passcode_low
    
    return f"{passcode:08d}", short_discriminator
