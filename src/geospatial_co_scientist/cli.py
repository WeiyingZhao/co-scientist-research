"""Command-line interface for the Geospatial AI Co-Scientist."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from geospatial_co_scientist.config import get_settings, update_settings
from geospatial_co_scientist.orchestration.workflow import GeospatialCoScientist

app = typer.Typer(
    name="geo-scientist",
    help="Geospatial AI Co-Scientist - AI-powered research assistant for geospatial science"
)
console = Console()


@app.command()
def research(
    question: str = typer.Argument(..., help="The research question or goal"),
    domain: str = typer.Option(
        "general_gis",
        "--domain", "-d",
        help="Research domain (e.g., remote_sensing, urban_planning)"
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context", "-c",
        help="Additional context for the research"
    ),
    iterations: int = typer.Option(
        3,
        "--iterations", "-i",
        help="Maximum number of generation-refinement iterations"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path for the research overview"
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Run in interactive mode with human-in-the-loop"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON"
    )
):
    """
    Conduct AI-assisted geospatial research.

    This command starts a research session with the AI Co-Scientist,
    which will generate hypotheses, review them, and create experiment designs.

    Example:
        geo-scientist research "How can satellite imagery detect urban heat islands?"
    """
    console.print(Panel(
        f"[bold blue]Geospatial AI Co-Scientist[/bold blue]\n\n"
        f"Research Question: {question}\n"
        f"Domain: {domain}\n"
        f"Max Iterations: {iterations}",
        title="Starting Research Session"
    ))

    # Run the research
    if interactive:
        asyncio.run(run_interactive_research(question, domain, context, iterations))
    else:
        result = asyncio.run(run_batch_research(
            question, domain, context, iterations
        ))

        if result:
            if json_output:
                output_text = json.dumps(result.model_dump(), indent=2, default=str)
            else:
                output_text = result.to_markdown()

            if output:
                output.write_text(output_text)
                console.print(f"[green]Results saved to {output}[/green]")
            else:
                if json_output:
                    console.print(output_text)
                else:
                    console.print(Markdown(output_text))


async def run_batch_research(
    question: str,
    domain: str,
    context: Optional[str],
    iterations: int
):
    """Run research in batch mode."""
    scientist = GeospatialCoScientist()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Conducting research...", total=None)

        try:
            result = await scientist.research(
                question=question,
                domain=domain,
                context=context,
                max_iterations=iterations
            )
            progress.update(task, description="Research complete!")
            return result

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None


async def run_interactive_research(
    question: str,
    domain: str,
    context: Optional[str],
    iterations: int
):
    """Run research in interactive mode with human checkpoints."""
    scientist = GeospatialCoScientist()

    # Initialize
    from geospatial_co_scientist.models.research import ResearchGoal
    from geospatial_co_scientist.models.state import CoScientistState

    goal = ResearchGoal(
        question=question,
        domain=domain,
        context=context
    )

    scientist._current_state = CoScientistState(
        research_goal=goal.model_dump(),
        max_iterations=iterations
    )

    console.print("[cyan]Interactive mode: You can provide feedback at checkpoints[/cyan]")

    while scientist._current_state.should_continue:
        # Execute one step
        state = await scientist.step()

        # Show status
        show_status(scientist)

        # Check for checkpoint
        if state.awaiting_human_input:
            feedback = Prompt.ask(
                "\n[yellow]Checkpoint reached. Enter feedback (or 'continue'):[/yellow]"
            )

            if feedback.lower() in ['quit', 'exit', 'stop']:
                break

            await scientist.provide_feedback(feedback)

        # Ask if user wants to continue (after each iteration)
        if state.current_iteration > 1 and state.current_iteration % 1 == 0:
            if not Confirm.ask("Continue to next step?", default=True):
                break

    # Show final results
    if scientist._current_state.research_overview:
        from geospatial_co_scientist.models.research import ResearchOverview
        overview = ResearchOverview(**scientist._current_state.research_overview)
        console.print(Markdown(overview.to_markdown()))


def show_status(scientist: GeospatialCoScientist):
    """Display current status."""
    status = scientist.get_status()

    table = Table(title="Research Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    for key, value in status.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print(table)


@app.command()
def hypotheses(
    session_file: Path = typer.Argument(..., help="Path to session state file"),
    top_n: int = typer.Option(5, "--top", "-n", help="Number of top hypotheses to show")
):
    """Display hypotheses from a saved session."""
    if not session_file.exists():
        console.print(f"[red]Session file not found: {session_file}[/red]")
        raise typer.Exit(1)

    data = json.loads(session_file.read_text())
    hypotheses = data.get("hypotheses", [])

    if not hypotheses:
        console.print("[yellow]No hypotheses found in session[/yellow]")
        return

    # Sort by Elo score
    sorted_hyps = sorted(hypotheses, key=lambda x: x.get("elo_score", 1000), reverse=True)

    table = Table(title=f"Top {top_n} Hypotheses")
    table.add_column("#", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Elo Score", style="green")
    table.add_column("Type", style="yellow")

    for i, hyp in enumerate(sorted_hyps[:top_n], 1):
        table.add_row(
            str(i),
            hyp.get("title", "Untitled")[:50],
            f"{hyp.get('elo_score', 1000):.0f}",
            hyp.get("hypothesis_type", "unknown")
        )

    console.print(table)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    set_key: Optional[str] = typer.Option(None, "--set", help="Set a configuration value (key=value)")
):
    """Manage configuration settings."""
    settings = get_settings()

    if show:
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        for key, value in settings.model_dump().items():
            # Hide sensitive values
            if "key" in key.lower() or "secret" in key.lower():
                value = "***" if value else "(not set)"
            table.add_row(key, str(value))

        console.print(table)

    if set_key:
        if "=" not in set_key:
            console.print("[red]Invalid format. Use: --set key=value[/red]")
            raise typer.Exit(1)

        key, value = set_key.split("=", 1)
        try:
            update_settings(**{key: value})
            console.print(f"[green]Updated {key}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to update: {e}[/red]")


@app.command()
def version():
    """Show version information."""
    from geospatial_co_scientist import __version__
    console.print(f"Geospatial AI Co-Scientist v{__version__}")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
