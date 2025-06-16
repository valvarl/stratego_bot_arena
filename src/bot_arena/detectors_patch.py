# detectors_patch.py
"""
Подмена (monkey-patch) детекторов правил Stratego.
Все проверки validate_select / validate_move всегда возвращают True.
"""

from typing import Any, List, Tuple
from stratego.core.primitives import Piece, Player, Pos

# ─────────────────────────── ЗАГЛУШКИ ────────────────────────────
class _AlwaysValidChasingDetector:
    """Замена ChasingDetector: правила «догонялок» отключены."""
    def __init__(self, *_, **__):
        self.chase_moves: List[Any] = []

    def validate_select(
        self, player: Player, piece: Piece, pos: Pos, board=None
    ) -> Tuple[bool, None]:
        return True, None            # Всегда разрешаем выбор

    def validate_move(
        self, player: Player, piece: Piece,
        from_pos: Pos, to_pos: Pos, board=None
    ) -> bool:
        return True                  # Всегда разрешаем ход

    # Методы-заглушки для совместимости с интерфейсом движка
    def update(self, *_, **__):      # type: ignore[no-self-use]
        pass

    def reset(self):
        self.chase_moves.clear()


class _AlwaysValidTwoSquareDetector:
    """Замена TwoSquareDetector: правило «двух клеток» отключено."""
    def __init__(self, *_, **__):
        self.p1: List[Any] = []
        self.p2: List[Any] = []

    def validate_select(
        self, player: Player, piece: Piece, pos: Pos
    ) -> Tuple[bool, None]:
        return True, None            # Всегда разрешаем выбор

    def validate_move(
        self, player: Player, piece: Piece,
        from_pos: Pos, to_pos: Pos
    ) -> bool:
        return True                  # Всегда разрешаем ход

    def update(self, *_, **__):       # type: ignore[no-self-use]
        pass

    def reset(self):
        self.p1.clear()
        self.p2.clear()

# ───────────────────── УСТАНАВЛИВАЕМ ПАТЧ ────────────────────────
# В разных версиях Stratego детекторы могут лежать в разных модулях,
# поэтому пробуем про-патчить несколько возможных мест.
for _mod_name in (
    "stratego.core.detectors",
    "stratego.core.stratego",
):
    try:
        _m = __import__(_mod_name, fromlist=["dummy"])
    except ModuleNotFoundError:
        continue

    setattr(_m, "ChasingDetector", _AlwaysValidChasingDetector)
    setattr(_m, "TwoSquareDetector", _AlwaysValidTwoSquareDetector)

# После `import detectors_patch`:
#     env = make_env()     # все правила будут считаться выполненными
