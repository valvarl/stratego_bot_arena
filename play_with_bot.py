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

blue_path = ensure_compiled(Path("lib/stratego_evaluator/agents/basic_cpp"))

bot_controller_blue = BotController(blue_path, "BlueBot")

game_manager = GameManager(
    config=StrategoConfig.from_game_mode(GameMode.ORIGINAL),
    blue_bot=bot_controller_blue,
    render_mode="human",
    log_file="game.log",
)

game_manager.run()
