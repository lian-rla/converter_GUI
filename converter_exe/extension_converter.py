import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from tkinter import ttk
import time
from typing import Optional, Tuple, List
import sys


if getattr(sys, "frozen", False):
    base_dir = sys._MEIPASS
    os.environ["PATH"] = base_dir + os.pathsep + os.environ.get("PATH", "")

    tcl_base = os.path.join(base_dir, "tcl")
    os.environ.setdefault("TCL_LIBRARY", os.path.join(tcl_base, "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY",  os.path.join(tcl_base, "tk8.6"))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
# ------------------------------------------------------

# ------------------------------------------------------------

def log(msg: str):
    output_box.insert(tk.END, msg + "\n")
    output_box.see(tk.END)
    root.update()

# ──────────────────────────────────────────────────────────────────────────────
# FFmpeg 옵션 처리
# ──────────────────────────────────────────────────────────────────────────────

def parse_user_params() -> Tuple[int, Optional[int], Optional[float], str]:
    try:
        fr = int(entry_framerate.get().strip())
    except Exception:
        fr = 30

    crf_val = entry_crf.get().strip()
    crf: Optional[int] = None
    if crf_val != "":
        try:
            crf = int(crf_val)
        except Exception:
            crf = None

    scale_val = entry_scale.get().strip()
    scale: Optional[float] = None
    if scale_val != "":
        try:
            scale = float(scale_val)
            if scale <= 0:
                scale = None
        except Exception:
            scale = None

    ext = ext_var.get()
    return fr, crf, scale, ext

def build_codec_and_container(ext: str):
    if ext.lower() in ("mp4", "mov"):
        return "libx264", ["-pix_fmt", "yuv420p"]
    elif ext.lower() == "avi":
        return "mpeg4", []
    else:
        return "libx264", ["-pix_fmt", "yuv420p"]

def map_crf_for_avi(crf: Optional[int]) -> Optional[int]:
    if crf is None:
        return None
    q = int(max(2, min(31, round((crf - 8) / 3))))
    return q

def build_scale_filter(scale: Optional[float]):
    if scale is None or abs(scale - 1.0) < 1e-6:
        return []
    return ["-vf", f"scale=iw*{scale}:ih*{scale}"]

def build_ffmpeg_cmd(input_path: str, output_path: str, mode: str = "primary", with_progress: bool = True):
    fr, crf, scale, ext = parse_user_params()
    codec, extra = build_codec_and_container(ext)
    scale_args = build_scale_filter(scale)

    cmd: List[str] = ["ffmpeg", "-y"]
    if mode == "fallback":
        cmd += ["-f", "h264", "-fflags", "+genpts"]

    # 진행률 파이프
    if with_progress:
        cmd += ["-progress", "pipe:1", "-nostats"]

    cmd += ["-framerate", str(fr), "-i", input_path, "-c:v", codec]

    if codec == "libx264":
        cmd += ["-crf", str(crf if crf is not None else 31), "-preset", "medium"]
    elif codec == "mpeg4":
        q = map_crf_for_avi(crf)
        if q is not None:
            cmd += ["-q:v", str(q)]

    cmd += scale_args + extra + [output_path]
    return cmd

# ──────────────────────────────────────────────────────────────────────────────
# 진행률 관련 유틸
# ──────────────────────────────────────────────────────────────────────────────

def ffprobe_duration_seconds(input_path: str) -> Optional[float]:
    try:
        # format.duration 먼저 시도, 없으면 streams의 duration 시도
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration:stream=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        # 여러 줄이 나올 수 있어 숫자 파싱 가능한 첫 번째 값을 사용
        for line in out.splitlines():
            line = line.strip()
            try:
                val = float(line)
                if val > 0:
                    return val
            except:
                continue
        return None
    except Exception:
        return None

def update_overall_progress(done: int, total: int):
    pct = 0 if total == 0 else (done / total) * 100
    overall_var.set(pct)
    overall_label_var.set(f"전체 진행률: {done}/{total} ({pct:.1f}%)")
    root.update_idletasks()

def set_file_progress(pct: Optional[float], indeterminate: bool):
    if indeterminate:
        file_progress.configure(mode="indeterminate")
        if not getattr(set_file_progress, "_running", False):
            file_progress.start(10)  # 10ms step
            set_file_progress._running = True
        file_label_var.set("현재 파일 변환 : 변환중...")
    else:
        if getattr(set_file_progress, "_running", False):
            file_progress.stop()
            set_file_progress._running = False
        file_progress.configure(mode="determinate")
        if pct is None:
            pct = 0.0
        if pct < 0: pct = 0.0
        if pct > 100: pct = 100.0
        file_var.set(pct)
        file_label_var.set(f"현재 파일 진행률: {pct:.1f}%")
    root.update_idletasks()

set_file_progress._running = False

# ──────────────────────────────────────────────────────────────────────────────
# 변환(1파일) 실행 + 진행률 파싱
# ──────────────────────────────────────────────────────────────────────────────

def run_ffmpeg_with_progress(input_path: str, output_path: str, mode: str = "primary") -> bool:
    duration = ffprobe_duration_seconds(input_path)
    indeterminate = duration is None or duration <= 0

    # 진행률 초기화
    root.after(0, set_file_progress, 0.0, indeterminate)

    cmd = build_ffmpeg_cmd(input_path, output_path, mode=mode, with_progress=True)

    # Popen으로 라인 단위 읽기
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    try:
        for line in proc.stdout:
            line = line.strip()
            # 로그창에도 흘려보내고 싶으면 주석 해제
            # root.after(0, log, line)

            if line.startswith("out_time_ms=") and not indeterminate:
                try:
                    out_ms = float(line.split("=", 1)[1].strip())
                    pct = (out_ms / (duration * 1_000_000.0)) * 100.0
                    root.after(0, set_file_progress, pct, False)
                except:
                    pass
            elif line.startswith("progress="):
                # 'continue' or 'end'
                if line.endswith("end"):
                    root.after(0, set_file_progress, 100.0, False if not indeterminate else True)
    finally:
        proc.wait()

    # 종료 코드 확인
    success = (proc.returncode == 0)
    if indeterminate:
        # indeterminate 바 멈추기
        root.after(0, set_file_progress, 100.0 if success else 0.0, True)
        # 강제로 멈춤
        if getattr(set_file_progress, "_running", False):
            file_progress.stop()
            set_file_progress._running = False
            file_progress.configure(mode="determinate")

    return success

# ──────────────────────────────────────────────────────────────────────────────
# 변환 함수
# ──────────────────────────────────────────────────────────────────────────────

def convert_sec_folder(sec_folder: str, overall_ctx: dict = None):
    files = [f for f in os.listdir(sec_folder) if f.lower().endswith(".sec")]
    if not files:
        log(f"{sec_folder} → 변환할 .sec 없음\n")
        return

    _, _, _, ext = parse_user_params()
    folder_name = os.path.basename(os.path.normpath(sec_folder))
    parent_folder = os.path.dirname(sec_folder)
    output_folder = os.path.join(parent_folder, f"{folder_name}_{ext.lower()}")
    os.makedirs(output_folder, exist_ok=True)

    log(f"변환 시작: {sec_folder}")
    log(f"저장 폴더: {output_folder}")
    log(f".sec 파일 {len(files)}개 발견\n")

    start_time = time.time()

    for filename in files:
        input_path = os.path.join(sec_folder, filename)
        base_name, _ = os.path.splitext(filename)
        output_path = os.path.join(output_folder, base_name + f".{ext}")

        log(f"▶ 변환 중: {filename}")
        ok = run_ffmpeg_with_progress(input_path, output_path, mode="primary")
        if ok:
            log(f"완료: {os.path.basename(output_path)}\n")
        else:
            log(f"실패: {filename}, 강제 재시도 중...")
            ok2 = run_ffmpeg_with_progress(input_path, output_path, mode="fallback")
            if ok2:
                log(f"완료 (강제변환): {os.path.basename(output_path)}\n")
            else:
                log(f"실패 (강제변환): {filename}\n")

        if overall_ctx is not None:
            overall_ctx["done"] += 1
            root.after(0, update_overall_progress, overall_ctx["done"], overall_ctx["total"])

    total_time = time.time() - start_time
    log(f"소요 시간: {total_time/60:.1f}분")
    log("─" * 60 + "\n")

def convert_single_file(sec_path: str):
    if not sec_path or not sec_path.lower().endswith(".sec"):
        messagebox.showwarning("경고", ".sec 파일을 선택해주세요.")
        return

    _, _, _, ext = parse_user_params()
    base_name = os.path.splitext(os.path.basename(sec_path))[0]
    output_path = os.path.join(os.path.dirname(sec_path), base_name + f".{ext}")

    log(f"단일 파일 변환 시작: {os.path.basename(sec_path)} → {os.path.basename(output_path)}")
    ok = run_ffmpeg_with_progress(sec_path, output_path, mode="primary")
    if ok:
        log(f"완료: {os.path.basename(output_path)}\n")
    else:
        log("실패: 1차 변환, 강제 재시도 중...")
        ok2 = run_ffmpeg_with_progress(sec_path, output_path, mode="fallback")
        if ok2:
            log(f"완료 (강제변환): {os.path.basename(output_path)}\n")
        else:
            log("실패 (강제변환)")

# ──────────────────────────────────────────────────────────────────────────────
# 탐색 함수
# ──────────────────────────────────────────────────────────────────────────────

def find_sec_folders_recursive(root_folder: str):
    sec_folders = []
    for dirpath, _, filenames in os.walk(root_folder):
        if any(f.lower().endswith(".sec") for f in filenames):
            sec_folders.append(dirpath)
    return sec_folders

def process_selected_root(root_folder: str):
    log(f"탐색 시작: {root_folder}")
    targets = find_sec_folders_recursive(root_folder)
    if not targets:
        messagebox.showinfo("알림", ".sec 파일이 포함된 하위 폴더가 없습니다.")
        return

    # 전체 파일 수 계산
    total_files = 0
    for folder in targets:
        total_files += sum(1 for f in os.listdir(folder) if f.lower().endswith(".sec"))

    overall_ctx = {"done": 0, "total": total_files}
    root.after(0, update_overall_progress, 0, total_files)

    # 가장 하위부터 변환
    targets_sorted = sorted(targets, key=lambda p: p.count(os.sep), reverse=True)
    for subfolder in targets_sorted:
        convert_sec_folder(subfolder, overall_ctx=overall_ctx)

    log("선택한 상위 폴더 내 모든 .sec 파일 변환 완료")

# ──────────────────────────────────────────────────────────────────────────────
# 스레드 래퍼
# ──────────────────────────────────────────────────────────────────────────────

def threaded(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t

# ──────────────────────────────────────────────────────────────────────────────
# GUI
# ──────────────────────────────────────────────────────────────────────────────

def select_root_folder():
    global top_root
    folder = filedialog.askdirectory()
    if folder:
        top_root = folder
        top_folder_label.config(text=f"상위 폴더: {folder}")

def start_folder_conversion():
    if not top_root:
        messagebox.showwarning("경고", "상위 폴더를 선택해주세요.")
        return
    threaded(process_selected_root, top_root)

def select_single_sec():
    global single_sec_path
    path = filedialog.askopenfilename(filetypes=[("SEC files", "*.sec"), ("All files", "*.*")])
    if path:
        single_sec_path = path
        single_file_label.config(text=f"단일 파일: {path}")

def start_single_conversion():
    if not single_sec_path:
        messagebox.showwarning("경고", "단일 .sec 파일을 선택해주세요.")
        return
    threaded(convert_single_file, single_sec_path)

top_root = ""
single_sec_path = ""

root = tk.Tk()
root.title("확장자 변환기 (by LeeLab)")
root.geometry("980x720")
root.resizable(False, False)

wrapper = tk.Frame(root)
wrapper.pack(pady=10)

folder_frame = tk.LabelFrame(wrapper, text="폴더 변환", padx=10, pady=8, font=("Arial", 10))
folder_frame.grid(row=0, column=0, sticky="w", padx=8)
btn_sel_root = tk.Button(folder_frame, text="상위 폴더 선택", command=select_root_folder, font=("Arial", 11))
btn_sel_root.grid(row=0, column=0, padx=5, pady=3)
btn_start_root = tk.Button(folder_frame, text="선택 폴더 전체 변환", command=start_folder_conversion, font=("Arial", 11), bg="#4CAF50", fg="white")
btn_start_root.grid(row=0, column=1, padx=5, pady=3)
top_folder_label = tk.Label(folder_frame, text="상위 폴더: 없음", fg="gray")
top_folder_label.grid(row=1, column=0, columnspan=2, sticky="w")

file_frame = tk.LabelFrame(wrapper, text="단일 파일 변환", padx=10, pady=8, font=("Arial", 10))
file_frame.grid(row=0, column=1, sticky="w", padx=8)
btn_sel_single = tk.Button(file_frame, text=".sec 파일 선택", command=select_single_sec, font=("Arial", 11))
btn_sel_single.grid(row=0, column=0, padx=5, pady=3)
btn_start_single = tk.Button(file_frame, text="선택 파일 변환", command=start_single_conversion, font=("Arial", 11), bg="#4CAF50", fg="white")
btn_start_single.grid(row=0, column=1, padx=5, pady=3)
single_file_label = tk.Label(file_frame, text="단일 파일: 없음", fg="gray")
single_file_label.grid(row=1, column=0, columnspan=2, sticky="w")

opt_frame = tk.LabelFrame(root, text="FFmpeg 옵션", padx=10, pady=8)
opt_frame.pack(padx=10, fill="x")

lbl_fr = tk.Label(opt_frame, text="framerate (기본 30):")
lbl_fr.grid(row=0, column=0, sticky="e", padx=5, pady=4)
entry_framerate = tk.Entry(opt_frame, width=10)
entry_framerate.insert(0, "30")
entry_framerate.grid(row=0, column=1, sticky="w", padx=5, pady=4)

lbl_crf = tk.Label(opt_frame, text="화질[crf] (기본 23):")
lbl_crf.grid(row=0, column=2, sticky="e", padx=5, pady=4)
entry_crf = tk.Entry(opt_frame, width=10)
entry_crf.insert(0, "23")
entry_crf.grid(row=0, column=3, sticky="w", padx=5, pady=4)

lbl_scale = tk.Label(opt_frame, text="해상도[scale] (비우면 원본):")
lbl_scale.grid(row=0, column=4, sticky="e", padx=5, pady=4)
entry_scale = tk.Entry(opt_frame, width=12)
entry_scale.insert(0, "")
entry_scale.grid(row=0, column=5, sticky="w", padx=5, pady=4)

lbl_ext = tk.Label(opt_frame, text="출력 확장자:")
lbl_ext.grid(row=1, column=0, sticky="e", padx=5, pady=4)

ext_var = tk.StringVar(value="mp4")
rb_mp4 = tk.Radiobutton(opt_frame, text=".mp4 (H.264)", variable=ext_var, value="mp4")
rb_avi = tk.Radiobutton(opt_frame, text=".avi (MPEG-4 Part 2)", variable=ext_var, value="avi")
rb_mov = tk.Radiobutton(opt_frame, text=".mov (H.264)", variable=ext_var, value="mov")
rb_mp4.grid(row=1, column=1, sticky="w", padx=5)
rb_avi.grid(row=1, column=2, sticky="w", padx=5)
rb_mov.grid(row=1, column=3, sticky="w", padx=5)

hint = tk.Label(opt_frame, fg="#666", justify="left", text=(
    "※ DVR환경에 따라 framerate와 해상도가 다를 수 있습니다. 확인 후 변환해 주세요.\n"
    "※ 화질[crf]는 0 ~ 51 사이 입력해주세요. 숫자가 클 수록 화질이 저하됩니다. 원본유지는 23 입력\n"
    "※ scale은 해상도 입력입니다. (예: 0.5입력 1920x1080 → 960x540 출력 ). 비우면 원본 유지."
))
hint.grid(row=2, column=0, columnspan=6, sticky="w", padx=5, pady=(4,0))

# ──────────────────────────────────────────────────────────────────────────────
# 진행률 영역
# ──────────────────────────────────────────────────────────────────────────────
prog_frame = tk.LabelFrame(root, text="진행 상황", padx=10, pady=8)
prog_frame.pack(padx=10, pady=6, fill="x")

overall_label_var = tk.StringVar(value="전체 진행률: 0/0 (0.0%)")
file_label_var = tk.StringVar(value="현재 파일 진행률: 0.0%")

overall_label = tk.Label(prog_frame, textvariable=overall_label_var)
overall_label.grid(row=0, column=0, sticky="w", padx=5, pady=3, columnspan=2)

overall_var = tk.DoubleVar(value=0.0)
overall_progress = ttk.Progressbar(prog_frame, variable=overall_var, maximum=100, length=700, mode="determinate")
overall_progress.grid(row=1, column=0, sticky="we", padx=5, pady=3, columnspan=2)

file_label = tk.Label(prog_frame, textvariable=file_label_var)
file_label.grid(row=2, column=0, sticky="w", padx=5, pady=3, columnspan=2)

file_var = tk.DoubleVar(value=0.0)
file_progress = ttk.Progressbar(prog_frame, variable=file_var, maximum=100, length=700, mode="determinate")
file_progress.grid(row=3, column=0, sticky="we", padx=5, pady=3, columnspan=2)

# ──────────────────────────────────────────────────────────────────────────────

output_box = scrolledtext.ScrolledText(root, width=120, height=18, font=("Consolas", 10))
output_box.pack(padx=10, pady=10, fill="both")

root.mainloop()
