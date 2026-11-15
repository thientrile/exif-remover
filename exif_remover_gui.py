"""Exif Remover window: pick folders/files, Run, read the log. With arguments it runs the CLI instead."""
import contextlib
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext

import exif_remover as er

FILETYPES = [("Images, video, PDF", " ".join("*" + e for e in sorted(er.SUPPORTED))), ("All files", "*.*")]


class ToQueue:
    """File-like object: the worker's print() lines go to the UI thread through a queue."""

    def __init__(self, q):
        self.q = q

    def write(self, s):
        self.q.put(s)

    def flush(self):
        pass


def work(args, q):
    with contextlib.redirect_stdout(ToQueue(q)), contextlib.redirect_stderr(ToQueue(q)):
        try:
            code = er.main(args)
        except Exception as e:  # never leave the window stuck in "running"
            print(f"FAILED: {e}")
            code = 2
    q.put(code)


def app(initial=(), on_done=None):
    """initial: paths to pre-fill; on_done(root): if given, Run starts at once and this is called when it ends."""
    root = tk.Tk()
    root.title("Exif Remover")
    root.minsize(680, 460)
    q = queue.Queue()

    top = tk.Frame(root)
    top.pack(fill="x", padx=8, pady=(8, 4))
    paths = tk.Listbox(root, height=6, selectmode="extended")
    paths.pack(fill="x", padx=8)

    def add(items):
        for p in items:
            if p and p not in paths.get(0, "end"):
                paths.insert("end", p.replace("/", "\\") if sys.platform == "win32" else p)

    def remove():
        for i in reversed(paths.curselection()):
            paths.delete(i)

    tk.Button(top, text="Add folder", command=lambda: add([filedialog.askdirectory()])).pack(side="left")
    tk.Button(top, text="Add files", command=lambda: add(filedialog.askopenfilenames(filetypes=FILETYPES))).pack(side="left", padx=4)
    tk.Button(top, text="Remove", command=remove).pack(side="left")

    opts = tk.Frame(root)
    opts.pack(fill="x", padx=8, pady=4)
    backup = tk.BooleanVar(value=True)
    tk.Checkbutton(opts, text="Make backup (copy each folder to <folder>_backup-YYYY-MM-DD first)",
                   variable=backup).pack(side="left")
    run_btn = tk.Button(opts, text="Run", width=12)
    run_btn.pack(side="right")

    log = scrolledtext.ScrolledText(root, height=16, state="disabled", font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=8)
    status = tk.Label(root, text="Add folders or files, then Run. Files are cleaned in place.", anchor="w",
                      font=("Segoe UI", 11, "bold"))
    status.pack(fill="x", padx=8, pady=8)

    def write(text):
        log.configure(state="normal")
        log.insert("end", text)
        log.see("end")
        log.configure(state="disabled")

    def poll():
        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, int):  # worker finished with this exit code
                run_btn.configure(state="normal")
                ok = item == 0
                status.configure(text="OK: all files cleaned and verified" if ok else "FAILED: see the log",
                                 fg="dark green" if ok else "red")
                if on_done:
                    on_done(root)
                return
            write(item)
        root.after(100, poll)

    def start():
        items = list(paths.get(0, "end"))
        if not items:
            status.configure(text="Add at least one folder or file first.", fg="red")
            return
        run_btn.configure(state="disabled")
        status.configure(text="Running...", fg="black")
        log.configure(state="normal")
        log.delete("1.0", "end")
        log.configure(state="disabled")
        args = ([] if backup.get() else ["--no-backup"]) + items
        threading.Thread(target=work, args=(args, q), daemon=True).start()
        root.after(100, poll)

    run_btn.configure(command=start)
    add(initial)
    if on_done:
        root.after(300, start)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(er.main(sys.argv[1:]))  # CLI mode, also used by the CI smoke test
    app()
