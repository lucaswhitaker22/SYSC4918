"""
Command-line interface for the Sample Project.

This module provides a comprehensive CLI for interacting with the sample project,
including data processing, configuration management, and various utility commands.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import track

from .main import SampleProcessor, DataProcessor, create_processor, ProcessingError
from .config import Config, load_config, save_config
from .models import DataModel, ValidationError
from .utils import format_output, validate_input

# Initialize rich console for beautiful output
console = Console()

# Typer app for modern CLI
app = typer.Typer(
    name="sample-project",
    help="A comprehensive sample project CLI for data processing and management.",
    add_completion=False,
    rich_markup_mode="rich"
)

# Version information
__version__ = "1.2.3"


class CLIError(Exception):
    """Custom exception for CLI-related errors."""
    pass


@app.command()
def version():
    """Show version information."""
    console.print(f"Sample Project CLI v{__version__}", style="bold green")
    console.print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


@app.command()
def process(
    input_data: str = typer.Argument(..., help="Input data to process"),
    processor_type: str = typer.Option("sample", help="Type of processor to use"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    output_format: str = typer.Option("json", help="Output format (json, yaml, table)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
    async_mode: bool = typer.Option(False, "--async", help="Use async processing"),
    save_result: Optional[str] = typer.Option(None, "--save", help="Save result to file"),
):
    """
    Process input data using the specified processor.
    
    Examples:
        sample-project process "Hello World" --debug
        sample-project process '{"name": "test", "value": 42}' --processor-type data
        sample-project process "batch data" --save results.json
    """
    try:
        # Load configuration
        if config_file:
            config = load_config(config_file)
            console.print(f"Loaded config from: {config_file}", style="dim")
        else:
            config = Config()
        
        # Override config with CLI options
        if debug:
            config.debug = debug
        
        # Create processor
        processor = create_processor(processor_type, config)
        
        # Process data
        start_time = time.time()
        
        if async_mode:
            result = asyncio.run(processor.process_async(input_data))
        else:
            result = processor.process(input_data)
        
        processing_time = time.time() - start_time
        
        # Format and display output
        if output_format == "table":
            _display_result_table(result, processing_time)
        elif output_format == "yaml":
            import yaml
            output = yaml.dump(result.to_dict(), default_flow_style=False)
            console.print(output)
        else:  # json
            output = json.dumps(result.to_dict(), indent=2)
            console.print_json(output)
        
        # Save result if requested
        if save_result:
            with open(save_result, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            console.print(f"Result saved to: {save_result}", style="green")
        
        # Show processing stats if debug
        if debug:
            stats = processor.get_statistics()
            console.print(f"\nProcessing Stats: {stats}", style="dim")
        
    except (ProcessingError, ValidationError) as e:
        console.print(f"Processing Error: {e}", style="bold red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"Unexpected Error: {e}", style="bold red")
        if debug:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def batch(
    input_file: str = typer.Argument(..., help="Input file with data to process"),
    processor_type: str = typer.Option("sample", help="Type of processor to use"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file"),
    max_items: int = typer.Option(100, help="Maximum items to process"),
    show_progress: bool = typer.Option(True, help="Show progress bar"),
):
    """
    Process multiple items from a file in batch mode.
    
    Input file should contain JSON lines or a JSON array.
    
    Examples:
        sample-project batch data.jsonl --output results.json
        sample-project batch data.json --max-items 50 --no-show-progress
    """
    try:
        # Load input data
        with open(input_file, 'r') as f:
            if input_file.endswith('.jsonl'):
                data_items = [json.loads(line.strip()) for line in f if line.strip()]
            else:
                content = json.load(f)
                data_items = content if isinstance(content, list) else [content]
        
        console.print(f"Loaded {len(data_items)} items from {input_file}")
        
        # Load configuration
        config = load_config(config_file) if config_file else Config()
        config.max_items = max_items
        
        # Create processor
        processor = create_processor(processor_type, config)
        
        # Process batch
        start_time = time.time()
        
        if show_progress:
            results = []
            for item in track(data_items[:max_items], description="Processing items..."):
                try:
                    result = processor.process(item)
                    results.append(result)
                except Exception as e:
                    console.print(f"Failed to process item: {e}", style="yellow")
                    results.append({"success": False, "error": str(e)})
        else:
            results = processor.process_batch(data_items[:max_items])
        
        processing_time = time.time() - start_time
        
        # Prepare output
        output_data = {
            "batch_info": {
                "total_items": len(results),
                "processing_time": processing_time,
                "processor_type": processor_type,
                "config": config.to_dict()
            },
            "results": [r.to_dict() if hasattr(r, 'to_dict') else r for r in results]
        }
        
        # Save or display results
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            console.print(f"Batch results saved to: {output_file}", style="green")
        else:
            console.print_json(json.dumps(output_data, indent=2))
        
        # Show summary
        successful = sum(1 for r in results if getattr(r, 'success', True))
        console.print(f"\nBatch Summary: {successful}/{len(results)} successful", style="bold")
        
    except FileNotFoundError:
        console.print(f"Input file not found: {input_file}", style="bold red")
        raise typer.Exit(1)
    except json.JSONDecodeError as e:
        console.print(f"Invalid JSON in input file: {e}", style="bold red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"Batch processing failed: {e}", style="bold red")
        raise typer.Exit(1)


@app.command()
def config(
    action: str = typer.Argument(..., help="Action: show, create, validate"),
    config_file: Optional[str] = typer.Option("sample_config.json", "--file", "-f", help="Configuration file path"),
    debug: bool = typer.Option(False, help="Debug mode"),
    max_items: int = typer.Option(100, help="Maximum items to process"),
    cache_enabled: bool = typer.Option(True, help="Enable caching"),
):
    """
    Manage configuration files.
    
    Actions:
        show: Display current configuration
        create: Create a new configuration file
        validate: Validate an existing configuration file
    
    Examples:
        sample-project config show --file my_config.json
        sample-project config create --debug --max-items 200
        sample-project config validate --file production.json
    """
    try:
        if action == "show":
            if Path(config_file).exists():
                config = load_config(config_file)
                console.print(f"Configuration from {config_file}:")
                console.print_json(json.dumps(config.to_dict(), indent=2))
            else:
                console.print(f"Configuration file not found: {config_file}", style="yellow")
                console.print("Using default configuration:")
                config = Config()
                console.print_json(json.dumps(config.to_dict(), indent=2))
        
        elif action == "create":
            config = Config(
                debug=debug,
                max_items=max_items,
                cache_enabled=cache_enabled
            )
            save_config(config, config_file)
            console.print(f"Configuration created: {config_file}", style="green")
            console.print_json(json.dumps(config.to_dict(), indent=2))
        
        elif action == "validate":
            if not Path(config_file).exists():
                console.print(f"Configuration file not found: {config_file}", style="bold red")
                raise typer.Exit(1)
            
            try:
                config = load_config(config_file)
                console.print(f"✓ Configuration is valid: {config_file}", style="green")
                
                # Additional validation checks
                issues = []
                if config.max_items <= 0:
                    issues.append("max_items must be positive")
                if config.max_size <= 0:
                    issues.append("max_size must be positive")
                
                if issues:
                    console.print("⚠ Configuration issues found:", style="yellow")
                    for issue in issues:
                        console.print(f"  - {issue}")
                else:
                    console.print("✓ All validation checks passed", style="green")
                    
            except Exception as e:
                console.print(f"✗ Configuration is invalid: {e}", style="bold red")
                raise typer.Exit(1)
        
        else:
            console.print(f"Unknown action: {action}", style="bold red")
            console.print("Available actions: show, create, validate")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"Configuration command failed: {e}", style="bold red")
        raise typer.Exit(1)


@app.command()
def stats(
    processor_type: str = typer.Option("sample", help="Type of processor"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file"),
    reset: bool = typer.Option(False, "--reset", help="Reset statistics"),
):
    """
    Show or reset processor statistics.
    
    Examples:
        sample-project stats --processor-type sample
        sample-project stats --reset
    """
    try:
        config = load_config(config_file) if config_file else Config()
        processor = create_processor(processor_type, config)
        
        if reset:
            processor.reset_counters()
            processor.clear_cache()
            console.print("Statistics reset", style="green")
        else:
            stats = processor.get_statistics()
            
            table = Table(title=f"{processor_type.title()} Processor Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            for key, value in stats.items():
                table.add_row(key.replace('_', ' ').title(), str(value))
            
            console.print(table)
    
    except Exception as e:
        console.print(f"Stats command failed: {e}", style="bold red")
        raise typer.Exit(1)


@app.command()
def interactive():
    """
    Start an interactive session for data processing.
    
    This provides a REPL-like interface for experimenting with the processors.
    """
    console.print("Welcome to Sample Project Interactive Mode!", style="bold green")
    console.print("Type 'help' for available commands, 'exit' to quit.\n")
    
    config = Config(debug=True)
    processor = create_processor("sample", config)
    
    while True:
        try:
            user_input = console.input("[bold blue]sample-project>[/bold blue] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit']:
                console.print("Goodbye!", style="green")
                break
            
            if user_input.lower() == 'help':
                _show_interactive_help()
                continue
            
            if user_input.startswith('config '):
                config_cmd = user_input[7:].strip()
                if config_cmd == 'show':
                    console.print_json(json.dumps(config.to_dict(), indent=2))
                continue
            
            if user_input.startswith('stats'):
                stats = processor.get_statistics()
                console.print(f"Statistics: {stats}")
                continue
            
            # Process the input
            try:
                result = processor.process(user_input)
                console.print("Result:", style="bold")
                console.print_json(json.dumps(result.to_dict(), indent=2))
            except Exception as e:
                console.print(f"Processing Error: {e}", style="red")
        
        except KeyboardInterrupt:
            console.print("\nGoodbye!", style="green")
            break
        except EOFError:
            console.print("\nGoodbye!", style="green")
            break


def _show_interactive_help():
    """Show help for interactive mode."""
    help_table = Table(title="Interactive Mode Commands")
    help_table.add_column("Command", style="cyan")
    help_table.add_column("Description", style="white")
    
    commands = [
        ("help", "Show this help message"),
        ("config show", "Show current configuration"),
        ("stats", "Show processor statistics"),
        ("exit/quit", "Exit interactive mode"),
        ("<data>", "Process any data input"),
    ]
    
    for command, description in commands:
        help_table.add_row(command, description)
    
    console.print(help_table)


def _display_result_table(result, processing_time):
    """Display processing result in table format."""
    table = Table(title="Processing Result")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Success", str(result.success))
    table.add_row("Processing Time", f"{processing_time:.3f}s")
    
    if result.content:
        content_str = str(result.content)[:100] + "..." if len(str(result.content)) > 100 else str(result.content)
        table.add_row("Content", content_str)
    
    if result.error:
        table.add_row("Error", result.error)
    
    if result.metadata:
        for key, value in result.metadata.items():
            table.add_row(f"Meta: {key}", str(value))
    
    console.print(table)


# Click-based alternative commands (for demonstration)
@click.group()
@click.version_option(version=__version__)
def cli():
    """Alternative Click-based CLI interface."""
    pass


@cli.command()
@click.argument('data')
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.option('--format', type=click.Choice(['json', 'yaml', 'table']), default='json')
def click_process(data, debug, format):
    """Process data using Click interface."""
    config = Config(debug=debug)
    processor = SampleProcessor(config)
    
    try:
        result = processor.process(data)
        
        if format == 'json':
            click.echo(json.dumps(result.to_dict(), indent=2))
        elif format == 'table':
            click.echo(f"Success: {result.success}")
            click.echo(f"Content: {result.content}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Entry point for console scripts
def main():
    """Main entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\nOperation cancelled by user.", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"Unexpected error: {e}", style="bold red")
        sys.exit(1)


# Alternative entry point for Click
def click_main():
    """Entry point for Click-based CLI."""
    cli()


if __name__ == "__main__":
    main()
