import argparse
from pathlib import Path
import subprocess

from stratego import StrategoConfig, GameMode
from bot_arena.bot_controller import BotController
from bot_arena.game_manager import GameManager


def ensure_compiled(bot_path: Path) -> str:
    """Return an executable path for the given bot.

    If ``bot_path`` is a directory, an executable with the same name as the
    directory is expected to be produced via ``make`` in that directory.
    Otherwise ``bot_path`` is assumed to point directly to the executable and is
    returned as is.
    """

    if bot_path.is_dir():
        exe = bot_path / bot_path.name
        if not exe.exists() and (bot_path / "Makefile").exists():
            subprocess.run(["make"], cwd=bot_path, check=True)
        return str(exe)

    return str(bot_path)


def create_controller(path: str | None, name: str) -> BotController | None:
    if path is None or path.lower() == "@human":
        return None
    bot_path = ensure_compiled(Path(path))
    return BotController(bot_path, name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Stratego game")
    parser.add_argument("--red", type=str, default="@human", help="Path to red bot or @human")
    parser.add_argument("--blue", type=str, default="@human", help="Path to blue bot or @human")
    parser.add_argument("--log", type=str, default="game.log", help="Log file path")
    parser.add_argument("--render", choices=["human", "none"], default="human", help="Render mode")
    args = parser.parse_args()

    red_bot = create_controller(args.red, "RedBot")
    blue_bot = create_controller(args.blue, "BlueBot")
    render = args.render if args.render != "none" else None

    gm = GameManager(
        config=StrategoConfig.from_game_mode(GameMode.ORIGINAL),
        red_bot=red_bot,
        blue_bot=blue_bot,
        render_mode=render,
        log_file=args.log,
    )
    gm.run()


if __name__ == "__main__":
    main()