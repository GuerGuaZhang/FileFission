# -*- coding: utf-8 -*-
"""
FileFission —— 文件名核裂变工具：批量提取文件名并按字符数分组输出

经典实用工具风格，所有反馈通过底部状态栏显示，无弹窗。
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog


# ============================================================================
# 核心处理逻辑
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
# 主窗口
# ============================================================================

class Application:
    """经典 Windows 实用工具风格，所有信息显示在状态栏，无弹窗。"""

    W = 420
    H = 340

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FileFission")
        self.root.resizable(False, False)
        self.root.geometry(f"{self.W}x{self.H}")
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
            if os.path.isfile(icon_path):
                self.root.iconbitmap(icon_path)
            elif getattr(sys, "frozen", False):
                self.root.iconbitmap(sys.executable)
        except Exception:
            pass

        # 控件变量
        self.input_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.keep_path_var = tk.BooleanVar(value=False)
        self.keep_ext_var = tk.BooleanVar(value=True)
        self.char_limit_var = tk.StringVar(value="0")

        self._build_ui()
        self._processing_thread = None

    def _build_ui(self):
        """构建界面：经典风格，全部使用标准 tk 控件默认外观"""

        # ====== 输入文件 ======
        tk.Label(self.root, text="输入文件：", anchor="w"
                 ).pack(fill="x", padx=12, pady=(14, 2))
        f1 = tk.Frame(self.root)
        f1.pack(fill="x", padx=12)
        tk.Entry(f1, textvariable=self.input_path_var, width=50,
                 relief="sunken", borderwidth=2
                 ).pack(side="left", padx=(0, 6))
        tk.Button(f1, text="浏览", command=self._browse_input, width=8
                  ).pack(side="left")

        # ====== 输出目录 ======
        tk.Label(self.root, text="输出目录：", anchor="w"
                 ).pack(fill="x", padx=12, pady=(10, 2))
        f2 = tk.Frame(self.root)
        f2.pack(fill="x", padx=12)
        tk.Entry(f2, textvariable=self.output_dir_var, width=50,
                 relief="sunken", borderwidth=2
                 ).pack(side="left", padx=(0, 6))
        tk.Button(f2, text="浏览", command=self._browse_output, width=8
                  ).pack(side="left")

        # ====== 复选框 ======
        cf = tk.Frame(self.root)
        cf.pack(fill="x", padx=12, pady=(12, 0))
        tk.Checkbutton(cf, text="保留路径", variable=self.keep_path_var,
                       onvalue=True, offvalue=False
                       ).pack(side="left", padx=(0, 20))
        tk.Checkbutton(cf, text="保留后缀", variable=self.keep_ext_var,
                       onvalue=True, offvalue=False
                       ).pack(side="left")

        # ====== 每组字符数 ======
        tk.Label(self.root, text="每组字符数（0 = 不分组）：", anchor="w"
                 ).pack(fill="x", padx=12, pady=(10, 2))
        sf = tk.Frame(self.root)
        sf.pack(fill="x", padx=12)
        tk.Spinbox(sf, from_=0, to=99999,
                   textvariable=self.char_limit_var,
                   width=12, relief="sunken", borderwidth=2
                   ).pack(side="left")

        # ====== 开始处理按钮 ======
        bf = tk.Frame(self.root)
        bf.pack(pady=(18, 6))
        self.process_btn = tk.Button(
            bf, text="开始处理",
            command=self._start_processing,
            width=20, relief="raised", borderwidth=2,
        )
        self.process_btn.pack()

        # ====== 状态栏（代替所有弹窗） ======
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        self.status_label = tk.Label(
            self.root, textvariable=self.status_var,
            anchor="center", wraplength=390,
            relief="sunken", borderwidth=1,
        )
        self.status_label.pack(fill="x", padx=12, pady=(6, 10))

    # ---- 回调 ----

    def _browse_input(self):
        p = filedialog.askopenfilename(
            title="选择输入文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if p:
            self.input_path_var.set(p)

    def _browse_output(self):
        p = filedialog.askdirectory(title="选择输出文件夹")
        if p:
            self.output_dir_var.set(p)

    def _set_status(self, msg):
        """安全更新状态栏（可在子线程中调用）"""
        self.root.after(0, lambda: self.status_var.set(msg))

    def _start_processing(self):
        inp = self.input_path_var.get().strip()
        out = self.output_dir_var.get().strip()
        cs = self.char_limit_var.get().strip()

        if not inp:
            self._set_status("错误：请选择输入文件")
            return
        if not out:
            self._set_status("错误：请选择输出目录")
            return
        if not cs.isdigit():
            self._set_status("错误：每组字符数必须为非负整数")
            return

        self.process_btn.config(state="disabled")
        self._set_status("处理中…")

        self._processing_thread = threading.Thread(
            target=self._task,
            args=(inp, out, int(cs), self.keep_path_var.get(),
                  self.keep_ext_var.get()),
            daemon=True).start()

    def _task(self, inp, out, cl, kp, ke):
        def en():
            self.root.after(0, lambda: self.process_btn.config(state="normal"))

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