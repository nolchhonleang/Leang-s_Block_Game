import tkinter as tk
from tkinter import ttk, messagebox
import random
import os
import json

# ─────────────────────────── Constants ───────────────────────────
GRID_WIDTH      = 20                     # number of columns
GRID_HEIGHT     = 30                     # number of rows
CELL_SIZE       = 20                     # pixel size of each square
START_SPEED     = 500                    # initial drop delay (ms)
LEVEL_UP_LINES  = 10                     # lines to clear before speed increases
COLORS          = ["#FF5733", "#33FF57", "#3357FF",
                   "#F1C40F", "#9B59B6", "#E67E22"]
# All the classic Tetris shapes, represented as 2D lists
SHAPES = [
    [[1, 1, 1, 1]],            # I-shape
    [[1, 1], [1, 1]],          # O-shape
    [[0, 1, 0], [1, 1, 1]],    # T-shape
    [[1, 0, 0], [1, 1, 1]],    # L-shape
    [[0, 0, 1], [1, 1, 1]],    # J-shape
    [[1, 1, 0], [0, 1, 1]],    # S-shape
    [[0, 1, 1], [1, 1, 0]]     # Z-shape
]
HIGH_SCORE_FILE = 'high_score.json'       # where we store the high score

class LeangsBlocks:
    def __init__(self, root):
        self.root = root
        self.root.title("Leang's Blocks")

        # Load high score from disk (or set to 0 if file missing)
        self.load_high_score()

        # Show a quick welcome/instructions dialog before anything else
        self.show_welcome()

        # Set up main container frame with some padding
        self.mainframe = ttk.Frame(self.root, padding=10)
        self.mainframe.pack(fill='both', expand=True)

        # ─── Game Canvas ───────────────────────────────────────────
        # Canvas where blocks will fall and be drawn
        self.canvas = tk.Canvas(
            self.mainframe,
            width=GRID_WIDTH * CELL_SIZE,
            height=GRID_HEIGHT * CELL_SIZE,
            bg='#222222'
        )
        self.canvas.grid(row=0, column=0, rowspan=6)

        # ─── Info Panel ────────────────────────────────────────────
        # Frame to hold score, level, next piece, etc.
        self.info_frame = ttk.Frame(self.mainframe)
        self.info_frame.grid(row=0, column=1, sticky='N', padx=10)

        # Variables for dynamic labels
        self.score_var      = tk.IntVar(value=0)
        self.level_var      = tk.IntVar(value=1)
        self.lines_var      = tk.IntVar(value=0)
        self.high_score_var = tk.IntVar(value=self.high_score)

        # Place labels in the info panel
        for txt, var in [
            ("Score:",      self.score_var),
            ("Level:",      self.level_var),
            ("Lines:",      self.lines_var),
            ("High Score:", self.high_score_var)
        ]:
            ttk.Label(self.info_frame, text=txt).pack(anchor='w', pady=(5, 0))
            ttk.Label(self.info_frame, textvariable=var).pack(anchor='w')

        # Next-piece preview
        ttk.Label(self.info_frame, text="Next:").pack(anchor='w', pady=(20, 0))
        self.next_canvas = tk.Canvas(
            self.info_frame,
            width=4 * CELL_SIZE,
            height=4 * CELL_SIZE,
            bg='#333333'
        )
        self.next_canvas.pack(pady=2)

        # ─── Controls ──────────────────────────────────────────────
        btn_frame = ttk.Frame(self.info_frame)
        btn_frame.pack(pady=(20, 0))
        self.start_pause_btn = ttk.Button(
            btn_frame, text="Start", command=self.toggle_start_pause
        )
        self.start_pause_btn.grid(row=0, column=0)
        self.restart_btn = ttk.Button(
            btn_frame, text="Restart", command=self.restart
        )
        self.restart_btn.grid(row=0, column=1, padx=5)

        # ─── Key Bindings ──────────────────────────────────────────
        self.root.bind('<Left>',  lambda e: self.move(-1))
        self.root.bind('<Right>', lambda e: self.move(1))
        self.root.bind('<Down>',  lambda e: self.drop())
        self.root.bind('<Up>',    lambda e: self.rotate())

        # ─── Internal State Flags ─────────────────────────────────
        self.running  = False    # is the game currently running?
        self.paused   = False    # is the game paused?
        self.speed    = START_SPEED
        self.after_id = None     # ID of the scheduled loop callback

    def show_welcome(self):
        """Modal dialog with title and basic instructions."""
        welcome = tk.Toplevel(self.root)
        welcome.title("Welcome")
        welcome.geometry("300x200")
        ttk.Label(welcome, text="Welcome to Leang's Blocks!",
                  font=('Arial', 14)).pack(pady=10)
        ttk.Label(welcome,
                  text="Arrange falling blocks to clear lines.\n"
                       "Use arrow keys to move and rotate,\n"
                       "and Down to drop.",
                  justify='center').pack(pady=5)
        ttk.Button(welcome, text="Play", command=welcome.destroy).pack(pady=15)
        welcome.transient(self.root)
        welcome.grab_set()
        self.root.wait_window(welcome)

    def load_high_score(self):
        """Read the high score from JSON file if it exists."""
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE) as f:
                data = json.load(f)
                self.high_score = data.get('high_score', 0)
        else:
            self.high_score = 0

    def save_high_score(self):
        """Write the current high score back to disk."""
        with open(HIGH_SCORE_FILE, 'w') as f:
            json.dump({'high_score': self.high_score}, f)

    def start_game(self):
        """Initialize or restart the game state and kick off the main loop."""
        # If a loop is already pending, cancel it
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.running = True
        self.paused  = False
        self.start_pause_btn.config(text="Pause")

        # Reset stats
        self.score_var.set(0)
        self.level_var.set(1)
        self.lines_var.set(0)
        self.speed = START_SPEED

        # Empty grid and new piece queue
        self.grid = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.queue = [self.random_piece() for _ in range(4)]

        # Spawn first piece & start loop
        self.new_piece()
        self.draw_all()
        self.loop()

    def toggle_start_pause(self):
        """Called by Start/Pause button or restart logic."""
        if not self.running:
            self.start_game()
        else:
            self.paused = not self.paused
            self.start_pause_btn.config(text="Resume" if self.paused else "Pause")

            # Cancel existing loop when pausing
            if self.paused and self.after_id is not None:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            # Resume loop when unpausing
            elif not self.paused:
                self.loop()

    def restart(self):
        """Stop current game and immediately start a fresh one."""
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.running = False
        self.paused  = False
        self.start_pause_btn.config(text="Start")
        self.start_game()

    def random_piece(self):
        """Return a randomly selected shape + color."""
        return {'shape': random.choice(SHAPES),
                'color': random.choice(COLORS)}

    def new_piece(self):
        """Move next piece from queue into active play; check for game over."""
        self.active = self.queue.pop(0)
        self.queue.append(self.random_piece())
        # Start position: top center
        self.x = GRID_WIDTH // 2 - len(self.active['shape'][0]) // 2
        self.y = 0

        # If we collide immediately, game over
        if self.collide():
            self.running = False
            messagebox.showinfo("Game Over", f"Score: {self.score_var.get()}")
            # Update persistent high score if beaten
            if self.score_var.get() > self.high_score:
                self.high_score = self.score_var.get()
                self.high_score_var.set(self.high_score)
                self.save_high_score()

    def rotate(self):
        """Rotate active piece 90° with basic wall-kick."""
        if not self.running or self.paused:
            return
        s = self.active['shape']
        rotated = list(zip(*s[::-1]))
        self.active['shape'] = rotated
        # If new orientation collides, revert
        if self.collide():
            self.active['shape'] = s
        self.draw_all()

    def move(self, dx):
        """Move piece left or right; dx = -1 (left) or +1 (right)."""
        if not self.running or self.paused:
            return
        self.x += dx
        if self.collide():
            self.x -= dx
        self.draw_all()

    def drop(self):
        """Soft-drop piece one row; lock if it collides."""
        if not self.running or self.paused:
            return
        self.y += 1
        if self.collide():
            self.y -= 1
            self.lock()
        self.draw_all()

    def collide(self):
        """Return True if active piece overlaps walls or filled cells."""
        for i, row in enumerate(self.active['shape']):
            for j, v in enumerate(row):
                if v:
                    x, y = self.x + j, self.y + i
                    if (x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT
                            or self.grid[y][x]):
                        return True
        return False

    def lock(self):
        """Lock active piece into grid, clear lines, spawn next."""
        s, c = self.active['shape'], self.active['color']
        # Write shape into grid
        for i, row in enumerate(s):
            for j, v in enumerate(row):
                if v:
                    self.grid[self.y + i][self.x + j] = c
        # Handle line clears, scoring, level up
        self.clear_lines()
        self.new_piece()
        self.update_level_speed()

    def clear_lines(self):
        """Remove any fully filled rows, shift above rows down, update score."""
        newg = [r for r in self.grid if any(v == 0 for v in r)]
        cleared = GRID_HEIGHT - len(newg)
        if cleared:
            # Add empty rows at top
            for _ in range(cleared):
                newg.insert(0, [0] * GRID_WIDTH)
            self.grid = newg
            # Score +100 per line
            new_score = self.score_var.get() + cleared * 100
            self.score_var.set(new_score)
            self.lines_var.set(self.lines_var.get() + cleared)
            # Update high score badge (but don’t save yet)
            if new_score > self.high_score:
                self.high_score = new_score
                self.high_score_var.set(self.high_score)

    def update_level_speed(self):
        """Adjust level and fall speed based on lines cleared."""
        lvl = self.lines_var.get() // LEVEL_UP_LINES + 1
        self.level_var.set(lvl)
        # Speed cannot drop below 50ms
        self.speed = max(50, START_SPEED - (lvl - 1) * 50)

    def loop(self):
        """Main game loop: drop piece and redraw, then reschedule itself."""
        if not self.running or self.paused:
            return

        # Move piece down one, or lock if colliding
        self.y += 1
        if self.collide():
            self.y -= 1
            self.lock()
        # Refresh canvas
        self.draw_all()
        # Schedule next iteration
        self.after_id = self.root.after(self.speed, self.loop)

    def draw_all(self):
        """Render the grid, the active piece, and the next-piece preview."""
        # Clear previous frame
        self.canvas.delete('all')
        # Draw locked cells
        for i, row in enumerate(self.grid):
            for j, v in enumerate(row):
                if v:
                    self.canvas.create_rectangle(
                        j * CELL_SIZE, i * CELL_SIZE,
                        (j + 1) * CELL_SIZE, (i + 1) * CELL_SIZE,
                        fill=v, outline='#111'
                    )
        # Draw active piece
        s, c = self.active['shape'], self.active['color']
        for i, row in enumerate(s):
            for j, v in enumerate(row):
                if v:
                    self.canvas.create_rectangle(
                        (self.x + j) * CELL_SIZE, (self.y + i) * CELL_SIZE,
                        (self.x + j + 1) * CELL_SIZE, (self.y + i + 1) * CELL_SIZE,
                        fill=c, outline='#fff'
                    )
        # Draw next piece in its small preview box
        self.next_canvas.delete('all')
        shape = self.queue[0]['shape']
        color = self.queue[0]['color']
        box_size = 4 * CELL_SIZE
        h, w = len(shape), len(shape[0])
        offset_x = (box_size - w * CELL_SIZE) // 2
        offset_y = (box_size - h * CELL_SIZE) // 2
        for i, row in enumerate(shape):
            for j, v in enumerate(row):
                if v:
                    self.next_canvas.create_rectangle(
                        offset_x + j * CELL_SIZE,
                        offset_y + i * CELL_SIZE,
                        offset_x + (j + 1) * CELL_SIZE,
                        offset_y + (i + 1) * CELL_SIZE,
                        fill=color, outline='#fff'
                    )

if __name__ == '__main__':
    root = tk.Tk()
    game = LeangsBlocks(root)
    root.mainloop()