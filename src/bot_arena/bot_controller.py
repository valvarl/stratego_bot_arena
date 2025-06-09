import subprocess
import select
import time

class BotController:
    def __init__(self, bot_path, name: str):
        """
        Initialize the bot controller.

        :param bot_path: Path to the bot's executable file.
        :param name: Name of the bot.
        """
        self.process = subprocess.Popen(
            [bot_path], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        self.name = name
        self.process.stdin.flush()
        self.process.stdout.flush()

    def send(self, message):
        """
        Send a message to the bot via stdin.

        :param message: String to send.
        """
        self.process.stdin.write(message + '\n')
        self.process.stdin.flush()

    def read_lines(self, timeout=2):
        """
        Read a line from the bot's stdout with a timeout.

        :param timeout: Timeout duration in seconds.
        :return: The read line or None if timeout occurs.
        """
        rlist, _, _ = select.select([self.process.stdout], [], [], timeout)
        lines = []
        if rlist:
            for _ in range(4):  # Read up to 4 lines
                line = self.process.stdout.readline()
                lines.append(line.strip())
        return lines

    def setup(self, color, width, height):
        """
        Setup phase: Send color and board dimensions to the bot,
        and receive the initial piece placement.

        :param color: Bot's color ("RED" or "BLUE").
        :param width: Board width (10).
        :param height: Board height (10).
        :return: List of four strings representing the piece placement.
        """
        self.send(f"{color} {self.name} {width} {height}")
        rows = self.read_lines()
        if not rows:
            raise TimeoutError("Bot did not respond in time to setup request.")
        return '\n'.join(rows)

    def make_move(self, last_move, outcome, board_state):
        """
        Move phase: Send the result of the previous move and board state,
        and receive the bot's move and confirmation.

        :param last_move: Opponent's last move or "START" for the first move.
        :param outcome: Outcome of the previous move.
        :param board_state: List of 10 strings representing the board state.
        :return: Tuple (bot's move, confirmation).
        """
        self.send(f"{last_move} {outcome}")
        for row in board_state:
            self.send(row)
        move = self.read_lines()
        if move is None:
            raise TimeoutError("Bot did not respond in time to move request.")
        confirmation = self.read_lines()
        if confirmation is None:
            raise TimeoutError("Bot did not respond in time to move confirmation.")
        return move, confirmation

    def end_game(self):
        """
        End game phase: Send the end game signal and terminate the bot process.
        """
        self.send("QUIT")
        self.process.terminate()

    def surrender(self):
        """
        Send the surrender command.
        """
        self.send("SURRENDER")

    # def __del__(self):
    #     """
    #     Destructor: Terminate the bot process when the object is deleted.
    #     """
    #     self.process.terminate()