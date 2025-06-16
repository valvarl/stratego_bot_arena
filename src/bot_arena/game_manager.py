from __future__ import annotations

import logging
import time
from typing import Optional

import gymnasium as gym
import numpy as np
from stratego import (
    StrategoConfigBase,
    StrategoConfig,
    StrategoConfigCpp,
    Piece,
    Player,
)

from .bot_controller import BotController
from .utils import  detectors_patch
from .utils.move_parser import (
    parse_move,
    parse_setup,
    setup_to_action,
    src_dest_from_move,
    TOKEN_TO_PIECE,
)


logger = logging.getLogger(__name__)


class GameManager:

    piece_to_token = {v: k for k, v in TOKEN_TO_PIECE.items()}

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
        self._log = open(log_file, "w", encoding="utf-8") if log_file else None

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
            red_setup = parse_setup(red_setup)

        if self.blue_bot is not None:
            raw_blue = self.blue_bot.setup(
                color="BLUE",
                width=self.config.width,
                height=self.config.height,
                opponent=self.red_bot.name if self.red_bot else "bot",
            )
            blue_setup = raw_blue

        if isinstance(blue_setup, str):
            blue_setup = parse_setup(blue_setup)
            blue_setup = [row[::-1] for row in blue_setup]

        red_total = sum(self.config.p1_pieces_num)
        blue_total = sum(self.config.p2_pieces_num)

        if self._log is None:
            logger.debug("Red setup: %s", red_setup)
            logger.debug("Blue setup: %s", blue_setup)

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
                    action = setup_to_action(red_setup, red_turn, self.config.p1_pieces)
                    action = (10 - action[1] - 1, 10 - action[0] - 1)
                else:
                    action = self.env.action_space.sample()  # Random action if no setup provided
                self.env.step(action)
                red_turn += 1
            else:
                if blue_setup is not None:
                    action = setup_to_action(blue_setup, blue_turn, self.config.p2_pieces)
                    action = (6 + action[1], 10 - action[0] - 1)
                else:
                    action = self.env.action_space.sample()  # Random action if no setup provided

                self.env.step(action)
                blue_turn += 1

        return raw_red, raw_blue

    def board_to_str(self, reveal: Player):
        board = self.env.board
        lines = []
        for r in range(board.shape[0]):
            row_chars = []
            for c in range(board.shape[1]):
                val = int(board[r, c])
                if val == Piece.EMPTY.value:
                    row_chars.append(".")
                elif val == Piece.LAKE.value or val == -Piece.LAKE.value:
                    row_chars.append("+")
                elif val > 0:
                    row_chars.append(self.piece_to_token.get(Piece(val), "?"))
                else:
                    row_chars.append("#")
            lines.append("".join(row_chars))

        if reveal == Player.RED:
            lines = [row[::-1] for row in lines[::-1]]

        return lines

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

    def _get_move_from_human(self):
        return input("Enter move (x y DIRECTION [MULT]) or SURRENDER: ")

    def run(
        self,
        red_setup: str | list[list[Piece]] | None = None,
        blue_setup: str | list[list[Piece]] | None = None,
    ):
        """Play a full game between the configured controllers.

        This version adds explicit handling of the *two‑square rule*.
        If a player violates the rule they receive *one* chance to pick
        another move; on a second consecutive violation they immediately
        lose by *ILLEGAL*.
        """

        # ---------------------------------------------------------------------
        #  INITIAL SET‑UP (unchanged)
        # ---------------------------------------------------------------------
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

        last_move: tuple[int, int, str, int] | None = None
        last_player: Player | None = None
        outcome = "OK"
        terminated = False
        turn_num = 1

        # ------------------------------------------------------------------
        #  NEW : per‑player retry counter for two‑square rule infractions
        # ------------------------------------------------------------------
        two_square_retries = {Player.RED: 0, Player.BLUE: 0}

        while not terminated:
            if self.render_mode == "human":
                time.sleep(0.2)
                self.env.render()

            player: Player = self.env.player
            board_lines = self.board_to_str(player)
            controller = self.red_bot if player == Player.RED else self.blue_bot

            # ------------------------------------------------------------------
            #  NEW : If the *current* player already committed a two‑square
            #  violation on the immediately preceding attempt, we must tell
            #  them that the opponent made *NO_MOVE*.
            # ------------------------------------------------------------------
            if two_square_retries[player] == 1:
                msg = "NO_MOVE"
            else:
                msg = self._move_to_str(last_move) if last_move is not None else "START"

            # ------------------------------------------------------------------
            #  SOLICIT MOVE
            # ------------------------------------------------------------------
            if controller is not None:
                move_str = controller.request_move(msg, outcome, board_lines)
            else:
                print("Last move:", msg, outcome)
                for line in board_lines:
                    print(line)
                move_str = self._get_move_from_human()

            if self._log is None:
                # console debug
                logger.info(
                    "Move from %s: %s",
                    "Red" if player == Player.RED else "Blue",
                    move_str,
                )

            parsed = parse_move(move_str)
            if parsed in {"SURRENDER", "QUIT"}:
                outcome = "SURRENDER"
                terminated = True
                break
            if parsed == "NO_MOVE" or parsed is None:
                outcome = "ILLEGAL"
                terminated = True
                break

            # --------------------------------------------------------------
            #  Convert the textual move into *src* and *dst* indices
            # --------------------------------------------------------------
            src, dst = src_dest_from_move(*parsed, player, self.config.height, self.config.width)

            # 1) SOURCE SQUARE MUST CONTAIN A SELECTABLE PIECE
            valid_select = self.env.valid_pieces_to_select()[src]
            if not valid_select:
                outcome = "ILLEGAL"
                terminated = True
                break

            # --------------------------------------------------------------
            # 2) TWO‑SQUARE RULE CHECK (performed *before* modifying env).
            # --------------------------------------------------------------
            two_square_ok = self.env.two_square_detector.validate_move(
                player, Piece(self.env.board[src]), src, dst
            )
            if not two_square_ok:
                # First or second consecutive violation?
                two_square_retries[player] += 1
                outcome = "ILLEGAL"

                # Tell the (still current) controller that their move failed.
                if controller is not None:
                    controller.confirm_result(move_str, outcome)

                # Logging of the illegal attempt
                if self._log:
                    color_str = "RED" if player == Player.RED else "BLU"
                    self._log.write(
                        f"{turn_num} {color_str}: {self._move_to_str(parsed)} {outcome} (2‑square)\n"
                    )

                # Second consecutive violation ‑> game over.
                if two_square_retries[player] >= 2:
                    terminated = True
                else:
                    # Give the same player another chance.  The opponent will
                    # subsequently see *NO_MOVE*.
                    outcome = "OK"  # protocol requires some outcome for next prompt
                    # Do *not* advance the turn counter because the move was not executed.
                    continue

            # The move passed the two‑square rule, so clear any outstanding retry flag.
            two_square_retries[player] = 0

            # --------------------------------------------------------------
            # 3) PROCEED WITH THE NORMAL TWO‑STEP MOVE SELECTION
            # --------------------------------------------------------------
            self.env.step(src)
            if self.env.valid_destinations()[dst]:
                before = self.env.board.copy()
                obs, reward, term, trunc, info = self.env.step(dst)
                after = np.rot90(self.env.board, 2) * -1
                outcome = self._compute_outcome(before, after, src, dst)
                terminated = term or trunc
                last_move = parsed
                last_player = player
            else:
                # destination itself illegal for some other reason
                outcome = "ILLEGAL"
                terminated = True

            # --------------------------------------------------------------
            # 4) LOGGING + TURN ACCOUNTING
            # --------------------------------------------------------------
            if self._log is None:
                logger.info("Outcome: %s", outcome)

            if self._log:
                color_str = "RED" if player == Player.RED else "BLU"
                self._log.write(
                    f"{turn_num} {color_str}: {self._move_to_str(parsed)} {outcome}\n"
                )
                turn_num += 1

            # Inform the controller about the outcome of *its own* move.
            if controller is not None and not terminated:
                controller.confirm_result(self._move_to_str(last_move), outcome)

        # ------------------------------------------------------------------
        #  GAME HAS ENDED
        # ------------------------------------------------------------------
        if self._log is None:
            logger.info("Game ended with outcome: %s", outcome)

        red_remaining = int(
            np.sum((self.env.board > 0) & (self.env.board != Piece.LAKE.value))
        )
        blue_remaining = int(
            np.sum((self.env.board < 0) & (self.env.board != -Piece.LAKE.value))
        )

        if self._log:
            winner = "RED" if last_player == Player.RED else "BLUE"
            winner_path = self.red_bot.path if last_player == Player.RED else self.blue_bot.path
            self._log.write(
                f"{winner_path} {winner} VICTORY {turn_num-1} {red_remaining} {blue_remaining}\n"
            )

        if self.red_bot is not None:
            self.red_bot.end_game(outcome)
        if self.blue_bot is not None:
            self.blue_bot.end_game(outcome)

        if self._log is not None:
            self._log.close()
