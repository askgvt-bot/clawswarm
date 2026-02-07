#!/usr/bin/env python3
"""Swarm Status CLI - Created by ClawSwarm Coder Agent"""

import requests
from rich.console import Console
from rich.table import Table

def fetch_status():
    try:
        response = requests.get("http://localhost:8200/status")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching status: {e}")
        return None

def main():
    data = fetch_status()
    
    if not data:
        print("No agents found or error fetching data.")
        return
    
    agents = data.get("agents", [])
    
    console = Console()
    table = Table(title="🦞 ClawSwarm Agent Status")

    table.add_column("Name", style="cyan", justify="left")
    table.add_column("Type", style="magenta", justify="left")
    table.add_column("Status", style="green", justify="left")
    table.add_column("Task", style="yellow", justify="left", max_width=40)

    for agent in agents:
        table.add_row(
            agent.get("name", "N/A"),
            agent.get("type", "N/A"),
            agent.get("status", "N/A"),
            (agent.get("task", "N/A") or "")[:40] + "..." if len(agent.get("task", "") or "") > 40 else agent.get("task", "N/A")
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {data.get('total_agents', 0)} agents | [green]Running:[/green] {data.get('running_agents', 0)} | [yellow]Idle:[/yellow] {data.get('idle_agents', 0)} | [red]Busy:[/red] {data.get('busy_agents', 0)}")

if __name__ == "__main__":
    main()
