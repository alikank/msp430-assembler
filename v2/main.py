import re
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox


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
        """
        - Label (etiket) satır başındaki 'foo:'
        - Directive  satır başındaki '.word', '.byte', '.space', '.text' vb.
        - Opcode     MOV, MOV.W, ADD, NOP, CMP, JMP vb. (MSP430Assembler.instructions tablosuna bakar)
        - operand1   ilk operand
        - operand2   ikinci operand
        - error      opcode da değilse reddeder
        """
        lines = self.text.get('1.0', tk.END).splitlines()
        # önce tüm tag'leri sil
        for tag in ('label','directive','opcode','operand1','operand2','error'):
            self.text.tag_remove(tag, '1.0', tk.END)

        asm = MSP430Assembler()

        for row, line in enumerate(lines, start=1):
            raw = line
            # 1) Label var mı?
            m_label = re.match(r"\s*([A-Za-z_]\w*):", raw)
            if m_label:
                start, end = m_label.start(1), m_label.end(1)
                self.text.tag_add('label', f"{row}.{start}", f"{row}.{end}")
                offset = m_label.end()  # işaretçinin devamı için
            else:
                offset = 0

            # kalan kısmı al
            rest = raw[offset:]
            # yorum satırıysa atla
            if rest.lstrip().startswith(';'):
                continue

            # 2) Directive kontrolü (.word, .byte, .space, .text, .data, .bss, .org, .end ...)
            m_dir = re.match(r"\s*(\.\w+)", rest)
            if m_dir:
                ds, de = m_dir.start(1)+offset, m_dir.end(1)+offset
                self.text.tag_add('directive', f"{row}.{ds}", f"{row}.{de}")
                # directive’in operand’larını renklemek isterseniz buraya ekleyebilirsiniz
                continue

            # 3) Opcode + operand’ları yakala
            #    (\w+(?:\.\w+)?) ile MOV, MOV.W, ADD, SUB, NOP vb.
            m_ins = re.match(r"\s*(\w+(?:\.\w+)?)(?:\s+([^,\s]+))?(?:\s*,\s*([^,\s]+))?", rest)
            if not m_ins:
                continue

            op, opd1, opd2 = m_ins.group(1), m_ins.group(2), m_ins.group(3)
            os_, oe = m_ins.start(1)+offset, m_ins.end(1)+offset

            # opcode mu, yoksa error mı?
            if op.upper() in asm.instructions:
                self.text.tag_add('opcode', f"{row}.{os_}", f"{row}.{oe}")
            else:
                self.text.tag_add('error', f"{row}.{os_}", f"{row}.{oe}")

            # operand1
            if opd1:
                s1, e1 = m_ins.start(2)+offset, m_ins.end(2)+offset
                self.text.tag_add('operand1', f"{row}.{s1}", f"{row}.{e1}")

            # operand2
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
            self.linenumbers.create_text(15, y, anchor="n", text=linenum, font=self.text.cget("font"))
            i = self.text.index(f"{i}+1line")


