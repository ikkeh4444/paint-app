import base64
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog

from pngio import decode_png, encode_png

PALETTE = [
    "#000000", "#ffffff", "#e53935", "#fb8c00", "#fdd835",
    "#43a047", "#1e88e5", "#8e24aa", "#6d4c41", "#90a4ae",
]
BACKGROUND = "#ffffff"
MAX_UNDO = 25
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
VIEW_MAX_WIDTH = 1000
VIEW_MAX_HEIGHT = 650


def hex_to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


class PaintApp:
    def __init__(self, root):
        self.root = root
        root.title("Paint App")
        self.width = DEFAULT_WIDTH
        self.height = DEFAULT_HEIGHT
        self.buf = bytearray(self.width * self.height * 3)
        self._fill(hex_to_rgb(BACKGROUND))
        self.path = None
        self.color = PALETTE[0]
        self.size = 6
        self.drawing = False
        self.last = None
        self.undo_stack = []
        self.base_img = None
        self._build_toolbar()
        self._build_status()
        self._build_canvas()
        self._bind()
        self._rebuild()

    def _fill(self, rgb):
        self.buf[:] = bytes(rgb) * (self.width * self.height)

    def _stroke_color(self):
        return BACKGROUND if self.eraser_var.get() else self.color

    def _build_toolbar(self):
        bar = tk.Frame(self.root)
        bar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(bar, text="New", command=self.new_image).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(bar, text="Open PNG...", command=self.open_file).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="Save As...", command=self.save_as).pack(side=tk.LEFT, padx=2)
        tk.Label(bar, text="Color").pack(side=tk.LEFT, padx=(8, 2))
        self.color_btn = tk.Button(bar, text="  ", bg=self.color, width=3, command=self.choose_color)
        self.color_btn.pack(side=tk.LEFT)
        for c in PALETTE:
            tk.Button(bar, text="  ", bg=c, width=2,
                      command=lambda c=c: self._set_color(c)).pack(side=tk.LEFT, padx=1)
        tk.Label(bar, text="Size").pack(side=tk.LEFT, padx=(8, 2))
        self.size_scale = tk.Scale(bar, from_=1, to=60, orient=tk.HORIZONTAL,
                                   command=lambda v: setattr(self, "size", int(v)))
        self.size_scale.set(self.size)
        self.size_scale.pack(side=tk.LEFT)
        self.eraser_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="Eraser", variable=self.eraser_var).pack(side=tk.LEFT, padx=(8, 2))
        self.undo_btn = tk.Button(bar, text="Undo", command=self.undo, state=tk.DISABLED)
        self.undo_btn.pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=2)

    def _build_status(self):
        self.status = tk.Label(self.root, text="", anchor="w")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_canvas(self):
        frame = tk.Frame(self.root)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(frame, bg=BACKGROUND, highlightthickness=0,
                                width=min(self.width, VIEW_MAX_WIDTH),
                                height=min(self.height, VIEW_MAX_HEIGHT))
        hbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _bind(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())

    def _set_color(self, c):
        self.color = c
        self.color_btn.config(bg=c)

    def choose_color(self):
        result = colorchooser.askcolor(self.color)
        if result and result[1]:
            self._set_color(result[1])

    def new_image(self):
        w = simpledialog.askinteger("New image", "Width:", parent=self.root,
                                    initialvalue=self.width, minvalue=16, maxvalue=4096)
        if w is None:
            return
        h = simpledialog.askinteger("New image", "Height:", parent=self.root,
                                    initialvalue=self.height, minvalue=16, maxvalue=4096)
        if h is None:
            return
        self._push_undo()
        self.width, self.height = w, h
        self.buf = bytearray(w * h * 3)
        self._fill(hex_to_rgb(BACKGROUND))
        self.path = None
        self._rebuild()

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open PNG", filetypes=[("PNG images", "*.png"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "rb") as f:
                w, h, rgb = decode_png(f.read())
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))
            return
        self._push_undo()
        self.width, self.height, self.buf = w, h, rgb
        self.path = path
        self._rebuild()

    def save_file(self):
        if not self.path:
            return self.save_as()
        self._write(self.path)

    def save_as(self):
        path = filedialog.asksaveasfilename(
            title="Save as PNG", defaultextension=".png",
            filetypes=[("PNG images", "*.png")])
        if not path:
            return
        self.path = path
        self._write(path)

    def _write(self, path):
        try:
            with open(path, "wb") as f:
                f.write(encode_png(self.width, self.height, self.buf))
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self._update_status()

    def _push_undo(self):
        self.undo_stack.append(encode_png(self.width, self.height, self.buf))
        if len(self.undo_stack) > MAX_UNDO:
            self.undo_stack.pop(0)
        self.undo_btn.config(state=tk.NORMAL)

    def undo(self):
        if not self.undo_stack:
            return
        data = self.undo_stack.pop()
        self.width, self.height, self.buf = decode_png(data)
        self.undo_btn.config(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        self._rebuild()

    def clear(self):
        self._push_undo()
        self._fill(hex_to_rgb(BACKGROUND))
        self._rebuild()

    def _rebuild(self):
        self.canvas.delete("all")
        png = encode_png(self.width, self.height, self.buf)
        self.base_img = tk.PhotoImage(data=base64.b64encode(png))
        self.canvas.create_image(0, 0, anchor="nw", image=self.base_img)
        self.canvas.config(scrollregion=(0, 0, self.width, self.height),
                           width=min(self.width, VIEW_MAX_WIDTH),
                           height=min(self.height, VIEW_MAX_HEIGHT))
        self._update_status()

    def _update_status(self, pos=None):
        name = self.path if self.path else "untitled"
        text = f"{name}  |  {self.width}x{self.height}"
        if pos:
            text += f"  |  ({pos[0]}, {pos[1]})"
        self.status.config(text=text)

    def _on_hover(self, e):
        x = int(self.canvas.canvasx(e.x))
        y = int(self.canvas.canvasy(e.y))
        if 0 <= x < self.width and 0 <= y < self.height:
            self._update_status((x, y))

    def _on_press(self, e):
        x = int(self.canvas.canvasx(e.x))
        y = int(self.canvas.canvasy(e.y))
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        self._push_undo()
        self.drawing = True
        self.last = (x, y)
        r = self.size / 2.0
        color = self._stroke_color()
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color)
        self._stamp(x, y)

    def _on_motion(self, e):
        if not self.drawing:
            return
        x = int(self.canvas.canvasx(e.x))
        y = int(self.canvas.canvasy(e.y))
        color = self._stroke_color()
        self.canvas.create_line(self.last[0], self.last[1], x, y,
                                fill=color, width=self.size,
                                capstyle=tk.ROUND, joinstyle=tk.ROUND)
        self._stamp_line(self.last[0], self.last[1], x, y)
        self.last = (x, y)

    def _on_release(self, e):
        self.drawing = False

    def _stamp_line(self, x0, y0, x1, y1):
        dist = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        step = max(1.0, self.size / 4.0)
        n = max(1, int(dist / step))
        for i in range(n + 1):
            t = i / n
            self._stamp(int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)))

    def _stamp(self, cx, cy):
        r = self.size / 2.0
        ri = int(r)
        c = hex_to_rgb(self._stroke_color())
        w, h, buf = self.width, self.height, self.buf
        for dy in range(-ri, ri + 1):
            y = cy + dy
            if y < 0 or y >= h:
                continue
            dx = int((r * r - dy * dy) ** 0.5)
            row = y * w * 3
            for x in range(max(0, cx - dx), min(w, cx + dx + 1)):
                i = row + x * 3
                buf[i] = c[0]
                buf[i + 1] = c[1]
                buf[i + 2] = c[2]


def main():
    root = tk.Tk()
    PaintApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
