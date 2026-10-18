"""Click two points on a floor plan to calibrate or estimate a distance."""

import argparse
from datetime import datetime
import math
from pathlib import Path
import re
import statistics
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk


def parse_distance(text):
    """Return meters; accept meters, feet/inches, or inches alone."""
    text = text.strip().lower().replace("′", "'").replace("’", "'")
    text = text.replace("″", '"').replace("''", '"')
    number = r"(\d+(?:\.\d*)?|\.\d+)"
    meters = re.fullmatch(number + r"\s*m", text)
    imperial = re.fullmatch(
        r"(?:" + number + r"\s*'\s*)?(?:" + number + r'\s*")?', text
    )
    if meters:
        value = float(meters[1])
    elif imperial and any(imperial.groups()):
        feet, inches = imperial.groups()
        value = (float(feet or 0) * 12 + float(inches or 0)) * 0.0254
    else:
        raise ValueError("Use 10'11'' for feet/inches, 24'' for inches, or 10.2m.")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Distance must be a positive, finite number.")
    return value


def format_distance(meters):
    total_inches = round(meters / 0.0254, 1)
    feet = int(total_inches // 12)
    inches = total_inches - feet * 12
    return f"{meters:.3f} m / {feet}'{inches:.1f}''"


def scale_color(deviation):
    if abs(deviation) <= 0.05:
        return "#17803d"
    if abs(deviation) <= 0.10:
        return "#b56700"
    return "#cc3030"


class MeasureApp:
    def __init__(self, root, path):
        self.root = root
        self.image_stem = path.stem
        self.panning = False
        with Image.open(path) as source:
            self.original = ImageOps.exif_transpose(source).convert("RGB")
        self.zoom = 1.0
        self.points = []
        self.records = []
        root.title(f"Room measurements — {path.name}")
        root.geometry("1100x850")

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        heading = ttk.Frame(top)
        heading.pack(fill="x")
        modes = ttk.Frame(heading)
        modes.pack(side="right")
        self.line_mode = tk.StringVar(value="Free")
        ttk.Label(modes, text="Line: ").pack(side="left")
        for mode in ("Free", "Horizontal", "Vertical"):
            ttk.Radiobutton(modes, text=mode, value=mode, variable=self.line_mode).pack(side="left")
        ttk.Label(heading, text="Click two endpoints. Enter a known distance, or leave blank to estimate.").pack(side="left")
        row = ttk.Frame(top)
        row.pack(fill="x", pady=6)
        self.entry = ttk.Entry(row, width=22)
        self.entry.pack(side="left")
        self.entry.bind("<Return>", self.submit)
        ttk.Button(row, text="Add / Measure (Enter)", command=self.submit).pack(side="left", padx=5)
        ttk.Button(row, text="Cancel points (Esc)", command=self.cancel).pack(side="left")
        ttk.Button(row, text="Undo (Ctrl+Z)", command=self.undo).pack(side="left", padx=5)
        ttk.Button(row, text="Clear all", command=self.clear).pack(side="left")
        ttk.Button(row, text="Fit image", command=self.fit).pack(side="left", padx=5)
        ttk.Button(row, text="Save image (Ctrl+P)", command=self.export).pack(side="left")
        ttk.Label(top, text="Examples: 10'11''   24''   10.2m     |     Wheel: zoom   •   Shift + left-drag or right-drag: pan").pack(anchor="w")

        self.summary = ttk.Label(root, padding=(8, 4))
        self.summary.pack(fill="x")
        self.status = ttk.Label(root, padding=(8, 4), text="Select the first endpoint.")
        self.status.pack(fill="x")
        body = ttk.Panedwindow(root, orient="horizontal")
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, background="#dedede", highlightthickness=0, confine=False)
        body.add(self.canvas, weight=4)
        sidebar = ttk.Frame(body, padding=6)
        body.add(sidebar, weight=1)
        ttk.Label(sidebar, text="Distances / scale difference").pack(anchor="w")
        self.history = tk.Listbox(sidebar, width=43, activestyle="none")
        self.history.pack(fill="both", expand=True)
        ttk.Label(sidebar, text="Known: green ≤5%, orange ≤10%, red >10%\nEstimates: blue; update with the average\nOne known distance cannot reveal distortion.\nAll values are kept in memory only.", justify="left").pack(anchor="w", pady=8)
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<Shift-ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.drag_pan)
        self.canvas.bind("<ButtonRelease-1>", self.end_pan)
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Button-4>", lambda e: self.wheel(e, 1.2))
        self.canvas.bind("<Button-5>", lambda e: self.wheel(e, 1 / 1.2))
        self.canvas.bind("<ButtonPress-3>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B3-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        root.bind("<Escape>", self.cancel)
        root.bind("<Control-z>", self.undo)
        root.bind("<Control-Z>", self.undo)
        root.bind("<Control-p>", self.export)
        root.bind("<Control-P>", self.export)
        root.after(100, self.fit)

    def average_scale(self):
        scales = [r["meters"] / r["pixels"] for r in self.records if r["meters"] is not None]
        return statistics.mean(scales) if scales else None

    def start_pan(self, event):
        self.panning = True
        self.canvas.configure(cursor="fleur")
        self.canvas.scan_mark(event.x, event.y)
        return "break"

    def drag_pan(self, event):
        if self.panning:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            return "break"

    def end_pan(self, event):
        self.panning = False
        self.canvas.configure(cursor="")

    def fit(self):
        self.zoom = min(
            max(1, self.canvas.winfo_width() - 20) / self.original.width,
            max(1, self.canvas.winfo_height() - 20) / self.original.height,
        )
        self.render_image()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def render_image(self):
        size = (max(1, round(self.original.width * self.zoom)), max(1, round(self.original.height * self.zoom)))
        self.photo = ImageTk.PhotoImage(self.original.resize(size, Image.Resampling.LANCZOS))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, *size))
        self.refresh()

    def wheel(self, event, factor=None):
        factor = factor or (1.2 if event.delta > 0 else 1 / 1.2)
        x, y = self.canvas.canvasx(event.x) / self.zoom, self.canvas.canvasy(event.y) / self.zoom
        self.zoom = max(0.05, min(5.0, self.zoom * factor))
        self.render_image()
        self.canvas.xview_moveto((x * self.zoom - event.x) / self.photo.width())
        self.canvas.yview_moveto((y * self.zoom - event.y) / self.photo.height())

    def click(self, event):
        x = self.canvas.canvasx(event.x) / self.zoom
        y = self.canvas.canvasy(event.y) / self.zoom
        if not (0 <= x < self.original.width and 0 <= y < self.original.height):
            return
        if len(self.points) == 2:
            self.points = []
        if len(self.points) == 1:
            if self.line_mode.get() == "Horizontal":
                y = self.points[0][1]
            elif self.line_mode.get() == "Vertical":
                x = self.points[0][0]
        self.points.append((x, y))
        if len(self.points) == 2:
            pixels = math.dist(*self.points)
            if pixels < 1:
                self.points.pop()
                self.status.config(text="Endpoints must be at least one image pixel apart.")
            else:
                scale = self.average_scale()
                estimate = f"Estimate: {format_distance(pixels * scale)}. " if scale else "No scale yet. "
                self.status.config(text=estimate + "Enter a known distance, or press Enter with an empty field to measure.")
                self.entry.focus_set()
        else:
            self.status.config(text="Select the second endpoint.")
        self.refresh()

    def submit(self, event=None):
        if len(self.points) != 2:
            self.status.config(text="Select two endpoints first.")
            return
        text = self.entry.get().strip()
        try:
            meters = parse_distance(text) if text else None
        except ValueError as error:
            self.status.config(text=str(error))
            return
        if meters is None and self.average_scale() is None:
            self.status.config(text="Enter at least one known distance before estimating.")
            return
        self.records.append(dict(points=self.points[:], pixels=math.dist(*self.points), meters=meters))
        self.points = []
        self.entry.delete(0, "end")
        self.refresh()
        self.status.config(text="Saved. Select two more endpoints.")

    def draw_segment(self, points, color, label):
        coords = [value * self.zoom for point in points for value in point]
        self.canvas.create_line(*coords, fill=color, width=2, tags="overlay")
        for x, y in zip(coords[::2], coords[1::2]):
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="white", tags="overlay")
        x, y = (coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2
        self.canvas.create_text(x + 6, y - 9, text=label, fill=color, anchor="sw", font=("Arial", 11, "bold"), tags="overlay")

    def refresh(self):
        self.canvas.delete("overlay")
        self.history.delete(0, "end")
        average = self.average_scale()
        count = sum(r["meters"] is not None for r in self.records)
        summary = f"Average scale: {average:.6f} m/pixel — {count} known distances" if average else "No scale — add a known distance."
        self.summary.config(text=summary)
        for index, record in enumerate(self.records, 1):
            known = record["meters"] is not None
            meters = record["meters"] if known else record["pixels"] * average
            deviation = (meters / record["pixels"]) / average - 1 if known else 0
            color = scale_color(deviation) if known else "#2455ce"
            suffix = f" ({deviation:+.1%})" if known else " (estimate)"
            self.history.insert("end", f"{index}: {format_distance(meters)}{suffix}")
            self.history.itemconfig("end", foreground=color)
            self.draw_segment(record["points"], color, str(index))
        if len(self.points) == 1:
            x, y = (v * self.zoom for v in self.points[0])
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#7c3aed", tags="overlay")
        elif len(self.points) == 2:
            self.draw_segment(self.points, "#7c3aed", "?")

    def cancel(self, event=None):
        self.points = []
        self.entry.delete(0, "end")
        self.status.config(text="Select the first endpoint.")
        self.refresh()

    def undo(self, event=None):
        if self.points:
            self.points.pop()
            self.status.config(text="Removed last endpoint. " + (
                "Select the second endpoint." if self.points else "Select the first endpoint."
            ))
        elif self.records:
            self.records.pop()
            self.status.config(text="Removed last saved measurement. Select the first endpoint.")
        else:
            self.status.config(text="Nothing to undo.")
        self.refresh()
        return "break"

    def annotated_image(self):
        """Render at source resolution, independently of the current view."""
        result = self.original.copy()
        draw = ImageDraw.Draw(result)
        font = ImageFont.load_default(size=max(12, round(min(result.size) / 55)))
        average = self.average_scale()
        labels = []
        for index, record in enumerate(self.records, 1):
            known = record["meters"] is not None
            meters = record["meters"] if known else record["pixels"] * average
            deviation = meters / record["pixels"] / average - 1 if known else 0
            color = scale_color(deviation) if known else "#2455ce"
            points = record["points"]
            draw.line(points, fill=color, width=3)
            for x, y in points:
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color, outline="white")
            suffix = f" ({deviation:+.1%})" if known else " (estimate)"
            label = f"{index}: {meters:.3f} m{suffix}"
            box = draw.textbbox((0, 0), label, font=font)
            width, height = box[2] - box[0] + 8, box[3] - box[1] + 8
            x = max(0, min((points[0][0] + points[1][0]) / 2, result.width - width))
            y = max(0, min((points[0][1] + points[1][1]) / 2 - height - 5, result.height - height))
            labels.append((x, y, width, height, label, color, box))
        # Draw text after all lines so later segments cannot cross out labels.
        for x, y, width, height, label, color, box in labels:
            draw.rectangle((x, y, x + width, y + height), fill="white", outline=color)
            draw.text((x + 4 - box[0], y + 4 - box[1]), label, fill=color, font=font)
        return result

    def export(self, event=None):
        if not self.records:
            self.status.config(text="Add a distance before saving an annotated image.")
            return "break"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = Path(__file__).with_name(f"{self.image_stem}_annotated_{stamp}.png")
        try:
            self.annotated_image().save(path)
        except OSError as error:
            self.status.config(text=f"Could not save image: {error}")
        else:
            self.status.config(text=f"Saved: {path}")
        return "break"

    def clear(self):
        self.records.clear()
        self.cancel()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", type=Path, default=Path(__file__).with_name("room_pic.png"))
    args = parser.parse_args()
    root = tk.Tk()
    try:
        MeasureApp(root, args.image)
    except (OSError, ValueError) as error:
        root.withdraw()
        messagebox.showerror("Cannot open image", str(error), parent=root)
        root.destroy()
        parser.exit(1, f"Cannot open image: {error}\n")
    root.mainloop()


if __name__ == "__main__":
    main()
