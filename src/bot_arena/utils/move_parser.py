from stratego import Piece, Player

TOKEN_TO_PIECE = {
    ".": Piece.EMPTY,
    "+": Piece.LAKE,
    "F": Piece.FLAG,
    "B": Piece.BOMB,
    "s": Piece.SPY,
    "9": Piece.SCOUT,
    "8": Piece.MINER,
    "7": Piece.SERGEANT,
    "6": Piece.LIEUTENANT,
    "5": Piece.CAPTAIN,
    "4": Piece.MAJOR,
    "3": Piece.COLONEL,
    "2": Piece.GENERAL,
    "1": Piece.MARSHAL,
}

def parse_setup(setup_string: str | list[str]) -> list[Piece]:
    rows = setup_string.strip().split("\n") if isinstance(setup_string, str) else setup_string

    result = []
    for row in rows:
        row_pieces = [TOKEN_TO_PIECE.get(char) for char in row]
        if None in row_pieces:
            invalid_chars = [char for char in row if char not in TOKEN_TO_PIECE]
            raise ValueError(f"Invalid characters in row '{row}': {invalid_chars}")
        result.append(row_pieces)

    return result

def setup_to_action(setup: list[list[Piece]], turn: int, pieces_num: dict[Piece, int]) -> tuple[int, int]:
    # Calculate which piece to place based on the turn
    current_turn = turn
    target_piece = None
    for piece in [Piece(i) for i in range(2, 14)]:
        count = pieces_num[piece]
        if current_turn < count:
            target_piece = piece
            break
        current_turn -= count
    else:
        raise ValueError("Unexpected turn number")

    # Find the first occurrence of the target piece in the setup
    for y, row in enumerate(setup):
        for x, cell in enumerate(row):
            if cell == target_piece:
                # Count how many of this piece type have been placed before this turn
                placed_count = sum(
                    1 for py in range(len(setup)) for px in range(len(setup[py]))
                    if setup[py][px] == target_piece and (py * len(setup[py]) + px < y * len(setup[y]) + x)
                )
                if placed_count == current_turn:
                    return (x, y)

    raise ValueError(f"No {target_piece.name} found for turn {turn}")


def parse_move(move: str):
    tokens = move.strip().split()
    if not tokens:
        return None
    if tokens[0].upper() in {"SURRENDER", "QUIT"}:
        return tokens[0].upper()
    if tokens[0].upper() == "NO_MOVE":
        return "NO_MOVE"
    if len(tokens) < 3:
        return None
    x = int(tokens[0])
    y = int(tokens[1])
    direction = tokens[2].upper()
    multiplier = int(tokens[3]) if len(tokens) > 3 else 1
    return x, y, direction, multiplier


def rotate_move(move, height: int, width: int):
    x, y, direction, mult = move
    x = width - 1 - x
    y = height - 1 - y
    dir_map = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
    direction = dir_map[direction]
    return x, y, direction, mult


def dest_from_move(x: int, y: int, direction: str, multiplier: int):
    dx, dy = 0, 0
    if direction == "UP":
        dy = -multiplier
    elif direction == "DOWN":
        dy = multiplier
    elif direction == "LEFT":
        dx = -multiplier
    elif direction == "RIGHT":
        dx = multiplier
    else:
        raise ValueError(f"Unknown direction: {direction}")
    return y + dy, x + dx


def src_dest_from_move(x: int, y: int, direction: str, multiplier: int, player: Player, height: int, width: int):
    move = (x, y, direction, multiplier)
    if player == Player.RED:
        move = rotate_move(move, height, width)
    src = (move[1], move[0])
    dst = dest_from_move(*move)
    return src, dst
