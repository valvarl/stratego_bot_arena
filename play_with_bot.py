from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from stratego import StrategoConfig, GameMode

from bot_arena.bot_controller import BotController
from bot_arena.game_manager import GameManager

bot_controller_blue = BotController("lib/stratego_evaluator/agents/basic_cpp/basic_cpp", "BlueBot")

game_manager = GameManager(
    config=StrategoConfig.from_game_mode(GameMode.ORIGINAL),
    blue_bot=bot_controller_blue,
    render_mode="human"
)

game_manager.run()
