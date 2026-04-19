import typer
import re
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.status import Status
from rich import box
from .core import (
    check_chip_tool,
    load_config,
    save_config,
    resolve_id,
    run_chip_tool,
    get_next_node_id,
    decode_manual_code,
    DEFAULT_ENDPOINT
)

app = typer.Typer(help="Panasonic Matter AC Control Wrapper")
console = Console()

@app.callback()
def main_callback():
    """Ensure chip-tool is available before running any commands."""
    if not check_chip_tool():
        console.print("[bold red]Error:[/bold red] 'chip-tool' not found in PATH.")
        console.print("Please install the Matter SDK (e.g., via snap: `sudo snap install chip-tool`).")
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
        try:
            run_chip_tool(["onoff", "on", node_id, str(DEFAULT_ENDPOINT)])
            
            # Read current temp
            t_out = run_chip_tool(["thermostat", "read", "local-temperature", node_id, str(DEFAULT_ENDPOINT)])
            cur_match = re.search(r"LocalTemperature: (\d+)", t_out)
            cur_temp = f"{int(cur_match.group(1))/100}°C" if cur_match else "Unknown"
            
            # Read target temp
            tgt_out = run_chip_tool(["thermostat", "read", "occupied-cooling-setpoint", node_id, str(DEFAULT_ENDPOINT)])
            tgt_match = re.search(r"OccupiedCoolingSetpoint: (\d+)", tgt_out)
            tgt_temp = f"{int(tgt_match.group(1))/100}°C" if tgt_match else "Unknown"
            
            console.print(f"[bold green]✔[/bold green] AC {identifier} is now [bold green]ON[/bold green].")
            console.print(f"Room: [bold cyan]{cur_temp}[/bold cyan] | Target: [bold yellow]{tgt_temp}[/bold yellow]")
        except RuntimeError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

@app.command()
def off(identifier: str):
    """Turn the AC OFF."""
    node_id = resolve_id(identifier)
    with Status(f"Turning OFF AC {identifier}...", console=console):
        try:
            run_chip_tool(["onoff", "off", node_id, str(DEFAULT_ENDPOINT)])
            console.print(f"[bold yellow]✔[/bold yellow] AC {identifier} is now [bold red]OFF[/bold red].")
        except RuntimeError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

@app.command()
def temp(identifier: str):
    """Get the current room temperature from the AC sensor."""
    node_id = resolve_id(identifier)
    try:
        output = run_chip_tool(["thermostat", "read", "local-temperature", node_id, str(DEFAULT_ENDPOINT)])
        match = re.search(r"LocalTemperature: (\d+)", output)
        if match:
            raw_temp = int(match.group(1))
            celsius = raw_temp / 100
            console.print(Panel(f"Current Room Temp: [bold cyan]{celsius}°C[/bold cyan]", title=f"AC {identifier} Sensor"))
        else:
            console.print("[red]Could not read temperature sensor.[/red]")
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def set(identifier: str, celsius: int):
    """Set the target cooling temperature."""
    node_id = resolve_id(identifier)
    raw_temp = celsius * 100
    with Status(f"Setting temperature to {celsius}°C...", console=console):
        try:
            run_chip_tool(["thermostat", "write", "occupied-cooling-setpoint", str(raw_temp), node_id, str(DEFAULT_ENDPOINT)])
            console.print(f"[bold green]✔[/bold green] Target temperature set to [bold cyan]{celsius}°C[/bold cyan].")
        except RuntimeError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

@app.command()
def fan(identifier: str, mode: int = typer.Argument(..., help="0:Off, 1:Low, 2:Med, 3:High, 5:Auto")):
    """Set the fan speed."""
    node_id = resolve_id(identifier)
    with Status(f"Setting fan mode to {mode}...", console=console):
        try:
            run_chip_tool(["fancontrol", "write", "fan-mode", str(mode), node_id, str(DEFAULT_ENDPOINT)])
            console.print(f"[bold green]✔[/bold green] Fan mode updated to [bold blue]{mode}[/bold blue].")
        except RuntimeError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

