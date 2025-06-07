from __future__ import annotations

from typing import Optional

import gymnasium as gym
import pygame
from stratego import StrategoConfigBase, StrategoEnv, StrategoEnvCpp, Piece, Player

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

    def __init__(
        self,
        config: StrategoConfigBase,
        red_bot: Optional[BotController] = None,
        blue_bot: Optional[BotController] = None,
        render_mode: Optional[str] = "human",
    ):
        self.config = config
        self.render_mode = render_mode
        if render_mode not in [None, "human", "rgb_array"]:
            raise ValueError("Invalid render mode. Choose 'human', 'rgb_array', or None.")
        
        if isinstance(self.config, StrategoEnv):
            self.env = gym.make("stratego_gym/Stratego-v0", render_mode=self.render_mode)
        elif isinstance(self.config, StrategoEnvCpp):
            self.env = gym.make("stratego_gym/StrategoCpp-v0", render_mode=self.render_mode)
        else:
            raise ValueError("Unsupported game configuration type.")
        self.env.reset()
        
        self.red_bot = red_bot
        self.blue_bot = blue_bot
    
    def run(
        self, 
        red_setup: str | list[list[Piece]] | None = None,
        blue_setup: str | list[list[Piece]] | None = None,
    ):
        self.setup(red_setup, blue_setup)
        

    def setup(
        self, 
        red_setup: str | list[list[Piece]] | None = None,
        blue_setup: str | list[list[Piece]] | None = None,
    ) -> None:
        if self.red_bot is not None:
            red_setup = self.red_bot.setup(
                color="RED",
                width=self.config.width,
                height=self.config.height,
            )

        if isinstance(red_setup, str):
            red_setup = self.parse_setup(red_setup)

        if self.blue_bot is not None:
            blue_setup = self.blue_bot.setup(
                color="BLUE",
                width=self.config.width,
                height=self.config.height,
            )

        if isinstance(blue_setup, str):
            blue_setup = self.parse_setup(blue_setup)

        red_total = sum(self.config.p1_pieces_num)
        blue_total = sum(self.config.p2_pieces_num)

        if red_total != blue_total:
            raise ValueError("Red and Blue setups must have the same number of pieces.")
        elif red_total != len(red_setup) * len(red_setup[0]) or blue_total != len(blue_setup) * len(blue_setup[0]):
            raise ValueError("Red and Blue setups must match the board dimensions.")
        
        red_turn = blue_turn = 0
        for turn in range(red_total + blue_total):
            if (turn % 2 == 0 and red_turn < red_total) or blue_turn >= blue_total:
                if red_setup is not None:
                    action = self.setup_to_action(red_setup, Player.RED, red_turn)
                else:
                    action = self.env.action_space.sample()  # Random action if no setup provided
                self.env.step(action)
                red_turn += 1
            else:
                if blue_setup is not None:
                    action = self.setup_to_action(blue_setup, Player.BLUE, blue_turn)
                else:
                    action = self.env.action_space.sample()  # Random action if no setup provided
                self.env.step(action)
                blue_turn += 1

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

    def board_to_str(self):
        pass
