; Assembly Code
;MSP430 Assembly Example Code
; --- Tanımlar ---
.def  start, equal_label, end
.exdef  external_func, extern_var

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


; Machine Code