@app.command()
def status(identifier: str):
    """Get a full status report from the AC."""
    node_id = resolve_id(identifier)
    
    with Status("Fetching status...", console=console):
        try:
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
            
            # Read RSSI
            rssi_out = run_chip_tool(["wifinetworkdiagnostics", "read", "rssi", node_id, "0"])
            rssi_match = re.search(r"RSSI: (-?\d+)", rssi_out)
            rssi = f"{rssi_match.group(1)} dBm" if rssi_match else "Unknown"
        except RuntimeError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)
            
    table = Table(title=f"Status Report: {identifier}", show_header=False, padding=(0, 1), box=box.ROUNDED)
    table.add_column(style="dim", width=20)
    table.add_column(width=20)
    table.add_row("Power State", f"[bold]{power}[/bold]", style="green" if power == "ON" else "red")
    table.add_row("Current Temp", f"[bold cyan]{cur_temp}[/bold cyan]")
    table.add_row("Target Temp", f"[bold yellow]{tgt_temp}[/bold yellow]")
    table.add_row("Wi-Fi Signal", f"[bold magenta]{rssi}[/bold magenta]")
    
    console.print(table)

@app.command()
def info(identifier: str):
    """Get detailed hardware and network diagnostics."""
    node_id = resolve_id(identifier)
    
    with Status("Gathering diagnostics...", console=console):
        results = {}
        
        # Helper to read single attribute
        def read_attr(cluster, attr, endpoint="0"):
            try:
                out = run_chip_tool([cluster, "read", attr, node_id, endpoint])
                m = re.search(f"{attr.replace('-', '')}: (.*)", out, re.IGNORECASE)
                if m:
                    return m.group(1).strip().strip('"')
            except Exception:
                pass
            return "Unknown"

        results["Model"] = read_attr("basicinformation", "product-name")
        results["Serial"] = read_attr("basicinformation", "serial-number")
        results["Firmware"] = read_attr("basicinformation", "software-version-string")
        results["RSSI"] = read_attr("wifinetworkdiagnostics", "rssi")
        results["Uptime"] = read_attr("generaldiagnostics", "up-time")
        results["Reboots"] = read_attr("generaldiagnostics", "reboot-count")
        results["Humidity"] = read_attr("relativehumiditymeasurement", "measured-value", "1")
        results["MfgDate"] = read_attr("basicinformation", "manufacturing-date")

    table = Table(title=f"Hardware Diagnostics: {identifier}", show_header=False, padding=(0, 1), box=box.ROUNDED)
    table.add_column(style="dim", width=20)
    table.add_column(width=20)
    table.add_row("Model", f"[bold]{results['Model']}[/bold]")
    table.add_row("Serial", results["Serial"])
    table.add_row("Firmware", results["Firmware"])
    table.add_row("Mfg Date", results["MfgDate"])
    
    if results["Humidity"] != "Unknown":
        try:
            h_val = int(results["Humidity"]) / 100
            table.add_row("Humidity", f"[bold blue]{h_val}%[/bold blue]")
        except ValueError:
            pass

    table.add_row("Wi-Fi Signal (RSSI)", f"[bold cyan]{results['RSSI']} dBm[/bold cyan]")
    
    if results["Uptime"] != "Unknown":
        try:
            seconds = int(results["Uptime"])
            hours = seconds // 3600
            days = hours // 24
            table.add_row("Uptime", f"[bold green]{days}d {hours % 24}h {(seconds // 60) % 60}m[/bold green]")
        except ValueError:
            table.add_row("Uptime", results["Uptime"])
        
    table.add_row("Reboot Count", f"[bold yellow]{results['Reboots']}[/bold yellow]")
    
    console.print(table)

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
        try:
            if ip:
                # Positional arguments for onnetwork: node-id setup-pin-code [ip-address] [port]
                pin, disc = decode_manual_code(clean_code)
                run_chip_tool(["pairing", "onnetwork", str(node_id), pin, ip, "5540", "--bypass-attestation-verifier", "true"])
            else:
                # For discovery, chip-tool handles the 11-digit code directly
                run_chip_tool(["pairing", "code", str(node_id), clean_code, "--bypass-attestation-verifier", "true"])
        except (ValueError, RuntimeError) as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)
    
    config = load_config()
    # Save the alias if provided, otherwise save the ID as its own name
    alias_name = name if name else str(node_id)
    config["aliases"][alias_name] = node_id
    save_config(config)
    
    console.print(f"[bold green]✔[/bold green] AC successfully paired!")
    console.print(f"Node ID [magenta]{node_id}[/magenta] is now ready.")
    if name:
        console.print(f"Alias [bold cyan]{name}[/bold cyan] linked.")

@app.command()
def identify(identifier: str, duration: int = 10):
    """Make the AC beep/flash to identify it."""
    node_id = resolve_id(identifier)
    with Status(f"Identifying AC {identifier} for {duration}s...", console=console):
        try:
            run_chip_tool(["identify", "identify", str(duration), node_id, str(DEFAULT_ENDPOINT)])
            console.print(f"[bold green]✔[/bold green] Identification command sent to {identifier}.")
        except RuntimeError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
