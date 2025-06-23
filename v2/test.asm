MOV.W #0x1234, R4       ; R4 = 0x1234
MOV.W #0x56, R5       ; R5 = 0x0056
ADD.W #1, R4            ; R4 = R4 + 1
SUB.W #2, R5            ; R5 = R5 - 2
CMP R4, R5            ; R4 ve R5'i kar��la�t�r
JEQ equal_label       ; E�er e�itse 'equal_label'e atla
JNE not_equal_label   ; De�ilse 'not_equal_label'e atla
equal_label: MOV R4, R6       ; E�itse R4'� R6'ya kopyala
JMP end           ; end etiketine atla
not_equal_label: MOV R5, R6   ; E�it de�ilse R5'i R6'ya kopyala
end: MOV R6, R5               ; Son olarak R6'dan R5'e kopyala
