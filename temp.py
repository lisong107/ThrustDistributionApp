import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from assign_force_vector import assign_force_vector
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # for Windows 8.1 or later
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # fallback for older Windows
    except Exception:
        pass


# === 函数1：加载 Excel 并构造 Rb ===
def load_rb_from_excel():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not file_path:
        raise RuntimeError("未选择文件")

    df = pd.read_excel(file_path, usecols=[0, 1, 2], header=None, engine="openpyxl")
    df.columns = ["col1", "radius", "theta"]

    # 转为数值，忽略非法数据
    radius = pd.to_numeric(df["radius"], errors="coerce")
    theta = pd.to_numeric(df["theta"], errors="coerce")
    valid = ~radius.isna() & ~theta.isna()

    radius = radius[valid].to_numpy()
    theta = theta[valid].to_numpy()

    # 如为角度单位，取消注释下面一行
    # theta = np.radians(theta)

    cosb = radius * np.cos(theta)
    sinb = radius * np.sin(theta)
    Rb = np.column_stack((cosb, sinb, np.ones(len(radius))))
    return Rb


# === 函数2：构造 J_in ===
def fcn(rb):
    m = rb.shape[0]
    max_m = 28
    u = np.zeros((max_m, 3))
    u[:m, :] = np.tile([0, 0, 1], (m, 1))
    J = np.zeros((6, max_m))
    cross_rb_u = np.cross(rb, u[:m, :])
    J[:, :m] = np.vstack((u[:m].T, cross_rb_u.T))
    return J, m


# === 主程序 ===
Rb = load_rb_from_excel()
J_in, n = fcn(Rb)

# Seg_in = np.array([1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 1, 1])
Seg_in = np.array(range(1, n + 1))  # 是否启用同块同压功能
Ret_in = np.zeros(n, dtype=bool)

f_in = np.ones(n)
F_in = np.array([0, 0, 1000, 200, -300, 0])
lb, ub = 0, 1000

f_out, success, msg = assign_force_vector(
    f_in, F_in, J_in[:, :n], Seg_in, Ret_in, lb, ub
)

print("Success:", success)
if not success:
    print("Message:", msg)
print("f_out:")
for i, val in enumerate(f_out):
    print(f"  [{i+1:3d}] {val:.3f}")

print("J_in * f_out:", np.round(J_in[:, :n] @ f_out, 3))
