from pathlib import Path
import subprocess
import sys

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from stratego import StrategoConfig, GameMode

from bot_arena.bot_controller import BotController
from bot_arena.game_manager import GameManager

def ensure_compiled(bot_dir: Path) -> str:
    exe = bot_dir / bot_dir.name
    if not exe.exists():
        subprocess.run(["make"], cwd=bot_dir, check=True)
    return str(exe)

red_path = ensure_compiled(Path("lib/stratego_evaluator/agents/basic_cpp"))
blue_path = ensure_compiled(Path("lib/stratego_evaluator/agents/basic_cpp"))

red_bot = BotController(red_path, "RedBot")
blue_bot = BotController(blue_path, "BlueBot")

game_manager = GameManager(
    config=StrategoConfig.from_game_mode(GameMode.ORIGINAL),
    red_bot=red_bot,
    blue_bot=blue_bot,
    render_mode=None,
    log_file="game.log",
)

game_manager.run()