class MSP430Assembler:
    def __init__(self):
        self.instructions = {
            "MOV":  "0100", 
            "MOV.W":  "0100",
            "ADD":  "0101",   
            "ADD.W":  "0101",
            "SUB.W":  "1000",
            "SUB":  "1000",   
            "CMP":  "1001",   
            "JNE":  "001000",   
            "JEQ":  "001001",
            "JNC":  "001010",
            "JC":   "001011",
            "JN":   "001100",
            "JGE":  "001101",
            "JL":   "001110",
            "JMP":  "001111",
            "NOP":  "0000",
            "CALL": "0001001010"
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
    
    def hexadec_to_binary(self, hexadec):
        """Hexadecimal sayıyı 16 bitlik bir binary sayıya dönüştürür."""
        binary = bin(int(hexadec, 16))[2:].zfill(16)
        return binary
    
    def binary_to_hex(self, binary):
        """Binary sayıyı hexadecimal formatına dönüştürür."""
        if len(binary) % 4 != 0:
            binary = binary.zfill((len(binary) // 4 + 1) * 4)
        hex_value = hex(int(binary, 2))[2:].upper().zfill(len(binary) // 4)
        return hex_value
    
    def msp430_hex_addition(self, hex1, hex2):
        dec1 = int(hex1, 16)
        dec2 = int(hex2, 16)
        total_dec = (dec1 + dec2) & 0xFFFF
        total_hex = format(total_dec, '04x')
        
        return total_hex 

    def pass1(self, lines):
                        # Otomatik section ekleme: Eğer hiçbir section yoksa başa .text ekle
            if not any(line.strip().startswith(('.text', '.data', '.bss')) for line in lines):
                lines = ['.text'] + lines
            address = "0000"
            current_section = ".text"
            section_addresses = {".text": "0000", ".data": "C000", ".bss": "E000"}
            self.labels.clear()
            self.sections.clear()
            self.line_addresses = []
            text_code_line_indices = []
            label_set = set()
            for line_no, line in enumerate(lines):
                orig_line = line
                line = line.strip()
                if not line or line.startswith(";"):
                    continue

                # Section belirleme
                if line.startswith(".text") or line.startswith(".data") or line.startswith(".bss"):
                    current_section = line
                    address = section_addresses[current_section]
                    self.sections[current_section] = {"start": address, "size": 0}
                    continue

                # ORG ile adres ayarı
                if line.startswith("ORG"):
                    address = line.split()[1].strip()
                    continue

                # Label kaydı
                if ":" in line:
                    label = line.split(":")[0]
                    if label in label_set:
                        raise Exception(f"Label '{label}' redefined in line: '{orig_line}'")
                    label_set.add(label)
                    self.labels[label] = (current_section, address)
                    line = line.split(":", 1)[1].strip()
                    if not line:
                        continue

                # Eğer halen satırda komut/veri yoksa devam et
                if not line:
                    continue

                # .text section'ındaki kod satırlarının adresini ve satır indexini ekle
                if current_section == ".text":
                    self.line_addresses.append(address)
                    text_code_line_indices.append(line_no)

                # Adres ve boyut hesaplama
                increment = 2
                if current_section == ".text" and any(x in line for x in ['#', '&', '(']):
                    increment = 4
                elif current_section == ".data":
                    if line.startswith(".word"):
                        values = line.split(".word", 1)[1]
                        increment = 2 * len([v for v in values.split(",") if v.strip()])
                    elif line.startswith(".byte"):
                        values = line.split(".byte", 1)[1]
                        increment = len([v for v in values.split(",") if v.strip()])
                elif current_section == ".bss":
                    if line.startswith(".space"):
                        size = int(line.split(".space", 1)[1].strip())
                        increment = 2 * size  # .bss genelde word olarak ayrılır
                self.sections[current_section]["size"] += increment
                address = format(int(address, 16) + increment, '04X')
            # text_code_line_indices sadece pass2 için kullanılacaksa döndürmeye gerek yok
            return self.labels, self.sections
    
    def get_operand_binary_dual_operand(self, operand1, operand2):
        """Operandı analiz eder ve uygun binary kodunu döndürür"""
        try: 

            # register mode: Rn
            if operand1 in self.registers and operand2 in self.registers:
                return self.registers[operand1], self.registers[operand2], "00" #2 byte
            
            # register mode (immediate): #1234
            if operand1.startswith("#"):
                value = operand1[1:]
                return self.registers["R3"], self.registers[operand2],"11",self.hexadec_to_binary(value) # 4 byte
            
            return "Desteklenmeyen Operand"+operand1+operand2
        except:
            return "Desteklenmeyen Operand"+operand1+operand2
        

    def pass2(self, lines):
            machine_code = []
            current_section = ".text"
            section_codes = {".text": [], ".data": [], ".bss": []}
            line_addresses = self.line_addresses
            text_code_line_index = 0  # Sadece .text section'ındaki kod satırları için

            section_indices = {".text": [], ".data": [], ".bss": []}
            for i, line in enumerate(lines):
                l = line.strip()
                if l.startswith(".text") or l.startswith(".data") or l.startswith(".bss"):
                    current_section = l.split()[0]
                section_indices[current_section].append(i)

            # --- TEXT: Kodları işle ---
            for idx in section_indices[".text"]:
                line = lines[idx].strip()
                if not line or line.startswith(";") or line.startswith(".text"):
                    continue
                if ":" in line:
                    line = line.split(":", 1)[1].strip()
                if not line:
                    continue
                parts = line.split()
                instruction = parts[0].upper()

                if instruction not in self.instructions:
                    raise Exception(f"Error: Desteklenmeyen komut kullanıldı: '{instruction}' satır: '{line}'")


                # Çift operandlı komutlar
                if instruction in ["MOV", "MOV.W", "ADD", "ADD.W", "SUB", "SUB.W", "CMP"]:
                    if len(parts) < 3:
                        raise Exception(f"Error: Unsupported Command -> {line}")

                    # Label varsa operandlarda değiştir (adres string olarak)
                    for label in self.labels:
                        if label in parts[1]:
                            parts[1] = parts[1].replace(label, self.labels[label][1])
                        if label in parts[2]:
                            parts[2] = parts[2].replace(label, self.labels[label][1])

                    src, dst = parts[1].strip(","), parts[2].strip(",")
                    operand_info = self.get_operand_binary_dual_operand(src, dst)
                    if isinstance(operand_info, str):
                        raise Exception(operand_info)
                    opcode = self.instructions[instruction]
                    ad = "0"
                    bw = "1"
                    if len(operand_info) == 3:
                        source, dest, ass = operand_info
                        binary_instruction = f"{opcode}{source}{ad}{bw}{ass}{dest}"
                    elif len(operand_info) == 4:
                        r3, dest, ass, immediate_value = operand_info
                        binary_instruction = f"{opcode}{r3}{ad}{bw}{ass}{dest}{immediate_value}"
                    section_codes[".text"].append(binary_instruction)
                    text_code_line_index += 1

                # Jump komutları
                elif instruction in ["JMP", "JEQ", "JNE", "JC", "JN", "JNC", "JGE", "JL"]:
                    if len(parts) < 2:
                        raise Exception(f"Error: Missing jump target in line -> {line}")
                    opcode = self.instructions[instruction]
                    target_label = parts[1]
                    if target_label not in self.labels:
                        raise Exception(f"Error: Undefined label {target_label} in line -> {line}")
                    current_address = int(line_addresses[text_code_line_index], 16)
                    dest_address = int(self.labels[target_label][1], 16)
                    next_address = current_address + 2
                    offset = (dest_address - next_address) // 2
                    offset = offset & 0x3FF
                    offset_bin = bin(offset)[2:].zfill(10)
                    binary_instruction = f"{opcode}{offset_bin}"
                    section_codes[".text"].append(binary_instruction)
                    text_code_line_index += 1

                # Tek operandlı komutlar (ör: NOP)
                elif instruction in ["NOP"]:
                    opcode = self.instructions[instruction]
                    binary_instruction = opcode.ljust(16, "0")
                    section_codes[".text"].append(binary_instruction)
                    text_code_line_index += 1
                else:
                    continue  

            # --- DATA: .word ve .byte tanımlarını işle ---
            for idx in section_indices[".data"]:
                line = lines[idx].strip()
                if not line or line.startswith(";") or line.startswith(".data"):
                    continue
                if ":" in line:
                    label, remain = line.split(":", 1)
                    line = remain.strip()
                    if not line: continue
                # .word
                if line.startswith(".word"):
                    values = line.split(".word", 1)[1]
                    for val in values.split(","):
                        v = val.strip()
                        if v.startswith("0x") or v.startswith("0X"):
                            bin_val = self.hexadec_to_binary(v)
                        else:
                            bin_val = bin(int(v))[2:].zfill(16)
                        section_codes[".data"].append(bin_val)
                # .byte
                elif line.startswith(".byte"):
                    values = line.split(".byte", 1)[1]
                    for val in values.split(","):
                        v = val.strip()
                        if v.startswith("0x") or v.startswith("0X"):
                            bin_val = bin(int(v,16))[2:].zfill(8)
                        else:
                            bin_val = bin(int(v))[2:].zfill(8)
                        section_codes[".data"].append(bin_val)
                else:
                    continue

            # --- BSS: .space tanımlarını işle (sadece adres ilerlet, veri yok) ---
            for idx in section_indices[".bss"]:
                line = lines[idx].strip()
                if not line or line.startswith(";") or line.startswith(".bss"):
                    continue
                if ":" in line:
                    label, remain = line.split(":", 1)
                    line = remain.strip()
                    if not line: continue
                if line.startswith(".space"):
                    size = int(line.split(".space", 1)[1].strip())
                    for _ in range(size):
                        section_codes[".bss"].append("0" * 16)  # Başlatılmamış veri: sıfır ekle
                else:
                    continue

            machine_code = (
                #section_codes[".bss"] +
                section_codes[".data"] +
                section_codes[".text"]
            )
            return machine_code


class MSP430AssemblerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MSP430 Assembler")
        self.root.geometry("1600x800")
        
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.title_label = tk.Label(self.main_frame, text="MSP430 Assembler", font=("Arial", 16, "bold"))
        self.title_label.pack(pady=5)
        
        self.split_frame = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL,         
        sashrelief=tk.RAISED,  # Ayırıcı çizginin görünümü
        sashwidth=4,           # Ayırıcı çizginin genişliği
        height=300)            # Başlangıç yüksekliği)
        self.split_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        self.left_frame = tk.LabelFrame(self.split_frame, text="Assembler Kodu", font=("Arial", 10, "bold"), height=300 )
        self.right_frame = tk.LabelFrame(self.split_frame, text="Dönüştürülmüş Kod", font=("Arial", 10, "bold"), height=300 )
        self.split_frame.add(self.left_frame)
        self.split_frame.add(self.right_frame)
        
        self.code_text = LineNumberedText(self.left_frame, wrap=tk.WORD, font=("Courier New", 12))
        self.code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        self.result_text = scrolledtext.ScrolledText(self.right_frame, wrap=tk.WORD, font=("Courier New", 12))
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        self.bottom_frame = tk.Frame(self.main_frame)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        self.add_example_code()


        # Semboller Tablosu
        self.symbols_frame = tk.LabelFrame(self.bottom_frame, text="Semboller", font=("Arial", 10, "bold"))
        self.symbols_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=1, pady=1)
        self.symbols_table = ttk.Treeview(self.symbols_frame, columns=("label", "section", "address"), show="headings")
        self.symbols_table.heading("label", text="Sembol")
        self.symbols_table.heading("section", text="Section")
        self.symbols_table.heading("address", text="Adres")
        self.symbols_table.pack(fill=tk.BOTH, expand=True)

        # Section Tablosu
        self.sections_frame = tk.LabelFrame(self.bottom_frame, text="Section Bilgileri", font=("Arial", 10, "bold"))
        self.sections_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, padx=1, pady=1)
        self.sections_table = ttk.Treeview(self.sections_frame, columns=("section", "start", "size"), show="headings")
        self.sections_table.heading("section", text="Section")
        self.sections_table.heading("start", text="Başlangıç Adresi")
        self.sections_table.heading("size", text="Boyut")
        self.sections_table.pack(fill=tk.BOTH, expand=True)

          # Buton Çerçevesi
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=1)  # En alta yerleştirildi

        # Dosya Aç Butonu
        self.load_button = tk.Button(self.button_frame, text="Dosya Aç", command=self.load_file, bg="#007bff", fg="white")
        self.load_button.pack(side=tk.LEFT, padx=5)

        # Kaydet Butonu
        self.save_button = tk.Button(self.button_frame, text="Kaydet", command=self.save_file, bg="#ffc107", fg="black")
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Temizle Butonu
        self.clear_button = tk.Button(self.button_frame, text="Temizle", command=self.clear_all, bg="#dc3545", fg="white")
        self.clear_button.pack(side=tk.RIGHT, padx=5)

        # Kodu Çevir Butonu
        self.convert_button = tk.Button(self.button_frame, text="Kodu Çevir", command=self.convert_code, bg="#28a745", fg="white")
        self.convert_button.pack(side=tk.RIGHT, padx=5)


        # Durum Çubuğu
        self.status_bar = tk.Label(root, text="Hazır", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def add_example_code(self):
        example_code = """        ; --- .data bölümünde veri ---
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
        ADD R5, R4           ; R4 = R4 + R5
        SUB R6, R4           ; R4 = R4 - R6
        CMP R4, R5             ; R4 ve R5'i karşılaştır
        JEQ equal_label        ; Eğer eşitse 'equal_label'e atla
        JMP not_equal_label    ; Değilse 'not_equal_label'e atla
equal_label:
        MOV R4, R7             ; R7 = R4
        JMP end
not_equal_label:
        MOV R5, R7             ; R7 = R5
end: NOP
"""
        self.code_text.text.insert(tk.END, example_code)
    
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Assembly Dosyaları", "*.asm")])
        if file_path:
            with open(file_path, 'r') as file:
                self.code_text.text.delete(1.0, tk.END)
                self.code_text.text.insert(tk.END, file.read())

    def save_file(self):
        try:
            # Dosya kaydetme dialogu
            file_path = filedialog.asksaveasfilename(
                defaultextension=".asm",
                filetypes=[("Assembly Dosyaları", "*.asm"), ("Tüm Dosyalar", "*.*")]
            )
            
            if file_path:
                # Assembly kodunu al
                assembly_code = self.code_text.text.get(1.0, tk.END)
                
                # Makine kodunu al
                machine_code = self.result_text.get(1.0, tk.END)
                
                with open(file_path, 'w') as file:
                    # Assembly kodunu kaydet
                    file.write("; Assembly Code\n")
                    file.write(assembly_code)
                    file.write("\n; Machine Code\n")
                    file.write(machine_code)
                
                self.status_bar.config(text=f"Dosya başarıyla kaydedildi: {file_path}")
                messagebox.showinfo("Başarılı", "Dosya başarıyla kaydedildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya kaydedilirken hata oluştu: {str(e)}")

    def clear_all(self):
        # Onay mesajı göster
        if messagebox.askyesno("Onay", "Tüm alanları temizlemek istediğinizden emin misiniz?"):
            # Assembly kodu alanını temizle
            self.code_text.text.delete(1.0, tk.END)
            
            # Makine kodu alanını temizle
            self.result_text.delete(1.0, tk.END)
            
            # Semboller tablosunu temizle
            for item in self.symbols_table.get_children():
                self.symbols_table.delete(item)
            
            # Section tablosunu temizle
            for item in self.sections_table.get_children():
                self.sections_table.delete(item)
            
            # Durum çubuğunu güncelle
            self.status_bar.config(text="Tüm alanlar temizlendi")
    
    def convert_code(self):
        # Get all raw lines (including blanks and comments)
        raw_code = self.code_text.text.get('1.0', tk.END).rstrip('\n')
        lines = raw_code.splitlines()
        if not lines:
            messagebox.showwarning("Uyarı", "Lütfen çevrilecek assembler kodunu giriniz.")
            return

        # Clean lines for assembler (remove comments)
        cleaned = [ln.split(';')[0].strip() for ln in lines]

        assembler = MSP430Assembler()
        # PASS1: collect labels and sections, update tables
        try:
            labels, sections = assembler.pass1(cleaned)
            # symbols table
            for item in self.symbols_table.get_children():
                self.symbols_table.delete(item)
            for label, (sec, addr) in labels.items():
                self.symbols_table.insert("", "end", values=(label, sec, addr))
            # sections table
            for item in self.sections_table.get_children():
                self.sections_table.delete(item)
            for sec, info in sections.items():
                self.sections_table.insert("", "end", values=(sec, info['start'], f"{info['size']} byte"))
            self.status_bar.config(text=f"PASS1 Başarılı: {len(labels)} sembol, {len(sections)} section bulundu.")
        except Exception as e:
            messagebox.showerror("Hata", f"PASS1 sırasında hata oluştu: {str(e)}")
            return

        # PASS2: generate machine codes
        try:
            machine_codes = assembler.pass2(cleaned)
        except Exception as e:
            messagebox.showerror("Hata", f"PASS2 sırasında hata oluştu: {str(e)}")
            return

        # Helper to detect real code lines
        def is_code_line(line):
            raw = line.strip()
            if not raw:
                return False
            # directive lines: allow .word and .byte but skip others
            if raw.startswith('.'):
                if raw.startswith('.word') or raw.startswith('.byte'):
                    pass
                else:
                    return False
            # ORG directive
            if raw.upper().startswith('ORG'):
                return False
            # comment-only
            if raw.startswith(';'):
                return False
            # strip label if present
            if ':' in raw:
                _, rest = raw.split(':', 1)
                raw = rest.strip()
                if not raw:
                    return False
            # first token is opcode or data directive
            token = raw.split()[0].upper()
            # treat .WORD/.BYTE lines as code
            if token in assembler.instructions or token in ['.WORD', '.BYTE']:
                return True
            return False

        # Display each original line with its corresponding machine code (if any)
        self.result_text.delete('1.0', tk.END)
        code_idx = 0
        for i, orig in enumerate(lines, start=1):
            entry = ''
            if is_code_line(cleaned[i-1]):
                if code_idx < len(machine_codes):
                    bin_code = machine_codes[code_idx]
                    hex_code = assembler.binary_to_hex(bin_code)
                    entry = f"{bin_code} -> 0x{hex_code}"
                    code_idx += 1
            self.result_text.insert(tk.END, f"{i}: {entry}\n")
        self.status_bar.config(text="PASS2 Başarılı: Satır numaralı çıktı oluşturuldu.")


if __name__ == "__main__":
    root = tk.Tk()
    app = MSP430AssemblerUI(root)
    root.mainloop()