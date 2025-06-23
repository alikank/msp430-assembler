; Assembly Code
;MSP430 Assembly Example Code
; --- Tanimlar ---
.def  external_func, extern_var

; --- .data bolmunde veri ---
.data
extern_var:   	 .byte 0xA

; --- .bss bolumunde sifirdan baslatilmis alan ---
.bss
temp:   .space 2

; --- .text bolumunde kod ---
.text
external_func: 				ADD R5, R4
				MOV R3, R5
 				MOV.W #0x1234, R4
				MOV R4, R7
				RET


; Machine Code
