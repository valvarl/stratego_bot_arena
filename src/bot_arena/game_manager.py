from __future__ import annotations

import time
from typing import Optional

import gymnasium as gym
import pygame
import numpy as np
from stratego import StrategoConfigBase, StrategoConfig, StrategoConfigCpp, Piece, Player

from .bot_controller import BotController


class GameManager:

    token_to_piece = {
        '.': Piece.EMPTY,
        '+': Piece.LAKE,
        'F': Piece.FLAG,
        'B': Piece.BOMB,
        's': Piece.SPY,
        '9': Piece.SCOUT,
        '8': Piece.MINER,
        '7': Piece.SERGEANT,
        '6': Piece.LIEUTENANT,
        '5': Piece.CAPTAIN,
        '4': Piece.MAJOR,
        '3': Piece.COLONEL,
        '2': Piece.GENERAL,
        '1': Piece.MARSHAL
    }

    piece_to_token = {v: k for k, v in token_to_piece.items()}

    def __init__(
        self,
        config: StrategoConfigBase,
        red_bot: Optional[BotController] = None,
        blue_bot: Optional[BotController] = None,
        render_mode: Optional[str] = "human",
        log_file: Optional[str] = None,
    ):
        self.config = config
        self.render_mode = render_mode
        if render_mode not in [None, "human", "rgb_array"]:
            raise ValueError("Invalid render mode. Choose 'human', 'rgb_array', or None.")
        
        if isinstance(self.config, StrategoConfig):
            self.env = gym.make("stratego_gym/Stratego-v0", render_mode=self.render_mode)
        elif isinstance(self.config, StrategoConfigCpp):
            self.env = gym.make("stratego_gym/StrategoCpp-v0", render_mode=self.render_mode)
        else:
            raise ValueError("Unsupported game configuration type.")
        self.env.reset()
        
        self.red_bot = red_bot
        self.blue_bot = blue_bot
        self.log_file = log_file
        self._log = open(log_file, "w") if log_file else None
    
    def setup(
        self,
        red_setup: str | list[list[Piece]] | None = None,
        blue_setup: str | list[list[Piece]] | None = None,
    ) -> tuple[str | None, str | None]:
        raw_red = None
        raw_blue = None
        if self.red_bot is not None:
            raw_red = self.red_bot.setup(
                color="RED",
                width=self.config.width,
                height=self.config.height,
                opponent=self.blue_bot.name if self.blue_bot else "bot",
            )
            red_setup = raw_red

        if isinstance(red_setup, str):
            red_setup = self.parse_setup(red_setup)

        if self.blue_bot is not None:
            raw_blue = self.blue_bot.setup(
                color="BLUE",
                width=self.config.width,
                height=self.config.height,
                opponent=self.red_bot.name if self.red_bot else "bot",
            )
            blue_setup = raw_blue

        if isinstance(blue_setup, str):
            blue_setup = self.parse_setup(blue_setup)

        red_total = sum(self.config.p1_pieces_num)
        blue_total = sum(self.config.p2_pieces_num)

        # if self._log is None:
        print(f"Red setup: {red_setup}")
        print(f"Blue setup: {blue_setup}")

        blue_setup = [row[::-1] for row in blue_setup]

        if red_total != blue_total:
            raise ValueError("Red and Blue setups must have the same number of pieces.")
        if red_setup is None and self.red_bot is not None:
            raise ValueError("Red bot setup is required but not provided.")
        if blue_setup is None and self.blue_bot is not None:
            raise ValueError("Blue bot setup is required but not provided.")
        if red_setup is not None and red_total != len(red_setup) * len(red_setup[0]):
            raise ValueError("Red setups must match the board dimensions.")
        if blue_setup is not None and blue_total != len(blue_setup) * len(blue_setup[0]):
            raise ValueError("Blue setups must match the board dimensions.")
        
        red_turn = blue_turn = 0
        for turn in range(red_total + blue_total):
            if (turn % 2 == 0 and red_turn < red_total) or blue_turn >= blue_total:
                if red_setup is not None:
                    action = self.setup_to_action(red_setup, Player.RED, red_turn)
                    action = (10 - action[1] - 1, 10 - action[0] - 1)
                else:
                    action = self.env.action_space.sample()  # Random action if no setup provided
                self.env.step(action)
                red_turn += 1
            else:
                if blue_setup is not None:
                    action = self.setup_to_action(blue_setup, Player.BLUE, blue_turn)
                    action = (6 + action[1], 10 - action[0] - 1)
                else:
                    action = self.env.action_space.sample()  # Random action if no setup provided
                print(action)

                self.env.step(action)
                blue_turn += 1

        print(self.env.board)

        return raw_red, raw_blue

    def setup_to_action(self, setup: list[list[Piece]], player: Player, turn: int) -> tuple[int, int]:
        pieces_num = self.config.p1_pieces if player == Player.RED else self.config.p2_pieces

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

    def parse_setup(self, setup_string: str) -> list[Piece]:
        rows = setup_string.strip().split('\n')

        result = []
        for row in rows:
            row_pieces = [self.token_to_piece.get(char) for char in row]
            if None in row_pieces:
                invalid_chars = [char for char in row if char not in self.token_to_piece]
                raise ValueError(f"Invalid characters in row '{row}': {invalid_chars}")
            result.append(row_pieces)

        return result

    def board_to_str(self, reveal: Player):
        board = self.env.board
        lines = []
        for r in range(board.shape[0]):
            row_chars = []
            for c in range(board.shape[1]):
                val = int(board[r, c])
                if val == Piece.EMPTY.value:
                    row_chars.append('.')
                elif val == Piece.LAKE.value or val == -Piece.LAKE.value:
                    row_chars.append('+')
                elif val > 0:
                    row_chars.append(self.piece_to_token.get(Piece(val), '?'))
                else:
                    row_chars.append('#')
            lines.append(''.join(row_chars))

        if reveal == Player.RED:
            lines = [row[::-1] for row in lines[::-1]]

        return lines

    def parse_move(self, move: str):
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

    def _dest_from_move(self, x: int, y: int, direction: str, multiplier: int):
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

    def _rotate_move(self, move):
        x, y, direction, mult = move
        x = self.config.width - 1 - x
        y = self.config.height - 1 - y
        dir_map = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        direction = dir_map[direction]
        return x, y, direction, mult
    
    def _rotate_move_str(self, move_str):
        move = move_str.strip().split()
        if len(move) > 4 or not move:
            raise ValueError(f"Invalid move format: {move_str}")
        if len(move) < 3:
            return move_str
        x, y, direction = int(move[0]), int(move[1]), move[2].upper()
        mult = int(move[3]) if len(move) > 3 else 1
        x, y, direction, mult = self._rotate_move((x, y, direction, mult))
        return self._move_to_str((x, y, direction, mult))

    def _move_to_str(self, move):
        x, y, direction, mult = move
        return f"{x} {y} {direction}" + (f" {mult}" if mult != 1 else "")

    def _compute_outcome(self, before, after, src, dst):
        atk = before[src]
        defn = before[dst]
        after_dst = after[dst]
        if defn == Piece.EMPTY.value:
            return "OK"
        atk_token = self.piece_to_token.get(Piece(abs(int(atk))), "?")
        def_token = self.piece_to_token.get(Piece(abs(int(defn))), "?")
        if defn == -Piece.FLAG.value:
            return "VICTORY_FLAG"
        if after_dst == atk:
            return f"KILLS {atk_token} {def_token}"
        elif after_dst == defn:
            return f"DIES {atk_token} {def_token}"
        elif after_dst == Piece.EMPTY.value:
            return f"BOTHDIE {atk_token} {def_token}"
        else:
            return "ILLEGAL"

    def _get_move_from_human(self, player: Player):
        move = input("Enter move (x y DIRECTION [MULT]) or SURRENDER: ")
        return move if player == Player.RED else self._rotate_move_str(move)
    
    def _src_dest_from_move(self, x: int, y: int, direction: str, multiplier: int, player: Player):
        if player == Player.RED:
            src = (10 - y - 1, 10 - x - 1)
            _direction = direction.upper()
            if _direction == "UP":
                _direction = "DOWN"
            elif _direction == "DOWN":
                _direction = "UP"
            elif _direction == "LEFT":
                _direction = "RIGHT"
            elif _direction == "RIGHT":
                _direction = "LEFT"
            dst = self._dest_from_move(10 - x - 1, 10 - y - 1, _direction, multiplier)
            return src, dst
        else:
            src = (y, x)
            dst = self._dest_from_move(x, y, direction, multiplier)
            return src, dst

    def run(
        self,
        red_setup: str | list[list[Piece]] | None = None,
        blue_setup: str | list[list[Piece]] | None = None,
    ):
        raw_red, raw_blue = self.setup(red_setup, blue_setup)

        if self._log:
            red_name = self.red_bot.path if self.red_bot else "HUMAN"
            self._log.write(f"{red_name} RED SETUP\n")
            if raw_red:
                for line in raw_red.splitlines():
                    self._log.write(line + "\n")
            blue_name = self.blue_bot.path if self.blue_bot else "HUMAN"
            self._log.write(f"{blue_name} BLUE SETUP\n")
            if raw_blue:
                for line in raw_blue.splitlines():
                    self._log.write(line + "\n")

        last_move: tuple[int,int,str,int] | None = None
        last_player: Player | None = None
        outcome = "OK"
        terminated = False
        turn_num = 1
        while not terminated:
            if self.render_mode == "human":
                time.sleep(0.2)
                self.env.render()

            player = self.env.player
            board_lines = self.board_to_str(player)
            controller = self.red_bot if player == Player.RED else self.blue_bot

            msg = self._move_to_str(last_move) if last_move is not None else "START"

            if controller is not None:
                print(">>>  Requesting move from bot:", msg, outcome)
                print('\n'.join(board_lines))
                move_str = controller.request_move(msg, outcome, board_lines)
                print(move_str)
            else:
                print("Last move:", msg, outcome)
                for line in board_lines:
                    print(line)
                move_str = self._get_move_from_human(player)

            if self._log is None:
                print(f"Move from {'Red' if player == Player.RED else 'Blue'}: {move_str}")

            parsed = self.parse_move(move_str)
            if parsed in {"SURRENDER", "QUIT"}:
                outcome = "SURRENDER"
                terminated = True
                break
            if parsed == "NO_MOVE" or parsed is None:
                outcome = "ILLEGAL"
                terminated = True
                break
            
            src, dst = self._src_dest_from_move(*parsed, player)

            print(self.env.valid_pieces_to_select())

            valid_select = self.env.valid_pieces_to_select()[src]
            if not valid_select:
                outcome = "ILLEGAL"
                terminated = True
                break
            
            print(src, dst)
            self.env.step(src)
            print(self.env.valid_destinations(), dst)

            if self.env.valid_destinations()[dst]:
                before = self.env.board.copy()
                obs, reward, term, trunc, info = self.env.step(dst)
                after = np.rot90(self.env.board, 2) * -1
                outcome = self._compute_outcome(before, after, src, dst)
                terminated = term or trunc
                last_move = parsed
                last_player = player
            else:
                outcome = "ILLEGAL"
                terminated = True

            if self._log is None:
                print("Outcome:", outcome)

            if self._log:
                color_str = "RED" if player == Player.RED else "BLU"
                self._log.write(f"{turn_num} {color_str}: {self._move_to_str(parsed)} {outcome}\n")
                turn_num += 1

            if controller is not None and not terminated:
                controller.confirm_result(self._move_to_str(last_move), outcome)

        if self._log is None:
            print("Game ended with outcome:", outcome)

        red_remaining = int(np.sum((self.env.board > 0) & (self.env.board != Piece.LAKE.value)))
        blue_remaining = int(np.sum((self.env.board < 0) & (self.env.board != -Piece.LAKE.value)))

        if self._log:
            winner = "RED" if last_player == Player.RED else "BLUE"
            winner_path = self.red_bot.path if last_player == Player.RED else self.blue_bot.path
            self._log.write(f"{winner_path} {winner} VICTORY {turn_num-1} {red_remaining} {blue_remaining}\n")


        if self.red_bot is not None:
            self.red_bot.end_game(outcome)
        if self.blue_bot is not None:
            self.blue_bot.end_game(outcome)

        if self._log is not None:
            self._log.close()
