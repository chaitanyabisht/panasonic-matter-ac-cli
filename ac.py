import typer
import subprocess
import json
import os
import re
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.status import Status

app = typer.Typer(help="Panasonic Matter AC Control Wrapper")
console = Console()

CONFIG_DIR = os.path.expanduser("~/.config/panasonic-ac")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CHIP_TOOL = "chip-tool"
DEFAULT_ENDPOINT = 1

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"aliases": {}}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def resolve_id(identifier: str) -> str:
    config = load_config()
    return str(config["aliases"].get(identifier, identifier))

def run_chip_tool(args: list[str]):
    try:
        result = subprocess.run(
            [CHIP_TOOL] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running chip-tool:[/bold red] {e.stderr or e.output}")
        raise typer.Exit(code=1)

@app.command()
def alias(name: str, node_id: int):
    """Assign a human-friendly name to a Node ID."""
    config = load_config()
    config["aliases"][name] = node_id
    save_config(config)
    console.print(f"[green]Success![/green] Assigned alias [bold]{name}[/bold] to Node ID [blue]{node_id}[/blue].")

@app.command(name="list")
def list_aliases():
    """List all saved AC aliases."""
    config = load_config()
    table = Table(title="Panasonic AC Aliases")
    table.add_column("Name", style="cyan")
    table.add_column("Node ID", style="magenta")
    
    for name, node_id in config["aliases"].items():
        table.add_row(name, str(node_id))
    
    console.print(table)

@app.command()
def on(identifier: str):
    """Turn the AC ON."""
    node_id = resolve_id(identifier)
    with Status(f"Turning ON AC {identifier}...", console=console):
        run_chip_tool(["onoff", "on", node_id, str(DEFAULT_ENDPOINT)])
    console.print(f"[bold green]✔[/bold green] AC {identifier} is now [bold green]ON[/bold green].")

@app.command()
def off(identifier: str):
    """Turn the AC OFF."""
    node_id = resolve_id(identifier)
    with Status(f"Turning OFF AC {identifier}...", console=console):
        run_chip_tool(["onoff", "off", node_id, str(DEFAULT_ENDPOINT)])
    console.print(f"[bold yellow]✔[/bold yellow] AC {identifier} is now [bold red]OFF[/bold red].")

@app.command()
def temp(identifier: str):
    """Get the current room temperature from the AC sensor."""
    node_id = resolve_id(identifier)
    output = run_chip_tool(["thermostat", "read", "local-temperature", node_id, str(DEFAULT_ENDPOINT)])
    
    match = re.search(r"LocalTemperature: (\d+)", output)
    if match:
        raw_temp = int(match.group(1))
        celsius = raw_temp / 100
        console.print(Panel(f"Current Room Temp: [bold cyan]{celsius}°C[/bold cyan]", title=f"AC {identifier} Sensor"))
    else:
        console.print("[red]Could not read temperature sensor.[/red]")

@app.command()
def set(identifier: str, celsius: int):
    """Set the target cooling temperature."""
    node_id = resolve_id(identifier)
    raw_temp = celsius * 100
    with Status(f"Setting temperature to {celsius}°C...", console=console):
        run_chip_tool(["thermostat", "write", "occupied-cooling-setpoint", str(raw_temp), node_id, str(DEFAULT_ENDPOINT)])
    console.print(f"[bold green]✔[/bold green] Target temperature set to [bold cyan]{celsius}°C[/bold cyan].")

@app.command()
def fan(identifier: str, mode: int = typer.Argument(..., help="0:Off, 1:Low, 2:Med, 3:High, 5:Auto")):
    """Set the fan speed."""
    node_id = resolve_id(identifier)
    with Status(f"Setting fan mode to {mode}...", console=console):
        run_chip_tool(["fancontrol", "write", "fan-mode", str(mode), node_id, str(DEFAULT_ENDPOINT)])
    console.print(f"[bold green]✔[/bold green] Fan mode updated to [bold blue]{mode}[/bold blue].")

@app.command()
def status(identifier: str):
    """Get a full status report from the AC."""
    node_id = resolve_id(identifier)
    
    with Status("Fetching status...", console=console):
        # Read power
        p_out = run_chip_tool(["onoff", "read", "on-off", node_id, str(DEFAULT_ENDPOINT)])
        power = "ON" if "OnOff: TRUE" in p_out else "OFF"
        
        # Read current temp
        t_out = run_chip_tool(["thermostat", "read", "local-temperature", node_id, str(DEFAULT_ENDPOINT)])
        cur_match = re.search(r"LocalTemperature: (\d+)", t_out)
        cur_temp = f"{int(cur_match.group(1))/100}°C" if cur_match else "Unknown"
        
        # Read target temp
        tgt_out = run_chip_tool(["thermostat", "read", "occupied-cooling-setpoint", node_id, str(DEFAULT_ENDPOINT)])
        tgt_match = re.search(r"OccupiedCoolingSetpoint: (\d+)", tgt_out)
        tgt_temp = f"{int(tgt_match.group(1))/100}°C" if tgt_match else "Unknown"
        
    table = Table(show_header=False, padding=(0, 2))
    table.add_row("Power State", f"[bold]{power}[/bold]", style="green" if power == "ON" else "red")
    table.add_row("Current Temp", f"[bold cyan]{cur_temp}[/bold cyan]")
    table.add_row("Target Temp", f"[bold yellow]{tgt_temp}[/bold yellow]")
    
    console.print(Panel(table, title=f"Status Report: {identifier}", expand=False))

def get_next_node_id():
    config = load_config()
    existing_ids = list(config["aliases"].values())
    if not existing_ids:
        return 101
    return max(int(id) for id in existing_ids) + 1

def decode_manual_code(code: str) -> str:
    """Decodes an 11-digit Manual Pairing Code into an 8-digit PIN."""
    # Ensure code is exactly 11 digits
    code = re.sub(r"\D", "", code)
    if len(code) != 11:
        raise ValueError("Manual code must be exactly 11 digits.")

    d1 = int(code[0])
    d2_6 = int(code[1:6])
    d7_10 = int(code[6:10])
    
    passcode_low = d2_6 & 0x3FFF
    passcode_high = d7_10
    
    passcode = (passcode_high << 14) | passcode_low
    return f"{passcode:08d}"

@app.command()
def pair(
    code: str = typer.Argument(..., help="The 11-digit setup code from the AC sticker"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="A human-friendly name for this AC"),
    node_id: Optional[int] = typer.Option(None, "--id", help="Manually specify a Node ID (optional)"),
    ip: Optional[str] = typer.Option(None, "--ip", help="Manually specify the IP address of the AC")
):
    """Pair a new AC using its 11-digit code."""
    # Remove dashes/spaces for storage but use original for decoding if needed
    clean_code = re.sub(r"\D", "", code)
    
    if node_id is None:
        node_id = get_next_node_id()
        
    with Status(f"Commissioning new AC as Node ID {node_id}...", console=console):
        if ip:
            # For direct IP, we MUST use the decoded 8-digit PIN
            pin = decode_manual_code(clean_code)
            run_chip_tool(["pairing", "onnetwork", str(node_id), pin, "--ip", ip, "--bypass-attestation-verifier", "true"])
        else:
            # For discovery, chip-tool handles the 11-digit code directly
            run_chip_tool(["pairing", "code", str(node_id), clean_code, "--bypass-attestation-verifier", "true"])
    
    config = load_config()
    # Save the alias if provided, otherwise save the ID as its own name
    alias_name = name if name else str(node_id)
    config["aliases"][alias_name] = node_id
    save_config(config)
    
    console.print(f"[bold green]✔[/bold green] AC successfully paired!")
    console.print(f"Node ID [magenta]{node_id}[/magenta] is now ready.")
    if name:
        console.print(f"Alias [bold cyan]{name}[/bold cyan] linked.")

if __name__ == "__main__":
    app()
