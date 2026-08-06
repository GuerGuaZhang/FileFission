# -*- coding: utf-8 -*-
"""
FileFission —— 文件名核裂变工具 + 文本分割器
   模式一：批量提取文件名并按字符数分组输出
   模式二：按分割线切分文本，左/右键分别保存到不同目录

经典实用工具风格，所有反馈通过底部状态栏显示，无弹窗。
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog


# ============================================================================
# 全局递增计数器
# ============================================================================

class GlobalCounter:
    """全局递增文件编号（左键/右键共用）"""
    _lock = threading.Lock()
    _counter = 0

    @classmethod
    def next(cls) -> int:
        with cls._lock:
            cls._counter += 1
            return cls._counter

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._counter = 0


# ============================================================================
# 核心处理逻辑 —— 文件名提取（原有）
# ============================================================================

class FileProcessor:
    """文件处理逻辑：读取、提取、去后缀、分组、写入。"""

    @staticmethod
    def read_lines(input_path: str) -> list:
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"输入文件不存在：{input_path}")
        lines = []
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if raw:
                    lines.append(raw)
        return lines

    @staticmethod
    def process_line(line: str, keep_path: bool, keep_extension: bool) -> str:
        if not keep_path:
            name = os.path.basename(line)
        else:
            name = line
        name = name.strip()
        if not keep_extension:
            root, _ = os.path.splitext(name)
            name = root
        return name

    @staticmethod
    def group_by_chars(items: list, char_limit: int) -> list:
        if char_limit <= 0:
            return [items[:]]
        groups, cur_group, cur_cnt = [], [], 0
        for item in items:
            l = len(item)
            if cur_group and cur_cnt + l > char_limit:
                groups.append(cur_group)
                cur_group, cur_cnt = [], 0
            cur_group.append(item)
            cur_cnt += l
        if cur_group:
            groups.append(cur_group)
        return groups

    @classmethod
    def process(cls, input_path, output_dir, char_limit,
                keep_path, keep_extension, progress_callback=None):
        lines = cls.read_lines(input_path)
        if not lines:
            return {"total_lines": 0, "total_groups": 0, "output_dir": output_dir}
        processed = [cls.process_line(l, keep_path, keep_extension) for l in lines]
        groups = cls.group_by_chars(processed, char_limit)
        os.makedirs(output_dir, exist_ok=True)
        total = len(groups)
        for idx, group in enumerate(groups, start=1):
            out_name = f"group_{idx:03d}.txt"
            out_path = os.path.join(output_dir, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                for item in group:
                    f.write(item + "\n")
            if progress_callback:
                progress_callback(idx, total, out_name)
        return {"total_lines": len(lines), "total_groups": total,
                "output_dir": output_dir}


# ============================================================================
# 核心处理逻辑 —— 文本分割器（新增）
# ============================================================================

class TextSplitterCore:
    """文本分割器核心：管理剩余内容列表、分割线高亮、保存逻辑。"""

    SEPARATOR = "------------------------------------------------------------"

    def __init__(self):
        self.lines = []             # 当前剩余内容（含分割线）
        self.source_path = ""       # 源文件路径
        self.output_a = ""          # 左键保存目录
        self.output_b = ""          # 右键保存目录
        self._hovered_index = None  # 当前悬浮的分割线索引

    def load_file(self, path: str) -> int:
        """读取源文件，存入 self.lines（包含分割线），返回总行数。"""
        self.source_path = path
        self.lines = []
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        raw_lines = content.splitlines(keepends=False)
        for line in raw_lines:
            self.lines.append(line)
            self.lines.append(self.SEPARATOR)
        # 去掉最后一条多余分割线
        if self.lines and self.lines[-1] == self.SEPARATOR:
            self.lines.pop()
        return len(raw_lines)

    def is_separator(self, idx: int) -> bool:
        """判断某行是否为分割线（基于内容匹配）。"""
        if idx < 0 or idx >= len(self.lines):
            return False
        return self.lines[idx] == self.SEPARATOR

    def save_and_remove(self, idx: int, target_dir: str) -> dict:
        if not self.is_separator(idx):
            return {"saved": False, "filename": "", "message": "非法操作：不是分割线"}
        above = self.lines[:idx]
        # 保留原始内容行，跳过分割线
        content_lines = [l for l in above if l != self.SEPARATOR]
        if not content_lines:
            self.lines = self.lines[idx + 1:]
            return {"saved": False, "filename": "", "message": "上方无有效内容，跳过"}
        os.makedirs(target_dir, exist_ok=True)
        seq = GlobalCounter.next()
        filename = f"{seq:03d}.txt"
        filepath = os.path.join(target_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            for line in content_lines:
                f.write(line + "\n")
        self.lines = self.lines[idx + 1:]
        return {"saved": True, "filename": filename, "message": f"已保存到 {target_dir}"}


# ============================================================================
# 文本分割器界面（设置页 + 分割页）
# ============================================================================

class TextSplitterFrame(tk.Frame):
    """文本分割器界面：内嵌设置表单，不弹出窗口。"""

    def __init__(self, master):
        super().__init__(master, bg="#f0f0f0")
        self.source_var = tk.StringVar()
        self.dir_a_var = tk.StringVar()
        self.dir_b_var = tk.StringVar()
        self.core = TextSplitterCore()
        self.text_widget = None
        self.separator_tags = {}
        self._sep_index_to_tag = {}   # 反向索引：行号 → tag_name，O(1) 查询
        self._last_op_status = tk.StringVar(value="")
        self._last_op_timer = None
        self._build_ui()

    def _build_ui(self):
        self.setup_frame = tk.Frame(self, bg="#f0f0f0")
        self._build_setup_page()
        self.split_page = tk.Frame(self, bg="white")
        self._build_split_page()
        self.setup_frame.pack(fill="both", expand=True)

    def _build_setup_page(self):
        f = self.setup_frame
        # 上部内容区（填充剩余空间）
        content = tk.Frame(f, bg="#f0f0f0")
        content.pack(fill="both", expand=True)

        tk.Label(content, text="源文件 (.txt)：", anchor="w", bg="#f0f0f0"
                 ).pack(fill="x", padx=12, pady=(20, 2))
        f1 = tk.Frame(content, bg="#f0f0f0")
        f1.pack(fill="x", padx=12)
        tk.Entry(f1, textvariable=self.source_var, width=50, relief="sunken", borderwidth=2
                 ).pack(side="left", padx=(0, 6))
        tk.Button(f1, text="浏览", command=self._browse_source, width=8).pack(side="left")

        tk.Label(content, text="输出文件夹 A（左键保存）：", anchor="w", bg="#f0f0f0"
                 ).pack(fill="x", padx=12, pady=(14, 2))
        f2 = tk.Frame(content, bg="#f0f0f0")
        f2.pack(fill="x", padx=12)
        tk.Entry(f2, textvariable=self.dir_a_var, width=50, relief="sunken", borderwidth=2
                 ).pack(side="left", padx=(0, 6))
        tk.Button(f2, text="浏览", command=lambda: self._browse_dir("a"), width=8).pack(side="left")

        tk.Label(content, text="输出文件夹 B（右键保存）：", anchor="w", bg="#f0f0f0"
                 ).pack(fill="x", padx=12, pady=(14, 2))
        f3 = tk.Frame(content, bg="#f0f0f0")
        f3.pack(fill="x", padx=12)
        tk.Entry(f3, textvariable=self.dir_b_var, width=50, relief="sunken", borderwidth=2
                 ).pack(side="left", padx=(0, 6))
        tk.Button(f3, text="浏览", command=lambda: self._browse_dir("b"), width=8).pack(side="left")

        # 底部栏（始终固定于下边缘）
        bottom = tk.Frame(f, bg="#f0f0f0")
        bottom.pack(fill="x", side="bottom")

        self.finish_btn = tk.Button(bottom, text="开始处理", command=self._on_finish,
                                    width=20, relief="raised", borderwidth=2, state="disabled")
        self.finish_btn.pack(pady=(0, 6))

        self.setup_status = tk.StringVar(value="就绪")
        tk.Label(bottom, textvariable=self.setup_status, anchor="center", wraplength=500,
                 relief="sunken", borderwidth=1, bg="#f0f0f0"
                 ).pack(fill="x", padx=12, pady=(0, 14))
        self.source_var.trace("w", self._check_ready)
        self.dir_a_var.trace("w", self._check_ready)
        self.dir_b_var.trace("w", self._check_ready)

    def _browse_source(self):
        p = filedialog.askopenfilename(title="选择源文件",
                                       filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if p:
            self.source_var.set(p)

    def _browse_dir(self, target: str):
        p = filedialog.askdirectory(title="选择输出文件夹")
        if p:
            if target == "a":
                self.dir_a_var.set(p)
            else:
                self.dir_b_var.set(p)

    def _check_ready(self, *args):
        a, b, c = self.source_var.get().strip(), self.dir_a_var.get().strip(), self.dir_b_var.get().strip()
        ready = bool(a and b and c)
        self.finish_btn.config(state="normal" if ready else "disabled")
        if ready:
            self.setup_status.set("已全部选择，点击「开始处理」进入分割界面")

    def _on_finish(self):
        src, d_a, d_b = self.source_var.get().strip(), self.dir_a_var.get().strip(), self.dir_b_var.get().strip()
        if not os.path.isfile(src):
            self.setup_status.set("错误：源文件不存在"); return
        if os.path.normpath(d_a) == os.path.normpath(d_b):
            self.setup_status.set("错误：输出文件夹 A 和 B 不能是同一个文件夹"); return
        self.setup_frame.pack_forget()
        GlobalCounter.reset()
        self.core.output_a, self.core.output_b = d_a, d_b
        total = self.core.load_file(src)
        self.split_page.pack(fill="both", expand=True)
        self._update_display()
        self._flash_status(f"已加载：{os.path.basename(src)}，共 {total} 行原始内容", "green")

    def _build_split_page(self):
        f = self.split_page
        top_frame = tk.Frame(f, bg="#f0f0f0", relief="sunken", borderwidth=1)
        top_frame.pack(fill="x", padx=4, pady=(4, 2))
        self.remain_label = tk.Label(top_frame, text="剩余 0 行", font=("Consolas", 11), anchor="w", bg="#f0f0f0")
        self.remain_label.pack(side="left", padx=8, pady=2)
        self.op_status_label = tk.Label(top_frame, textvariable=self._last_op_status,
                                        font=("Consolas", 11), anchor="e", bg="#f0f0f0", width=30)
        self.op_status_label.pack(side="right", padx=8, pady=2)

        middle_frame = tk.Frame(f, bg="white")
        middle_frame.pack(fill="both", expand=True, padx=4, pady=2)
        self.line_canvas = tk.Canvas(middle_frame, width=40, bg="#f5f5f5", highlightthickness=0, relief="flat")
        self.line_canvas.pack(side="left", fill="y")
        self.v_scrollbar = tk.Scrollbar(middle_frame, orient="vertical")
        self.v_scrollbar.pack(side="right", fill="y")
        self.text_widget = tk.Text(middle_frame, wrap="none", font=("Consolas", 10),
                                   bg="white", fg="black", relief="sunken", borderwidth=2,
                                   state="disabled", cursor="arrow", padx=8, pady=4,
                                   yscrollcommand=self._on_text_scroll)
        self.text_widget.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.config(command=self._on_scrollbar)
        self.text_widget.bind("<Motion>", self._on_mouse_move)
        self.text_widget.bind("<Button-1>", self._on_left_click)
        self.text_widget.bind("<Button-3>", self._on_right_click)
        self.text_widget.bind("<Button-2>", self._on_right_click)

        bottom_frame = tk.Frame(f, bg="#d0d0d0", relief="sunken", borderwidth=1)
        bottom_frame.pack(fill="x", padx=4, pady=(2, 4))
        tk.Label(bottom_frame, text="左键点击分割线 → 保存到 A    |    右键点击分割线 → 保存到 B",
                 font=("Consolas", 9), anchor="center", bg="#d0d0d0", fg="#333333"
                 ).pack(fill="x", padx=8, pady=2)

    def _update_display(self):
        text = self.text_widget
        text.config(state="normal")
        text.delete("1.0", "end")
        self.line_canvas.delete("all")
        if not self.core.lines:
            text.insert("1.0", "【处理完成，无剩余内容】")
            text.config(state="disabled", fg="gray")
            text.tag_configure("center", justify="center")
            text.tag_add("center", "1.0", "end")
            self.remain_label.config(text="剩余 0 行")
            return
        text.config(fg="black")
        self.remain_label.config(text=f"剩余 {len(self.core.lines)} 行")
        content = "\n".join(self.core.lines)
        text.insert("1.0", content)
        self.line_canvas.config(width=45)
        line_count = len(self.core.lines)
        font_height = self._get_font_height()
        self.line_canvas.config(scrollregion=(0, 0, 40, line_count * font_height + 8))
        for i in range(1, line_count + 1):
            y = (i - 1) * font_height + 4
            self.line_canvas.create_text(38, y, anchor="ne", text=str(i), font=("Consolas", 10), fill="#888888")
        self.separator_tags.clear()
        self._sep_index_to_tag.clear()
        for i, line_text in enumerate(self.core.lines):
            if line_text == TextSplitterCore.SEPARATOR:
                tag_name = f"sep_{i}"
                self.separator_tags[tag_name] = i
                self._sep_index_to_tag[i] = tag_name
                text.tag_add(tag_name, f"{i+1}.0", f"{i+1}.end")
                text.tag_configure(tag_name, foreground="#999999", background="white", font=("Consolas", 10))
        text.config(state="disabled")

    def _get_font_height(self):
        if not hasattr(self, "_cached_font_height"):
            try:
                self._cached_font_height = tk.font.Font(font=("Consolas", 10)).metrics("linespace")
            except Exception:
                self._cached_font_height = 18
        return self._cached_font_height

    def _on_text_scroll(self, *args):
        self.line_canvas.yview_moveto(args[0])
        self.v_scrollbar.set(*args)

    def _on_scrollbar(self, *args):
        self.text_widget.yview(*args)
        self.line_canvas.yview(*args)

    def _get_line_index(self, event) -> int:
        index = self.text_widget.index(f"@{event.x},{event.y}")
        return -1 if not index else int(index.split(".")[0]) - 1

    def _clear_all_highlights(self):
        for tag_name in self.separator_tags:
            self.text_widget.tag_configure(tag_name, foreground="#999999", background="white", font=("Consolas", 10))

    def _on_mouse_move(self, event):
        idx = self._get_line_index(event)
        if idx >= 0 and self.core.is_separator(idx):
            if self.core._hovered_index != idx:
                self._clear_all_highlights()
                tag_name = self._sep_index_to_tag.get(idx)
                if tag_name:
                    self.text_widget.config(cursor="hand2")
                    self.text_widget.tag_configure(tag_name, foreground="#000080", background="#e0f0ff", font=("Consolas", 10))
                    self.core._hovered_index = idx
        else:
            if self.core._hovered_index is not None:
                self._clear_all_highlights()
                self.text_widget.config(cursor="arrow")
                self.core._hovered_index = None

    def _on_left_click(self, event):
        idx = self._get_line_index(event)
        if idx >= 0 and self.core.is_separator(idx):
            self._do_save(idx, self.core.output_a)

    def _on_right_click(self, event):
        idx = self._get_line_index(event)
        if idx >= 0 and self.core.is_separator(idx):
            self._do_save(idx, self.core.output_b)

    def _do_save(self, idx: int, target_dir: str):
        if not self.core.lines:
            self._flash_status("无剩余内容", "red"); return
        if not target_dir:
            self._flash_status("错误：未设置保存目录", "red"); return
        result = self.core.save_and_remove(idx, target_dir)
        if result["saved"]:
            self._flash_status(f"保存 {result['filename']} → {os.path.basename(target_dir)}", "green")
        else:
            self._flash_status(result["message"], "red")
        self._update_display()

    def _flash_status(self, msg: str, color: str):
        self._last_op_status.set(msg)
        self.op_status_label.config(fg=color)
        if self._last_op_timer:
            self.root.after_cancel(self._last_op_timer)
        self._last_op_timer = self.root.after(4000, self._clear_status)

    def _clear_status(self):
        self._last_op_status.set("")
        self._last_op_timer = None

    @property
    def root(self):
        return self.winfo_toplevel()


# ============================================================================
# 模式一：文件名提取界面（原有功能）
# ============================================================================

class FileExtractFrame(tk.Frame):
    """文件名提取界面 Frame。"""

    def __init__(self, master):
        super().__init__(master, bg="#f0f0f0")
        self.input_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.keep_path_var = tk.BooleanVar(value=False)
        self.keep_ext_var = tk.BooleanVar(value=True)
        self.char_limit_var = tk.StringVar(value="0")
        self._processing_thread = None
        self.process_btn = None
        self.status_label = None
        self.status_var = tk.StringVar(value="就绪")
        self._build_ui()

    def _build_ui(self):
        # 上部内容区（填充剩余空间）
        content = tk.Frame(self, bg="#f0f0f0")
        content.pack(fill="both", expand=True)

        tk.Label(content, text="输入文件：", anchor="w", bg="#f0f0f0"
                 ).pack(fill="x", padx=12, pady=(20, 2))
        f1 = tk.Frame(content, bg="#f0f0f0")
        f1.pack(fill="x", padx=12)
        tk.Entry(f1, textvariable=self.input_path_var, width=50, relief="sunken", borderwidth=2
                 ).pack(side="left", padx=(0, 6))
        tk.Button(f1, text="浏览", command=self._browse_input, width=8).pack(side="left")

        tk.Label(content, text="输出目录：", anchor="w", bg="#f0f0f0"
                 ).pack(fill="x", padx=12, pady=(14, 2))
        f2 = tk.Frame(content, bg="#f0f0f0")
        f2.pack(fill="x", padx=12)
        tk.Entry(f2, textvariable=self.output_dir_var, width=50, relief="sunken", borderwidth=2
                 ).pack(side="left", padx=(0, 6))
        tk.Button(f2, text="浏览", command=self._browse_output, width=8).pack(side="left")

        cf = tk.Frame(content, bg="#f0f0f0")
        cf.pack(fill="x", padx=12, pady=(16, 0))
        tk.Checkbutton(cf, text="保留路径", variable=self.keep_path_var,
                       onvalue=True, offvalue=False, bg="#f0f0f0").pack(side="left", padx=(0, 20))
        tk.Checkbutton(cf, text="保留后缀", variable=self.keep_ext_var,
                       onvalue=True, offvalue=False, bg="#f0f0f0").pack(side="left")

        tk.Label(content, text="每组字符数（0 = 不分组）：", anchor="w", bg="#f0f0f0"
                 ).pack(fill="x", padx=12, pady=(14, 2))
        sf = tk.Frame(content, bg="#f0f0f0")
        sf.pack(fill="x", padx=12)
        tk.Spinbox(sf, from_=0, to=99999, textvariable=self.char_limit_var,
                   width=12, relief="sunken", borderwidth=2).pack(side="left")

        # 底部栏（始终固定于下边缘）
        bottom = tk.Frame(self, bg="#f0f0f0")
        bottom.pack(fill="x", side="bottom")

        self.process_btn = tk.Button(bottom, text="开始处理", command=self._start_processing,
                                     width=20, relief="raised", borderwidth=2)
        self.process_btn.pack(pady=(0, 6))
        self.status_var.set("就绪")
        self.status_label = tk.Label(bottom, textvariable=self.status_var, anchor="center",
                                     wraplength=500, relief="sunken", borderwidth=1, bg="#f0f0f0")
        self.status_label.pack(fill="x", padx=12, pady=(0, 14))

    def _browse_input(self):
        p = filedialog.askopenfilename(title="选择输入文件", filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if p:
            self.input_path_var.set(p)

    def _browse_output(self):
        p = filedialog.askdirectory(title="选择输出文件夹")
        if p:
            self.output_dir_var.set(p)

    def _set_status(self, msg):
        self.master.after(0, lambda: self.status_var.set(msg))

    def _start_processing(self):
        inp, out, cs = self.input_path_var.get().strip(), self.output_dir_var.get().strip(), self.char_limit_var.get().strip()
        if not inp:
            self._set_status("错误：请选择输入文件"); return
        if not out:
            self._set_status("错误：请选择输出目录"); return
        if not cs.isdigit():
            self._set_status("错误：每组字符数必须为非负整数"); return
        self.process_btn.config(state="disabled")
        self._set_status("处理中…")
        self._processing_thread = threading.Thread(
            target=self._task,
            args=(inp, out, int(cs), self.keep_path_var.get(),
                  self.keep_ext_var.get()),
            daemon=True)
        self._processing_thread.start()

    def _task(self, inp, out, cl, kp, ke):
        def en():
            self.master.after(0, lambda: self.process_btn.config(state="normal"))
        try:
            r = FileProcessor.process(inp, out, cl, kp, ke)
            tl, tg = r["total_lines"], r["total_groups"]
            if tl == 0:
                self._set_status("完成：输入文件为空，未生成任何文件")
            else:
                self._set_status(f"完成：读取 {tl} 行，生成 {tg} 个文件（{r['output_dir']}）")
        except FileNotFoundError as e:
            self._set_status(f"错误：{e}")
        except UnicodeDecodeError:
            self._set_status("错误：输入文件不是有效的 UTF-8 编码")
        except Exception as e:
            self._set_status(f"错误：{e}")
        finally:
            en()


# ============================================================================
# 主窗口 —— 标签栏常驻 + 内容区切换
# ============================================================================

class Application:
    """经典 Windows 实用工具风格，标签栏始终可见，内容区显示欢迎页或功能页。"""

    WIN_W = 560
    WIN_H = 440

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FileFission")
        self.root.resizable(False, False)
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}")
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
            if os.path.isfile(icon_path):
                self.root.iconbitmap(icon_path)
            elif getattr(sys, "frozen", False):
                self.root.iconbitmap(sys.executable)
        except Exception:
            pass

        self.extract_frame = None
        self.splitter_frame = None
        self.splash_frame = None
        self.content_frame = None
        self._active_tab = -1

        # 构建主框架
        self._build_tabs()

        # 内容区容器
        self.content_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.content_frame.pack(fill="both", expand=True)

        # 显示欢迎页
        self._show_splash()

    # ========== 标签栏 ==========

    def _build_tabs(self):
        tab_bar = tk.Frame(self.root, bg="#c0c0c0", relief="raised", borderwidth=2)
        tab_bar.pack(fill="x", padx=0, pady=0)

        self.tab_btns = []

        btn_extract = tk.Button(
            tab_bar, text=" 文件名提取 ",
            command=lambda: self._switch_to(0),
            relief="raised", borderwidth=2,
            font=("Consolas", 10, "bold"),
            padx=12, pady=2,
        )
        btn_extract.pack(side="left", padx=(4, 0), pady=3)
        self.tab_btns.append(btn_extract)

        btn_splitter = tk.Button(
            tab_bar, text=" 文本分割器 ",
            command=lambda: self._switch_to(1),
            relief="raised", borderwidth=2,
            font=("Consolas", 10, "bold"),
            padx=12, pady=2,
        )
        btn_splitter.pack(side="left", padx=(2, 4), pady=3)
        self.tab_btns.append(btn_splitter)

    def _update_tab_style(self):
        for i, btn in enumerate(self.tab_btns):
            if i == self._active_tab:
                btn.config(relief="sunken", bg="#e0e0e0")
            else:
                btn.config(relief="raised", bg="#f0f0f0")

    # ========== 内容切换 ==========

    def _clear_content(self):
        if self.splash_frame:
            self.splash_frame.pack_forget()
        if self.extract_frame:
            self.extract_frame.pack_forget()
        if self.splitter_frame:
            self.splitter_frame.pack_forget()

    def _switch_to(self, idx: int):
        if idx == self._active_tab:
            return
        self._clear_content()
        if idx == 0:
            self._show_extract()
        else:
            self._show_splitter()

    def _show_splash(self):
        """显示欢迎页（ASCII 字符画 LOGO + 版本号）。"""
        self._clear_content()
        self._active_tab = -1
        self._update_tab_style()

        self.splash_frame = tk.Frame(self.content_frame, bg="#f0f0f0")
        self.splash_frame.pack(fill="both", expand=True)

        # FILEFISSION 11个字母 ASCII 字符画（全部验证正确）
        logo_text = (
            "\n"
            "   ███████╗██╗██╗     ███████╗███████╗██╗███████╗███████╗██╗ ██████╗ ███╗   ██╗\n"
            "   ██╔════╝██║██║     ██╔════╝██╔════╝██║██╔════╝██╔════╝██║██╔═══██╗████╗  ██║\n"
            "   █████╗  ██║██║     █████╗  █████╗  ██║███████╗███████╗██║██║   ██║██╔██╗ ██║\n"
            "   ██╔══╝  ██║██║     ██╔══╝  ██╔══╝  ██║╚════██║╚════██║██║██║   ██║██║╚██╗██║\n"
            "   ██║     ██║███████╗███████╗██║     ██║███████╗███████╗██║╚██████╔╝██║ ╚████║\n"
            "   ╚═╝     ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝\n"
        )
        logo_label = tk.Label(
            self.splash_frame,
            text=logo_text,
            font=("Consolas", 9),
            fg="#333333",
            bg="#f0f0f0",
            justify="left",
        )
        logo_label.pack(pady=(60, 2))

        # 版本号紧跟在标题下方
        ver = tk.Label(
            self.splash_frame,
            text="v2.0",
            font=("Consolas", 10),
            fg="#999999",
            bg="#f0f0f0",
        )
        ver.pack()

    def _show_extract(self):
        self.root.title("FileFission - 文件名提取")
        if not self.extract_frame:
            self.extract_frame = FileExtractFrame(self.content_frame)
        self.extract_frame.pack(fill="both", expand=True)
        self._active_tab = 0
        self._update_tab_style()

    def _show_splitter(self):
        self.root.title("FileFission - 文本分割器")
        if not self.splitter_frame:
            self.splitter_frame = TextSplitterFrame(self.content_frame)
        self.splitter_frame.pack(fill="both", expand=True)
        self._active_tab = 1
        self._update_tab_style()


# ============================================================================
# 入口
# ============================================================================

def main():
    if getattr(sys, "frozen", False):
        pass
    root = tk.Tk()
    app = Application(root)
    root.mainloop()


if __name__ == "__main__":
    main()