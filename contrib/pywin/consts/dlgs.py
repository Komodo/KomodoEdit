"""
This module contains all dialog ids used by common dialogs 
as they appear in dlgs.h

When customizing a common dialog your ids should start somewhere
above ctlLast.

"""

ctlFirst  =  1024
ctlLast   =  1279

#
# ids from windows.h
#
IDOK       = 1
IDCANCEL   = 2
IDABORT    = 3
IDRETRY    = 4
IDIGNORE   = 5
IDYES      = 6
IDNO       = 7
IDCLOSE    = 8
IDHELP     = 9
IDTRYAGAIN = 10
IDCONTINUE = 11
IDTIMEOUT  = 32000



# reserved for common dialogs
#
#  Push buttons.
#
psh1   =     1024
psh2   =    1025
psh3   =     1026
psh4    =    1027
psh5   =     1028
psh6    =    1029
psh7   =     1030
psh8   =     1031
psh9    =    1032
psh10  =     1033
psh11   =    1034
psh12   =    1035
psh13   =    1036
psh14   =    1037
psh15   =    1038
pshHelp  =   psh15
psh16   =   1039

#
#  Checkboxes.
#
chx1     =   1040
chx2   =     1041
chx3   =     1042
chx4   =     1043
chx5   =     1044
chx6   =     1045
chx7     =   1046
chx8     = 1047
chx9     =  1048
chx10    =   1049
chx11     =  1050
chx12   =    1051
chx13   =    1052
chx14   =    1053
chx15    =   1054
chx16    =   1055

#
#  Radio buttons.
#
rad1    =    1056
rad2    =    1057
rad3   =    1058
rad4   =     1059
rad5    =    1060
rad6   =     1061
rad7   =     1062
rad8    =    1063
rad9    =    1064
rad10    =   1065
rad11    =   1066
rad12    =   1067
rad13   =    1068
rad14    =   1069
rad15   =    1070
rad16   =    1071

#
#  Groups, frames, rectangles, and icons.
#
grp1    =    1072
grp2   =     1073
grp3    =    1074
grp4    =    1075
frm1    =    1076
frm2    =    1077
frm3    =    1078
frm4    =    1079
rct1     =   1080
rct2    =    1081
rct3    =    1082
rct4    =    1083
ico1   =     1084
ico2    =    1085
ico3    =    1086
ico4    =    1087

#
#  Static text.
#
stc1   =     1088
stc2  =     1089
stc3    =    1090
stc4   =    1091
stc5    =    1092
stc6    =    1093
stc7    =    1094
stc8    =    1095
stc9     =   1096
stc10    =   1097
stc11   =    1098
stc12    =   1099
stc13    =   1100
stc14  =     1101
stc15   =    1102
stc16  =     1103
stc17  =     1104
stc18   =    1105
stc19   =    1106
stc20   =    1107
stc21  =     1108
stc22   =    1109
stc23   =    1110
stc24   =    1111
stc25   =    1112
stc26  =     1113
stc27  =     1114
stc28   =    1115
stc29   =    1116
stc30    =   1117
stc31    =   1118
stc32   =    1119

#
#  Listboxes.
#
lst1   =     1120
lst2   =     1121
lst3   =     1122
lst4   =     1123
lst5   =     1124
lst6   =     1125
lst7   =     1126
lst8    =    1127
lst9    =    1128
lst10  =     1129
lst11   =    1130
lst12    =   1131
lst13   =   1132
lst14  =     1133
lst15   =    1134
lst16   =    1135

#
#  Combo boxes.
#
cmb1  =      1136
cmb2   =     1137
cmb3    =    1138
cmb4    =    1139
cmb5     =   1140
cmb6    =    1141
cmb7   =     1142
cmb8    =    1143
cmb9    =    1144
cmb10   =    1145
cmb11   =    1146
cmb12   =    1147
cmb13   =    1148
cmb14   =    1149
cmb15    =   1150
cmb16     =  1151

#
#  Edit controls.
#
edt1   =     1152
edt2   =     1153
edt3   =     1154
edt4   =     1155
edt5   =     1156
edt6   =     1157
edt7    =    1158
edt8     =   1159
edt9     =   1160
edt10   =    1161
edt11   =    1162
edt12   =    1163
edt13    =   1164
edt14    =   1165
edt15    =   1166
edt16    =   1167

#
#  Scroll bars.
#
scr1   =     1168
scr2   =     1169
scr3    =    1170
scr4    =    1171
scr5    =    1172
scr6    =    1173
scr7    =    1174
scr8   =     1175

#
#  These dialog resource ordinals really start at 1536, but the
#  RC Compiler can't handle hex for resource IDs, hence the decimal.
#
FILEOPENORD   =   1536
MULTIFILEOPENORD =1537
PRINTDLGORD   =   1538
PRNSETUPDLGORD  = 1539
FINDDLGORD   =    1540
REPLACEDLGORD  =  1541
FONTDLGORD   =    1542
FORMATDLGORD31 =  1543
FORMATDLGORD30 =  1544
RUNDLGORD    =    1545

#if (WINVER >= 1024)
PAGESETUPDLGORD = 1546
NEWFILEOPENORD  = 1547
NEWOBJECTOPENORD =1548
#endif /* WINVER >= 1024) */



