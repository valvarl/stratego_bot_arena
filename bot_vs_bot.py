from stratego import StrategoConfig, GameMode

from bot_arena.bot_controller import BotController
from bot_arena.game_manager import GameManager

red_bot = BotController("lib/stratego_evaluator/agents/basic_cpp/basic_cpp", "RedBot")
blue_bot = BotController("lib/stratego_evaluator/agents/basic_cpp/basic_cpp", "BlueBot")

game_manager = GameManager(
    config=StrategoConfig.from_game_mode(GameMode.ORIGINAL),
    red_bot=red_bot,
    blue_bot=blue_bot,
    render_mode=None,
)

game_manager.run()
