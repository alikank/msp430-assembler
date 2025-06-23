import os
import re
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import time


class LineNumberedText(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent)
        self.text = scrolledtext.ScrolledText(self, *args, **kwargs)
        self.linenumbers = tk.Canvas(self, width=30, bg='#f0f0f0')
        
        self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)
        self.text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.text.tag_config('label',     foreground='#499C81')
        self.text.tag_config('directive', foreground='#FF8800')
        self.text.tag_config('opcode',    foreground='blue')
        self.text.tag_config('operand1',  foreground='green')
        self.text.tag_config('operand2',  foreground='purple')
        self.text.tag_config('error',     foreground='red')
        
        for seq in ('<KeyRelease>', '<ButtonRelease-1>', '<MouseWheel>'):
            self.text.bind(seq, lambda e: self._on_text_change())

        self.text.config(yscrollcommand=self.on_text_scroll)
        self.textscroll = self.text.vbar
        
        self.update_line_numbers()

    def on_text_scroll(self, *args):
        self.textscroll.set(*args)
        self.update_line_numbers()

    def _on_text_change(self):
        self.update_line_numbers()
        self._highlight_syntax()

    def _highlight_syntax(self):
        lines = self.text.get('1.0', tk.END).splitlines()
        for tag in ('label','directive','opcode','operand1','operand2','error'):
            self.text.tag_remove(tag, '1.0', tk.END)

        asm = MSP430Assembler()

        for row, line in enumerate(lines, start=1):
            raw = line
            m_label = re.match(r"\s*([A-Za-z_]\w*):", raw)
            if m_label:
                start, end = m_label.start(1), m_label.end(1)
                self.text.tag_add('label', f"{row}.{start}", f"{row}.{end}")
                offset = m_label.end()
            else:
                offset = 0

            rest = raw[offset:]
            if rest.lstrip().startswith(';'):
                continue

            m_dir = re.match(r"\s*(\.(?:word|byte|space|text|data|bss|org|end|def|ref))", rest, re.IGNORECASE)
            if m_dir:
                ds, de = m_dir.start(1)+offset, m_dir.end(1)+offset
                self.text.tag_add('directive', f"{row}.{ds}", f"{row}.{de}")
                continue

            m_ins = re.match(
                r"\s*(\w+(?:\.\w+)?)(?:\s+([^,\s]+))?"
                r"(?:\s*,\s*([^,\s]+))?", rest
            )
            if not m_ins:
                continue

            op, opd1, opd2 = m_ins.group(1), m_ins.group(2), m_ins.group(3)
            os_, oe = m_ins.start(1)+offset, m_ins.end(1)+offset

            if op.upper() in asm.instructions:
                self.text.tag_add('opcode', f"{row}.{os_}", f"{row}.{oe}")
            else:
                self.text.tag_add('error', f"{row}.{os_}", f"{row}.{oe}")

            if opd1:
                s1, e1 = m_ins.start(2)+offset, m_ins.end(2)+offset
                self.text.tag_add('operand1', f"{row}.{s1}", f"{row}.{e1}")
            if opd2:
                s2, e2 = m_ins.start(3)+offset, m_ins.end(3)+offset
                self.text.tag_add('operand2', f"{row}.{s2}", f"{row}.{e2}")

    def update_line_numbers(self):
        self.linenumbers.delete("all")
        i = self.text.index("@0,0")
        while True:
            dline = self.text.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.linenumbers.create_text(
                15, y, anchor="n",
                text=linenum,
                font=self.text.cget("font")
            )
            i = self.text.index(f"{i}+1line")


