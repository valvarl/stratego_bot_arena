import re
from stratego import Pos, Player, StrategoConfigBase

from .move_parser import (
    parse_setup, 
    setup_to_action, 
    src_dest_from_move
)

_MOVE_RE = re.compile(
    r"""^\s*                # optional leading spaces
        \d+\s+              # turn number
        (?:RED|BLU):\s+     # player color and colon
        (\d+)\s+            # x coordinate
        (\d+)\s+            # y coordinate
        (LEFT|RIGHT|UP|DOWN) # direction
        (?:\s+(\d+))?       # optional multiplier
        \b                  # word boundary
    """,
    re.VERBOSE | re.IGNORECASE,
)

def parse_line(line: str) -> tuple[int, int, str, int] | None:
    """
    Parses a line like '182 BLU: 9 8 UP 5 OK'.

    Returns a tuple (x, y, direction, multiplier).
    If multiplier is not provided, returns 1.
    If the line does not contain coordinates (e.g. SURRENDER), returns None.
    """
    m = _MOVE_RE.match(line)
    if not m:
        return None                     # line without a coordinate-based move
    x, y, direction, mult = m.groups()
    return int(x), int(y), direction.upper(), int(mult) if mult else 1

def actions_from_log(log_path: str, config: StrategoConfigBase) -> tuple[list[Pos], list[int], int]:

    with open(log_path, "r", encoding="utf-8") as file:
        red_info = file.readline().strip()
        red_setup = file.readlines(4)
        blue_info = file.readline().strip()
        blue_setup = file.readlines(4)
        moves = file.readlines()

    actions = []
    player_ids = []

    red_setup = parse_setup(red_setup)
    blue_setup = parse_setup(blue_setup)
    blue_setup = [row[::-1] for row in blue_setup]

    red_total = sum(config.p1_pieces_num)
    blue_total = sum(config.p2_pieces_num)

    red_turn = blue_turn = 0
    for turn in range(red_total + blue_total):
        if (turn % 2 == 0 and red_turn < red_total) or blue_turn >= blue_total:
            action = setup_to_action(red_setup, red_turn, config.p1_pieces)
            action = (10 - action[1] - 1, 10 - action[0] - 1)
            actions.append(action)
            player_ids.append(Player.RED.value)
            red_turn += 1
        else:
            action = setup_to_action(blue_setup, blue_turn, config.p2_pieces)
            action = (6 + action[1], 10 - action[0] - 1)
            actions.append(action)
            player_ids.append(Player.BLUE.value)
            blue_turn += 1

    player = Player.RED
    for line in moves:
        move = parse_line(line)
        if move is None:
            break

        src, dest = src_dest_from_move(*move, player=player, height=config.height, width=config.width)
        actions.append(src)
        actions.append(dest)
        player_ids.append(player.value)
        player_ids.append(player.value)

        player = Player(player.value * -1)

    return actions, player_ids
