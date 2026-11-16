"""Exif Remover window (customtkinter, Vietnamese UI). With arguments it runs the CLI instead."""
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

import customtkinter as ctk

import backups as bk
import exif_remover as er
import updater

try:  # drag and drop is a nicety; the buttons work without it
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

FILETYPES = [("Ảnh, video, PDF", " ".join("*" + e for e in sorted(er.SUPPORTED))), ("Tất cả", "*.*")]
KIND = {**{e: "Ảnh" for e in er.IMAGE_EXT}, **{e: "Video" for e in er.VIDEO_EXT}, ".pdf": "PDF"}
WAIT, BUSY, DONE, ERR, STOPPED = "•  Chờ", "…  Đang xoá", "✓  Đã xoá", "✗  Lỗi", "■  Đã dừng"
ACCENT, ACCENT_HOVER, STOP, STOP_HOVER = "#2563eb", "#1d4ed8", "#dc2626", "#b91c1c"
GREEN, RED, MUTED, AMBER = ("#15803d", "#4ade80"), ("#b91c1c", "#f87171"), ("#6b7280", "#9ca3af"), ("#b45309", "#fbbf24")
COUNT_BATCH = 8  # files per exiftool call when counting tags: one process start each, and rows fill in steadily


def asset(name):
    return os.path.join(er.HERE, "assets", name)


def ui_family(root):
    """A font with Vietnamese glyphs: Segoe UI on Windows, else the first installed fallback."""
    if sys.platform == "win32":
        return "Segoe UI"
    have = set(tkfont.families(root))
    return next((f for f in ("Noto Sans", "DejaVu Sans", "Liberation Sans") if f in have), "TkDefaultFont")


def shorten(path, n=64):
    return path if len(path) <= n else path[: n // 2 - 1] + "…" + path[-(n // 2):]


def pick_folders_win(owner, title, start=None):
    """Windows' own folder dialog with multi-select (IFileOpenDialog via raw COM vtable calls, no extra
    package). Returns the picked folders, [] on cancel, None when the dialog is unavailable."""
    import ctypes
    from ctypes import byref, c_void_p, c_wchar_p, wintypes
    ole = ctypes.windll.ole32
    shell = ctypes.windll.shell32

    def guid(s):
        g = (ctypes.c_byte * 16)()
        ole.CLSIDFromString(c_wchar_p(s), byref(g))
        return g

    def call(obj, index, *args, types=()):
        fn = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(c_void_p))).contents[index]
        return ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, *types)(fn)(obj, *args)

    def release(obj):
        if obj:
            call(obj, 2)

    ole.CoInitialize(None)  # Tk/tkdnd may have done it already: S_FALSE / RPC_E_CHANGED_MODE are fine
    dlg, items, folder = c_void_p(), c_void_p(), c_void_p()
    if ole.CoCreateInstance(guid("{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}"), None, 1,  # CLSCTX_INPROC_SERVER
                            guid("{d57c7288-d4ad-4768-be02-9d969532d960}"), byref(dlg)) != 0:
        return None
    try:
        # FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_ALLOWMULTISELECT | FOS_PATHMUSTEXIST
        call(dlg, 9, 0x20 | 0x40 | 0x200 | 0x800, types=(wintypes.DWORD,))
        call(dlg, 17, title, types=(c_wchar_p,))
        if start and shell.SHCreateItemFromParsingName(c_wchar_p(start), None,
                                                       guid("{43826d1e-e718-42ee-bc55-a1e261c37bfe}"), byref(folder)) == 0:
            call(dlg, 12, folder, types=(c_void_p,))
        if call(dlg, 3, owner, types=(wintypes.HWND,)) != 0:  # Show: cancelled or failed
            return []
        if call(dlg, 27, byref(items), types=(ctypes.POINTER(c_void_p),)) != 0:  # GetResults
            return []
        count = wintypes.DWORD()
        call(items, 7, byref(count), types=(ctypes.POINTER(wintypes.DWORD),))
        picked = []
        for i in range(count.value):
            item, name = c_void_p(), c_wchar_p()
            if call(items, 8, i, byref(item), types=(wintypes.DWORD, ctypes.POINTER(c_void_p))) == 0:
                if call(item, 5, 0x80058000, byref(name), types=(wintypes.DWORD, ctypes.POINTER(c_wchar_p))) == 0:
                    picked.append(name.value)  # SIGDN_FILESYSPATH
                    ole.CoTaskMemFree(name)
                release(item)
        return picked
    finally:
        release(folder)
        release(items)
        release(dlg)


def open_folder(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


class Tooltip:
    def __init__(self, widget, text=""):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _):
        if self.text and not self.tip:
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.geometry(f"+{self.widget.winfo_pointerx() + 12}+{self.widget.winfo_pointery() + 16}")
            tk.Label(self.tip, text=self.text, bg="#111827", fg="white", padx=8, pady=4,
                     font=(App.family, 9)).pack()

    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class Root(ctk.CTk, *([TkinterDnD.DnDWrapper] if TkinterDnD else [])):
    def __init__(self):
        super().__init__()
        self.dnd = False
        if TkinterDnD:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd = True
            except Exception:  # tkdnd binary missing for this Tk: keep the buttons only
                pass


