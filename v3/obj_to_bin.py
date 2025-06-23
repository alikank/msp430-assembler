import tkinter as tk
from tkinter import filedialog, messagebox
import os

def parse_obj_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    data = []
    reading = False
    for line in lines:
        line = line.strip()
        if line.startswith("SECTION .text") or line.startswith("SECTION .data"):
            reading = True
            continue
        elif line == "EOF":
            break
        elif line.startswith("SECTION"):
            reading = False
            continue

        if reading and line.startswith("0x"):
            value = int(line, 16)
            data.append(value)

    return data

def convert_to_bin(obj_path, output_path):
    data = parse_obj_file(obj_path)
    with open(output_path, 'wb') as f:
        for word in data:
            f.write(word.to_bytes(2, byteorder='little'))  # MSP430 = little endian

def select_obj_file():
    filepath = filedialog.askopenfilename(filetypes=[("OBJ Dosyaları", "*.obj")])
    if filepath:
        try:
            bin_filename = os.path.splitext(filepath)[0] + ".bin"
            convert_to_bin(filepath, bin_filename)
            messagebox.showinfo("Başarılı", f"Binary dosya oluşturuldu:\n{bin_filename}")
        except Exception as e:
            messagebox.showerror("Hata", f"Bir hata oluştu:\n{e}")

# === GUI ===
root = tk.Tk()
root.title("📦 OBJ ➜ BIN Dönüştürücü")
root.geometry("420x200")
root.configure(bg="#f2f2f2")

# Başlık
title_label = tk.Label(
    root,
    text="MSP430 OBJ ➜ BIN Dönüştürücü",
    font=("Segoe UI", 14, "bold"),
    fg="#333",
    bg="#f2f2f2"
)
title_label.pack(pady=(20, 10))

# Açıklama
desc_label = tk.Label(
    root,
    text="Bir .obj dosyası seçin ve .bin dosyasına dönüştürün.",
    font=("Segoe UI", 10),
    fg="#555",
    bg="#f2f2f2",
    wraplength=360
)
desc_label.pack()

# Buton
button = tk.Button(
    root,
    text="📁 OBJ Dosyasını Seç",
    command=select_obj_file,
    font=("Segoe UI", 11),
    bg="#4CAF50",
    fg="white",
    activebackground="#45a049",
    padx=10,
    pady=5,
    relief="raised",
    bd=2
)
button.pack(pady=20)

# Footer
footer = tk.Label(
    root,
    text="obj to bin converter",
    font=("Segoe UI", 8),
    fg="#aaa",
    bg="#f2f2f2"
)
footer.pack(side="bottom", pady=5)

root.mainloop()