class MSP430Assembler:
    def __init__(self):
        # instruction ve register tabloları
        self.instructions = {
            "MOV": "0100", "MOV.W": "0100",
            "ADD": "0101", "ADD.W": "0101",
            "SUB": "1000", "SUB.W": "1000",
            "CMP": "1001", "RET": "000100110",
            "JNE": "001000", "JEQ": "001001",
            "JNC": "001010", "JC": "001011",
            "JN": "001100", "JGE": "001101",
            "JL": "001110", "JMP": "001111",
            "NOP": "0000", "CALL": "000100101"
        }
        self.registers = {
            "R0": "0000",
            "R1": "0001",
            "R2": "0010",
            "R3": "0011",
            "R4": "0100",
            "R5": "0101",
            "R6": "0110",
            "R7": "0111",
            "R8": "1000",
            "R9": "1001",   
            "R10": "1010",
            "R11": "1011",
            "R12": "1100",
            "R13": "1101",
            "R14": "1110",
            "R15": "1111"
        }

        self.labels = {}
        self.sections = {}
        self.exports = {}   # .def ile tanımlanan sembolleri tutacak
        self.imports = {}    # .ref ile extern ilan edilenleri tutacak
        self.relocations = [] # (symbol, section, offset) kayıtlarımız

    def hexadec_to_binary(self, hexadec):
        return bin(int(hexadec, 16))[2:].zfill(16)

    def binary_to_hex(self, binary):
        if len(binary) % 4 != 0:
            binary = binary.zfill((len(binary)//4 + 1)*4)
        return hex(int(binary, 2))[2:].upper().zfill(len(binary)//4)

    def msp430_hex_addition(self, h1, h2):
        total = (int(h1, 16) + int(h2, 16)) & 0xFFFF
        return format(total, '04x')

    def pass1(self, lines, mapping):
        # otomatik .text ekleme
        if not any(l.strip().startswith(('.text','.data','.bss')) for l in lines):
            lines = ['.text'] + lines
            mapping = [0] + mapping

        address = "0000"
        current_section = ".text"
        base_addrs = {".text":"0000", ".data":"C000", ".bss":"E000"}

        self.labels.clear()
        self.sections.clear()
        self.exports.clear()
        self.imports.clear()
        self.line_addresses = []
        label_set = set()

        self.sections[current_section] = {
            "start": base_addrs[current_section],
            "size": 0,
            "symbols": {},
            "references": []
        }

        for idx, ln in enumerate(lines):
            orig_no = mapping[idx]
            line = ln.strip()
            if not line or line.startswith(";"):
                continue

            # --- .def: export tanımı (export table'a isim ekle, adresi henüz bilinmiyor) ---
            if line.upper().startswith(".DEF"):
                names = re.split(r'[\s,]+', line, maxsplit=1)[1].split(",")
                for n in names:
                    n = n.strip()
                    if n:
                        # adresini daha sonra label gördüğümüzde ayarlayacağız
                        self.exports[n] = None
                continue

            # --- .ref: import tanımı (import table'a isim ekle) ---
            # case-insensitive .ref
            if line.lower().startswith(".ref"):
                names = re.split(r'[\s,]+', line, maxsplit=1)[1].split(",")
                for n in names:
                    n = n.strip()
                    if n:
                        self.imports.setdefault(n, [])
                continue

            # yeni section
            if line.startswith((".text",".data",".bss")):
                current_section = line
                address = base_addrs[current_section]
                self.sections[current_section] = {
                    "start": address,
                    "size": 0,
                    "symbols": {},
                    "references": []
                }
                continue

            # ORG
            if line.upper().startswith("ORG"):
                address = line.split()[1]
                continue

            # label
            if ":" in line:
                lbl, rest = line.split(":", 1)
                if lbl in label_set:
                    raise Exception(f"Label '{lbl}' redefined (satır {orig_no})")
                label_set.add(lbl)
                if lbl in self.exports:
                    self.exports[lbl] = address
                self.labels[lbl] = (current_section, address)
                self.sections[current_section]["symbols"][lbl] = address
                line = rest.strip()
                if not line:
                    continue

            # 1) .word / .byte directive
            if line.startswith(".word") or line.startswith(".byte"):
                parts = re.split(r'[\s,]+', line, maxsplit=1)
                if len(parts) > 1:
                    for tok in re.findall(r"\b[A-Za-z_]\w*\b", parts[1]):
                        if tok not in self.registers:
                            self.sections[current_section]["references"].append((tok, orig_no))
                # boyut hesabı aşağıda
            # 2) kod satırları
            tok0 = line.split()[0].upper()
            if tok0 in self.instructions:
                inst_idx = len(self.line_addresses)
                for sym in self.imports:
                    if re.search(r'\b{}\b'.format(sym), line):
                        self.relocations.append((sym, current_section, inst_idx))
                self.line_addresses.append(address)
                parts = re.split(r'[\s,]+', line)
                for opd in parts[1:]:
                    if opd.startswith("#"):
                        continue
                    if (re.match(r'^[A-Za-z_]\w*$', opd)
                            and opd not in self.registers
                            and opd.upper() not in self.instructions):
                        self.sections[current_section]["references"].append((opd, orig_no))

            # boyut hesaplama
            inc = 2
            if current_section == ".text" and any(x in line for x in ['#','&','(']):
                inc = 4
            elif current_section == ".data":
                if line.startswith(".word"):
                    cnt = len([v for v in line.split(".word",1)[1].split(",") if v.strip()])
                    inc = 2*cnt
                elif line.startswith(".byte"):
                    cnt = len([v for v in line.split(".byte",1)[1].split(",") if v.strip()])
                    inc = cnt
            elif current_section == ".bss" and line.startswith(".space"):
                sz = int(line.split(".space",1)[1])
                inc = 2*sz

            self.sections[current_section]["size"] += inc
            address = format(int(address,16) + inc, '04X')

        return self.labels, self.sections

    def get_operand_binary_dual_operand(self, o1, o2):
        try:
            if o1 in self.registers and o2 in self.registers:
                return (self.registers[o1], self.registers[o2], "00")
            if o1 or o2 in self.imports:
                if o1 or o2 in self.registers:
                    if o1 in self.registers:
                        return (self.registers[o1], "0000", "00")
                    else:
                        return ("0000", self.registers[o2], "00")
                else:
                    return ("0000", "0000", "00")
            if o1.startswith("#"):
                imm = self.hexadec_to_binary(o1[1:])
                return (self.registers["R3"], self.registers[o2], "11", imm)
            return f"Unsupported operands {o1},{o2}"
        except:
            return f"Unsupported operands {o1},{o2}"

    def pass2(self, lines):
        section_indices = {".text":[], ".data":[], ".bss":[]}
        current = ".text"
        for i,ln in enumerate(lines):
            if ln.strip().startswith((".text",".data",".bss")):
                current = ln.strip().split()[0]
            section_indices[current].append(i)

        data_codes = []
        text_codes = []
        bss_codes  = []

        # DATA
        for idx in section_indices[".data"]:
            ln = lines[idx].strip()
            if not ln or ln.startswith((".data",";")):
                continue
            if ":" in ln:
                ln = ln.split(":",1)[1].strip()
                if not ln:
                    continue
            if ln.startswith(".word"):
                for v in ln.split(".word",1)[1].split(","):
                    data_codes.append(self.hexadec_to_binary(v.strip()))
            elif ln.startswith(".byte"):
                for v in ln.split(".byte",1)[1].split(","):
                    val=v.strip()
                    if val.lower().startswith("0x"):
                        data_codes.append(bin(int(val,16))[2:].zfill(8))
                    else:
                        data_codes.append(bin(int(val))[2:].zfill(8))

        
        
        # TEXT
        text_ptr = 0
        for idx in section_indices[".text"]:
            ln = lines[idx].strip()
            if not ln or ln.startswith((".text",";")):
                continue
            if ":" in ln:
                ln = ln.split(":",1)[1].strip()
                if not ln:
                    continue
            parts = ln.split()
            instr = parts[0].upper()
            if instr in ["MOV","MOV.W","ADD","ADD.W","SUB","SUB.W","CMP"]:
                # replace labels
                for lbl,(sec,addr) in self.labels.items():
                    for j in (1,2):
                        if lbl in parts[j]:
                            parts[j] = parts[j].replace(lbl, addr)
                src,dst = parts[1].rstrip(","), parts[2].rstrip(",")
                opi = self.get_operand_binary_dual_operand(src,dst)
                if isinstance(opi,str):
                    raise Exception(opi)
                code = self.instructions[instr]
                ad,bw = "0","1"
                if len(opi)==3:
                    s,d,a = opi; binstr=f"{code}{s}{ad}{bw}{a}{d}"
                elif len(opi)==2:
                    s,d,a,imm = opi; binstr=f"{code}{s}{ad}{bw}{a}{d}{imm}"
                else:
                    r3,d,a,imm = opi; binstr=f"{code}{r3}{ad}{bw}{a}{d}{imm}"
                text_codes.append(binstr); text_ptr+=1

            elif instr in ["JMP","JEQ","JNE","JC","JN","JNC","JGE","JL"]:
                tgt = parts[1]
                if tgt not in self.labels:
                    raise Exception(f"Undefined label {tgt}")
                opcode = self.instructions[instr]
                cur_addr = int(self.line_addresses[text_ptr],16)
                dest = int(self.labels[tgt][1],16)
                off = ((dest-(cur_addr+2))//2) & 0x3FF
                text_codes.append(f"{opcode}{bin(off)[2:].zfill(10)}"); text_ptr+=1

            elif instr=="NOP":
                text_codes.append(self.instructions["NOP"].ljust(16,"0")); text_ptr+=1
            elif instr=="RET":
                code = self.instructions["RET"]
                ad,bw = "00","0"
                binstr=f"{code}{bw}{ad}{'0000'}"
                text_codes.append(binstr); text_ptr+=1
                
            elif instr=="CALL":
                code = self.instructions[instr]
                ad,bw = "00","1"
                binstr=f"{code}{bw}{ad}{'0000'}"
                text_codes.append(binstr); text_ptr+=1

                # BSS
        for idx in section_indices[".bss"]:
            ln = lines[idx].strip()
            if not ln or ln.startswith((".bss",";")):
                continue
            if ":" in ln:
                ln=ln.split(":",1)[1].strip()
                if not ln:
                    continue
            if ln.startswith(".space"):
                sz=int(ln.split(".space",1)[1])
                for _ in range(sz):
                    bss_codes.append("0"*16)
        
        all_codes = data_codes + text_codes
        return data_codes, text_codes, all_codes

class LinkEditor:
    def __init__(self, obj_dir):
        self.obj_dir = obj_dir
        self.modules = []   # her modül: { text: [...], data: [...], exports: {sym:addr}, relocs:[(sym,sec,off)] }
        self.global_exports = {}
        self.global_text = []
        self.global_data = []
        self._load_modules()

    def _load_modules(self):
        for fn in os.listdir(self.obj_dir):
            if not fn.endswith(".obj"): continue
            path = os.path.join(self.obj_dir, fn)
            self.modules.append(self._parse_obj(path))

        # önce tüm export’ları topluyoruz
        for m in self.modules:
            for sym, addr in m["exports"].items():
                if addr is None:
                    raise Exception(f"Undefined exported symbol {sym}")
                if sym in self.global_exports:
                    raise Exception(f"Duplicate export {sym}")
                # global_exports’de tutulacak adresi modülün kendi .text + base’e göre hesaplayacağız
                self.global_exports[sym] = (m, addr)

    def _parse_obj(self, path):
        section = None
        data = []
        text = []
        exports = {}
        relocs = []
        with open(path) as f:
            for ln in f:
                ln = ln.strip()
                if ln == "SECTION .text":
                    section = "text"; continue
                if ln == "SECTION .data":
                    section = "data"; continue
                if ln == "EXPORTS":
                    section = "exports"; continue
                if ln == "RELOCATIONS":
                    section = "relocs"; continue
                if ln == "EOF":
                    break

                if section == "text":
                    val = int(ln, 16)
                    text.append(format(val, '016b'))
                elif section == "data":
                    data.append(ln)
                elif section == "exports":
                    # “sym addr”
                    parts=ln.split()
                    exports[parts[0]] = int(parts[1],16)
                elif section == "relocs":
                    # “sym .text 0x0010”
                    sym, sec, off = ln.split()
                    relocs.append((sym, sec, int(off,16)))
        return {"text":text, "data":data, "exports":exports, "relocs":relocs}

    def link(self):
        # her modülde text segmente bir base adres ata
        txt_base_idx = 0
        dat_base_idx = 0
        layout = []
        for m in self.modules:
            m["txt_base_idx"] = txt_base_idx
            m["dat_base_idx"] = dat_base_idx
            txt_base_idx += len(m["text"])
            dat_base_idx += len(m["data"])
            layout.append(m)

        # global text/data birleştir
        for m in layout:
            self.global_text.extend(m["text"])
            self.global_data.extend(m["data"])

        # relocation: her modülde kendi base’e göre patch et
        for m in layout:
            for sym, sec, inst_idx in m["relocs"]:
                if sym not in self.global_exports:
                    raise Exception(f"Unresolved extern: {sym}")
                mod, sym_addr = self.global_exports[sym]
                # global_text’e gömülecek index:
                base_idx = m["txt_base_idx"]   # aşağıda def edeceğiz
                idx      = base_idx + inst_idx

                old_bin = self.global_text[idx]       # örn. "0001001011000000" == 0x12C0
                # high bits (üst 8 bit) koru:
                high = old_bin[:8]                    # "00010010" == 0x12
                # düşük baytı yeni adresin alt byte’ı ile değiştir
                low  = format(sym_addr & 0xFF, '08b') # eğer sym_addr=0x000A -> "00001010"
                self.global_text[idx] = high + low    # "00010010"+"00001010" == "0001001000001010" == 0x120A


    def write(self, path):
        with open(path, "w") as f:
            f.write("COFF_LINKED EXECUTABLE FILE\n")
            f.write("SECTION .text\n")
            for b in self.global_text:
                h = hex(int(b,2))[2:].upper().zfill(len(b)//4)
                f.write(f"0x{h}\n")
            f.write("SECTION .data\n")
            for d in self.global_data:
                # eğer data’yı binary olarak parse etmediyseniz, d zaten "0x12A4" formundaysa doğrudan:
                if re.match(r'^[01]{8,16}$', d):
                    h = hex(int(d,2))[2:].upper().zfill(len(d)//4)
                    f.write(f"0x{h}\n")
                else:
                    f.write(f"{d}\n")
            f.write("EOF\n")



class MSP430AssemblerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MSP430 Assembler")
        self.root.geometry("1600x800")
        
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.title_label = tk.Label(self.main_frame, text="MSP430 Assembler", font=("Arial",16,"bold"))
        self.title_label.pack(pady=5)
        
        self.split_frame = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4, height=300)
        self.split_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        self.left_frame = tk.LabelFrame(self.split_frame, text="Assembler Kodu", font=("Arial",10,"bold"), height=300)
        self.right_frame= tk.LabelFrame(self.split_frame, text="Dönüştürülmüş Kod", font=("Arial",10,"bold"), height=300)
        self.split_frame.add(self.left_frame); self.split_frame.add(self.right_frame)
        
        self.code_text   = LineNumberedText(self.left_frame, wrap=tk.WORD, font=("Courier New",12))
        self.code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.result_text = scrolledtext.ScrolledText(self.right_frame, wrap=tk.WORD, font=("Courier New",12))
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        self.bottom_frame = tk.Frame(self.main_frame)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        self.add_example_code()

        # Semboller Tablosu
        self.symbols_frame = tk.LabelFrame(self.bottom_frame, text="Semboller", font=("Arial",10,"bold"))
        self.symbols_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=1, pady=1)
        self.symbols_table = ttk.Treeview(self.symbols_frame, columns=("label","section","address"), show="headings")
        self.symbols_table.heading("label", text="Sembol")
        self.symbols_table.heading("section", text="Section")
        self.symbols_table.heading("address",text="Adres")
        self.symbols_table.pack(fill=tk.BOTH, expand=True)

        # Exports (.def) Tablosu
        self.exports_table = ttk.Treeview(self.symbols_frame, columns=("symbol","address"), show="headings", height=4)
        self.exports_table.heading("symbol", text="Export Symbol (def)")
        self.exports_table.heading("address", text="Address")
        self.exports_table.pack(fill=tk.BOTH, expand=True, pady=(5,0))

        # import (.ref) Tablosu
        self.import_table = ttk.Treeview(self.symbols_frame, columns=("symbol","address"), show="headings", height=4)
        self.import_table.heading("symbol", text="Import Symbol (ref)")
        self.import_table.heading("address", text="Address")
        self.import_table.pack(fill=tk.BOTH, expand=True, pady=(5,0))


        # Section Tablosu
        self.sections_frame = tk.LabelFrame(self.bottom_frame, text="Section Bilgileri", font=("Arial",10,"bold"))
        self.sections_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, padx=1, pady=1)
        self.sections_table = ttk.Treeview(self.sections_frame, columns=("section","start","size"), show="headings")
        self.sections_table.heading("section", text="Section")
        self.sections_table.heading("start",   text="Başlangıç Adresi")
        self.sections_table.heading("size",    text="Boyut")
        self.sections_table.pack(fill=tk.BOTH, expand=True)

        # ───── Detay Görünümü ─────
        self.details_frame = tk.LabelFrame(self.bottom_frame, text="Section Details", font=("Arial",10,"bold"))
        self.details_frame.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM, padx=1, pady=1)

        cols_syms = ("symbol","address")
        self.syms_detail = ttk.Treeview(self.details_frame, columns=cols_syms, show="headings", height=5)
        self.syms_detail.heading("symbol", text="Symbol")
        self.syms_detail.heading("address", text="Address")
        self.syms_detail.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        cols_refs = ("symbol","line")
        self.refs_detail = ttk.Treeview(self.details_frame, columns=cols_refs, show="headings", height=5)
        self.refs_detail.heading("symbol", text="Referenced Symbol")
        self.refs_detail.heading("line",   text="Line No")
        self.refs_detail.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        # ────────────────

        # Buton Çerçevesi
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=1)

        self.load_button   = tk.Button(self.button_frame, text="Dosya Aç", command=self.load_file, bg="#007bff", fg="white")
        self.load_button.pack(side=tk.LEFT, padx=5)
        self.save_button   = tk.Button(self.button_frame, text="Kaydet", command=self.save_file, bg="#ffc107", fg="black")
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.clear_button  = tk.Button(self.button_frame, text="Temizle",command=self.clear_all, bg="#dc3545", fg="white")
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        self.convert_button= tk.Button(self.button_frame, text="Kodu Çevir",command=self.convert_code,bg="#28a745",fg="white")
        self.convert_button.pack(side=tk.RIGHT, padx=5)
        self.link_button= tk.Button(self.button_frame, text="Modülleri Link Et", command=self.link_modules, bg="#17a2b8",fg="white")
        self.link_button.pack(side=tk.RIGHT, padx=5)

        # Durum Çubuğu
        self.status_bar = tk.Label(root, text="Hazır", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Bölüm seçimi için event
        self.sections_table.bind("<<TreeviewSelect>>", self.on_section_select)

    def add_example_code(self):
        example_code = """;MSP430 Assembly Example Code
; --- Tanımlar ---
.def  start, equal_label, end
.ref  external_func, extern_var

; --- .data bölümünde veri ---
.data
val1:   .word 0x1234
val2:   .byte 0xA

; --- .bss bölümünde sıfırdan başlatılmış alan ---
.bss
temp:   .space 2

; --- .text bölümünde kod ---
.text
start:  MOV.W #0x1234, R4      ; R4 = 0x1234
        MOV.W #0x4567, R5         ; R5 = 0x4567
        MOV.W #0x89AB, R6         ; R6 = 0x89AB
        CALL external_func    ; dışarıdan gelen fonksiyonu çağır
        ADD R5, R4           ; R4 = R4 + R5
        MOV     extern_var, R5      ; extern_var değişkenine R5'i ata
        SUB R6, R4           ; R4 = R4 - R6
        CMP R4, R5             ; R4 ve R5'i karşılaştır
        JEQ equal_label        ; Eğer eşitse 'equal_label'e atla
        JMP not_equal_label    ; Değilse 'not_equal_label'e atla
equal_label:
        MOV R4, R7             ; R7 = R4
        JMP end
not_equal_label:
        MOV R5, R7             ; R7 = R5
end:    NOP
"""
        self.code_text.text.insert(tk.END, example_code)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Assembly Dosyaları","*.asm")])
        if path:
            with open(path,'r') as f:
                self.code_text.text.delete("1.0",tk.END)
                self.code_text.text.insert(tk.END,f.read())

    def save_file(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".asm",
                                                filetypes=[("Assembly Dosyaları","*.asm"),("Tüm Dosyalar","*.*")])
            if path:
                asm_code = self.code_text.text.get("1.0",tk.END)
                mc_code  = self.result_text.get("1.0",tk.END)
                with open(path,'w') as f:
                    f.write("; Assembly Code\n"+asm_code+"\n; Machine Code\n"+mc_code)
                self.status_bar.config(text=f"Dosya kaydedildi: {path}")
                messagebox.showinfo("Başarılı","Dosya kaydedildi!")
        except Exception as e:
            messagebox.showerror("Hata",str(e))
    
    def link_modules(self):
        try:
            linker = LinkEditor("temp")
            linker.link()
            out = "temp/final.obj"
            linker.write(out)
            messagebox.showinfo("Link Başarılı", f"Final obj oluşturuldu:\n{out}")
        except Exception as e:
            messagebox.showerror("Link Hatası", str(e))


    def clear_all(self):
        if messagebox.askyesno("Onay","Tüm alanları temizlemek istediğinize emin misiniz?"):
            self.code_text.text.delete("1.0",tk.END)
            self.result_text.delete("1.0",tk.END)
            for i in self.symbols_table.get_children(): self.symbols_table.delete(i)
            for i in self.sections_table.get_children(): self.sections_table.delete(i)
            self.status_bar.config(text="Temizlendi")

    def write_cof_object(self, path, asm, data_codes, text_codes):
        """
        Common Object File Format (COFF) dosyası:
        - Bölümler (text/data) ikili verileri (hex)
        - EXPORTS: .def ile tanımlanan semboller ve adresleri
        - RELOCATIONS: .ref ile toplanmış relocation girdileri
        - EOF
        """
        with open(path, "w") as f:
            f.write("COFF\n")
            # önce text
            f.write("SECTION .text\n")
            for binstr in text_codes:
                h = hex(int(binstr,2))[2:].upper().zfill(len(binstr)//4)
                f.write(f"0x{h}\n")
            # sonra data
            f.write("SECTION .data\n")
            for binstr in data_codes:
                h = hex(int(binstr,2))[2:].upper().zfill(len(binstr)//4)
                f.write(f"0x{h}\n")
            # exports
            f.write("EXPORTS\n")
            for sym, addr in asm.exports.items():
                f.write(f"{sym} 0x{addr or '????'}\n")
            # relocations
            f.write("RELOCATIONS\n")
            for sym, sec, off in asm.relocations:
                f.write(f"{sym} {sec} 0x{off:04X}\n")
            f.write("EOF\n")


    def convert_code(self):
        raw_lines = self.code_text.text.get("1.0", tk.END).splitlines()
        if not raw_lines:
            messagebox.showwarning("Uyarı","Assembler kodu girin")
            return

        cleaned = []  # yorumlar temizlenmiş satırlar
        mapping = []

        for lineno, line in enumerate(raw_lines, start=1):
            # yorumdan öncesini al, baş-son boşluğu sil
            clean = line.split(";")[0].strip()
            cleaned.append(clean)
            mapping.append(lineno)
            
        asm=MSP430Assembler()
        try:
            labels, sections = asm.pass1(cleaned, mapping)
            # detayları sakla
            self.last_sections = sections
            # sembol tablosu
            for i in self.symbols_table.get_children(): self.symbols_table.delete(i)
            for lbl,(sec,addr) in labels.items():
                self.symbols_table.insert("","end",values=(lbl,sec,addr))
            # exports (.def)
            for iid in self.exports_table.get_children():
                self.exports_table.delete(iid)
            for sym, addr in asm.exports.items():
                self.exports_table.insert("", "end", values=(sym, addr))

            # imports (.ref)
            for iid in self.import_table.get_children():
                self.import_table.delete(iid)
            for sym, addr in asm.imports.items():
                self.import_table.insert("", "end", values=(sym, addr or "-"))
            
            # section tablosu
            for i in self.sections_table.get_children(): self.sections_table.delete(i)
            for sec,info in sections.items():
                self.sections_table.insert("","end",values=(sec,info["start"],f"{info['size']} byte"))
            self.status_bar.config(text=f"PASS1: {len(labels)} sembol, {len(sections)} section")
        except Exception as e:
            messagebox.showerror("Hata",f"PASS1: {e}")
            return

        try:
            data_codes, text_codes, machine_codes = asm.pass2(cleaned)
        except Exception as e:
            messagebox.showerror("Hata",f"PASS2: {e}")
            return

        def is_code_line(line):
            r=line.strip()
            if not r: return False
            if r.startswith('.') and not r.startswith(('.word','.byte')): return False
            if r.upper().startswith('ORG'): return False
            if r.startswith(';'): return False
            if ':' in r:
                _,rest=r.split(':',1); r=rest.strip()
                if not r: return False
            tok=r.split()[0].upper()
            return tok in asm.instructions or tok in ['.WORD','.BYTE']

        self.result_text.delete("1.0",tk.END)
        idx=0
        for i,orig in enumerate(cleaned, start=1):
            entry=''
            if is_code_line(cleaned[i-1]) and idx<len(machine_codes):
                b=machine_codes[idx]; h=asm.binary_to_hex(b)
                entry=f"{b} -> 0x{h}"
                idx+=1
            self.result_text.insert(tk.END,f"{i}: {entry}\n")
        self.status_bar.config(text="PASS2 tamamlandı")
        try:
            # temp/ klasörünü oluştur
            os.makedirs("temp", exist_ok=True)
            # dosya adı olarak timestamp veya sabit bir isim kullanabilirsiniz
            uniq = int(time.time() * 1000)
            obj_path = os.path.join("temp", f"module_{uniq}.obj")
            # write_cof_object(self, path, asm, sections, machine_codes)
            self.write_cof_object(obj_path, asm, data_codes, text_codes)
            self.status_bar.config(text=f"PASS2 tamamlandı • Obj yazıldı: {obj_path}")
        except Exception as e:
            messagebox.showwarning("Uyarı", f"Obj dosyası yazılamadı: {e}")

    def on_section_select(self, event):
        sel = self.sections_table.selection()
        if not sel: return
        section = self.sections_table.item(sel[0],"values")[0]
        data = getattr(self, 'last_sections', {}).get(section, {})
        # symbols
        for i in self.syms_detail.get_children(): self.syms_detail.delete(i)
        for sym, addr in data.get("symbols",{}).items():
            self.syms_detail.insert("","end",values=(sym,addr))
        # references
        for i in self.refs_detail.get_children(): self.refs_detail.delete(i)
        for sym, ln in data.get("references",[]):
            self.refs_detail.insert("","end",values=(sym,ln))


if __name__ == "__main__":
    root = tk.Tk()
    app = MSP430AssemblerUI(root)
    root.mainloop()