class App:
    family = "Segoe UI"

    def __init__(self, initial=(), demo=False):
        """demo: light theme and no update check (screenshots); the caller drives start()."""
        self.q = queue.Queue()  # callables from worker threads, run on the UI thread
        self.rows = {}  # treeview iid -> (path, folder it was added from or None)
        self.reasons = {}  # treeview iid -> why cleaning failed, shown in the row tooltip
        self.running = False
        self.stop = threading.Event()
        self.close_after = False
        self.on_finish = None
        self.pending_update = None
        self.settings = updater.load_settings()

        ctk.set_appearance_mode("light" if demo else "system")
        self.root = root = Root()
        App.family = ui_family(root)
        ctk.ThemeManager.theme["CTkFont"]["family"] = App.family
        root.title("Exif Remover")
        root.minsize(820, 600)
        root.geometry("920x680+0+0" if demo else "920x700")  # demo: fits the 1024x768 CI screen
        try:
            if sys.platform == "win32":
                root.iconbitmap(asset("icon.ico"))
            else:
                root.iconphoto(True, tk.PhotoImage(file=asset("icon.png")))
        except tk.TclError:
            pass
        root.configure(fg_color=("#f6f7f9", "#111318"))
        root.grid_columnconfigure(0, weight=1)
        self.build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.add(initial)
        root.after(100, self.pump)
        if not demo and self.settings["check_updates"]:
            self.check_updates(manual=False)
        if not demo and self.settings.get("auto_clean_days"):
            root.after(800, self.offer_old_cleanup)

    def font(self, size=13, weight="normal"):
        return ctk.CTkFont(family=App.family, size=size, weight=weight)

    def secondary(self, parent, text, command, width=0):
        return ctk.CTkButton(parent, text=text, command=command, width=width or 28, height=32, corner_radius=6,
                             fg_color=("white", "#1f2329"), hover_color=("#eef2f7", "#2a2f37"), border_width=1,
                             border_color=("#d1d5db", "#3a3f47"), text_color=("#111827", "#e5e7eb"), font=self.font(13))

    # ---------- layout ----------
    def build(self):
        root, pad = self.root, {"padx": 20}

        self.banner = ctk.CTkFrame(root, fg_color=("#dbeafe", "#1e3a8a"), corner_radius=0)
        self.banner_text = ctk.CTkLabel(self.banner, text="", font=self.font(13))
        self.banner_text.pack(side="left", padx=20, pady=8)
        self.banner_bar = ctk.CTkProgressBar(self.banner, width=220, progress_color=ACCENT)
        self.banner_bar.pack(side="right", padx=20)

        drop = ctk.CTkFrame(root, border_width=2, border_color=("#bfdbfe", "#1e40af"), corner_radius=10,
                            fg_color=("white", "#161a20"))
        drop.grid(row=1, column=0, sticky="ew", pady=(16, 12), **pad)
        try:
            self.drop_img = tk.PhotoImage(file=asset("drop.png"))
            ctk.CTkLabel(drop, text="", image=self.drop_img).pack(pady=(14, 2))
        except tk.TclError:
            pass
        title = "Kéo thả ảnh, video, PDF hoặc thư mục vào đây" if root.dnd else "Chọn ảnh, video, PDF hoặc thư mục"
        ctk.CTkLabel(drop, text=title, font=self.font(18, "bold")).pack()
        ctk.CTkLabel(drop, text="JPG, PNG, WebP, HEIC, AVIF, GIF, TIFF, MP4, MOV, PDF  ·  xử lý ngay trên máy, không tải tệp lên mạng",
                     text_color=MUTED, font=self.font(12)).pack(pady=(2, 0))
        btns = ctk.CTkFrame(drop, fg_color="transparent")
        btns.pack(pady=(12, 16))
        ctk.CTkButton(btns, text="Chọn tệp", width=130, height=34, corner_radius=6, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, font=self.font(13, "bold"), command=self.pick_files).pack(side="left", padx=6)
        self.secondary(btns, "Chọn thư mục", self.pick_folder, 130).pack(side="left", padx=6)
        if root.dnd:
            root.drop_target_register(DND_FILES)
            root.dnd_bind("<<Drop>>", lambda e: self.drop(e.data))

        bar = ctk.CTkFrame(root, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", pady=(0, 8), **pad)
        self.count = ctk.CTkLabel(bar, text="", font=self.font(14, "bold"))
        self.count.pack(side="left")
        self.secondary(bar, "Xoá danh sách", self.clear, 110).pack(side="right")
        self.secondary(bar, "Bỏ tệp đã chọn", self.remove, 120).pack(side="right", padx=8)
        self.secondary(bar, "Xem metadata", self.view_selected, 110).pack(side="right")

        table = ctk.CTkFrame(root, corner_radius=8, border_width=1, border_color=("#e5e7eb", "#2a2f37"),
                             fg_color=("white", "#161a20"))
        table.grid(row=3, column=0, sticky="nsew", **pad)
        root.grid_rowconfigure(3, weight=1)
        self.style_tables()
        self.tree = ttk.Treeview(table, columns=("name", "kind", "meta", "status"), show="headings",
                                 style="App.Treeview", selectmode="extended")
        for col, text, width, anchor in (("name", "Tên tệp", 400, "w"), ("kind", "Loại", 100, "w"),
                                         ("meta", "Metadata", 110, "center"), ("status", "Trạng thái", 130, "w")):
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor, stretch=col == "name")
        scroll = ctk.CTkScrollbar(table, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        scroll.pack(side="right", fill="y", pady=4)
        self.tree.bind("<Double-1>", lambda e: self.view_selected())
        self.tree.bind("<Delete>", lambda e: self.remove())
        self.row_tip, self.tip_iid = Tooltip(self.tree), None
        self.tree.bind("<Motion>", self.tree_tip, add="+")
        self.tree.bind("<Leave>", lambda e: setattr(self, "tip_iid", None), add="+")

        act = ctk.CTkFrame(root, fg_color="transparent")
        act.grid(row=4, column=0, sticky="ew", pady=(14, 0), **pad)
        self.backup = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(act, text="Tạo bản sao lưu trước khi xoá (khuyên dùng)", variable=self.backup,
                      progress_color=ACCENT, button_color="white", button_hover_color="#f3f4f6",
                      fg_color=("#d1d5db", "#4b5563"), font=self.font(13)).pack(side="left")
        self.run_btn = ctk.CTkButton(act, text="Xoá metadata", height=44, width=210, corner_radius=8,
                                     fg_color=ACCENT, hover_color=ACCENT_HOVER, font=self.font(16, "bold"),
                                     command=lambda: self.request_stop() if self.running else self.start())
        self.run_btn.pack(side="right")

        self.progress = ctk.CTkProgressBar(root, height=8, progress_color=ACCENT)
        self.progress.set(0)

        self.card = ctk.CTkFrame(root, corner_radius=8, border_width=1)
        self.card.grid_columnconfigure(0, weight=1)
        self.card_title = ctk.CTkLabel(self.card, text="", font=self.font(16, "bold"))
        self.card_title.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self.card_text = ctk.CTkLabel(self.card, text="", justify="left", anchor="w", font=self.font(13))
        self.card_text.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        self.card_tip = Tooltip(self.card_text)
        self.card_btn = self.secondary(self.card, "Mở thư mục sao lưu", None, 160)
        self.card_btn_tip = Tooltip(self.card_btn)
        self.card_del = self.secondary(self.card, "Xoá bản sao lưu", None, 140)
        self.card_del_tip = Tooltip(self.card_del)

        foot = ctk.CTkFrame(root, fg_color="transparent")
        foot.grid(row=7, column=0, sticky="ew", pady=(12, 0), **pad)
        link = {"fg_color": "transparent", "hover_color": ("#e5e7eb", "#2a2f37"), "height": 26, "corner_radius": 6,
                "text_color": MUTED, "font": self.font(12)}
        self.log_btn = ctk.CTkButton(foot, text="▸  Chi tiết", width=90, command=self.toggle_log, **link)
        self.log_btn.pack(side="left")
        ctk.CTkButton(foot, text="Bản sao lưu", width=100, command=self.show_backups, **link).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(foot, text=f"Phiên bản {er.__version__}", text_color=MUTED, font=self.font(12)).pack(side="right")
        ctk.CTkButton(foot, text="Kiểm tra cập nhật", width=120, command=lambda: self.check_updates(manual=True),
                      **link).pack(side="right", padx=(0, 12))
        self.auto = ctk.BooleanVar(value=self.settings["check_updates"])
        ctk.CTkCheckBox(foot, text="Tự kiểm tra cập nhật khi mở", variable=self.auto, checkbox_width=16,
                        checkbox_height=16, corner_radius=4, border_width=1, fg_color=ACCENT, text_color=MUTED,
                        font=self.font(12), command=self.save_auto).pack(side="right", padx=(0, 8))
        mono = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"
        self.log = ctk.CTkTextbox(root, height=150, corner_radius=8, font=ctk.CTkFont(family=mono, size=12))
        self.log.configure(state="disabled")
        ctk.CTkFrame(root, fg_color="transparent", height=16).grid(row=9, column=0)
        self.refresh_count()

    def style_tables(self):
        light = ctk.get_appearance_mode() == "Light"
        bg, fg, head, sel, stripe, line = (
            ("white", "#111827", "#f9fafb", "#dbeafe", "#f8fafc", "#e5e7eb") if light
            else ("#161a20", "#e5e7eb", "#1f2329", "#1e3a8a", "#1b2027", "#2a2f37"))
        scale = self.root.tk.call("tk", "scaling") / (96 / 72)  # Tk is DPI-aware on Windows; row height is pixels
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.Treeview", background=bg, fieldbackground=bg, foreground=fg, borderwidth=0,
                        relief="flat", rowheight=int(30 * scale), font=(App.family, 10))
        style.layout("App.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # no inner border
        style.configure("App.Treeview.Heading", background=head, foreground=MUTED[0] if light else MUTED[1],
                        relief="flat", borderwidth=0, font=(App.family, 10, "bold"), padding=(8, 6))
        style.map("App.Treeview.Heading", background=[("active", line)])
        style.map("App.Treeview", background=[("selected", sel)], foreground=[("selected", fg)])
        self.tree_tags = {"stripe": stripe, "ok": GREEN[0] if light else GREEN[1], "err": RED[0] if light else RED[1],
                          "muted": MUTED[0] if light else MUTED[1]}

    def tag_rows(self):
        for i, iid in enumerate(self.tree.get_children()):
            state = [t for t in self.tree.item(iid, "tags") if t in ("ok", "err")]
            self.tree.item(iid, tags=(["stripe"] if i % 2 else []) + state)
        self.tree.tag_configure("stripe", background=self.tree_tags["stripe"])
        self.tree.tag_configure("ok", foreground=self.tree_tags["ok"])
        self.tree.tag_configure("err", foreground=self.tree_tags["err"])

    # ---------- file list ----------
    def pick_files(self):
        self.add(filedialog.askopenfilenames(parent=self.root, filetypes=FILETYPES))

    def drop(self, data):
        """Explorer drops several items as one Tcl list, e.g. '{C:/a b} C:/c'."""
        self.add(self.root.tk.splitlist(data))

    def pick_folder(self):
        dirs = None
        if sys.platform == "win32":
            try:
                dirs = pick_folders_win(int(self.root.wm_frame(), 16), "Chọn một hoặc nhiều thư mục (giữ Ctrl)")
            except Exception as e:  # never lose the button: fall back to Tk's single-folder dialog
                self.write(f"Hộp chọn nhiều thư mục lỗi, dùng hộp thường: {e}\n")
        if dirs is None:
            d = filedialog.askdirectory(parent=self.root)
            dirs = [d] if d else []
        if dirs:
            self.add(dirs)

    def add(self, items):
        if self.running:
            return
        known = {p for p, _ in self.rows.values()}
        new, skipped, backups = [], 0, []
        for item in items:
            item = os.path.normpath(er.to_posix(item))
            if er.in_backup(item):
                backups.append(item)
                continue
            files, bad = er.collect([item])
            skipped += len(bad)
            folder = item if os.path.isdir(item) else None
            for f in files:
                if f not in known:
                    known.add(f)
                    name = shorten(os.path.relpath(f, folder) if folder else os.path.basename(f), 60)
                    ext = os.path.splitext(f)[1].lower()
                    iid = self.tree.insert("", "end", values=(name, f"{KIND[ext]} {ext[1:].upper()}", "…", WAIT))
                    self.rows[iid] = (f, folder)
                    new.append((iid, f))
        if skipped:
            self.write(f"Bỏ qua {skipped} mục không hỗ trợ\n")
        if backups:
            messagebox.showwarning("Thư mục sao lưu", "Bỏ qua:\n" + "\n".join(er.to_windows(b) for b in backups) +
                                   "\n\nĐây là bản sao lưu (chứa tệp gốc còn metadata) nên ứng dụng không xoá "
                                   "metadata trong đó.", parent=self.root)
        self.tag_rows()
        self.refresh_count()
        self.card.grid_forget()
        threading.Thread(target=self.count_meta, args=(new,), daemon=True).start()

    def count_meta(self, items):
        for i in range(0, len(items), COUNT_BATCH):
            chunk = items[i:i + COUNT_BATCH]
            try:
                found = er.read_tags_many([f for _, f in chunk])
            except Exception:  # one unreadable file fails the batch: retry file by file
                found = []
                for _, f in chunk:
                    try:
                        found.append(er.read_tags(f))
                    except Exception:
                        found.append(None)
            for (iid, f), tags in zip(chunk, found):
                self.q.put(lambda iid=iid, f=f, tags=tags: self.show_count(iid, f, tags))

    def show_count(self, iid, path, tags):
        if not self.tree.exists(iid):
            return
        self.tree.set(iid, "meta", "?" if tags is None else str(er.meta_count(tags)))
        ext = os.path.splitext(path)[1].lower()
        if tags and er.real_ext(path, tags) != ext:  # e.g. a JPEG saved as .png
            self.tree.set(iid, "kind", f"{er.file_type(tags)} (đuôi {ext})")

    def tree_tip(self, e):
        iid = self.tree.identify_row(e.y)
        if iid != self.tip_iid:
            self.tip_iid = iid
            self.row_tip.hide(None)
            path = self.rows.get(iid, ("",))[0]
            self.row_tip.text = er.to_windows(path) + (f"\nLỗi: {self.reasons[iid]}" if iid in self.reasons else "")
            self.row_tip.show(None)

    def remove(self):
        if not self.running:
            for iid in self.tree.selection():
                self.tree.delete(iid)
                del self.rows[iid]
                self.reasons.pop(iid, None)
            self.tag_rows()
            self.refresh_count()

    def clear(self):
        if not self.running:
            self.tree.delete(*self.rows)
            self.rows.clear()
            self.reasons.clear()
            self.card.grid_forget()
            self.refresh_count()

    def refresh_count(self):
        n = len(self.rows)
        self.count.configure(text=f"Danh sách tệp ({n})" if n else "Chưa có tệp nào")

    # ---------- metadata viewer ----------
    def view_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Xem metadata", "Chọn một tệp trong danh sách trước.", parent=self.root)
            return
        return self.view(self.rows[sel[0]][0])

    def view(self, path):
        try:
            tags = er.read_tags(path)
        except Exception as e:
            messagebox.showerror("Xem metadata", f"Không đọc được metadata:\n{e}", parent=self.root)
            return None
        win = ctk.CTkToplevel(self.root)
        win.title(f"Metadata – {os.path.basename(path)}")
        win.geometry("780x540")
        win.configure(fg_color=("#f6f7f9", "#111318"))
        win.transient(self.root)
        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(top, text=os.path.basename(path), font=self.font(16, "bold")).pack(side="left")
        search = ctk.CTkEntry(top, placeholder_text="Tìm, ví dụ: GPS, Date", width=240, height=32, corner_radius=6,
                              font=self.font(13))
        search.pack(side="right")
        frame = ctk.CTkFrame(win, corner_radius=8, border_width=1, border_color=("#e5e7eb", "#2a2f37"),
                             fg_color=("white", "#161a20"))
        frame.pack(fill="both", expand=True, padx=16)
        tree = ttk.Treeview(frame, columns=("g", "t", "v"), show="headings", style="App.Treeview")
        for col, text, width in (("g", "Nhóm", 130), ("t", "Thẻ", 190), ("v", "Giá trị", 420)):
            tree.heading(col, text=text, anchor="w")
            tree.column(col, width=width, anchor="w", stretch=col == "v")
        tree.tag_configure("stripe", background=self.tree_tags["stripe"])
        scroll = ctk.CTkScrollbar(frame, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        scroll.pack(side="right", fill="y", pady=4)
        shown = ctk.CTkLabel(win, text="", text_color=MUTED, font=self.font(12))
        shown.pack(anchor="w", padx=16, pady=(6, 12))
        # ExifTool/System rows describe the file on disk (folder, dates), not metadata inside it.
        rows = [(g, n, str(v)[:300]) for g, n, v in tags if g not in ("ExifTool", "System")]
        rows.sort(key=lambda r: r[0] in ("File", "JFIF", "Composite"))  # identifying groups first

        def fill(*_):
            needle = search.get().strip().lower()
            tree.delete(*tree.get_children())
            hits = [r for r in rows if needle in " ".join(r).lower()]
            for i, r in enumerate(hits):
                tree.insert("", "end", values=r, tags=("stripe",) if i % 2 else ())
            shown.configure(text=f"{len(hits)} / {len(rows)} thẻ  ·  chỉ xem, không sửa")

        search.bind("<KeyRelease>", fill)
        fill()
        win.after(150, win.lift)
        return win

    # ---------- cleaning ----------
    def start(self):
        if self.running:
            return
        if not self.rows:
            messagebox.showinfo("Exif Remover", "Thêm tệp hoặc thư mục trước.", parent=self.root)
            return
        missing = [t for t in ("exiftool", "ffmpeg", "qpdf") if not er.tool(t)]
        if missing:
            messagebox.showerror("Exif Remover", "Thiếu công cụ: " + ", ".join(missing), parent=self.root)
            return
        self.running = True
        self.stop.clear()
        self.reasons.clear()
        self.run_btn.configure(text="Dừng", fg_color=STOP, hover_color=STOP_HOVER)
        self.card.grid_forget()
        self.progress.set(0)
        self.progress.grid(row=5, column=0, sticky="ew", padx=20, pady=(12, 0))
        for iid in self.rows:
            self.tree.set(iid, "status", WAIT)
            self.tree.item(iid, tags=())
        self.tag_rows()
        jobs = list(self.rows.items())
        folders = sorted({r for _, r in self.rows.values() if r}) if self.backup.get() else []
        self.write(f"--- Bắt đầu: {len(jobs)} tệp ---\n")
        threading.Thread(target=self.work, args=(jobs, folders), daemon=True).start()

    def work(self, jobs, folders):
        post = self.q.put
        backups = []
        try:
            for d in folders:
                backups.append(er.backup_dir(d, self.stop))
                bk.record(backups[-1], d)
                post(lambda b=backups[-1]: self.write(f"BACKUP {b}  ({er.count_files(b)} tệp)\n"))
        except er.Stopped:
            for b in backups:  # nothing was cleaned, so these copies are not needed
                shutil.rmtree(b, ignore_errors=True)
            post(lambda: self.mark_stopped([iid for iid, _ in jobs]))
            post(lambda: self.finish(0, len(jobs), [], stopped=True))
            return
        except Exception as e:
            post(lambda msg=str(e): self.finish(0, 0, [], f"Sao lưu thất bại, chưa xoá tệp nào: {msg}"))
            return
        ok = 0
        for i, (iid, (path, _)) in enumerate(jobs):
            if self.stop.is_set():  # checked between files only: a file is never left half-done
                post(lambda rest=[j for j, _ in jobs[i:]]: self.mark_stopped(rest))
                break
            post(lambda iid=iid: self.tree.set(iid, "status", BUSY))
            try:
                b, a = er.clean_file(path)
                ok += 1
                post(lambda iid=iid, b=b, a=a, p=path: self.row_done(iid, f"{b} → {a}", DONE, "ok",
                                                                      f"OK     {b:4d} -> {a:3d}  {p}"))
            except Exception as e:
                post(lambda iid=iid, msg=str(e), p=path: self.row_done(iid, None, ERR, "err", f"FAIL   {p}: {msg}", msg))
            post(lambda v=(i + 1) / len(jobs): self.progress.set(v))
        post(lambda: self.finish(ok, len(jobs), backups, stopped=self.stop.is_set()))

    def request_stop(self):
        self.stop.set()
        self.run_btn.configure(state="disabled", text="Đang dừng…")

    def mark_stopped(self, iids):
        for iid in iids:
            if self.tree.exists(iid):
                self.tree.set(iid, "status", STOPPED)
        self.write(f"Đã dừng: {len(iids)} tệp chưa xử lý, giữ nguyên.\n")

    def close(self):
        if not self.running:
            self.root.destroy()
        elif messagebox.askyesno("Exif Remover", "Đang xoá metadata. Dừng sau tệp hiện tại rồi thoát?\n"
                                 "Các tệp chưa xử lý được giữ nguyên.", parent=self.root):
            if not self.running:  # the run ended while the dialog was open
                self.root.destroy()
                return
            self.close_after = True
            self.request_stop()

    def row_done(self, iid, meta, status, tag, line, reason=None):
        if reason:
            self.reasons[iid] = reason
        if self.tree.exists(iid):
            if meta:
                self.tree.set(iid, "meta", meta)
            self.tree.set(iid, "status", status)
            stripe = [t for t in self.tree.item(iid, "tags") if t == "stripe"]
            self.tree.item(iid, tags=stripe + [tag])
        self.write(line + "\n")

    def finish(self, ok, total, backups, fatal=None, stopped=False):
        self.running = False
        if self.close_after:
            self.root.destroy()
            return
        self.run_btn.configure(state="normal", text="Xoá metadata", fg_color=ACCENT, hover_color=ACCENT_HOVER)
        self.progress.grid_forget()
        good = not fatal and not stopped and ok == total
        self.card.configure(fg_color=("#f0fdf4", "#0f2a1a") if good else ("#fef2f2", "#2a1212"),
                            border_color=("#bbf7d0", "#14532d") if good else ("#fecaca", "#7f1d1d"))
        if stopped:
            self.card.configure(fg_color=("#fffbeb", "#2a2008"), border_color=("#fde68a", "#78350f"))
        title = fatal or (f"■  Đã dừng: đã xoá {ok}/{total} tệp" if stopped else
                          f"✓  Đã xoá metadata {ok}/{total} tệp" if good else f"✗  Đã xoá {ok}/{total} tệp")
        self.card_title.configure(text=title, text_color=AMBER if stopped else GREEN if good else RED)
        failed = len(self.reasons)
        lines = [] if good or fatal else (
            ([f"{failed} tệp lỗi (rê chuột lên dòng để xem lý do)."] if failed else []) +
            ["Tệp chưa xoá được giữ nguyên. Xem ▸ Chi tiết."])
        lines.append("Bản sao lưu: " + ("; ".join(shorten(b) for b in backups) if backups else "không có"))
        self.card_text.configure(text="\n".join(lines))
        self.card_tip.text = self.card_btn_tip.text = "\n".join(backups)
        if backups:
            self.card_btn.configure(command=lambda: open_folder(backups[0]))
            self.card_btn.grid(row=0, column=1, rowspan=2, padx=(16, 0), pady=12)
            # only after a clean run: if any file failed or the run stopped, the backup is the only good copy
            self.card_del.configure(state="normal" if good else "disabled",
                                    command=lambda: self.delete_backups(backups) and self.card_del.configure(state="disabled"))
            self.card_del_tip.text = ("Chuyển bản sao lưu của lần chạy này vào Thùng rác" if good else
                                      "Chỉ xoá được khi mọi tệp đã xoá metadata thành công")
            self.card_del.grid(row=0, column=2, rowspan=2, padx=16, pady=12)
        else:
            self.card_btn.grid_forget()
            self.card_del.grid_forget()
        self.card.grid(row=6, column=0, sticky="ew", padx=20, pady=(14, 0))
        self.write(f"{'OK' if good else 'STOPPED' if stopped else 'FAILED'}: {ok}/{total} cleaned. Backup: {'; '.join(backups) or 'none'}\n")
        if self.pending_update:
            info, self.pending_update = self.pending_update, None
            self.offer_update(info)
        if self.on_finish:
            self.on_finish()

    # ---------- backups ----------
    def delete_backups(self, paths, title="Xoá bản sao lưu"):
        """Confirm (path, file count, size), then recycle. Returns the folders deleted."""
        lines, files, total = [], 0, 0
        for p in paths:
            n, size = bk.size(p)
            files, total = files + n, total + size
            lines.append(f"{er.to_windows(p)}  ({n} tệp, {bk.human(size)})")
        where = ("Các thư mục sẽ được chuyển vào Thùng rác (khôi phục được)." if sys.platform == "win32"
                 else "Các thư mục sẽ bị xoá vĩnh viễn.")
        shown = lines[:12] + ([f"… và {len(lines) - 12} thư mục khác"] if len(lines) > 12 else [])
        if not messagebox.askyesno(title, f"Xoá {len(paths)} bản sao lưu ({files} tệp, {bk.human(total)})?\n\n" +
                                   "\n".join(shown) + f"\n\n{where}", icon="warning", parent=self.root):
            return []
        done, errors = bk.delete(paths)
        for p in done:
            self.write(f"Đã xoá bản sao lưu {p}\n")
        if errors:
            messagebox.showerror(title, "Không xoá được:\n" + "\n".join(f"{er.to_windows(p)}: {m}" for p, m in errors),
                                 parent=self.root)
        return done

    def offer_old_cleanup(self):
        days = self.settings.get("auto_clean_days", 0)
        old = [e["path"] for e in bk.older_than(days)] if days else []
        if old and not self.running:
            self.delete_backups(old, f"Bản sao lưu cũ hơn {days} ngày")

    def show_backups(self):
        win = ctk.CTkToplevel(self.root)
        win.title("Bản sao lưu")
        win.geometry("860x520")
        win.configure(fg_color=("#f6f7f9", "#111318"))
        win.transient(self.root)
        ctk.CTkLabel(win, text="Bản sao lưu do ứng dụng tạo", font=self.font(16, "bold")).pack(anchor="w", padx=16, pady=(16, 0))
        ctk.CTkLabel(win, text="Chỉ liệt kê các thư mục ..._backup-NĂM-THÁNG-NGÀY mà ứng dụng này đã tạo.",
                     text_color=MUTED, font=self.font(12)).pack(anchor="w", padx=16, pady=(0, 8))
        frame = ctk.CTkFrame(win, corner_radius=8, border_width=1, border_color=("#e5e7eb", "#2a2f37"),
                             fg_color=("white", "#161a20"))
        frame.pack(fill="both", expand=True, padx=16)
        tree = ttk.Treeview(frame, columns=("p", "d", "s", "src"), show="headings", style="App.Treeview",
                            selectmode="extended")
        for col, text, width in (("p", "Thư mục", 430), ("d", "Ngày tạo", 100), ("s", "Dung lượng", 140),
                                 ("src", "Thư mục gốc", 110)):
            tree.heading(col, text=text, anchor="w")
            tree.column(col, width=width, anchor="w", stretch=col == "p")
        tree.tag_configure("stripe", background=self.tree_tags["stripe"])
        scroll = ctk.CTkScrollbar(frame, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        scroll.pack(side="right", fill="y", pady=4)
        tip, tip_row = Tooltip(tree), [None]

        def hover(e):
            iid = tree.identify_row(e.y)
            if iid != tip_row[0]:
                tip_row[0], tip.text = iid, er.to_windows(iid) if iid else ""
                tip.hide(None)
                tip.show(None)
        tree.bind("<Motion>", hover, add="+")

        def fill():
            tree.delete(*tree.get_children())
            # shortcut: sizes are summed on the UI thread; fine for photo folders, thread it if lists get huge
            for i, e in enumerate(bk.listed()):
                n, size = bk.size(e["path"])
                tree.insert("", "end", iid=e["path"], tags=("stripe",) if i % 2 else (), values=(
                    shorten(er.to_windows(e["path"]), 60), e.get("created", "?"), f"{bk.human(size)} · {n} tệp",
                    "còn" if e["src_exists"] else "không còn"))
            empty.configure(text="" if tree.get_children() else "Chưa có bản sao lưu nào.")

        def delete():
            sel = list(tree.selection())
            if not sel:
                messagebox.showinfo("Bản sao lưu", "Chọn bản sao lưu cần xoá trước.", parent=win)
                return
            self.delete_backups(sel)
            fill()

        auto = ctk.CTkFrame(win, fg_color="transparent")
        auto.pack(side="bottom", fill="x", padx=16, pady=(0, 14), before=frame)  # before: never squeezed out by the list
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=16, pady=12, before=frame)
        empty = ctk.CTkLabel(btns, text="", text_color=MUTED, font=self.font(12))
        empty.pack(side="left")
        ctk.CTkButton(btns, text="Xoá", width=100, height=32, corner_radius=6, fg_color=STOP, hover_color=STOP_HOVER,
                      font=self.font(13, "bold"), command=delete).pack(side="right")
        self.secondary(btns, "Mở thư mục", lambda: [open_folder(p) for p in tree.selection()[:1]], 100).pack(side="right", padx=8)
        self.secondary(btns, "Chọn tất cả", lambda: tree.selection_set(tree.get_children()), 100).pack(side="right")

        days = self.settings.get("auto_clean_days", 0)
        on = ctk.BooleanVar(value=bool(days))
        n = ctk.StringVar(value=str(days or 30))

        def save(*_):
            v = n.get().strip()
            self.settings["auto_clean_days"] = int(v) if on.get() and v.isdigit() and int(v) > 0 else 0
            updater.save_settings(self.settings)
        ctk.CTkCheckBox(auto, text="Khi mở ứng dụng, đề nghị xoá bản sao lưu cũ hơn", variable=on, command=save,
                        checkbox_width=16, checkbox_height=16, corner_radius=4, border_width=1, fg_color=ACCENT,
                        font=self.font(12)).pack(side="left")
        entry = ctk.CTkEntry(auto, textvariable=n, width=50, height=26, font=self.font(12))
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", save)
        ctk.CTkLabel(auto, text="ngày (luôn hỏi trước khi xoá)", text_color=MUTED, font=self.font(12)).pack(side="left")
        fill()
        win.after(150, win.lift)
        return win

    # ---------- log ----------
    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def toggle_log(self):
        if self.log.winfo_ismapped():
            self.log.grid_forget()
            self.log_btn.configure(text="▸  Chi tiết")
        else:
            self.log.grid(row=8, column=0, sticky="ew", padx=20, pady=(6, 0))
            self.log_btn.configure(text="▾  Chi tiết")

    def pump(self):
        while True:
            try:
                self.q.get_nowait()()
            except queue.Empty:
                break
        self.root.after(100, self.pump)

    # ---------- updates ----------
    def save_auto(self):
        self.settings["check_updates"] = self.auto.get()
        updater.save_settings(self.settings)

    def check_updates(self, manual):
        def work():
            try:
                info = updater.latest()
            except Exception as e:
                msg = str(e)
                self.q.put(lambda: self.write(f"Không kiểm tra được cập nhật: {msg}\n"))
                if manual:
                    self.q.put(lambda: messagebox.showerror(
                        "Kiểm tra cập nhật", f"Không kiểm tra được cập nhật.\n{msg}", parent=self.root))
                return
            if updater.is_newer(info["tag"]):
                self.q.put(lambda: self.offer_update(info))
            elif manual:
                self.q.put(lambda: messagebox.showinfo(
                    "Kiểm tra cập nhật", f"Bạn đang dùng bản mới nhất ({er.__version__}).", parent=self.root))
        threading.Thread(target=work, daemon=True).start()

    def offer_update(self, info):
        if self.running:  # never interrupt a cleaning run; ask again when it ends
            self.pending_update = info
            return None
        win = ctk.CTkToplevel(self.root)
        win.title("Cập nhật Exif Remover")
        win.geometry("540x400")
        win.resizable(False, False)
        win.configure(fg_color=("#f6f7f9", "#111318"))
        win.transient(self.root)
        ctk.CTkLabel(win, text=f"Có bản mới {info['tag']}", font=self.font(18, "bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(win, text=f"Bạn đang dùng bản {er.__version__}. Cập nhật mất khoảng một phút, xong ứng dụng tự mở lại.",
                     wraplength=490, justify="left", text_color=MUTED, font=self.font(13)).pack(anchor="w", padx=24, pady=(4, 10))
        notes = ctk.CTkTextbox(win, height=180, corner_radius=8, border_width=1, font=self.font(13))
        notes.insert("end", info["notes"][:2000] or "(không có ghi chú)")
        notes.configure(state="disabled")
        notes.pack(fill="both", expand=True, padx=24)
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=18)

        def now():
            win.destroy()
            self.install_update(info)

        ctk.CTkButton(btns, text="Cập nhật ngay", width=140, height=36, corner_radius=6, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, font=self.font(13, "bold"), command=now).pack(side="right")
        self.secondary(btns, "Để sau", win.destroy, 100).pack(side="right", padx=10)
        win.after(150, lambda: (win.lift(), win.grab_set()))
        return win

    def install_update(self, info):
        if not (sys.platform == "win32" and getattr(sys, "frozen", False)):
            messagebox.showinfo("Cập nhật", "Tự cập nhật chỉ chạy trong bản cài đặt trên Windows.", parent=self.root)
            return
        self.run_btn.configure(state="disabled")
        self.banner_text.configure(text=f"Đang tải bản cập nhật {info['tag']}…")
        self.banner_bar.set(0)
        self.banner.grid(row=0, column=0, sticky="ew")

        def work():
            try:
                path = updater.download(info, progress=lambda p: self.q.put(lambda: self.banner_bar.set(p / 100)))
            except Exception as e:
                msg = str(e)
                self.q.put(lambda: self.update_failed(msg))
                return
            self.q.put(lambda: self.launch(path))
        threading.Thread(target=work, daemon=True).start()

    def update_failed(self, msg):
        self.banner.grid_forget()
        self.run_btn.configure(state="normal")
        messagebox.showerror("Cập nhật", f"Không cập nhật được, bạn vẫn dùng bản hiện tại.\n{msg}", parent=self.root)

    def launch(self, path):
        try:
            updater.run_installer(path)
        except OSError as e:
            self.update_failed(str(e))
            return
        self.root.destroy()  # the installer replaces the files and starts the new version


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-update"]:
        sys.exit(updater.self_update())
    if len(sys.argv) > 1:
        sys.exit(er.main(sys.argv[1:]))  # CLI mode, also used by the CI smoke test
    App().root.mainloop()
