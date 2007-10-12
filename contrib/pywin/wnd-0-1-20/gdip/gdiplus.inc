
' Original .NET translation by Avery P. - 07/29/2002 
'
' Translated to PB/WIN by Patrice Terrier - 08/17/2002 
' pterrier@zapsolution.com
'
' WinLIFT 2.5 provides a full encapsulation of GDIPLUS with several helper functions and several detailed examples (see PICTURE.EXE), 
' there is also a common dialog using thumbnails for preview of all supported GDI+ graphic file formats.
' The WinLIFT GDI+ package includes the full source code to everything !.
' You can download a trial version of WinLIFT GDI+ that will show you GDIPLUS in action from this url:
' http://www.zapsolution.com/preview/WinLIFT.EXE 
'
' NOTES:
'   - All GDI+ Strings expect and return ONLY Unicode - you'll need to use UCODE$ when using them.
'   - Functions with an I (i) at the end are non-floating point declarations
'   - If a function without the I (i) at the end doesn't work, try the one with (if any).
'     If neither version worked, then you did something wrong, or the API *may* be misdeclared.
'   - The word (ALL) next to an API set mean all of the functions are declared. (ALL GDI+ functions are now declared 8/12/2002)
'   - Search for "TODO:" (no quotes) to see what still needs done within the file. If there is no TODO, there is nothing to do!
'   - If you want to get all of the encoder or decoder file extensions, MIME type, or other values, try to use the Get__Clsid functions as a base.
'   - If you don't like the idea of converting strings to and from Unicode, change all As String occurances in the API declarations
'     to As Long, and use the StrPtr() result instead. I opted to use the As String for clarity, especially since the GDI+ docs are
'     geared toward how to use the C++ classes.
'   - I may have misdeclared the IStream functions as I'm not too familiar with them. Do a "TODO:" or "IStream" search (no quotes) to see the
'     IStream functions. All parameters except one where declared as 'IStream* stream' in C++. The exception has a comment above it. The possible
'     problem is that the IStream parameters should be passed ByRef instead of ByVal. If they are wrong, please tell me!
'   - APIs are in ordered groups, just like the C++ header, but the groups themselves are not in the same order as in the C++ headers.
'
' WARNINGS:
'   - Some of the structs may not work, though I didn't test them all fully.
'     If a function causes a GPF or performs unexpectedly, the declarations are probably a bit off.
'   - Some APIs that have a ByRef parameter may expect an array; check the MSDN to find out if unsure.
'
'-----------------------------------------------
' GDI+ Constants
'-----------------------------------------------
%LF_FACESIZE = 32

' Shift count and bit mask for A, R, G, B components
%AlphaShift = 24
%RedShift = 16
%GreenShift = 8
%BlueShift = 0

%AlphaMask = &HFF000000
%RedMask = &HFF0000
%GreenMask = &HFF00
%BlueMask = &HFF


' Image property types
%PropertyTagTypeByte = 1
%PropertyTagTypeASCII = 2
%PropertyTagTypeShort = 3
%PropertyTagTypeLong = 4
%PropertyTagTypeRational = 5
%PropertyTagTypeUndefined = 7
%PropertyTagTypeSLONG = 9
%PropertyTagTypeSRational = 10


' Image property ID tags
%PropertyTagExifIFD = &H8769
%PropertyTagGpsIFD = &H8825

%PropertyTagNewSubfileType = &HFE
%PropertyTagSubfileType = &HFF
%PropertyTagImageWidth = &H100
%PropertyTagImageHeight = &H101
%PropertyTagBitsPerSample = &H102
%PropertyTagCompression = &H103
%PropertyTagPhotometricInterp = &H106
%PropertyTagThreshHolding = &H107
%PropertyTagCellWidth = &H108
%PropertyTagCellHeight = &H109
%PropertyTagFillOrder = &H10A
%PropertyTagDocumentName = &H10D
%PropertyTagImageDescription = &H10E
%PropertyTagEquipMake = &H10F
%PropertyTagEquipModel = &H110
%PropertyTagStripOffsets = &H111
%PropertyTagOrientation = &H112
%PropertyTagSamplesPerPixel = &H115
%PropertyTagRowsPerStrip = &H116
%PropertyTagStripBytesCount = &H117
%PropertyTagMinSampleValue = &H118
%PropertyTagMaxSampleValue = &H119
%PropertyTagXResolution = &H11A ' Image resolution in width direction
%PropertyTagYResolution = &H11B ' Image resolution in height direction
%PropertyTagPlanarConfig = &H11C ' Image data arrangement
%PropertyTagPageName = &H11D
%PropertyTagXPosition = &H11E
%PropertyTagYPosition = &H11F
%PropertyTagFreeOffset = &H120
%PropertyTagFreeByteCounts = &H121
%PropertyTagGrayResponseUnit = &H122
%PropertyTagGrayResponseCurve = &H123
%PropertyTagT4Option = &H124
%PropertyTagT6Option = &H125
%PropertyTagResolutionUnit = &H128 ' Unit of X and Y resolution
%PropertyTagPageNumber = &H129
%PropertyTagTransferFuncition = &H12D
%PropertyTagSoftwareUsed = &H131
%PropertyTagDateTime = &H132
%PropertyTagArtist = &H13B
%PropertyTagHostComputer = &H13C
%PropertyTagPredictor = &H13D
%PropertyTagWhitePoint = &H13E
%PropertyTagPrimaryChromaticities = &H13F
%PropertyTagColorMap = &H140
%PropertyTagHalftoneHints = &H141
%PropertyTagTileWidth = &H142
%PropertyTagTileLength = &H143
%PropertyTagTileOffset = &H144
%PropertyTagTileByteCounts = &H145
%PropertyTagInkSet = &H14C
%PropertyTagInkNames = &H14D
%PropertyTagNumberOfInks = &H14E
%PropertyTagDotRange = &H150
%PropertyTagTargetPrinter = &H151
%PropertyTagExtraSamples = &H152
%PropertyTagSampleFormat = &H153
%PropertyTagSMinSampleValue = &H154
%PropertyTagSMaxSampleValue = &H155
%PropertyTagTransferRange = &H156

%PropertyTagJPEGProc = &H200
%PropertyTagJPEGInterFormat = &H201
%PropertyTagJPEGInterLength = &H202
%PropertyTagJPEGRestartInterval = &H203
%PropertyTagJPEGLosslessPredictors = &H205
%PropertyTagJPEGPointTransforms = &H206
%PropertyTagJPEGQTables = &H207
%PropertyTagJPEGDCTables = &H208
%PropertyTagJPEGACTables = &H209

%PropertyTagYCbCrCoefficients = &H211
%PropertyTagYCbCrSubsampling = &H212
%PropertyTagYCbCrPositioning = &H213
%PropertyTagREFBlackWhite = &H214

%PropertyTagICCProfile = &H8773 ' This TAG is defined by ICC
' for embedded ICC in TIFF
%PropertyTagGamma = &H301
%PropertyTagICCProfileDescriptor = &H302
%PropertyTagSRGBRenderingIntent = &H303

%PropertyTagImageTitle = &H320
%PropertyTagCopyright = &H8298

' Extra TAGs (Like Adobe Image Information tags etc.)

%PropertyTagResolutionXUnit = &H5001
%PropertyTagResolutionYUnit = &H5002
%PropertyTagResolutionXLengthUnit = &H5003
%PropertyTagResolutionYLengthUnit = &H5004
%PropertyTagPrintFlags = &H5005
%PropertyTagPrintFlagsVersion = &H5006
%PropertyTagPrintFlagsCrop = &H5007
%PropertyTagPrintFlagsBleedWidth = &H5008
%PropertyTagPrintFlagsBleedWidthScale = &H5009
%PropertyTagHalftoneLPI = &H500A
%PropertyTagHalftoneLPIUnit = &H500B
%PropertyTagHalftoneDegree = &H500C
%PropertyTagHalftoneShape = &H500D
%PropertyTagHalftoneMisc = &H500E
%PropertyTagHalftoneScreen = &H500F
%PropertyTagJPEGQuality = &H5010
%PropertyTagGridSize = &H5011
%PropertyTagThumbnailFormat = &H5012 ' 1 = JPEG, 0 = RAW RGB
%PropertyTagThumbnailWidth = &H5013
%PropertyTagThumbnailHeight = &H5014
%PropertyTagThumbnailColorDepth = &H5015
%PropertyTagThumbnailPlanes = &H5016
%PropertyTagThumbnailRawBytes = &H5017
%PropertyTagThumbnailSize = &H5018
%PropertyTagThumbnailCompressedSize = &H5019
%PropertyTagColorTransferFunction = &H501A
%PropertyTagThumbnailData = &H501B ' RAW thumbnail bits in JPEG format or RGB format
' depends on PropertyTagThumbnailFormat

' Thumbnail related TAGs
%PropertyTagThumbnailImageWidth = &H5020 ' Thumbnail width
%PropertyTagThumbnailImageHeight = &H5021 ' Thumbnail height
%PropertyTagThumbnailBitsPerSample = &H5022 ' Number of bits per component
%PropertyTagThumbnailCompression = &H5023 ' Compression Scheme
%PropertyTagThumbnailPhotometricInterp = &H5024 ' Pixel composition
%PropertyTagThumbnailImageDescription = &H5025 ' Image Tile
%PropertyTagThumbnailEquipMake = &H5026 ' Manufacturer of Image Input equipment
%PropertyTagThumbnailEquipModel = &H5027 ' Model of Image input equipment
%PropertyTagThumbnailStripOffsets = &H5028 ' Image data location
%PropertyTagThumbnailOrientation = &H5029 ' Orientation of image
%PropertyTagThumbnailSamplesPerPixel = &H502A ' Number of components
%PropertyTagThumbnailRowsPerStrip = &H502B ' Number of rows per strip
%PropertyTagThumbnailStripBytesCount = &H502C ' Bytes per compressed strip
%PropertyTagThumbnailResolutionX = &H502D ' Resolution in width direction
%PropertyTagThumbnailResolutionY = &H502E ' Resolution in height direction
%PropertyTagThumbnailPlanarConfig = &H502F ' Image data arrangement
%PropertyTagThumbnailResolutionUnit = &H5030 ' Unit of X and Y resolution
%PropertyTagThumbnailTransferFunction = &H5031 ' Transfer function
%PropertyTagThumbnailSoftwareUsed = &H5032 ' Software used
%PropertyTagThumbnailDateTime = &H5033 ' File change date and time
%PropertyTagThumbnailArtist = &H5034 ' Person who created the image
%PropertyTagThumbnailWhitePoint = &H5035 ' White point chromaticity
%PropertyTagThumbnailPrimaryChromaticities = &H5036 ' Chromaticities of primaries
%PropertyTagThumbnailYCbCrCoefficients = &H5037 ' Color space transformation coefficients
%PropertyTagThumbnailYCbCrSubsampling = &H5038 ' Subsampling ratio of Y to C
%PropertyTagThumbnailYCbCrPositioning = &H5039 ' Y and C position
%PropertyTagThumbnailRefBlackWhite = &H503A ' Pair of black and white reference values
%PropertyTagThumbnailCopyRight = &H503B ' CopyRight holder

%PropertyTagLuminanceTable = &H5090
%PropertyTagChrominanceTable = &H5091

%PropertyTagFrameDelay = &H5100
%PropertyTagLoopCount = &H5101

%PropertyTagPixelUnit = &H5110 ' Unit specifier for pixel/unit
%PropertyTagPixelPerUnitX = &H5111 ' Pixels per unit in X
%PropertyTagPixelPerUnitY = &H5112 ' Pixels per unit in Y
%PropertyTagPaletteHistogram = &H5113 ' Palette histogram

' EXIF specific tag

%PropertyTagExifExposureTime = &H829A
%PropertyTagExifFNumber = &H829D

%PropertyTagExifExposureProg = &H8822
%PropertyTagExifSpectralSense = &H8824
%PropertyTagExifISOSpeed = &H8827
%PropertyTagExifOECF = &H8828

%PropertyTagExifVer = &H9000
%PropertyTagExifDTOrig = &H9003 ' Date & time of original
%PropertyTagExifDTDigitized = &H9004 ' Date & time of digital data generation

%PropertyTagExifCompConfig = &H9101
%PropertyTagExifCompBPP = &H9102

%PropertyTagExifShutterSpeed = &H9201
%PropertyTagExifAperture = &H9202
%PropertyTagExifBrightness = &H9203
%PropertyTagExifExposureBias = &H9204
%PropertyTagExifMaxAperture = &H9205
%PropertyTagExifSubjectDist = &H9206
%PropertyTagExifMeteringMode = &H9207
%PropertyTagExifLightSource = &H9208
%PropertyTagExifFlash = &H9209
%PropertyTagExifFocalLength = &H920A
%PropertyTagExifMakerNote = &H927C
%PropertyTagExifUserComment = &H9286
%PropertyTagExifDTSubsec = &H9290 ' Date & Time subseconds
%PropertyTagExifDTOrigSS = &H9291 ' Date & Time original subseconds
%PropertyTagExifDTDigSS = &H9292 ' Date & TIme digitized subseconds

%PropertyTagExifFPXVer = &HA000
%PropertyTagExifColorSpace = &HA001
%PropertyTagExifPixXDim = &HA002
%PropertyTagExifPixYDim = &HA003
%PropertyTagExifRelatedWav = &HA004 ' related sound file
%PropertyTagExifInterop = &HA005
%PropertyTagExifFlashEnergy = &HA20B
%PropertyTagExifSpatialFR = &HA20C ' Spatial Frequency Response
%PropertyTagExifFocalXRes = &HA20E ' Focal Plane X Resolution
%PropertyTagExifFocalYRes = &HA20F ' Focal Plane Y Resolution
%PropertyTagExifFocalResUnit = &HA210 ' Focal Plane Resolution Unit
%PropertyTagExifSubjectLoc = &HA214
%PropertyTagExifExposureIndex = &HA215
%PropertyTagExifSensingMethod = &HA217
%PropertyTagExifFileSource = &HA300
%PropertyTagExifSceneType = &HA301
%PropertyTagExifCfaPattern = &HA302

%PropertyTagGpsVer = &H0
%PropertyTagGpsLatitudeRef = &H1
%PropertyTagGpsLatitude = &H2
%PropertyTagGpsLongitudeRef = &H3
%PropertyTagGpsLongitude = &H4
%PropertyTagGpsAltitudeRef = &H5
%PropertyTagGpsAltitude = &H6
%PropertyTagGpsGpsTime = &H7
%PropertyTagGpsGpsSatellites = &H8
%PropertyTagGpsGpsStatus = &H9
%PropertyTagGpsGpsMeasureMode = &HA
%PropertyTagGpsGpsDop = &HB ' Measurement precision
%PropertyTagGpsSpeedRef = &HC
%PropertyTagGpsSpeed = &HD
%PropertyTagGpsTrackRef = &HE
%PropertyTagGpsTrack = &HF
%PropertyTagGpsImgDirRef = &H10
%PropertyTagGpsImgDir = &H11
%PropertyTagGpsMapDatum = &H12
%PropertyTagGpsDestLatRef = &H13
%PropertyTagGpsDestLat = &H14
%PropertyTagGpsDestLongRef = &H15
%PropertyTagGpsDestLong = &H16
%PropertyTagGpsDestBearRef = &H17
%PropertyTagGpsDestBear = &H18
%PropertyTagGpsDestDistRef = &H19
%PropertyTagGpsDestDist = &H1A

' TODO: Make a function to get these GUIDs
' CLSIDs (aka GUIDs) used with the GdipGetImageRawFormat function:
'DEFINE_GUID(ImageFormatUndefined, 0xb96b3ca9,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatMemoryBMP, 0xb96b3caa,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatBMP, 0xb96b3cab,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatEMF, 0xb96b3cac,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatWMF, 0xb96b3cad,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatJPEG, 0xb96b3cae,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatPNG, 0xb96b3caf,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatGIF, 0xb96b3cb0,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatTIFF, 0xb96b3cb1,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatEXIF, 0xb96b3cb2,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);
'DEFINE_GUID(ImageFormatIcon, 0xb96b3cb5,0x0728,0x11d3,0x9d,0x7b,0x00,0x00,0xf8,0x1e,0xf3,0x2e);

'-----------------------------------------------
' The following types are NOT in the GDI+ docs, per se
'-----------------------------------------------

TYPE POINTF ' aka PointF
x AS SINGLE
y AS SINGLE
END TYPE

TYPE RECTF ' aka RectF
nLEFT AS SINGLE
nTop AS SINGLE
nRIGHT AS SINGLE
nBottom AS SINGLE
END TYPE

TYPE SIZEF ' aka SizeF
cx AS SINGLE
cy AS SINGLE
END TYPE

' Custom types
TYPE COLORBYTES
BlueByte AS BYTE
GreenByte AS BYTE
RedByte AS BYTE
AlphaByte AS BYTE
END TYPE

TYPE COLORLONG
longval AS LONG
END TYPE


'-----------------------------------------------
' GDI+ Structs/Types
'-----------------------------------------------

TYPE GdiplusStartupInput
GdiplusVersion AS LONG ' Must be 1
DebugEventCallback AS LONG ' Ignored on free builds
SuppressBackgroundThread AS LONG ' FALSE unless you're prepared to call
' the hook/unhook functions properly
SuppressExternalCodecs AS LONG ' FALSE unless you want GDI+ only to use
' its internal image codecs.
END TYPE

'TYPE GUIDAPI
' Data1 AS LONG
' Data2 AS INTEGER
' Data3 AS INTEGER
' Data4(0 TO 7) AS BYTE
'END TYPE

TYPE ImageCodecInfo
ClassID AS GUIDAPI
FormatID AS GUIDAPI
CodecName AS LONG ' String Pointer; const WCHAR*
DllName AS LONG ' String Pointer; const WCHAR*
FormatDescription AS LONG ' String Pointer; const WCHAR*
FilenameExtension AS LONG ' String Pointer; const WCHAR*
MimeType AS LONG ' String Pointer; const WCHAR*
flags AS LONG
Version AS LONG
SigCount AS LONG
SigSize AS LONG
SigPattern AS LONG ' Byte Array Pointer; BYTE*
SigMask AS LONG ' Byte Array Pointer; BYTE*
END TYPE

' Encoder Parameter structure
TYPE EncoderParameter
pGUID AS GUIDAPI ' GUID of the parameter
NumberOfValues AS LONG ' Number of the parameter values; usually 1
vType AS LONG ' EncoderParameterValueType ' Value type, like ValueTypeLONG etc.
value AS LONG ' A pointer to the parameter values
END TYPE

' Encoder Parameters structure
TYPE EncoderParameters
Count AS LONG ' Number of parameters in this structure; Should be 1
Parameter AS EncoderParameter ' Parameter values; this CAN be an array!!!! (Use CopyMemory and a string or byte array as workaround)
END TYPE

TYPE ColorPalette
flags AS LONG ' Palette flags
Count AS LONG ' Number of color entries
Entries AS LONG ' Palette color entries; this CAN be an array!!!! (Use CopyMemory and a string or byte array as workaround)
END TYPE

TYPE ColorMatrix
m(0 TO 4, 0 TO 4) AS SINGLE
END TYPE

' Information about image pixel data
TYPE BitmapData
nWIDTH AS LONG
nHeight AS LONG
stride AS LONG
PixelFormat AS LONG
scan0 AS LONG
Reserved AS LONG
END TYPE


TYPE PathData
Count AS LONG
pPoint AS LONG ' Pointer to POINTF array
types AS LONG ' Pointer to BYTE array
END TYPE

TYPE PropertyItem
propId AS LONG ' ID of this property
length AS LONG ' Length of the property value, in bytes
nType AS INTEGER ' Type of the value, as one of TAG_TYPE_XXX
' defined above
value AS LONG ' property value
END TYPE

TYPE LOGFONTA
lfHeight AS LONG
lfWidth AS LONG
lfEscapement AS LONG
lfOrientation AS LONG
lfWeight AS LONG
lfItalic AS BYTE
lfUnderline AS BYTE
lfStrikeOut AS BYTE
lfCharSet AS BYTE
lfOutPrecision AS BYTE
lfClipPrecision AS BYTE
lfQuality AS BYTE
lfPitchAndFamily AS BYTE
lfFaceName AS STRING * %LF_FACESIZE
END TYPE

TYPE LOGFONTW
lfHeight AS LONG
lfWidth AS LONG
lfEscapement AS LONG
lfOrientation AS LONG
lfWeight AS LONG
lfItalic AS BYTE
lfUnderline AS BYTE
lfStrikeOut AS BYTE
lfCharSet AS BYTE
lfOutPrecision AS BYTE
lfClipPrecision AS BYTE
lfQuality AS BYTE
lfPitchAndFamily AS BYTE
lfFaceName(1 TO %LF_FACESIZE) AS INTEGER ' TODO: Spruce this up a bit
END TYPE

TYPE CharacterRange
First AS LONG
length AS LONG
END TYPE

TYPE PWMFRect16
nLEFT AS INTEGER
nTop AS INTEGER
nRIGHT AS INTEGER
nBottom AS INTEGER
END TYPE

TYPE WmfPlaceableFileHeader
Key AS LONG ' GDIP_WMF_PLACEABLEKEY
Hmf AS INTEGER ' Metafile HANDLE number (always 0)
boundingBox AS PWMFRect16 ' Coordinates in metafile units
Inch AS INTEGER ' Number of metafile units per inch
Reserved AS LONG ' Reserved (always 0)
Checksum AS INTEGER ' Checksum value for previous 10 WORDs
END TYPE

TYPE ENHMETAHEADER3
itype AS LONG ' Record type EMR_HEADER
nSize AS LONG ' Record size in bytes. This may be greater
' than the sizeof(ENHMETAHEADER).
rclBounds AS RECTL ' Inclusive-inclusive bounds in device units
rclFrame AS RECTL ' Inclusive-inclusive Picture Frame .01mm unit
dSignature AS LONG ' Signature. Must be ENHMETA_SIGNATURE.
nVersion AS LONG ' Version number
nBytes AS LONG ' Size of the metafile in bytes
nRecords AS LONG ' Number of records in the metafile
nHandles AS INTEGER ' Number of handles in the handle table
' Handle index zero is reserved.
sReserved AS INTEGER ' Reserved. Must be zero.
nDescription AS LONG ' Number of chars in the unicode desc string
' This is 0 if there is no description string
offDescription AS LONG ' Offset to the metafile description record.
' This is 0 if there is no description string
nPalEntries AS LONG ' Number of entries in the metafile palette.
szlDevice AS SIZEL ' Size of the reference device in pels
szlMillimeters AS SIZEL ' Size of the reference device in millimeters
END TYPE

TYPE MetafileHeader
mType AS LONG ' MetafileType
SIZE AS LONG ' Size of the metafile (in bytes)
Version AS LONG ' EMF+, EMF, or WMF version
EmfPlusFlags AS LONG
DpiX AS SINGLE
DpiY AS SINGLE
x AS LONG ' Bounds in device units
y AS LONG
nWIDTH AS LONG
Height AS LONG
'Union
'{
' METAHEADER WmfHeader
' ENHMETAHEADER3 EmfHeader
'}
EmfHeader AS ENHMETAHEADER3 ' NOTE: You'll have to use CopyMemory to view the METAHEADER type
EmfPlusHeaderSize AS LONG ' size of the EMF+ header in file
LogicalDpiX AS LONG ' Logical Dpi of reference Hdc
LogicalDpiY AS LONG ' usually valid only for EMF+
END TYPE

'-----------------------------------------------
' GDI+ Enums
'-----------------------------------------------

%UnitWorld = 0 ' World coordinate (non-physical unit)
%UnitDisplay = 1 ' Variable -- for PageTransform only
%UnitPixel = 2 ' Each unit is one device pixel.
%UnitPoint = 3 ' Each unit is a printer's point, or 1/72 inch.
%UnitInch = 4 ' Each unit is 1 inch.
%UnitDocument = 5 ' Each unit is 1/300 inch.
%UnitMillimeter = 6 ' Each unit is 1 millimeter.

' Common color constants
' NOTE: Original enum was unnamed
%ColorsAliceBlue = &HFFF0F8FF
%ColorsAntiqueWhite = &HFFFAEBD7
%ColorsAqua = &HFF00FFFF
%ColorsAquamarine = &HFF7FFFD4
%ColorsAzure = &HFFF0FFFF
%ColorsBeige = &HFFF5F5DC
%ColorsBisque = &HFFFFE4C4
%ColorsBlack = &HFF000000
%ColorsBlanchedAlmond = &HFFFFEBCD
%ColorsBlue = &HFF0000FF
%ColorsBlueViolet = &HFF8A2BE2
%ColorsBrown = &HFFA52A2A
%ColorsBurlyWood = &HFFDEB887
%ColorsCadetBlue = &HFF5F9EA0
%ColorsChartreuse = &HFF7FFF00
%ColorsChocolate = &HFFD2691E
%ColorsCoral = &HFFFF7F50
%ColorsCornflowerBlue = &HFF6495ED
%ColorsCornsilk = &HFFFFF8DC
%ColorsCrimson = &HFFDC143C
%ColorsCyan = &HFF00FFFF
%ColorsDarkBlue = &HFF00008B
%ColorsDarkCyan = &HFF008B8B
%ColorsDarkGoldenrod = &HFFB8860B
%ColorsDarkGray = &HFFA9A9A9
%ColorsDarkGreen = &HFF006400
%ColorsDarkKhaki = &HFFBDB76B
%ColorsDarkMagenta = &HFF8B008B
%ColorsDarkOliveGreen = &HFF556B2F
%ColorsDarkOrange = &HFFFF8C00
%ColorsDarkOrchid = &HFF9932CC
%ColorsDarkRed = &HFF8B0000
%ColorsDarkSalmon = &HFFE9967A
%ColorsDarkSeaGreen = &HFF8FBC8B
%ColorsDarkSlateBlue = &HFF483D8B
%ColorsDarkSlateGray = &HFF2F4F4F
%ColorsDarkTurquoise = &HFF00CED1
%ColorsDarkViolet = &HFF9400D3
%ColorsDeepPink = &HFFFF1493
%ColorsDeepSkyBlue = &HFF00BFFF
%ColorsDimGray = &HFF696969
%ColorsDodgerBlue = &HFF1E90FF
%ColorsFirebrick = &HFFB22222
%ColorsFloralWhite = &HFFFFFAF0
%ColorsForestGreen = &HFF228B22
%ColorsFuchsia = &HFFFF00FF
%ColorsGainsboro = &HFFDCDCDC
%ColorsGhostWhite = &HFFF8F8FF
%ColorsGold = &HFFFFD700
%ColorsGoldenrod = &HFFDAA520
%ColorsGray = &HFF808080
%ColorsGreen = &HFF008000
%ColorsGreenYellow = &HFFADFF2F
%ColorsHoneydew = &HFFF0FFF0
%ColorsHotPink = &HFFFF69B4
%ColorsIndianRed = &HFFCD5C5C
%ColorsIndigo = &HFF4B0082
%ColorsIvory = &HFFFFFFF0
%ColorsKhaki = &HFFF0E68C
%ColorsLavender = &HFFE6E6FA
%ColorsLavenderBlush = &HFFFFF0F5
%ColorsLawnGreen = &HFF7CFC00
%ColorsLemonChiffon = &HFFFFFACD
%ColorsLightBlue = &HFFADD8E6
%ColorsLightCoral = &HFFF08080
%ColorsLightCyan = &HFFE0FFFF
%ColorsLightGoldenrodYellow = &HFFFAFAD2
%ColorsLightGray = &HFFD3D3D3
%ColorsLightGreen = &HFF90EE90
%ColorsLightPink = &HFFFFB6C1
%ColorsLightSalmon = &HFFFFA07A
%ColorsLightSeaGreen = &HFF20B2AA
%ColorsLightSkyBlue = &HFF87CEFA
%ColorsLightSlateGray = &HFF778899
%ColorsLightSteelBlue = &HFFB0C4DE
%ColorsLightYellow = &HFFFFFFE0
%ColorsLime = &HFF00FF00
%ColorsLimeGreen = &HFF32CD32
%ColorsLinen = &HFFFAF0E6
%ColorsMagenta = &HFFFF00FF
%ColorsMaroon = &HFF800000
%ColorsMediumAquamarine = &HFF66CDAA
%ColorsMediumBlue = &HFF0000CD
%ColorsMediumOrchid = &HFFBA55D3
%ColorsMediumPurple = &HFF9370DB
%ColorsMediumSeaGreen = &HFF3CB371
%ColorsMediumSlateBlue = &HFF7B68EE
%ColorsMediumSpringGreen = &HFF00FA9A
%ColorsMediumTurquoise = &HFF48D1CC
%ColorsMediumVioletRed = &HFFC71585
%ColorsMidnightBlue = &HFF191970
%ColorsMintCream = &HFFF5FFFA
%ColorsMistyRose = &HFFFFE4E1
%ColorsMoccasin = &HFFFFE4B5
%ColorsNavajoWhite = &HFFFFDEAD
%ColorsNavy = &HFF000080
%ColorsOldLace = &HFFFDF5E6
%ColorsOlive = &HFF808000
%ColorsOliveDrab = &HFF6B8E23
%ColorsOrange = &HFFFFA500
%ColorsOrangeRed = &HFFFF4500
%ColorsOrchid = &HFFDA70D6
%ColorsPaleGoldenrod = &HFFEEE8AA
%ColorsPaleGreen = &HFF98FB98
%ColorsPaleTurquoise = &HFFAFEEEE
%ColorsPaleVioletRed = &HFFDB7093
%ColorsPapayaWhip = &HFFFFEFD5
%ColorsPeachPuff = &HFFFFDAB9
%ColorsPeru = &HFFCD853F
%ColorsPink = &HFFFFC0CB
%ColorsPlum = &HFFDDA0DD
%ColorsPowderBlue = &HFFB0E0E6
%ColorsPurple = &HFF800080
%ColorsRed = &HFFFF0000
%ColorsRosyBrown = &HFFBC8F8F
%ColorsRoyalBlue = &HFF4169E1
%ColorsSaddleBrown = &HFF8B4513
%ColorsSalmon = &HFFFA8072
%ColorsSandyBrown = &HFFF4A460
%ColorsSeaGreen = &HFF2E8B57
%ColorsSeaShell = &HFFFFF5EE
%ColorsSienna = &HFFA0522D
%ColorsSilver = &HFFC0C0C0
%ColorsSkyBlue = &HFF87CEEB
%ColorsSlateBlue = &HFF6A5ACD
%ColorsSlateGray = &HFF708090
%ColorsSnow = &HFFFFFAFA
%ColorsSpringGreen = &HFF00FF7F
%ColorsSteelBlue = &HFF4682B4
%ColorsTan = &HFFD2B48C
%ColorsTeal = &HFF008080
%ColorsThistle = &HFFD8BFD8
%ColorsTomato = &HFFFF6347
%ColorsTransparent = &HFFFFFF
%ColorsTurquoise = &HFF40E0D0
%ColorsViolet = &HFFEE82EE
%ColorsWheat = &HFFF5DEB3
%ColorsWhite = &HFFFFFFFF
%ColorsWhiteSmoke = &HFFF5F5F5
%ColorsYellow = &HFFFFFF00
%ColorsYellowGreen = &HFF9ACD32

' NOTE: Enums evaluate to a Long
%GpStatusOk = 0
%GpStatusGenericError = 1
%GpStatusInvalidParameter = 2
%GpStatusOutOfMemory = 3
%GpStatusObjectBusy = 4
%GpStatusInsufficientBuffer = 5
%GpStatusNotImplemented = 6
%GpStatusWin32Error = 7
%GpStatusWrongState = 8
%GpStatusAborted = 9
%GpStatusFileNotFound = 10
%GpStatusValueOverflow = 11
%GpStatusAccessDenied = 12
%GpStatusUnknownImageFormat = 13
%GpStatusFontFamilyNotFound = 14
%GpStatusFontStyleNotFound = 15
%GpStatusNotTrueTypeFont = 16
%GpStatusUnsupportedGdiplusVersion = 17
%GpStatusGdiplusNotInitialized = 18
%GpStatusPropertyNotFound = 19
%GpStatusPropertyNotSupported = 20

' Quality mode constants
%QualityModeInvalid = -1
%QualityModeDefault = 0
%QualityModeLow = 1 ' Best performance
%QualityModeHigh = 2 ' Best rendering quality

' Alpha Compositing mode constants
%CompositingModeSourceOver = 0
%CompositingModeSourceCopy = 1

' Alpha Compositing quality constants
%CompositingQualityInvalid = %QualityModeInvalid
%CompositingQualityDefault = %QualityModeDefault
%CompositingQualityHighSpeed = %QualityModeLow
%CompositingQualityHighQuality = %QualityModeHigh
%CompositingQualityGammaCorrected = 3
%CompositingQualityAssumeLinear = 4

' Generic font families
%GenericFontFamilySerif = 0
%GenericFontFamilySansSerif = 1
%GenericFontFamilyMonospace = 2

' FontStyle: face types and common styles
%FontStyleRegular = 0
%FontStyleBold = 1
%FontStyleItalic = 2
%FontStyleBoldItalic = 3
%FontStyleUnderline = 4
%FontStyleStrikeout = 8

%SmoothingModeInvalid = %QualityModeInvalid
%SmoothingModeDefault = %QualityModeDefault
%SmoothingModeHighSpeed = %QualityModeLow
%SmoothingModeHighQuality = %QualityModeHigh
%SmoothingModeNone = 3
%SmoothingModeAntiAlias = 4

%FillModeAlternate = 0
%FillModeWinding = 1

%InterpolationModeInvalid = %QualityModeInvalid
%InterpolationModeDefault = %QualityModeDefault
%InterpolationModeLowQuality = %QualityModeLow
%InterpolationModeHighQuality = %QualityModeHigh
%InterpolationModeBilinear = 3
%InterpolationModeBicubic = 4
%InterpolationModeNearestNeighbor = 5
%InterpolationModeHighQualityBilinear = 6
%InterpolationModeHighQualityBicubic = 7

' Various wrap modes for brushes
%WrapModeTile = 0
%WrapModeTileFlipX = 1
%WrapModeTileFlipY = 2
%WrapModeTileFlipXY = 3
%WrapModeClamp = 4

%LinearGradientModeHorizontal = 0
%LinearGradientModeVertical = 1
%LinearGradientModeForwardDiagonal = 2
%LinearGradientModeBackwardDiagonal = 3

%ImageTypeUnknown = 0
%ImageTypeBitmap = 1
%ImageTypeMetafile = 2

' Various Hatch Styles
%HatchStyleHorizontal = 0
%HatchStyleVertical = 1
%HatchStyleForwardDiagonal = 2
%HatchStyleBackwardDiagonal = 3
%HatchStyleCross = 4
%HatchStyleDiagonalCross = 5
%HatchStyle05Percent = 6
%HatchStyle10Percent = 7
%HatchStyle20Percent = 8
%HatchStyle25Percent = 9
%HatchStyle30Percent = 10
%HatchStyle40Percent = 11
%HatchStyle50Percent = 12
%HatchStyle60Percent = 13
%HatchStyle70Percent = 14
%HatchStyle75Percent = 15
%HatchStyle80Percent = 16
%HatchStyle90Percent = 17
%HatchStyleLightDownwardDiagonal = 18
%HatchStyleLightUpwardDiagonal = 19
%HatchStyleDarkDownwardDiagonal = 20
%HatchStyleDarkUpwardDiagonal = 21
%HatchStyleWideDownwardDiagonal = 22
%HatchStyleWideUpwardDiagonal = 23
%HatchStyleLightVertical = 24
%HatchStyleLightHorizontal = 25
%HatchStyleNarrowVertical = 26
%HatchStyleNarrowHorizontal = 27
%HatchStyleDarkVertical = 28
%HatchStyleDarkHorizontal = 29
%HatchStyleDashedDownwardDiagonal = 30
%HatchStyleDashedUpwardDiagonal = 31
%HatchStyleDashedHorizontal = 32
%HatchStyleDashedVertical = 33
%HatchStyleSmallConfetti = 34
%HatchStyleLargeConfetti = 35
%HatchStyleZigZag = 36
%HatchStyleWave = 37
%HatchStyleDiagonalBrick = 38
%HatchStyleHorizontalBrick = 39
%HatchStyleWeave = 40
%HatchStylePlaid = 41
%HatchStyleDivot = 42
%HatchStyleDottedGrid = 43
%HatchStyleDottedDiamond = 44
%HatchStyleShingle = 45
%HatchStyleTrellis = 46
%HatchStyleSphere = 47
%HatchStyleSmallGrid = 48
%HatchStyleSmallCheckerBoard = 49
%HatchStyleLargeCheckerBoard = 50
%HatchStyleOutlinedDiamond = 51
%HatchStyleSolidDiamond = 52

%HatchStyleTotal = 53
%HatchStyleLargeGrid = %HatchStyleCross

%HatchStyleMin = %HatchStyleHorizontal
%HatchStyleMax = %HatchStyleTotal - 1

%MatrixOrderPrepend = 0
%MatrixOrderAppend = 1

%ColorAdjustTypeDefault = 0
%ColorAdjustTypeBitmap = 1
%ColorAdjustTypeBrush = 2
%ColorAdjustTypePen = 3
%ColorAdjustTypeText = 4
%ColorAdjustTypeCount = 5
%ColorAdjustTypeAny = 6 ' Reserved

%ColorChannelFlagsC = 0
%ColorChannelFlagsM = 1
%ColorChannelFlagsY = 2
%ColorChannelFlagsK = 3
%ColorChannelFlagsLast = 4

%ColorMatrixFlagsDefault = 0
%ColorMatrixFlagsSkipGrays = 1
%ColorMatrixFlagsAltGray = 2

%PenAlignmentCenter = 0
%PenAlignmentInset = 1

%BrushTypeSolidColor = 0
%BrushTypeHatchFill = 1
%BrushTypeTextureFill = 2
%BrushTypePathGradient = 3
%BrushTypeLinearGradient = 4

%DashStyleSolid = 0
%DashStyleDash = 1
%DashStyleDot = 2
%DashStyleDashDot = 3
%DashStyleDashDotDot = 4
%DashStyleCustom = 5

' Dash cap constants
%DashCapFlat = 0
%DashCapRound = 2
%DashCapTriangle = 3

' Line cap constants (only the lowest 8 bits are used).
%LineCapFlat = 0
%LineCapSquare = 1
%LineCapRound = 2
%LineCapTriangle = 3

%LineCapNoAnchor = &H10 ' corresponds to flat cap
%LineCapSquareAnchor = &H11 ' corresponds to square cap
%LineCapRoundAnchor = &H12 ' corresponds to round cap
%LineCapDiamondAnchor = &H13 ' corresponds to triangle cap
%LineCapArrowAnchor = &H14 ' no correspondence

%LineCapCustom = &HFF ' custom cap

%LineCapAnchorMask = &HF0 ' mask to check for anchor or not.

' Custom Line cap type constants
%CustomLineCapTypeDefault = 0
%CustomLineCapTypeAdjustableArrow = 1

' Line join constants
%LineJoinMiter = 0
%LineJoinBevel = 1
%LineJoinRound = 2
%LineJoinMiterClipped = 3

' Pen's Fill types
%PenTypeSolidColor = %BrushTypeSolidColor
%PenTypeHatchFill = %BrushTypeHatchFill
%PenTypeTextureFill = %BrushTypeTextureFill
%PenTypePathGradient = %BrushTypePathGradient
%PenTypeLinearGradient = %BrushTypeLinearGradient
%PenTypeUnknown = -1

%WarpModePerspective = 0
%WarpModeBilinear = 1

' Region Comine Modes
%CombineModeReplace = 0
%CombineModeIntersect = 1
%CombineModeUnion = 2
%CombineModeXor = 3
%CombineModeExclude = 4
%CombineModeComplement = 5 ' (Exclude From)

%RotateNoneFlipNone = 0
%Rotate90FlipNone = 1
%Rotate180FlipNone = 2
%Rotate270FlipNone = 3

%RotateNoneFlipX = 4
%Rotate90FlipX = 5
%Rotate180FlipX = 6
%Rotate270FlipX = 7

%RotateNoneFlipY = %Rotate180FlipX
%Rotate90FlipY = %Rotate270FlipX
%Rotate180FlipY = %RotateNoneFlipX
%Rotate270FlipY = %Rotate90FlipX

%RotateNoneFlipXY = %Rotate180FlipNone
%Rotate90FlipXY = %Rotate270FlipNone
%Rotate180FlipXY = %RotateNoneFlipNone
%Rotate270FlipXY = %Rotate90FlipNone


' String format flags
'
' DirectionRightToLeft - For horizontal text, the reading order is
' right to left. This value is called
' the base embedding level by the Unicode
' bidirectional engine.
' For vertical text, columns are read from
' right to left.
' By default, horizontal or vertical text is
' read from left to right.
'
' DirectionVertical - Individual lines of text are vertical. In
' each line, characters progress from top to
' bottom.
' By default, lines of text are horizontal,
' each new line below the previous line.
'
' NoFitBlackBox - Allows parts of glyphs to overhang the
' bounding rectangle.
' By default glyphs are first aligned
' inside the margines, then any glyphs which
' still overhang the bounding box are
' repositioned to avoid any overhang.
' For example when an italic
' lower case letter f in a font such as
' Garamond is aligned at the far left of a
' rectangle, the lower part of the f will
' reach slightly further left than the left
' edge of the rectangle. Setting this flag
' will ensure the character aligns visually
' with the lines above and below, but may
' cause some pixels outside the formatting
' rectangle to be clipped or painted.
'
' DisplayFormatControl - Causes control characters such as the
' left-to-right mark to be shown in the
' output with a representative glyph.
'
' NoFontFallback - Disables fallback to alternate fonts for
' characters not supported in the requested
' font. Any missing characters will be
' be displayed with the fonts missing glyph,
' usually an open square.
'
' NoWrap - Disables wrapping of text between lines
' when formatting within a rectangle.
' NoWrap is implied when a point is passed
' instead of a rectangle, or when the
' specified rectangle has a zero line length.
'
' NoClip - By default text is clipped to the
' formatting rectangle. Setting NoClip
' allows overhanging pixels to affect the
' device outside the formatting rectangle.
' Pixels at the end of the line may be
' affected if the glyphs overhang their
' cells, and either the NoFitBlackBox flag
' has been set, or the glyph extends to far
' to be fitted.
' Pixels above/before the first line or
' below/after the last line may be affected
' if the glyphs extend beyond their cell
' ascent / descent. This can occur rarely
' with unusual diacritic mark combinations.
%StringFormatFlagsDirectionRightToLeft = &H1
%StringFormatFlagsDirectionVertical = &H2
%StringFormatFlagsNoFitBlackBox = &H4
%StringFormatFlagsDisplayFormatControl = &H20
%StringFormatFlagsNoFontFallback = &H400
%StringFormatFlagsMeasureTrailingSpaces = &H800
%StringFormatFlagsNoWrap = &H1000
%StringFormatFlagsLineLimit = &H2000

%StringFormatFlagsNoClip = &H4000

%StringTrimmingNone = 0
%StringTrimmingCharacter = 1
%StringTrimmingWord = 2
%StringTrimmingEllipsisCharacter = 3
%StringTrimmingEllipsisWord = 4
%StringTrimmingEllipsisPath = 5

' National language digit substitution
%StringDigitSubstituteUser = 0 ' As NLS setting
%StringDigitSubstituteNone = 1
%StringDigitSubstituteNational = 2
%StringDigitSubstituteTraditional = 3

' Hotkey prefix interpretation
%HotkeyPrefixNone = 0
%HotkeyPrefixShow = 1
%HotkeyPrefixHide = 2

' Left edge for left-to-right text,
' right for right-to-left text,
' and top for vertical
%StringAlignmentNear = 0
%StringAlignmentCenter = 1
%StringAlignmentFar = 2

%FlushIntentionFlush = 0 ' Flush all batched rendering operations
%FlushIntentionSync = 1 ' Flush all batched rendering operations
' and wait for them to complete

' Image encoder parameter related types
%EncoderParameterValueTypeByte = 1 ' 8-bit unsigned int
%EncoderParameterValueTypeASCII = 2 ' 8-bit byte containing one 7-bit ASCII
' code. NULL terminated.
%EncoderParameterValueTypeShort = 3 ' 16-bit unsigned int
%EncoderParameterValueTypeLong = 4 ' 32-bit unsigned int
%EncoderParameterValueTypeRational = 5 ' Two Longs. The first Long is the
' numerator the second Long expresses the
' denomintor.
%EncoderParameterValueTypeLongRange = 6 ' Two longs which specify a range of
' integer values. The first Long specifies
' the lower end and the second one
' specifies the higher end. All values
' are inclusive at both ends
%EncoderParameterValueTypeUndefined = 7 ' 8-bit byte that can take any value
' depending on field definition
%EncoderParameterValueTypeRationalRange = 8 ' Two Rationals. The first Rational
' specifies the lower end and the second
' specifies the higher end. All values
' are inclusive at both ends


' Image encoder value types
%EncoderValueColorTypeCMYK = 0
%EncoderValueColorTypeYCCK = 1
%EncoderValueCompressionLZW = 2
%EncoderValueCompressionCCITT3 = 3
%EncoderValueCompressionCCITT4 = 4
%EncoderValueCompressionRle = 5
%EncoderValueCompressionNone = 6
%EncoderValueScanMethodInterlaced = 7
%EncoderValueScanMethodNonInterlaced = 8
%EncoderValueVersionGif87 = 9
%EncoderValueVersionGif89 = 10
%EncoderValueRenderProgressive = 11
%EncoderValueRenderNonProgressive = 12
%EncoderValueTransformRotate90 = 13
%EncoderValueTransformRotate180 = 14
%EncoderValueTransformRotate270 = 15
%EncoderValueTransformFlipHorizontal = 16
%EncoderValueTransformFlipVertical = 17
%EncoderValueMultiFrame = 18
%EncoderValueLastFrame = 19
%EncoderValueFlush = 20
%EncoderValueFrameDimensionTime = 21
%EncoderValueFrameDimensionResolution = 22
%EncoderValueFrameDimensionPage = 23

' CLSIDs (aka GUIDs) used with the EncoderParameter structure:
' NOTE: You won't find this enum in the GDI+ Docs. It was created as
' part of the workaround for the constant GUID problem.
%EncoderCompression = 0
%EncoderColorDepth = 1
%EncoderScanMethod = 2
%EncoderVersion = 3
%EncoderRenderMethod = 4
%EncoderQuality = 5
%EncoderTransformation = 6
%EncoderLuminanceTable = 7
%EncoderChrominanceTable = 8
%EncoderSaveFlag = 9

%PixelOffsetModeInvalid = %QualityModeInvalid
%PixelOffsetModeDefault = %QualityModeDefault
%PixelOffsetModeHighSpeed = %QualityModeLow
%PixelOffsetModeHighQuality = %QualityModeHigh
%PixelOffsetModeNone = 3 ' No pixel offset
%PixelOffsetModeHalf = 4 ' Offset by -0.5 -0.5 for fast anti-alias perf

%TextRenderingHintSystemDefault = 0 ' Glyph with system default rendering hint
%TextRenderingHintSingleBitPerPixelGridFit = 1 ' Glyph bitmap with hinting
%TextRenderingHintSingleBitPerPixel = 2 ' Glyph bitmap without hinting
%TextRenderingHintAntiAliasGridFit = 3 ' Glyph anti-alias bitmap with hinting
%TextRenderingHintAntiAlias = 4 ' Glyph anti-alias bitmap without hinting
%TextRenderingHintClearTypeGridFit = 5 ' Glyph CT bitmap with hinting

%MetafileTypeInvalid = 0 ' Invalid metafile
%MetafileTypeWmf = 1 ' Standard WMF
%MetafileTypeWmfPlaceable = 2 ' Placeable WMF
%MetafileTypeEmf = 3 ' EMF (not EMF+)
%MetafileTypeEmfPlusOnly = 4 ' EMF+ without dual down-level records
%MetafileTypeEmfPlusDual = 5 ' EMF+ with dual down-level records

' Specifies the type of EMF to record
%EmfTypeEmfOnly = %MetafileTypeEmf ' no EMF+ only EMF
%EmfTypeEmfPlusOnly = %MetafileTypeEmfPlusOnly ' no EMF only EMF+
%EmfTypeEmfPlusDual = %MetafileTypeEmfPlusDual ' both EMF+ and EMF

' EMF+ Persistent object types
%ObjectTypeInvalid = 0
%ObjectTypeBrush = 1
%ObjectTypePen = 2
%ObjectTypePath = 3
%ObjectTypeRegion = 4
%ObjectTypeImage = 5
%ObjectTypeFont = 6
%ObjectTypeStringFormat = 7
%ObjectTypeImageAttributes = 8
%ObjectTypeCustomLineCap = 9

%ObjectTypeMax = %ObjectTypeCustomLineCap
%ObjectTypeMin = %ObjectTypeBrush

' The frameRect for creating a metafile can be specified in any of these
' units. There is an extra frame unit value (MetafileFrameUnitGdi) so
' that units can be supplied in the same units that GDI expects for
' frame rects -- these units are in .01 (1/100ths) millimeter units
' as defined by GDI.
%MetafileFrameUnitPixel = %UnitPixel
%MetafileFrameUnitPoint = %UnitPoint
%MetafileFrameUnitInch = %UnitInch
%MetafileFrameUnitDocument = %UnitDocument
%MetafileFrameUnitMillimeter = %UnitMillimeter
%MetafileFrameUnitGdi = 7 ' GDI compatible .01 MM units

' Coordinate space identifiers
%CoordinateSpaceWorld = 0
%CoordinateSpacePage = 1
%CoordinateSpaceDevice = 2


------------------
Patrice Terrier
pterrier@zapsolution.com

IP: Logged
Patrice Terrier
Member 	posted November 06, 2002 05:06 AM     Click Here to See the Profile for Patrice Terrier     Edit/Delete Message GDIPLUS.INC for PB/WIN part 2


'-----------------------------------------------
' APIs
'-----------------------------------------------

DECLARE FUNCTION GdiplusStartup LIB "gdiplus.dll" ALIAS "GdiplusStartup" (token AS LONG, inputbuf AS GdiplusStartupInput, OPTIONAL BYVAL outputbuf AS LONG) AS LONG
DECLARE FUNCTION GdiplusShutdown LIB "gdiplus.dll" ALIAS "GdiplusShutdown" (BYVAL token AS LONG) AS LONG

' Graphics Functions (ALL)
DECLARE FUNCTION GdipFlush LIB "gdiplus.dll" ALIAS "GdipFlush" (BYVAL graphics AS LONG, BYVAL intention AS LONG) AS LONG
DECLARE FUNCTION GdipCreateFromHDC LIB "gdiplus.dll" ALIAS "GdipCreateFromHDC" (BYVAL hdc AS LONG, graphics AS LONG) AS LONG
DECLARE FUNCTION GdipCreateFromHWND LIB "gdiplus.dll" ALIAS "GdipCreateFromHWND" (BYVAL hwnd AS LONG, graphics AS LONG) AS LONG
DECLARE FUNCTION GdipCreateFromHWNDICM LIB "gdiplus.dll" ALIAS "GdipCreateFromHWNDICM" (BYVAL hwnd AS LONG, graphics AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteGraphics LIB "gdiplus.dll" ALIAS "GdipDeleteGraphics" (BYVAL graphics AS LONG) AS LONG
DECLARE FUNCTION GdipGetDC LIB "gdiplus.dll" ALIAS "GdipGetDC" (BYVAL graphics AS LONG, hdc AS LONG) AS LONG
DECLARE FUNCTION GdipReleaseDC LIB "gdiplus.dll" ALIAS "GdipReleaseDC" (BYVAL graphics AS LONG, BYVAL hdc AS LONG) AS LONG
DECLARE FUNCTION GdipSetCompositingMode LIB "gdiplus.dll" ALIAS "GdipSetCompositingMode" (BYVAL graphics AS LONG, BYVAL CompositingMd AS LONG) AS LONG
DECLARE FUNCTION GdipGetCompositingMode LIB "gdiplus.dll" ALIAS "GdipGetCompositingMode" (BYVAL graphics AS LONG, CompositingMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetRenderingOrigin LIB "gdiplus.dll" ALIAS "GdipSetRenderingOrigin" (BYVAL graphics AS LONG, BYVAL x AS LONG, BYVAL y AS LONG) AS LONG
DECLARE FUNCTION GdipGetRenderingOrigin LIB "gdiplus.dll" ALIAS "GdipGetRenderingOrigin" (BYVAL graphics AS LONG, x AS LONG, y AS LONG) AS LONG
DECLARE FUNCTION GdipSetCompositingQuality LIB "gdiplus.dll" ALIAS "GdipSetCompositingQuality" (BYVAL graphics AS LONG, BYVAL CompositingQlty AS LONG) AS LONG
DECLARE FUNCTION GdipGetCompositingQuality LIB "gdiplus.dll" ALIAS "GdipGetCompositingQuality" (BYVAL graphics AS LONG, CompositingQlty AS LONG) AS LONG
DECLARE FUNCTION GdipSetSmoothingMode LIB "gdiplus.dll" ALIAS "GdipSetSmoothingMode" (BYVAL graphics AS LONG, BYVAL SmoothingMd AS LONG) AS LONG
DECLARE FUNCTION GdipGetSmoothingMode LIB "gdiplus.dll" ALIAS "GdipGetSmoothingMode" (BYVAL graphics AS LONG, SmoothingMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetPixelOffsetMode LIB "gdiplus.dll" ALIAS "GdipSetPixelOffsetMode" (BYVAL graphics AS LONG, BYVAL PixOffsetMode AS LONG) AS LONG
DECLARE FUNCTION GdipGetPixelOffsetMode LIB "gdiplus.dll" ALIAS "GdipGetPixelOffsetMode" (BYVAL graphics AS LONG, PixOffsetMode AS LONG) AS LONG
DECLARE FUNCTION GdipSetTextRenderingHint LIB "gdiplus.dll" ALIAS "GdipSetTextRenderingHint" (BYVAL graphics AS LONG, BYVAL mode AS LONG) AS LONG
DECLARE FUNCTION GdipGetTextRenderingHint LIB "gdiplus.dll" ALIAS "GdipGetTextRenderingHint" (BYVAL graphics AS LONG, mode AS LONG) AS LONG
DECLARE FUNCTION GdipSetTextContrast LIB "gdiplus.dll" ALIAS "GdipSetTextContrast" (BYVAL graphics AS LONG, BYVAL contrast AS LONG) AS LONG
DECLARE FUNCTION GdipGetTextContrast LIB "gdiplus.dll" ALIAS "GdipGetTextContrast" (BYVAL graphics AS LONG, contrast AS LONG) AS LONG
DECLARE FUNCTION GdipSetInterpolationMode LIB "gdiplus.dll" ALIAS "GdipSetInterpolationMode" (BYVAL graphics AS LONG, BYVAL interpolation AS LONG) AS LONG
DECLARE FUNCTION GdipGetInterpolationMode LIB "gdiplus.dll" ALIAS "GdipGetInterpolationMode" (BYVAL graphics AS LONG, interpolation AS LONG) AS LONG
DECLARE FUNCTION GdipSetWorldTransform LIB "gdiplus.dll" ALIAS "GdipSetWorldTransform" (BYVAL graphics AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipResetWorldTransform LIB "gdiplus.dll" ALIAS "GdipResetWorldTransform" (BYVAL graphics AS LONG) AS LONG
DECLARE FUNCTION GdipMultiplyWorldTransform LIB "gdiplus.dll" ALIAS "GdipMultiplyWorldTransform" (BYVAL graphics AS LONG, BYVAL matrix AS LONG, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipTranslateWorldTransform LIB "gdiplus.dll" ALIAS "GdipTranslateWorldTransform" (BYVAL graphics AS LONG, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipScaleWorldTransform LIB "gdiplus.dll" ALIAS "GdipScaleWorldTransform" (BYVAL graphics AS LONG, BYVAL sx AS SINGLE, BYVAL sy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipRotateWorldTransform LIB "gdiplus.dll" ALIAS "GdipRotateWorldTransform" (BYVAL graphics AS LONG, BYVAL angle AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipGetWorldTransform LIB "gdiplus.dll" ALIAS "GdipGetWorldTransform" (BYVAL graphics AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipResetPageTransform LIB "gdiplus.dll" ALIAS "GdipResetPageTransform" (BYVAL graphics AS LONG) AS LONG
DECLARE FUNCTION GdipGetPageUnit LIB "gdiplus.dll" ALIAS "GdipGetPageUnit" (BYVAL graphics AS LONG, unit AS LONG) AS LONG
DECLARE FUNCTION GdipGetPageScale LIB "gdiplus.dll" ALIAS "GdipGetPageScale" (BYVAL graphics AS LONG, sscale AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetPageUnit LIB "gdiplus.dll" ALIAS "GdipSetPageUnit" (BYVAL graphics AS LONG, BYVAL unit AS LONG) AS LONG
DECLARE FUNCTION GdipSetPageScale LIB "gdiplus.dll" ALIAS "GdipSetPageScale" (BYVAL graphics AS LONG, BYVAL sscale AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetDpiX LIB "gdiplus.dll" ALIAS "GdipGetDpiX" (BYVAL graphics AS LONG, dpi AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetDpiY LIB "gdiplus.dll" ALIAS "GdipGetDpiY" (BYVAL graphics AS LONG, dpi AS SINGLE) AS LONG
DECLARE FUNCTION GdipTransformPoints LIB "gdiplus.dll" ALIAS "GdipTransformPoints" (BYVAL graphics AS LONG, BYVAL destSpace AS LONG, BYVAL srcSpace AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipTransformPointsI LIB "gdiplus.dll" ALIAS "GdipTransformPointsI" (BYVAL graphics AS LONG, BYVAL destSpace AS LONG, BYVAL srcSpace AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetNearestColor LIB "gdiplus.dll" ALIAS "GdipGetNearestColor" (BYVAL graphics AS LONG, argb AS LONG) AS LONG
' Creates the Win9x Halftone Palette (even on NT) with correct Desktop colors
DECLARE FUNCTION GdipCreateHalftonePalette LIB "gdiplus.dll" ALIAS "GdipCreateHalftonePalette" () AS LONG
DECLARE FUNCTION GdipDrawLine LIB "gdiplus.dll" ALIAS "GdipDrawLine" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x1 AS SINGLE, BYVAL y1 AS SINGLE, BYVAL x2 AS SINGLE, BYVAL y2 AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawLineI LIB "gdiplus.dll" ALIAS "GdipDrawLineI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x1 AS LONG, BYVAL y1 AS LONG, BYVAL x2 AS LONG, BYVAL y2 AS LONG) AS LONG
DECLARE FUNCTION GdipDrawLines LIB "gdiplus.dll" ALIAS "GdipDrawLines" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawLinesI LIB "gdiplus.dll" ALIAS "GdipDrawLinesI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawArc LIB "gdiplus.dll" ALIAS "GdipDrawArc" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawArcI LIB "gdiplus.dll" ALIAS "GdipDrawArcI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawBezier LIB "gdiplus.dll" ALIAS "GdipDrawBezier" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x1 AS SINGLE, BYVAL y1 AS SINGLE, BYVAL x2 AS SINGLE, BYVAL y2 AS SINGLE, BYVAL x3 AS SINGLE, BYVAL y3 AS SINGLE, BYVAL x4 AS SINGLE, BYVAL y4 AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawBezierI LIB "gdiplus.dll" ALIAS "GdipDrawBezierI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x1 AS LONG, BYVAL y1 AS LONG, BYVAL x2 AS LONG, BYVAL y2 AS LONG, BYVAL x3 AS LONG, BYVAL y3 AS LONG, BYVAL x4 AS LONG, BYVAL y4 AS LONG) AS LONG
DECLARE FUNCTION GdipDrawBeziers LIB "gdiplus.dll" ALIAS "GdipDrawBeziers" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawBeziersI LIB "gdiplus.dll" ALIAS "GdipDrawBeziersI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawRectangle LIB "gdiplus.dll" ALIAS "GdipDrawRectangle" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawRectangleI LIB "gdiplus.dll" ALIAS "GdipDrawRectangleI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG) AS LONG
DECLARE FUNCTION GdipDrawRectangles LIB "gdiplus.dll" ALIAS "GdipDrawRectangles" (BYVAL graphics AS LONG, BYVAL pen AS LONG, rects AS RECTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawRectanglesI LIB "gdiplus.dll" ALIAS "GdipDrawRectanglesI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, rects AS RECTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawEllipse LIB "gdiplus.dll" ALIAS "GdipDrawEllipse" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawEllipseI LIB "gdiplus.dll" ALIAS "GdipDrawEllipseI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG) AS LONG
DECLARE FUNCTION GdipDrawPie LIB "gdiplus.dll" ALIAS "GdipDrawPie" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawPieI LIB "gdiplus.dll" ALIAS "GdipDrawPieI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawPolygon LIB "gdiplus.dll" ALIAS "GdipDrawPolygon" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawPolygonI LIB "gdiplus.dll" ALIAS "GdipDrawPolygonI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawPath LIB "gdiplus.dll" ALIAS "GdipDrawPath" (BYVAL graphics AS LONG, BYVAL pen AS LONG, BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipDrawCurve LIB "gdiplus.dll" ALIAS "GdipDrawCurve" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawCurveI LIB "gdiplus.dll" ALIAS "GdipDrawCurveI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawCurve2 LIB "gdiplus.dll" ALIAS "GdipDrawCurve2" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawCurve2I LIB "gdiplus.dll" ALIAS "GdipDrawCurve2I" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawCurve3 LIB "gdiplus.dll" ALIAS "GdipDrawCurve3" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL offset AS LONG, BYVAL numberOfSegments AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawCurve3I LIB "gdiplus.dll" ALIAS "GdipDrawCurve3I" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL offset AS LONG, BYVAL numberOfSegments AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawClosedCurve LIB "gdiplus.dll" ALIAS "GdipDrawClosedCurve" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawClosedCurveI LIB "gdiplus.dll" ALIAS "GdipDrawClosedCurveI" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawClosedCurve2 LIB "gdiplus.dll" ALIAS "GdipDrawClosedCurve2" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawClosedCurve2I LIB "gdiplus.dll" ALIAS "GdipDrawClosedCurve2I" (BYVAL graphics AS LONG, BYVAL pen AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipGraphicsClear LIB "gdiplus.dll" ALIAS "GdipGraphicsClear" (BYVAL graphics AS LONG, BYVAL lColor AS LONG) AS LONG
DECLARE FUNCTION GdipFillRectangle LIB "gdiplus.dll" ALIAS "GdipFillRectangle" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipFillRectangleI LIB "gdiplus.dll" ALIAS "GdipFillRectangleI" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG) AS LONG
DECLARE FUNCTION GdipFillRectangles LIB "gdiplus.dll" ALIAS "GdipFillRectangles" (BYVAL graphics AS LONG, BYVAL brush AS LONG, rects AS RECTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipFillRectanglesI LIB "gdiplus.dll" ALIAS "GdipFillRectanglesI" (BYVAL graphics AS LONG, BYVAL brush AS LONG, rects AS RECTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipFillPolygon LIB "gdiplus.dll" ALIAS "GdipFillPolygon" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL FillMd AS LONG) AS LONG
DECLARE FUNCTION GdipFillPolygonI LIB "gdiplus.dll" ALIAS "GdipFillPolygonI" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL FillMd AS LONG) AS LONG
DECLARE FUNCTION GdipFillPolygon2 LIB "gdiplus.dll" ALIAS "GdipFillPolygon2" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipFillPolygon2I LIB "gdiplus.dll" ALIAS "GdipFillPolygon2I" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipFillEllipse LIB "gdiplus.dll" ALIAS "GdipFillEllipse" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipFillEllipseI LIB "gdiplus.dll" ALIAS "GdipFillEllipseI" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG) AS LONG
DECLARE FUNCTION GdipFillPie LIB "gdiplus.dll" ALIAS "GdipFillPie" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipFillPieI LIB "gdiplus.dll" ALIAS "GdipFillPieI" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipFillPath LIB "gdiplus.dll" ALIAS "GdipFillPath" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipFillClosedCurve LIB "gdiplus.dll" ALIAS "GdipFillClosedCurve" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipFillClosedCurveI LIB "gdiplus.dll" ALIAS "GdipFillClosedCurveI" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipFillClosedCurve2 LIB "gdiplus.dll" ALIAS "GdipFillClosedCurve2" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL tension AS SINGLE, BYVAL FillMd AS LONG) AS LONG
DECLARE FUNCTION GdipFillClosedCurve2I LIB "gdiplus.dll" ALIAS "GdipFillClosedCurve2I" (BYVAL graphics AS LONG, BYVAL brush AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL tension AS SINGLE, BYVAL FillMd AS LONG) AS LONG
DECLARE FUNCTION GdipFillRegion LIB "gdiplus.dll" ALIAS "GdipFillRegion" (BYVAL graphics AS LONG, BYVAL brush AS LONG, BYVAL region AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImage LIB "gdiplus.dll" ALIAS "GdipDrawImage" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawImageI LIB "gdiplus.dll" ALIAS "GdipDrawImageI" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL x AS LONG, BYVAL y AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImageRect LIB "gdiplus.dll" ALIAS "GdipDrawImageRect" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipDrawImageRectI LIB "gdiplus.dll" ALIAS "GdipDrawImageRectI" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImagePoints LIB "gdiplus.dll" ALIAS "GdipDrawImagePoints" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, dstpoints AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImagePointsI LIB "gdiplus.dll" ALIAS "GdipDrawImagePointsI" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, dstpoints AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImagePointRect LIB "gdiplus.dll" ALIAS "GdipDrawImagePointRect" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL srcx AS SINGLE, BYVAL srcy AS SINGLE, BYVAL srcwidth AS SINGLE, BYVAL srcheight AS SINGLE, BYVAL srcUnit AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImagePointRectI LIB "gdiplus.dll" ALIAS "GdipDrawImagePointRectI" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL srcx AS LONG, BYVAL srcy AS LONG, BYVAL srcwidth AS LONG, BYVAL srcheight AS LONG, BYVAL srcUnit AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImageRectRect LIB "gdiplus.dll" ALIAS "GdipDrawImageRectRect" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL dstx AS SINGLE, BYVAL dsty AS SINGLE, BYVAL dstwidth AS LONG, BYVAL dstheight AS SINGLE, BYVAL srcx AS SINGLE, BYVAL srcy AS SINGLE, BYVAL srcwidth AS SINGLE, BYVAL srcheight AS SINGLE, BYVAL srcUnit AS LONG, OPTIONAL BYVAL imageAttributes AS LONG, OPTIONAL BYVAL pCALLBACK AS LONG, OPTIONAL BYVAL callbackData AS LONG) AS LONG
' Callback declaration: Public Function DrawImageAbort(ByVal lpData as Long) as Long
DECLARE FUNCTION GdipDrawImageRectRectI LIB "gdiplus.dll" ALIAS "GdipDrawImageRectRectI" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, BYVAL dstx AS LONG, BYVAL dsty AS LONG, BYVAL dstwidth AS LONG, BYVAL dstheight AS LONG, BYVAL srcx AS LONG, BYVAL srcy AS LONG, BYVAL srcwidth AS LONG, BYVAL srcheight AS LONG, BYVAL srcUnit AS LONG, OPTIONAL BYVAL imageAttributes AS LONG, OPTIONAL BYVAL pCALLBACK AS LONG, OPTIONAL BYVAL callbackData AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImagePointsRect LIB "gdiplus.dll" ALIAS "GdipDrawImagePointsRect" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL srcx AS SINGLE, BYVAL srcy AS SINGLE, BYVAL srcwidth AS SINGLE, BYVAL srcheight AS SINGLE, BYVAL srcUnit AS LONG, OPTIONAL BYVAL imageAttributes AS LONG, OPTIONAL BYVAL pCALLBACK AS LONG, OPTIONAL BYVAL callbackData AS LONG) AS LONG
DECLARE FUNCTION GdipDrawImagePointsRectI LIB "gdiplus.dll" ALIAS "GdipDrawImagePointsRectI" (BYVAL graphics AS LONG, BYVAL nImage AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL srcx AS LONG, BYVAL srcy AS LONG, BYVAL srcwidth AS LONG, BYVAL srcheight AS LONG, BYVAL srcUnit AS LONG, OPTIONAL BYVAL imageAttributes AS LONG, OPTIONAL BYVAL pCALLBACK AS LONG, OPTIONAL BYVAL callbackData AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileDestPoint LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileDestPoint" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destPoint AS POINTF, lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, imageAttributes AS LONG) AS LONG
' Callback declaration: Public Function EnumMetafilesProc(Byval rtype as EmfPlusRecordType, byval _ as Long, byval _ as Long, bytes as Any, byval callbackData as long) as long
DECLARE FUNCTION GdipEnumerateMetafileDestPointI LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileDestPointI" (graphics AS LONG, BYVAL metafile AS LONG, destPoint AS POINTL, BYVAL lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, BYVAL imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileDestRect LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileDestRect" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destRect AS RECTF, lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileDestRectI LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileDestRectI" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destRect AS RECTL, lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileDestPoints LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileDestPoints" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destPoint AS POINTF, BYVAL Count AS LONG, lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileDestPointsI LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileDestPointsI" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destPoint AS POINTL, BYVAL Count AS LONG, lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileSrcRectDestPoint LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileSrcRectDestPoint" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destPoint AS POINTF, srcRect AS RECTF, BYVAL srcUnit AS LONG, BYVAL lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, BYVAL imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileSrcRectDestPointI LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileSrcRectDestPointI" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destPoint AS POINTL, srcRect AS RECTL, BYVAL srcUnit AS LONG, BYVAL lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, BYVAL imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileSrcRectDestRect LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileSrcRectDestRect" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destRect AS RECTF, srcRect AS RECTF, BYVAL srcUnit AS LONG, BYVAL lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, BYVAL imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileSrcRectDestRectI LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileSrcRectDestRectI" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destRect AS RECTL, srcRect AS RECTL, BYVAL srcUnit AS LONG, BYVAL lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, BYVAL imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileSrcRectDestPoints LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileSrcRectDestPoints" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destPoints AS POINTF, BYVAL Count AS LONG, srcRect AS RECTF, BYVAL srcUnit AS LONG, BYVAL lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, BYVAL imageAttributes AS LONG) AS LONG
DECLARE FUNCTION GdipEnumerateMetafileSrcRectDestPointsI LIB "gdiplus.dll" ALIAS "GdipEnumerateMetafileSrcRectDestPointsI" (BYVAL graphics AS LONG, BYVAL metafile AS LONG, destPoints AS POINTL, BYVAL Count AS LONG, srcRect AS RECTL, BYVAL srcUnit AS LONG, BYVAL lpEnumerateMetafileProc AS LONG, BYVAL callbackData AS LONG, BYVAL imageAttributes AS LONG) AS LONG
' TODO: Declare the EmfPlusRecordType enum and uncomment
'DECLARE FUNCTION GdipPlayMetafileRecord LIB "gdiplus.dll" ALIAS "GdipPlayMetafileRecord" (ByVal metafile As Long, ByVal recordType As EmfPlusRecordType, ByVal flags As Long, ByVal dataSize As Long, byteData As Any) AS LONG
DECLARE FUNCTION GdipSetClipGraphics LIB "gdiplus.dll" ALIAS "GdipSetClipGraphics" (BYVAL graphics AS LONG, BYVAL srcgraphics AS LONG, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetClipRect LIB "gdiplus.dll" ALIAS "GdipSetClipRect" (BYVAL graphics AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetClipRectI LIB "gdiplus.dll" ALIAS "GdipSetClipRectI" (BYVAL graphics AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetClipPath LIB "gdiplus.dll" ALIAS "GdipSetClipPath" (BYVAL graphics AS LONG, BYVAL path AS LONG, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetClipRegion LIB "gdiplus.dll" ALIAS "GdipSetClipRegion" (BYVAL graphics AS LONG, BYVAL region AS LONG, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetClipHrgn LIB "gdiplus.dll" ALIAS "GdipSetClipHrgn" (BYVAL graphics AS LONG, BYVAL hRgn AS LONG, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipResetClip LIB "gdiplus.dll" ALIAS "GdipResetClip" (BYVAL graphics AS LONG) AS LONG
DECLARE FUNCTION GdipTranslateClip LIB "gdiplus.dll" ALIAS "GdipTranslateClip" (BYVAL graphics AS LONG, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE) AS LONG
DECLARE FUNCTION GdipTranslateClipI LIB "gdiplus.dll" ALIAS "GdipTranslateClipI" (BYVAL graphics AS LONG, BYVAL dx AS LONG, BYVAL dy AS LONG) AS LONG
DECLARE FUNCTION GdipGetClip LIB "gdiplus.dll" ALIAS "GdipGetClip" (BYVAL graphics AS LONG, BYVAL region AS LONG) AS LONG
DECLARE FUNCTION GdipGetClipBounds LIB "gdiplus.dll" ALIAS "GdipGetClipBounds" (BYVAL graphics AS LONG, nRect AS RECTF) AS LONG
DECLARE FUNCTION GdipGetClipBoundsI LIB "gdiplus.dll" ALIAS "GdipGetClipBoundsI" (BYVAL graphics AS LONG, nRect AS RECTL) AS LONG
DECLARE FUNCTION GdipIsClipEmpty LIB "gdiplus.dll" ALIAS "GdipIsClipEmpty" (BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipGetVisibleClipBounds LIB "gdiplus.dll" ALIAS "GdipGetVisibleClipBounds" (BYVAL graphics AS LONG, nRect AS RECTF) AS LONG
DECLARE FUNCTION GdipGetVisibleClipBoundsI LIB "gdiplus.dll" ALIAS "GdipGetVisibleClipBoundsI" (BYVAL graphics AS LONG, nRect AS RECTL) AS LONG
DECLARE FUNCTION GdipIsVisibleClipEmpty LIB "gdiplus.dll" ALIAS "GdipIsVisibleClipEmpty" (BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisiblePoint LIB "gdiplus.dll" ALIAS "GdipIsVisiblePoint" (BYVAL graphics AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisiblePointI LIB "gdiplus.dll" ALIAS "GdipIsVisiblePointI" (BYVAL graphics AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisibleRect LIB "gdiplus.dll" ALIAS "GdipIsVisibleRect" (BYVAL graphics AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisibleRectI LIB "gdiplus.dll" ALIAS "GdipIsVisibleRectI" (BYVAL graphics AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipSaveGraphics LIB "gdiplus.dll" ALIAS "GdipSaveGraphics" (BYVAL graphics AS LONG, STATE AS LONG) AS LONG
DECLARE FUNCTION GdipRestoreGraphics LIB "gdiplus.dll" ALIAS "GdipRestoreGraphics" (BYVAL graphics AS LONG, BYVAL STATE AS LONG) AS LONG
DECLARE FUNCTION GdipBeginContainer LIB "gdiplus.dll" ALIAS "GdipBeginContainer" (BYVAL graphics AS LONG, dstrect AS RECTF, srcRect AS RECTF, BYVAL unit AS LONG, STATE AS LONG) AS LONG
DECLARE FUNCTION GdipBeginContainerI LIB "gdiplus.dll" ALIAS "GdipBeginContainerI" (BYVAL graphics AS LONG, dstrect AS RECTL, srcRect AS RECTL, BYVAL unit AS LONG, STATE AS LONG) AS LONG
DECLARE FUNCTION GdipBeginContainer2 LIB "gdiplus.dll" ALIAS "GdipBeginContainer2" (BYVAL graphics AS LONG, STATE AS LONG) AS LONG
DECLARE FUNCTION GdipEndContainer LIB "gdiplus.dll" ALIAS "GdipEndContainer" (BYVAL graphics AS LONG, BYVAL STATE AS LONG) AS LONG
DECLARE FUNCTION GdipGetMetafileHeaderFromWmf LIB "gdiplus.dll" ALIAS "GdipGetMetafileHeaderFromWmf" (BYVAL hWmf AS LONG, WmfPlaceableFileHdr AS WmfPlaceableFileHeader, header AS MetafileHeader) AS LONG
DECLARE FUNCTION GdipGetMetafileHeaderFromEmf LIB "gdiplus.dll" ALIAS "GdipGetMetafileHeaderFromEmf" (BYVAL hEmf AS LONG, header AS MetafileHeader) AS LONG
DECLARE FUNCTION GdipGetMetafileHeaderFromFile LIB "gdiplus.dll" ALIAS "GdipGetMetafileHeaderFromFile" (BYVAL FilName AS STRING, header AS MetafileHeader) AS LONG
' TODO: Uncomment if you have the IStream object declared, or equivalent
'DECLARE FUNCTION GdipGetMetafileHeaderFromStream LIB "gdiplus.dll" ALIAS "GdipGetMetafileHeaderFromStream" (Byval stream as IStream, header As MetafileHeader) AS LONG
DECLARE FUNCTION GdipGetMetafileHeaderFromMetafile LIB "gdiplus.dll" ALIAS "GdipGetMetafileHeaderFromMetafile" (BYVAL metafile AS LONG, header AS MetafileHeader) AS LONG
DECLARE FUNCTION GdipGetHemfFromMetafile LIB "gdiplus.dll" ALIAS "GdipGetHemfFromMetafile" (BYVAL metafile AS LONG, hEmf AS LONG) AS LONG
' TODO: Uncomment if you have the IStream object declared, or equivalent
' NOTE: The C++ stream parameter was declared as IStream** stream
'DECLARE FUNCTION GdipCreateStreamOnFile LIB "gdiplus.dll" ALIAS "GdipCreateStreamOnFile" (ByVal FilName As String, ByVal access As Long, stream As IStream) AS LONG
DECLARE FUNCTION GdipCreateMetafileFromWmf LIB "gdiplus.dll" ALIAS "GdipCreateMetafileFromWmf" (BYVAL hWmf AS LONG, BYVAL bDeleteWmf AS LONG, WmfPlaceableFileHdr AS WmfPlaceableFileHeader, BYVAL metafile AS LONG) AS LONG
DECLARE FUNCTION GdipCreateMetafileFromEmf LIB "gdiplus.dll" ALIAS "GdipCreateMetafileFromEmf" (BYVAL hEmf AS LONG, BYVAL bDeleteEmf AS LONG, metafile AS LONG) AS LONG
DECLARE FUNCTION GdipCreateMetafileFromFile LIB "gdiplus.dll" ALIAS "GdipCreateMetafileFromFile" (byvalfile AS STRING, metafile AS LONG) AS LONG
DECLARE FUNCTION GdipCreateMetafileFromWmfFile LIB "gdiplus.dll" ALIAS "GdipCreateMetafileFromWmfFile" (BYVAL file AS STRING, WmfPlaceableFileHdr AS WmfPlaceableFileHeader, metafile AS LONG) AS LONG
' TODO: Uncomment if you have the IStream object declared, or equivalent
'DECLARE FUNCTION GdipCreateMetafileFromStream LIB "gdiplus.dll" ALIAS "GdipCreateMetafileFromStream" (Byval stream as IStream, metafile As Long) AS LONG
DECLARE FUNCTION GdipRecordMetafile LIB "gdiplus.dll" ALIAS "GdipRecordMetafile" (BYVAL referenceHdc AS LONG, etype AS LONG, frameRect AS RECTF, BYVAL frameUnit AS LONG, BYVAL description AS STRING, metafile AS LONG) AS LONG
DECLARE FUNCTION GdipRecordMetafileI LIB "gdiplus.dll" ALIAS "GdipRecordMetafileI" (BYVAL referenceHdc AS LONG, etype AS LONG, frameRect AS RECTL, BYVAL frameUnit AS LONG, BYVAL description AS STRING, metafile AS LONG) AS LONG
DECLARE FUNCTION GdipRecordMetafileFileName LIB "gdiplus.dll" ALIAS "GdipRecordMetafileFileName" (BYVAL FilName AS STRING, BYVAL referenceHdc AS LONG, etype AS LONG, frameRect AS RECTF, BYVAL frameUnit AS LONG, BYVAL description AS STRING, metafile AS LONG) AS LONG
DECLARE FUNCTION GdipRecordMetafileFileNameI LIB "gdiplus.dll" ALIAS "GdipRecordMetafileFileNameI" (BYVAL FilName AS STRING, BYVAL referenceHdc AS LONG, etype AS LONG, frameRect AS RECTL, BYVAL frameUnit AS LONG, BYVAL description AS STRING, metafile AS LONG) AS LONG
' TODO: Uncomment if you have the IStream object declared, or equivalent
'DECLARE FUNCTION GdipRecordMetafileFileStream LIB "gdiplus.dll" ALIAS "GdipRecordMetafileFileStream" (Byval stream as IStream, ByVal referenceHdc As Long, etype AS LONG, frameRect As RECTF, ByVal frameUnit As LONG, ByVal description As STRING, metafile AS LONG) AS LONG
'DECLARE FUNCTION GdipRecordMetafileFileStreamI LIB "gdiplus.dll" ALIAS "GdipRecordMetafileFileStreamI" (Byval stream as IStream, ByVal referenceHdc As Long, etype AS LONG, frameRect As RECTL, ByVal frameUnit As LONG, ByVal description As STRING, metafile AS LONG) AS LONG
DECLARE FUNCTION GdipSetMetafileDownLevelRasterizationLimit LIB "gdiplus.dll" ALIAS "GdipSetMetafileDownLevelRasterizationLimit" (BYVAL metafile AS LONG, BYVAL metafileRasterizationLimitDpi AS LONG) AS LONG
DECLARE FUNCTION GdipGetMetafileDownLevelRasterizationLimit LIB "gdiplus.dll" ALIAS "GdipGetMetafileDownLevelRasterizationLimit" (BYVAL metafile AS LONG, metafileRasterizationLimitDpi AS LONG) AS LONG
' NOTE: These encoders/decoders functions expect an ImageCodecInfo array
DECLARE FUNCTION GdipGetImageDecodersSize LIB "gdiplus.dll" ALIAS "GdipGetImageDecodersSize" (numDecoders AS LONG, SIZE AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageDecoders LIB "gdiplus.dll" ALIAS "GdipGetImageDecoders" (BYVAL numDecoders AS LONG, BYVAL SIZE AS LONG, decoders AS ANY) AS LONG
DECLARE FUNCTION GdipGetImageEncodersSize LIB "gdiplus.dll" ALIAS "GdipGetImageEncodersSize" (numEncoders AS LONG, SIZE AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageEncoders LIB "gdiplus.dll" ALIAS "GdipGetImageEncoders" (BYVAL numEncoders AS LONG, BYVAL SIZE AS LONG, encoders AS ANY) AS LONG
DECLARE FUNCTION GdipComment LIB "gdiplus.dll" ALIAS "GdipComment" (BYVAL graphics AS LONG, BYVAL sizeData AS LONG, nData AS ANY) AS LONG

' Image Functions (ALL)
DECLARE FUNCTION GdipLoadImageFromFile LIB "gdiplus.dll" ALIAS "GdipLoadImageFromFile" (BYVAL FilName AS STRING, nImage AS LONG) AS LONG
DECLARE FUNCTION GdipLoadImageFromFileICM LIB "gdiplus.dll" ALIAS "GdipLoadImageFromFileICM" (BYVAL FilName AS STRING, nImage AS LONG) AS LONG
' TODO: Uncomment if you have the IStream object declared, or equivalent
'DECLARE FUNCTION GdipLoadImageFromStream LIB "gdiplus.dll" ALIAS "GdipLoadImageFromStream" (Byval stream as IStream, nImage AS LONG) AS LONG
'DECLARE FUNCTION GdipLoadImageFromStreamICM LIB "gdiplus.dll" ALIAS "GdipLoadImageFromStreamICM" (Byval stream as IStream, nImage AS LONG) AS LONG
DECLARE FUNCTION GdipDisposeImage LIB "gdiplus.dll" ALIAS "GdipDisposeImage" (BYVAL nImage AS LONG) AS LONG
' NOTE: The encoderParams parameter expects a EncoderParameters struct or a NULL
DECLARE FUNCTION GdipSaveImageToFile LIB "gdiplus.dll" ALIAS "GdipSaveImageToFile" (BYVAL nImage AS LONG, BYVAL FilName AS STRING, clsidEncoder AS GUIDAPI, encoderParams AS ANY) AS LONG
' TODO: Uncomment if you have the IStream object declared, or equivalent
'DECLARE FUNCTION GdipSaveImageToStream LIB "gdiplus.dll" ALIAS "GdipSaveImageToStream" (ByVal nImage AS LONG, ByVal stream As IStream, clsidEncoder As GUIDAPI, encoderParams As Any) AS LONG
DECLARE FUNCTION GdipSaveAdd LIB "gdiplus.dll" ALIAS "GdipSaveAdd" (BYVAL nImage AS LONG, encoderParams AS EncoderParameters) AS LONG
DECLARE FUNCTION GdipSaveAddImage LIB "gdiplus.dll" ALIAS "GdipSaveAddImage" (BYVAL nImage AS LONG, BYVAL newnImage AS LONG, encoderParams AS EncoderParameters) AS LONG
DECLARE FUNCTION GdipGetImageGraphicsContext LIB "gdiplus.dll" ALIAS "GdipGetImageGraphicsContext" (BYVAL nImage AS LONG, graphics AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageBounds LIB "gdiplus.dll" ALIAS "GdipGetImageBounds" (BYVAL nImage AS LONG, srcRect AS RECTF, srcUnit AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageDimension LIB "gdiplus.dll" ALIAS "GdipGetImageDimension" (BYVAL nImage AS LONG, nWidth AS SINGLE, Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetImageType LIB "gdiplus.dll" ALIAS "GdipGetImageType" (BYVAL nImage AS LONG, itype AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageWidth LIB "gdiplus.dll" ALIAS "GdipGetImageWidth" (BYVAL nImage AS LONG, nWidth AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageHeight LIB "gdiplus.dll" ALIAS "GdipGetImageHeight" (BYVAL nImage AS LONG, Height AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageHorizontalResolution LIB "gdiplus.dll" ALIAS "GdipGetImageHorizontalResolution" (BYVAL nImage AS LONG, resolution AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetImageVerticalResolution LIB "gdiplus.dll" ALIAS "GdipGetImageVerticalResolution" (BYVAL nImage AS LONG, resolution AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetImageFlags LIB "gdiplus.dll" ALIAS "GdipGetImageFlags" (BYVAL nImage AS LONG, flags AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageRawFormat LIB "gdiplus.dll" ALIAS "GdipGetImageRawFormat" (BYVAL nImage AS LONG, format AS GUIDAPI) AS LONG
DECLARE FUNCTION GdipGetImagePixelFormat LIB "gdiplus.dll" ALIAS "GdipGetImagePixelFormat" (BYVAL nImage AS LONG, PixelFormat AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageThumbnail LIB "gdiplus.dll" ALIAS "GdipGetImageThumbnail" (BYVAL nImage AS LONG, BYVAL thumbWidth AS LONG, BYVAL thumbHeight AS LONG, thumbnImage AS LONG, OPTIONAL BYVAL pCALLBACK AS LONG, OPTIONAL BYVAL callbackData AS LONG) AS LONG
DECLARE FUNCTION GdipGetEncoderParameterListSize LIB "gdiplus.dll" ALIAS "GdipGetEncoderParameterListSize" (BYVAL nImage AS LONG, clsidEncoder AS GUIDAPI, SIZE AS LONG) AS LONG
DECLARE FUNCTION GdipGetEncoderParameterList LIB "gdiplus.dll" ALIAS "GdipGetEncoderParameterList" (BYVAL nImage AS LONG, clsidEncoder AS GUIDAPI, BYVAL SIZE AS LONG, buffer AS EncoderParameters) AS LONG
DECLARE FUNCTION GdipImageGetFrameDimensionsCount LIB "gdiplus.dll" ALIAS "GdipImageGetFrameDimensionsCount" (BYVAL nImage AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipImageGetFrameDimensionsList LIB "gdiplus.dll" ALIAS "GdipImageGetFrameDimensionsList" (BYVAL nImage AS LONG, dimensionIDs AS GUIDAPI, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipImageGetFrameCount LIB "gdiplus.dll" ALIAS "GdipImageGetFrameCount" (BYVAL nImage AS LONG, dimensionID AS GUIDAPI, Count AS LONG) AS LONG
DECLARE FUNCTION GdipImageSelectActiveFrame LIB "gdiplus.dll" ALIAS "GdipImageSelectActiveFrame" (BYVAL nImage AS LONG, dimensionID AS GUIDAPI, BYVAL frameIndex AS LONG) AS LONG
DECLARE FUNCTION GdipImageRotateFlip LIB "gdiplus.dll" ALIAS "GdipImageRotateFlip" (BYVAL nImage AS LONG, BYVAL rfType AS LONG) AS LONG
DECLARE FUNCTION GdipGetImagePalette LIB "gdiplus.dll" ALIAS "GdipGetImagePalette" (BYVAL nImage AS LONG, palette AS ColorPalette, BYVAL SIZE AS LONG) AS LONG
DECLARE FUNCTION GdipSetImagePalette LIB "gdiplus.dll" ALIAS "GdipSetImagePalette" (BYVAL nImage AS LONG, palette AS ColorPalette) AS LONG
DECLARE FUNCTION GdipGetImagePaletteSize LIB "gdiplus.dll" ALIAS "GdipGetImagePaletteSize" (BYVAL nImage AS LONG, SIZE AS LONG) AS LONG
DECLARE FUNCTION GdipGetPropertyCount LIB "gdiplus.dll" ALIAS "GdipGetPropertyCount" (BYVAL nImage AS LONG, numOfProperty AS LONG) AS LONG
DECLARE FUNCTION GdipGetPropertyIdList LIB "gdiplus.dll" ALIAS "GdipGetPropertyIdList" (BYVAL nImage AS LONG, BYVAL numOfProperty AS LONG, list AS LONG) AS LONG
DECLARE FUNCTION GdipGetPropertyItemSize LIB "gdiplus.dll" ALIAS "GdipGetPropertyItemSize" (BYVAL nImage AS LONG, BYVAL propId AS LONG, SIZE AS LONG) AS LONG
DECLARE FUNCTION GdipGetPropertyItem LIB "gdiplus.dll" ALIAS "GdipGetPropertyItem" (BYVAL nImage AS LONG, BYVAL propId AS LONG, BYVAL propSize AS LONG, buffer AS PropertyItem) AS LONG
DECLARE FUNCTION GdipGetPropertySize LIB "gdiplus.dll" ALIAS "GdipGetPropertySize" (BYVAL nImage AS LONG, totalBufferSize AS LONG, numProperties AS LONG) AS LONG
DECLARE FUNCTION GdipGetAllPropertyItems LIB "gdiplus.dll" ALIAS "GdipGetAllPropertyItems" (BYVAL nImage AS LONG, BYVAL totalBufferSize AS LONG, BYVAL numProperties AS LONG, allItems AS PropertyItem) AS LONG
DECLARE FUNCTION GdipRemovePropertyItem LIB "gdiplus.dll" ALIAS "GdipRemovePropertyItem" (BYVAL nImage AS LONG, BYVAL propId AS LONG) AS LONG
DECLARE FUNCTION GdipSetPropertyItem LIB "gdiplus.dll" ALIAS "GdipSetPropertyItem" (BYVAL nImage AS LONG, item AS PropertyItem) AS LONG
DECLARE FUNCTION GdipImageForceValidation LIB "gdiplus.dll" ALIAS "GdipImageForceValidation" (BYVAL nImage AS LONG) AS LONG

' Pen Functions (ALL)
DECLARE FUNCTION GdipCreatePen1 LIB "gdiplus.dll" ALIAS "GdipCreatePen1" (BYVAL Colr AS LONG, BYVAL nWidth AS SINGLE, BYVAL unit AS LONG, pen AS LONG) AS LONG
DECLARE FUNCTION GdipCreatePen2 LIB "gdiplus.dll" ALIAS "GdipCreatePen2" (BYVAL brush AS LONG, BYVAL nWidth AS SINGLE, BYVAL unit AS LONG, pen AS LONG) AS LONG
DECLARE FUNCTION GdipClonePen LIB "gdiplus.dll" ALIAS "GdipClonePen" (BYVAL pen AS LONG, clonepen AS LONG) AS LONG
DECLARE FUNCTION GdipDeletePen LIB "gdiplus.dll" ALIAS "GdipDeletePen" (BYVAL pen AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenWidth LIB "gdiplus.dll" ALIAS "GdipSetPenWidth" (BYVAL pen AS LONG, BYVAL nWidth AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetPenWidth LIB "gdiplus.dll" ALIAS "GdipGetPenWidth" (BYVAL pen AS LONG, nWidth AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetPenUnit LIB "gdiplus.dll" ALIAS "GdipSetPenUnit" (BYVAL pen AS LONG, BYVAL unit AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenUnit LIB "gdiplus.dll" ALIAS "GdipGetPenUnit" (BYVAL pen AS LONG, unit AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenLineCap LIB "gdiplus.dll" ALIAS "GdipSetPenLineCap197819" (BYVAL pen AS LONG, BYVAL startCap AS LONG, BYVAL endCap AS LONG, BYVAL dcap AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenStartCap LIB "gdiplus.dll" ALIAS "GdipSetPenStartCap" (BYVAL pen AS LONG, BYVAL startCap AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenEndCap LIB "gdiplus.dll" ALIAS "GdipSetPenEndCap" (BYVAL pen AS LONG, BYVAL endCap AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenDashCap LIB "gdiplus.dll" ALIAS "GdipSetPenDashCap197819" (BYVAL pen AS LONG, BYVAL dcap AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenStartCap LIB "gdiplus.dll" ALIAS "GdipGetPenStartCap" (BYVAL pen AS LONG, startCap AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenEndCap LIB "gdiplus.dll" ALIAS "GdipGetPenEndCap" (BYVAL pen AS LONG, endCap AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenDashCap LIB "gdiplus.dll" ALIAS "GdipGetPenDashCap197819" (BYVAL pen AS LONG, dcap AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenLineJoin LIB "gdiplus.dll" ALIAS "GdipSetPenLineJoin" (BYVAL pen AS LONG, BYVAL LnJoin AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenLineJoin LIB "gdiplus.dll" ALIAS "GdipGetPenLineJoin" (BYVAL pen AS LONG, LnJoin AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenCustomStartCap LIB "gdiplus.dll" ALIAS "GdipSetPenCustomStartCap" (BYVAL pen AS LONG, BYVAL customCap AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenCustomStartCap LIB "gdiplus.dll" ALIAS "GdipGetPenCustomStartCap" (BYVAL pen AS LONG, customCap AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenCustomEndCap LIB "gdiplus.dll" ALIAS "GdipSetPenCustomEndCap" (BYVAL pen AS LONG, BYVAL customCap AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenCustomEndCap LIB "gdiplus.dll" ALIAS "GdipGetPenCustomEndCap" (BYVAL pen AS LONG, customCap AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenMiterLimit LIB "gdiplus.dll" ALIAS "GdipSetPenMiterLimit" (BYVAL pen AS LONG, BYVAL miterLimit AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetPenMiterLimit LIB "gdiplus.dll" ALIAS "GdipGetPenMiterLimit" (BYVAL pen AS LONG, miterLimit AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetPenMode LIB "gdiplus.dll" ALIAS "GdipSetPenMode" (BYVAL pen AS LONG, BYVAL penMode AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenMode LIB "gdiplus.dll" ALIAS "GdipGetPenMode" (BYVAL pen AS LONG, penMode AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenTransform LIB "gdiplus.dll" ALIAS "GdipSetPenTransform" (BYVAL pen AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenTransform LIB "gdiplus.dll" ALIAS "GdipGetPenTransform" (BYVAL pen AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipResetPenTransform LIB "gdiplus.dll" ALIAS "GdipResetPenTransform" (BYVAL pen AS LONG) AS LONG
DECLARE FUNCTION GdipMultiplyPenTransform LIB "gdiplus.dll" ALIAS "GdipMultiplyPenTransform" (BYVAL pen AS LONG, BYVAL matrix AS LONG, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipTranslatePenTransform LIB "gdiplus.dll" ALIAS "GdipTranslatePenTransform" (BYVAL pen AS LONG, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipScalePenTransform LIB "gdiplus.dll" ALIAS "GdipScalePenTransform" (BYVAL pen AS LONG, BYVAL sx AS SINGLE, BYVAL sy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipRotatePenTransform LIB "gdiplus.dll" ALIAS "GdipRotatePenTransform" (BYVAL pen AS LONG, BYVAL angle AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenColor LIB "gdiplus.dll" ALIAS "GdipSetPenColor" (BYVAL pen AS LONG, BYVAL argb AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenColor LIB "gdiplus.dll" ALIAS "GdipGetPenColor" (BYVAL pen AS LONG, argb AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenBrushFill LIB "gdiplus.dll" ALIAS "GdipSetPenBrushFill" (BYVAL pen AS LONG, BYVAL brush AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenBrushFill LIB "gdiplus.dll" ALIAS "GdipGetPenBrushFill" (BYVAL pen AS LONG, brush AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenFillType LIB "gdiplus.dll" ALIAS "GdipGetPenFillType" (BYVAL pen AS LONG, ptype AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenDashStyle LIB "gdiplus.dll" ALIAS "GdipGetPenDashStyle" (BYVAL pen AS LONG, dStyle AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenDashStyle LIB "gdiplus.dll" ALIAS "GdipSetPenDashStyle" (BYVAL pen AS LONG, BYVAL dStyle AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenDashOffset LIB "gdiplus.dll" ALIAS "GdipGetPenDashOffset" (BYVAL pen AS LONG, offset AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetPenDashOffset LIB "gdiplus.dll" ALIAS "GdipSetPenDashOffset" (BYVAL pen AS LONG, BYVAL offset AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetPenDashCount LIB "gdiplus.dll" ALIAS "GdipGetPenDashCount" (BYVAL pen AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenDashArray LIB "gdiplus.dll" ALIAS "GdipSetPenDashArray" (BYVAL pen AS LONG, dash AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenDashArray LIB "gdiplus.dll" ALIAS "GdipGetPenDashArray" (BYVAL pen AS LONG, dash AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenCompoundCount LIB "gdiplus.dll" ALIAS "GdipGetPenCompoundCount" (BYVAL pen AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetPenCompoundArray LIB "gdiplus.dll" ALIAS "GdipSetPenCompoundArray" (BYVAL pen AS LONG, dash AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPenCompoundArray LIB "gdiplus.dll" ALIAS "GdipGetPenCompoundArray" (BYVAL pen AS LONG, dash AS SINGLE, BYVAL Count AS LONG) AS LONG

' CustomLineCap Functions (ALL)
DECLARE FUNCTION GdipCreateCustomLineCap LIB "gdiplus.dll" ALIAS "GdipCreateCustomLineCap" (BYVAL PathtoFill AS LONG, BYVAL PathStroke AS LONG, BYVAL baseCap AS LONG, BYVAL baseInset AS SINGLE, customCap AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteCustomLineCap LIB "gdiplus.dll" ALIAS "GdipDeleteCustomLineCap" (BYVAL customCap AS LONG) AS LONG
DECLARE FUNCTION GdipCloneCustomLineCap LIB "gdiplus.dll" ALIAS "GdipCloneCustomLineCap" (BYVAL customCap AS LONG, clonedCap AS LONG) AS LONG
DECLARE FUNCTION GdipGetCustomLineCapType LIB "gdiplus.dll" ALIAS "GdipGetCustomLineCapType" (BYVAL customCap AS LONG, capType AS LONG) AS LONG
DECLARE FUNCTION GdipSetCustomLineCapStrokeCaps LIB "gdiplus.dll" ALIAS "GdipSetCustomLineCapStrokeCaps" (BYVAL customCap AS LONG, BYVAL startCap AS LONG, BYVAL endCap AS LONG) AS LONG
DECLARE FUNCTION GdipGetCustomLineCapStrokeCaps LIB "gdiplus.dll" ALIAS "GdipGetCustomLineCapStrokeCaps" (BYVAL customCap AS LONG, startCap AS LONG, endCap AS LONG) AS LONG
DECLARE FUNCTION GdipSetCustomLineCapStrokeJoin LIB "gdiplus.dll" ALIAS "GdipSetCustomLineCapStrokeJoin" (BYVAL customCap AS LONG, BYVAL LnJoin AS LONG) AS LONG
DECLARE FUNCTION GdipGetCustomLineCapStrokeJoin LIB "gdiplus.dll" ALIAS "GdipGetCustomLineCapStrokeJoin" (BYVAL customCap AS LONG, LnJoin AS LONG) AS LONG
DECLARE FUNCTION GdipSetCustomLineCapBaseCap LIB "gdiplus.dll" ALIAS "GdipSetCustomLineCapBaseCap" (BYVAL customCap AS LONG, BYVAL baseCap AS LONG) AS LONG
DECLARE FUNCTION GdipGetCustomLineCapBaseCap LIB "gdiplus.dll" ALIAS "GdipGetCustomLineCapBaseCap" (BYVAL customCap AS LONG, baseCap AS LONG) AS LONG
DECLARE FUNCTION GdipSetCustomLineCapBaseInset LIB "gdiplus.dll" ALIAS "GdipSetCustomLineCapBaseInset" (BYVAL customCap AS LONG, BYVAL inset AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetCustomLineCapBaseInset LIB "gdiplus.dll" ALIAS "GdipGetCustomLineCapBaseInset" (BYVAL customCap AS LONG, inset AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetCustomLineCapWidthScale LIB "gdiplus.dll" ALIAS "GdipSetCustomLineCapWidthScale" (BYVAL customCap AS LONG, BYVAL widthScale AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetCustomLineCapWidthScale LIB "gdiplus.dll" ALIAS "GdipGetCustomLineCapWidthScale" (BYVAL customCap AS LONG, widthScale AS SINGLE) AS LONG

' AdjustableArrowCap Functions (ALL)
DECLARE FUNCTION GdipCreateAdjustableArrowCap LIB "gdiplus.dll" ALIAS "GdipCreateAdjustableArrowCap" (BYVAL Height AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL isFilled AS LONG, cap AS LONG) AS LONG
DECLARE FUNCTION GdipSetAdjustableArrowCapHeight LIB "gdiplus.dll" ALIAS "GdipSetAdjustableArrowCapHeight" (BYVAL cap AS LONG, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetAdjustableArrowCapHeight LIB "gdiplus.dll" ALIAS "GdipGetAdjustableArrowCapHeight" (BYVAL cap AS LONG, Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetAdjustableArrowCapWidth LIB "gdiplus.dll" ALIAS "GdipSetAdjustableArrowCapWidth" (BYVAL cap AS LONG, BYVAL nWidth AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetAdjustableArrowCapWidth LIB "gdiplus.dll" ALIAS "GdipGetAdjustableArrowCapWidth" (BYVAL cap AS LONG, nWidth AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetAdjustableArrowCapMiddleInset LIB "gdiplus.dll" ALIAS "GdipSetAdjustableArrowCapMiddleInset" (BYVAL cap AS LONG, BYVAL middleInset AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetAdjustableArrowCapMiddleInset LIB "gdiplus.dll" ALIAS "GdipGetAdjustableArrowCapMiddleInset" (BYVAL cap AS LONG, middleInset AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetAdjustableArrowCapFillState LIB "gdiplus.dll" ALIAS "GdipSetAdjustableArrowCapFillState" (BYVAL cap AS LONG, BYVAL bFillState AS LONG) AS LONG
DECLARE FUNCTION GdipGetAdjustableArrowCapFillState LIB "gdiplus.dll" ALIAS "GdipGetAdjustableArrowCapFillState" (BYVAL cap AS LONG, bFillState AS LONG) AS LONG

' Bitmap Functions (ALL)
DECLARE FUNCTION GdipCreateBitmapFromFile LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromFile" (BYVAL FilName AS LONG, nBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipCreateBitmapFromFileICM LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromFileICM" (BYVAL FilName AS LONG, nBitmap AS LONG) AS LONG
' TODO: Uncomment if you have the IStream object declared, or equivalent
'DECLARE FUNCTION GdipCreateBitmapFromStream LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromStream" (Byval stream as IStream, nBitmap As Long) AS LONG
'DECLARE FUNCTION GdipCreateBitmapFromStreamICM LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromStreamICM" (Byval stream as IStream, nBitmap As Long) AS LONG
' NOTE: The scan0 parameter is treated as a byte array
DECLARE FUNCTION GdipCreateBitmapFromScan0 LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromScan0" (BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL stride AS LONG, BYVAL PixelFormat AS LONG, scan0 AS ANY, nBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipCreateBitmapFromGraphics LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromGraphics" (BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL graphics AS LONG, nBitmap AS LONG) AS LONG
' TODO: Uncomment if DirectX is in your program
'DECLARE FUNCTION GdipCreateBitmapFromDirectDrawSurface LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromDirectDrawSurface" (surface As DirectDrawSurface7, nBitmap As Long) AS LONG
DECLARE FUNCTION GdipCreateBitmapFromGdiDib LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromGdiDib" (gdiBitmapInfo AS BITMAPINFO, BYVAL gdiBitmapData AS LONG, nBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipCreateBitmapFromHBITMAP LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromHBITMAP" (BYVAL hbm AS LONG, BYVAL hpal AS LONG, nBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipCreateHBITMAPFromBitmap LIB "gdiplus.dll" ALIAS "GdipCreateHBITMAPFromBitmap" (BYVAL nBitmap AS LONG, hbmReturn AS LONG, BYVAL background AS LONG) AS LONG
DECLARE FUNCTION GdipCreateBitmapFromHICON LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromHICON" (BYVAL hicon AS LONG, nBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipCreateHICONFromBitmap LIB "gdiplus.dll" ALIAS "GdipCreateHICONFromBitmap" (BYVAL nBitmap AS LONG, hbmReturn AS LONG) AS LONG
DECLARE FUNCTION GdipCreateBitmapFromResource LIB "gdiplus.dll" ALIAS "GdipCreateBitmapFromResource" (BYVAL hInstance AS LONG, BYVAL lpBitmapName AS STRING, nBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipCloneBitmapArea LIB "gdiplus.dll" ALIAS "GdipCloneBitmapArea" (BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL PixelFormat AS LONG, BYVAL srcBitmap AS LONG, dstBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipCloneBitmapAreaI LIB "gdiplus.dll" ALIAS "GdipCloneBitmapAreaI" (BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL PixelFormat AS LONG, BYVAL srcBitmap AS LONG, dstBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipBitmapLockBits LIB "gdiplus.dll" ALIAS "GdipBitmapLockBits" (BYVAL nBitmap AS LONG, nRect AS RECTL, BYVAL flags AS LONG, BYVAL PixelFormat AS LONG, lockedBitmapData AS BitmapData) AS LONG
DECLARE FUNCTION GdipBitmapUnlockBits LIB "gdiplus.dll" ALIAS "GdipBitmapUnlockBits" (BYVAL nBitmap AS LONG, lockedBitmapData AS BitmapData) AS LONG
DECLARE FUNCTION GdipBitmapGetPixel LIB "gdiplus.dll" ALIAS "GdipBitmapGetPixel" (BYVAL nBitmap AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, COLOR AS LONG) AS LONG
DECLARE FUNCTION GdipBitmapSetPixel LIB "gdiplus.dll" ALIAS "GdipBitmapSetPixel" (BYVAL nBitmap AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL COLOR AS LONG) AS LONG
DECLARE FUNCTION GdipBitmapSetResolution LIB "gdiplus.dll" ALIAS "GdipBitmapSetResolution" (BYVAL nBitmap AS LONG, BYVAL xdpi AS SINGLE, BYVAL ydpi AS SINGLE) AS LONG

' CachedBitmap Functions (ALL)
DECLARE FUNCTION GdipCreateCachedBitmap LIB "gdiplus.dll" ALIAS "GdipCreateCachedBitmap" (BYVAL nBitmap AS LONG, BYVAL graphics AS LONG, cachedBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteCachedBitmap LIB "gdiplus.dll" ALIAS "GdipDeleteCachedBitmap" (BYVAL cachedBitmap AS LONG) AS LONG
DECLARE FUNCTION GdipDrawCachedBitmap LIB "gdiplus.dll" ALIAS "GdipDrawCachedBitmap" (BYVAL graphics AS LONG, BYVAL cachedBitmap AS LONG, BYVAL x AS LONG, BYVAL y AS LONG) AS LONG

' Brush Functions (ALL)
DECLARE FUNCTION GdipCloneBrush LIB "gdiplus.dll" ALIAS "GdipCloneBrush" (BYVAL brush AS LONG, cloneBrush AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteBrush LIB "gdiplus.dll" ALIAS "GdipDeleteBrush" (BYVAL brush AS LONG) AS LONG
DECLARE FUNCTION GdipGetBrushType LIB "gdiplus.dll" ALIAS "GdipGetBrushType" (BYVAL brush AS LONG, brshType AS LONG) AS LONG

' HatchBrush Functions (ALL)
DECLARE FUNCTION GdipCreateHatchBrush LIB "gdiplus.dll" ALIAS "GdipCreateHatchBrush" (BYVAL style AS LONG, BYVAL forecolr AS LONG, BYVAL backcolr AS LONG, brush AS LONG) AS LONG
DECLARE FUNCTION GdipGetHatchStyle LIB "gdiplus.dll" ALIAS "GdipGetHatchStyle" (BYVAL brush AS LONG, style AS LONG) AS LONG
DECLARE FUNCTION GdipGetHatchForegroundColor LIB "gdiplus.dll" ALIAS "GdipGetHatchForegroundColor" (BYVAL brush AS LONG, forecolr AS LONG) AS LONG
DECLARE FUNCTION GdipGetHatchBackgroundColor LIB "gdiplus.dll" ALIAS "GdipGetHatchBackgroundColor" (BYVAL brush AS LONG, backcolr AS LONG) AS LONG

' SolidBrush Functions (ALL)
DECLARE FUNCTION GdipCreateSolidFill LIB "gdiplus.dll" ALIAS "GdipCreateSolidFill" (BYVAL argb AS LONG, brush AS LONG) AS LONG
DECLARE FUNCTION GdipSetSolidFillColor LIB "gdiplus.dll" ALIAS "GdipSetSolidFillColor" (BYVAL brush AS LONG, BYVAL argb AS LONG) AS LONG
DECLARE FUNCTION GdipGetSolidFillColor LIB "gdiplus.dll" ALIAS "GdipGetSolidFillColor" (BYVAL brush AS LONG, argb AS LONG) AS LONG

' LineBrush Functions (ALL)
DECLARE FUNCTION GdipCreateLineBrush LIB "gdiplus.dll" ALIAS "GdipCreateLineBrush" (point1 AS POINTF, point2 AS POINTF, BYVAL color1 AS LONG, BYVAL color2 AS LONG, BYVAL WrapMd AS LONG, lineGradient AS LONG) AS LONG
DECLARE FUNCTION GdipCreateLineBrushI LIB "gdiplus.dll" ALIAS "GdipCreateLineBrushI" (point1 AS POINTL, point2 AS POINTL, BYVAL color1 AS LONG, BYVAL color2 AS LONG, BYVAL WrapMd AS LONG, lineGradient AS LONG) AS LONG
DECLARE FUNCTION GdipCreateLineBrushFromRect LIB "gdiplus.dll" ALIAS "GdipCreateLineBrushFromRect" (nRect AS RECTF, BYVAL color1 AS LONG, BYVAL color2 AS LONG, BYVAL mode AS LONG, BYVAL WrapMd AS LONG, lineGradient AS LONG) AS LONG
DECLARE FUNCTION GdipCreateLineBrushFromRectI LIB "gdiplus.dll" ALIAS "GdipCreateLineBrushFromRectI" (nRect AS RECTL, BYVAL color1 AS LONG, BYVAL color2 AS LONG, BYVAL mode AS LONG, BYVAL WrapMd AS LONG, lineGradient AS LONG) AS LONG
DECLARE FUNCTION GdipCreateLineBrushFromRectWithAngle LIB "gdiplus.dll" ALIAS "GdipCreateLineBrushFromRectWithAngle" (nRect AS RECTF, BYVAL color1 AS LONG, BYVAL color2 AS LONG, BYVAL angle AS SINGLE, BYVAL isAngleScalable AS LONG, BYVAL WrapMd AS LONG, lineGradient AS LONG) AS LONG
DECLARE FUNCTION GdipCreateLineBrushFromRectWithAngleI LIB "gdiplus.dll" ALIAS "GdipCreateLineBrushFromRectWithAngleI" (nRect AS RECTL, BYVAL color1 AS LONG, BYVAL color2 AS LONG, BYVAL angle AS SINGLE, BYVAL isAngleScalable AS LONG, BYVAL WrapMd AS LONG, lineGradient AS LONG) AS LONG
DECLARE FUNCTION GdipSetLineColors LIB "gdiplus.dll" ALIAS "GdipSetLineColors" (BYVAL brush AS LONG, BYVAL color1 AS LONG, BYVAL color2 AS LONG) AS LONG
DECLARE FUNCTION GdipGetLineColors LIB "gdiplus.dll" ALIAS "GdipGetLineColors" (BYVAL brush AS LONG, lColors AS LONG) AS LONG
DECLARE FUNCTION GdipGetLineRect LIB "gdiplus.dll" ALIAS "GdipGetLineRect" (BYVAL brush AS LONG, nRect AS RECTF) AS LONG
DECLARE FUNCTION GdipGetLineRectI LIB "gdiplus.dll" ALIAS "GdipGetLineRectI" (BYVAL brush AS LONG, nRect AS RECTL) AS LONG
DECLARE FUNCTION GdipSetLineGammaCorrection LIB "gdiplus.dll" ALIAS "GdipSetLineGammaCorrection" (BYVAL brush AS LONG, BYVAL useGammaCorrection AS LONG) AS LONG
DECLARE FUNCTION GdipGetLineGammaCorrection LIB "gdiplus.dll" ALIAS "GdipGetLineGammaCorrection" (BYVAL brush AS LONG, useGammaCorrection AS LONG) AS LONG
DECLARE FUNCTION GdipGetLineBlendCount LIB "gdiplus.dll" ALIAS "GdipGetLineBlendCount" (BYVAL brush AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetLineBlend LIB "gdiplus.dll" ALIAS "GdipGetLineBlend" (BYVAL brush AS LONG, blend AS SINGLE, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetLineBlend LIB "gdiplus.dll" ALIAS "GdipSetLineBlend" (BYVAL brush AS LONG, blend AS SINGLE, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetLinePresetBlendCount LIB "gdiplus.dll" ALIAS "GdipGetLinePresetBlendCount" (BYVAL brush AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetLinePresetBlend LIB "gdiplus.dll" ALIAS "GdipGetLinePresetBlend" (BYVAL brush AS LONG, blend AS LONG, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetLinePresetBlend LIB "gdiplus.dll" ALIAS "GdipSetLinePresetBlend" (BYVAL brush AS LONG, blend AS LONG, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetLineSigmaBlend LIB "gdiplus.dll" ALIAS "GdipSetLineSigmaBlend" (BYVAL brush AS LONG, BYVAL FOCUS AS SINGLE, BYVAL theScale AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetLineLinearBlend LIB "gdiplus.dll" ALIAS "GdipSetLineLinearBlend" (BYVAL brush AS LONG, BYVAL FOCUS AS SINGLE, BYVAL theScale AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetLineWrapMode LIB "gdiplus.dll" ALIAS "GdipSetLineWrapMode" (BYVAL brush AS LONG, BYVAL WrapMd AS LONG) AS LONG
DECLARE FUNCTION GdipGetLineWrapMode LIB "gdiplus.dll" ALIAS "GdipGetLineWrapMode" (BYVAL brush AS LONG, WrapMd AS LONG) AS LONG
DECLARE FUNCTION GdipGetLineTransform LIB "gdiplus.dll" ALIAS "GdipGetLineTransform" (BYVAL brush AS LONG, matrix AS LONG) AS LONG
DECLARE FUNCTION GdipSetLineTransform LIB "gdiplus.dll" ALIAS "GdipSetLineTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipResetLineTransform LIB "gdiplus.dll" ALIAS "GdipResetLineTransform" (BYVAL brush AS LONG) AS LONG
DECLARE FUNCTION GdipMultiplyLineTransform LIB "gdiplus.dll" ALIAS "GdipMultiplyLineTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipTranslateLineTransform LIB "gdiplus.dll" ALIAS "GdipTranslateLineTransform" (BYVAL brush AS LONG, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipScaleLineTransform LIB "gdiplus.dll" ALIAS "GdipScaleLineTransform" (BYVAL brush AS LONG, BYVAL sx AS SINGLE, BYVAL sy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipRotateLineTransform LIB "gdiplus.dll" ALIAS "GdipRotateLineTransform" (BYVAL brush AS LONG, BYVAL angle AS SINGLE, BYVAL order AS LONG) AS LONG

' TextureBrush Functions (ALL)
DECLARE FUNCTION GdipCreateTexture LIB "gdiplus.dll" ALIAS "GdipCreateTexture" (BYVAL nImage AS LONG, BYVAL WrapMd AS LONG, texture AS LONG) AS LONG
DECLARE FUNCTION GdipCreateTexture2 LIB "gdiplus.dll" ALIAS "GdipCreateTexture2" (BYVAL nImage AS LONG, BYVAL WrapMd AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, texture AS LONG) AS LONG
DECLARE FUNCTION GdipCreateTextureIA LIB "gdiplus.dll" ALIAS "GdipCreateTextureIA" (BYVAL nImage AS LONG, BYVAL imageAttributes AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, texture AS LONG) AS LONG
DECLARE FUNCTION GdipCreateTexture2I LIB "gdiplus.dll" ALIAS "GdipCreateTexture2I" (BYVAL nImage AS LONG, BYVAL WrapMd AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, texture AS LONG) AS LONG
DECLARE FUNCTION GdipCreateTextureIAI LIB "gdiplus.dll" ALIAS "GdipCreateTextureIAI" (BYVAL nImage AS LONG, BYVAL imageAttributes AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, texture AS LONG) AS LONG
DECLARE FUNCTION GdipGetTextureTransform LIB "gdiplus.dll" ALIAS "GdipGetTextureTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipSetTextureTransform LIB "gdiplus.dll" ALIAS "GdipSetTextureTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipResetTextureTransform LIB "gdiplus.dll" ALIAS "GdipResetTextureTransform" (BYVAL brush AS LONG) AS LONG
DECLARE FUNCTION GdipTranslateTextureTransform LIB "gdiplus.dll" ALIAS "GdipTranslateTextureTransform" (BYVAL brush AS LONG, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipMultiplyTextureTransform LIB "gdiplus.dll" ALIAS "GdipMultiplyTextureTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipScaleTextureTransform LIB "gdiplus.dll" ALIAS "GdipScaleTextureTransform" (BYVAL brush AS LONG, BYVAL sx AS SINGLE, BYVAL sy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipRotateTextureTransform LIB "gdiplus.dll" ALIAS "GdipRotateTextureTransform" (BYVAL brush AS LONG, BYVAL angle AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipSetTextureWrapMode LIB "gdiplus.dll" ALIAS "GdipSetTextureWrapMode" (BYVAL brush AS LONG, BYVAL WrapMd AS LONG) AS LONG
DECLARE FUNCTION GdipGetTextureWrapMode LIB "gdiplus.dll" ALIAS "GdipGetTextureWrapMode" (BYVAL brush AS LONG, WrapMd AS LONG) AS LONG
DECLARE FUNCTION GdipGetTextureImage LIB "gdiplus.dll" ALIAS "GdipGetTextureImage" (BYVAL brush AS LONG, nImage AS LONG) AS LONG

' PathGradientBrush Functions (ALL)
DECLARE FUNCTION GdipCreatePathGradient LIB "gdiplus.dll" ALIAS "GdipCreatePathGradient" (pPoint AS POINTF, BYVAL Count AS LONG, BYVAL WrapMd AS LONG, polyGradient AS LONG) AS LONG
DECLARE FUNCTION GdipCreatePathGradientI LIB "gdiplus.dll" ALIAS "GdipCreatePathGradientI" (pPoint AS POINTL, BYVAL Count AS LONG, BYVAL WrapMd AS LONG, polyGradient AS LONG) AS LONG
DECLARE FUNCTION GdipCreatePathGradientFromPath LIB "gdiplus.dll" ALIAS "GdipCreatePathGradientFromPath" (BYVAL path AS LONG, polyGradient AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientCenterColor LIB "gdiplus.dll" ALIAS "GdipGetPathGradientCenterColor" (BYVAL brush AS LONG, lColors AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientCenterColor LIB "gdiplus.dll" ALIAS "GdipSetPathGradientCenterColor" (BYVAL brush AS LONG, BYVAL lColors AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientSurroundColorsWithCount LIB "gdiplus.dll" ALIAS "GdipGetPathGradientSurroundColorsWithCount" (BYVAL brush AS LONG, argb AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientSurroundColorsWithCount LIB "gdiplus.dll" ALIAS "GdipSetPathGradientSurroundColorsWithCount" (BYVAL brush AS LONG, argb AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientPath LIB "gdiplus.dll" ALIAS "GdipGetPathGradientPath" (BYVAL brush AS LONG, BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientPath LIB "gdiplus.dll" ALIAS "GdipSetPathGradientPath" (BYVAL brush AS LONG, BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientCenterPoint LIB "gdiplus.dll" ALIAS "GdipGetPathGradientCenterPoint" (BYVAL brush AS LONG, pPoint AS POINTF) AS LONG
DECLARE FUNCTION GdipGetPathGradientCenterPointI LIB "gdiplus.dll" ALIAS "GdipGetPathGradientCenterPointI" (BYVAL brush AS LONG, pPoint AS POINTL) AS LONG
DECLARE FUNCTION GdipSetPathGradientCenterPoint LIB "gdiplus.dll" ALIAS "GdipSetPathGradientCenterPoint" (BYVAL brush AS LONG, pPoint AS POINTF) AS LONG
DECLARE FUNCTION GdipSetPathGradientCenterPointI LIB "gdiplus.dll" ALIAS "GdipSetPathGradientCenterPointI" (BYVAL brush AS LONG, pPoint AS POINTL) AS LONG
DECLARE FUNCTION GdipGetPathGradientRect LIB "gdiplus.dll" ALIAS "GdipGetPathGradientRect" (BYVAL brush AS LONG, nRect AS RECTF) AS LONG
DECLARE FUNCTION GdipGetPathGradientRectI LIB "gdiplus.dll" ALIAS "GdipGetPathGradientRectI" (BYVAL brush AS LONG, nRect AS RECTL) AS LONG
DECLARE FUNCTION GdipGetPathGradientPointCount LIB "gdiplus.dll" ALIAS "GdipGetPathGradientPointCount" (BYVAL brush AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientSurroundColorCount LIB "gdiplus.dll" ALIAS "GdipGetPathGradientSurroundColorCount" (BYVAL brush AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientGammaCorrection LIB "gdiplus.dll" ALIAS "GdipSetPathGradientGammaCorrection" (BYVAL brush AS LONG, BYVAL useGammaCorrection AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientGammaCorrection LIB "gdiplus.dll" ALIAS "GdipGetPathGradientGammaCorrection" (BYVAL brush AS LONG, useGammaCorrection AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientBlendCount LIB "gdiplus.dll" ALIAS "GdipGetPathGradientBlendCount" (BYVAL brush AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientBlend LIB "gdiplus.dll" ALIAS "GdipGetPathGradientBlend" (BYVAL brush AS LONG, blend AS SINGLE, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientBlend LIB "gdiplus.dll" ALIAS "GdipSetPathGradientBlend" (BYVAL brush AS LONG, blend AS SINGLE, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientPresetBlendCount LIB "gdiplus.dll" ALIAS "GdipGetPathGradientPresetBlendCount" (BYVAL brush AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientPresetBlend LIB "gdiplus.dll" ALIAS "GdipGetPathGradientPresetBlend" (BYVAL brush AS LONG, blend AS LONG, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientPresetBlend LIB "gdiplus.dll" ALIAS "GdipSetPathGradientPresetBlend" (BYVAL brush AS LONG, blend AS LONG, positions AS SINGLE, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientSigmaBlend LIB "gdiplus.dll" ALIAS "GdipSetPathGradientSigmaBlend" (BYVAL brush AS LONG, BYVAL FOCUS AS SINGLE, BYVAL sscale AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetPathGradientLinearBlend LIB "gdiplus.dll" ALIAS "GdipSetPathGradientLinearBlend" (BYVAL brush AS LONG, BYVAL FOCUS AS SINGLE, BYVAL sscale AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetPathGradientWrapMode LIB "gdiplus.dll" ALIAS "GdipGetPathGradientWrapMode" (BYVAL brush AS LONG, WrapMd AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientWrapMode LIB "gdiplus.dll" ALIAS "GdipSetPathGradientWrapMode" (BYVAL brush AS LONG, BYVAL WrapMd AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientTransform LIB "gdiplus.dll" ALIAS "GdipGetPathGradientTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathGradientTransform LIB "gdiplus.dll" ALIAS "GdipSetPathGradientTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipResetPathGradientTransform LIB "gdiplus.dll" ALIAS "GdipResetPathGradientTransform" (BYVAL brush AS LONG) AS LONG
DECLARE FUNCTION GdipMultiplyPathGradientTransform LIB "gdiplus.dll" ALIAS "GdipMultiplyPathGradientTransform" (BYVAL brush AS LONG, BYVAL matrix AS LONG, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipTranslatePathGradientTransform LIB "gdiplus.dll" ALIAS "GdipTranslatePathGradientTransform" (BYVAL brush AS LONG, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipScalePathGradientTransform LIB "gdiplus.dll" ALIAS "GdipScalePathGradientTransform" (BYVAL brush AS LONG, BYVAL sx AS SINGLE, BYVAL sy AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipRotatePathGradientTransform LIB "gdiplus.dll" ALIAS "GdipRotatePathGradientTransform" (BYVAL brush AS LONG, BYVAL angle AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathGradientFocusScales LIB "gdiplus.dll" ALIAS "GdipGetPathGradientFocusScales" (BYVAL brush AS LONG, xScale AS SINGLE, yScale AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetPathGradientFocusScales LIB "gdiplus.dll" ALIAS "GdipSetPathGradientFocusScales" (BYVAL brush AS LONG, BYVAL xScale AS SINGLE, BYVAL yScale AS SINGLE) AS LONG

' GraphicsPath Functions (ALL)
DECLARE FUNCTION GdipCreatePath LIB "gdiplus.dll" ALIAS "GdipCreatePath" (BYVAL brushmode AS LONG, path AS LONG) AS LONG
' NOTE: The types parameter is treated as a byte array
DECLARE FUNCTION GdipCreatePath2 LIB "gdiplus.dll" ALIAS "GdipCreatePath2" (pPoint AS POINTF, types AS ANY, BYVAL Count AS LONG, brushmode AS LONG, path AS LONG) AS LONG
DECLARE FUNCTION GdipCreatePath2I LIB "gdiplus.dll" ALIAS "GdipCreatePath2I" (pPoint AS POINTL, types AS ANY, BYVAL Count AS LONG, brushmode AS LONG, path AS LONG) AS LONG
DECLARE FUNCTION GdipClonePath LIB "gdiplus.dll" ALIAS "GdipClonePath" (BYVAL path AS LONG, clonePath AS LONG) AS LONG
DECLARE FUNCTION GdipDeletePath LIB "gdiplus.dll" ALIAS "GdipDeletePath" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipResetPath LIB "gdiplus.dll" ALIAS "GdipResetPath" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipGetPointCount LIB "gdiplus.dll" ALIAS "GdipGetPointCount" (BYVAL path AS LONG, Count AS LONG) AS LONG
' NOTE: The types parameter is treated as a byte array
DECLARE FUNCTION GdipGetPathTypes LIB "gdiplus.dll" ALIAS "GdipGetPathTypes" (BYVAL path AS LONG, types AS ANY, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathPoints LIB "gdiplus.dll" ALIAS "GdipGetPathPoints" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathPointsI LIB "gdiplus.dll" ALIAS "GdipGetPathPointsI" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathFillMode LIB "gdiplus.dll" ALIAS "GdipGetPathFillMode" (BYVAL path AS LONG, BYVAL brushmode AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathFillMode LIB "gdiplus.dll" ALIAS "GdipSetPathFillMode" (BYVAL path AS LONG, BYVAL brushmode AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathData LIB "gdiplus.dll" ALIAS "GdipGetPathData" (BYVAL path AS LONG, pdata AS PathData) AS LONG
DECLARE FUNCTION GdipStartPathFigure LIB "gdiplus.dll" ALIAS "GdipStartPathFigure" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipClosePathFigure LIB "gdiplus.dll" ALIAS "GdipClosePathFigure" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipClosePathFigures LIB "gdiplus.dll" ALIAS "GdipClosePathFigures" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipSetPathMarker LIB "gdiplus.dll" ALIAS "GdipSetPathMarker" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipClearPathMarkers LIB "gdiplus.dll" ALIAS "GdipClearPathMarkers" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipReversePath LIB "gdiplus.dll" ALIAS "GdipReversePath" (BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathLastPoint LIB "gdiplus.dll" ALIAS "GdipGetPathLastPoint" (BYVAL path AS LONG, lastPoint AS POINTF) AS LONG
DECLARE FUNCTION GdipAddPathLine LIB "gdiplus.dll" ALIAS "GdipAddPathLine" (BYVAL path AS LONG, BYVAL x1 AS SINGLE, BYVAL y1 AS SINGLE, BYVAL x2 AS SINGLE, BYVAL y2 AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathLine2 LIB "gdiplus.dll" ALIAS "GdipAddPathLine2" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathArc LIB "gdiplus.dll" ALIAS "GdipAddPathArc" (BYVAL path AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathBezier LIB "gdiplus.dll" ALIAS "GdipAddPathBezier" (BYVAL path AS LONG, BYVAL x1 AS SINGLE, BYVAL y1 AS SINGLE, BYVAL x2 AS SINGLE, BYVAL y2 AS SINGLE, BYVAL x3 AS SINGLE, BYVAL y3 AS SINGLE, BYVAL x4 AS SINGLE, BYVAL y4 AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathBeziers LIB "gdiplus.dll" ALIAS "GdipAddPathBeziers" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathCurve LIB "gdiplus.dll" ALIAS "GdipAddPathCurve" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathCurve2 LIB "gdiplus.dll" ALIAS "GdipAddPathCurve2" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathCurve3 LIB "gdiplus.dll" ALIAS "GdipAddPathCurve3" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL offset AS LONG, BYVAL numberOfSegments AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathClosedCurve LIB "gdiplus.dll" ALIAS "GdipAddPathClosedCurve" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathClosedCurve2 LIB "gdiplus.dll" ALIAS "GdipAddPathClosedCurve2" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathRectangle LIB "gdiplus.dll" ALIAS "GdipAddPathRectangle" (BYVAL path AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathRectangles LIB "gdiplus.dll" ALIAS "GdipAddPathRectangles" (BYVAL path AS LONG, nRect AS RECTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathEllipse LIB "gdiplus.dll" ALIAS "GdipAddPathEllipse" (BYVAL path AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathPie LIB "gdiplus.dll" ALIAS "GdipAddPathPie" (BYVAL path AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathPolygon LIB "gdiplus.dll" ALIAS "GdipAddPathPolygon" (BYVAL path AS LONG, pPoint AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathPath LIB "gdiplus.dll" ALIAS "GdipAddPathPath" (BYVAL path AS LONG, BYVAL addingPath AS LONG, BYVAL bConnect AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathString LIB "gdiplus.dll" ALIAS "GdipAddPathString" (BYVAL path AS LONG, BYVAL str AS STRING, BYVAL length AS LONG, BYVAL family AS LONG, BYVAL style AS LONG, BYVAL emSize AS SINGLE, layoutRect AS RECTF, BYVAL StringFormat AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathStringI LIB "gdiplus.dll" ALIAS "GdipAddPathStringI" (BYVAL path AS LONG, BYVAL str AS STRING, BYVAL length AS LONG, BYVAL family AS LONG, BYVAL style AS LONG, BYVAL emSize AS SINGLE, layoutRect AS RECTL, BYVAL StringFormat AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathLineI LIB "gdiplus.dll" ALIAS "GdipAddPathLineI" (BYVAL path AS LONG, BYVAL x1 AS LONG, BYVAL y1 AS LONG, BYVAL x2 AS LONG, BYVAL y2 AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathLine2I LIB "gdiplus.dll" ALIAS "GdipAddPathLine2I" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathArcI LIB "gdiplus.dll" ALIAS "GdipAddPathArcI" (BYVAL path AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathBezierI LIB "gdiplus.dll" ALIAS "GdipAddPathBezierI" (BYVAL path AS LONG, BYVAL x1 AS LONG, BYVAL y1 AS LONG, BYVAL x2 AS LONG, BYVAL y2 AS LONG, BYVAL x3 AS LONG, BYVAL y3 AS LONG, BYVAL x4 AS LONG, BYVAL y4 AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathBeziersI LIB "gdiplus.dll" ALIAS "GdipAddPathBeziersI" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathCurveI LIB "gdiplus.dll" ALIAS "GdipAddPathCurveI" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathCurve2I LIB "gdiplus.dll" ALIAS "GdipAddPathCurve2I" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL tension AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathCurve3I LIB "gdiplus.dll" ALIAS "GdipAddPathCurve3I" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL offset AS LONG, BYVAL numberOfSegments AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathClosedCurveI LIB "gdiplus.dll" ALIAS "GdipAddPathClosedCurveI" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathClosedCurve2I LIB "gdiplus.dll" ALIAS "GdipAddPathClosedCurve2I" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG, BYVAL tension AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathRectangleI LIB "gdiplus.dll" ALIAS "GdipAddPathRectangleI" (BYVAL path AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathRectanglesI LIB "gdiplus.dll" ALIAS "GdipAddPathRectanglesI" (BYVAL path AS LONG, rects AS RECTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathEllipseI LIB "gdiplus.dll" ALIAS "GdipAddPathEllipseI" (BYVAL path AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG) AS LONG
DECLARE FUNCTION GdipAddPathPieI LIB "gdiplus.dll" ALIAS "GdipAddPathPieI" (BYVAL path AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL startAngle AS SINGLE, BYVAL sweepAngle AS SINGLE) AS LONG
DECLARE FUNCTION GdipAddPathPolygonI LIB "gdiplus.dll" ALIAS "GdipAddPathPolygonI" (BYVAL path AS LONG, pPoint AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipFlattenPath LIB "gdiplus.dll" ALIAS "GdipFlattenPath" (BYVAL path AS LONG, BYVAL matrix AS LONG, BYVAL flatness AS SINGLE) AS LONG
DECLARE FUNCTION GdipWindingModeOutline LIB "gdiplus.dll" ALIAS "GdipWindingModeOutline" (BYVAL path AS LONG, BYVAL matrix AS LONG, BYVAL flatness AS SINGLE) AS LONG
DECLARE FUNCTION GdipWidenPath LIB "gdiplus.dll" ALIAS "GdipWidenPath" (BYVAL nativePath AS LONG, BYVAL pen AS LONG, BYVAL matrix AS LONG, BYVAL flatness AS SINGLE) AS LONG
DECLARE FUNCTION GdipWarpPath LIB "gdiplus.dll" ALIAS "GdipWarpPath" (BYVAL path AS LONG, BYVAL matrix AS LONG, pPoint AS POINTF, BYVAL Count AS LONG, BYVAL srcx AS SINGLE, BYVAL srcy AS SINGLE, BYVAL srcwidth AS SINGLE, BYVAL srcheight AS SINGLE, BYVAL WarpMd AS LONG, BYVAL flatness AS SINGLE) AS LONG
DECLARE FUNCTION GdipTransformPath LIB "gdiplus.dll" ALIAS "GdipTransformPath" (BYVAL path AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathWorldBounds LIB "gdiplus.dll" ALIAS "GdipGetPathWorldBounds" (BYVAL path AS LONG, bounds AS RECTF, BYVAL matrix AS LONG, BYVAL pen AS LONG) AS LONG
DECLARE FUNCTION GdipGetPathWorldBoundsI LIB "gdiplus.dll" ALIAS "GdipGetPathWorldBoundsI" (BYVAL path AS LONG, bounds AS RECTL, BYVAL matrix AS LONG, BYVAL pen AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisiblePathPoint LIB "gdiplus.dll" ALIAS "GdipIsVisiblePathPoint" (BYVAL path AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisiblePathPointI LIB "gdiplus.dll" ALIAS "GdipIsVisiblePathPointI" (BYVAL path AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsOutlineVisiblePathPoint LIB "gdiplus.dll" ALIAS "GdipIsOutlineVisiblePathPoint" (BYVAL path AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL pen AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsOutlineVisiblePathPointI LIB "gdiplus.dll" ALIAS "GdipIsOutlineVisiblePathPointI" (BYVAL path AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL pen AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG

' PathIterator Functions (ALL)
DECLARE FUNCTION GdipCreatePathIter LIB "gdiplus.dll" ALIAS "GdipCreatePathIter" (iterator AS LONG, BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipDeletePathIter LIB "gdiplus.dll" ALIAS "GdipDeletePathIter" (BYVAL iterator AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterNextSubpath LIB "gdiplus.dll" ALIAS "GdipPathIterNextSubpath" (BYVAL iterator AS LONG, resultCount AS LONG, startIndex AS LONG, endIndex AS LONG, isClosed AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterNextSubpathPath LIB "gdiplus.dll" ALIAS "GdipPathIterNextSubpathPath" (BYVAL iterator AS LONG, resultCount AS LONG, BYVAL path AS LONG, isClosed AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterNextPathType LIB "gdiplus.dll" ALIAS "GdipPathIterNextPathType" (BYVAL iterator AS LONG, resultCount AS LONG, pathType AS ANY, startIndex AS LONG, endIndex AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterNextMarker LIB "gdiplus.dll" ALIAS "GdipPathIterNextMarker" (BYVAL iterator AS LONG, resultCount AS LONG, startIndex AS LONG, endIndex AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterNextMarkerPath LIB "gdiplus.dll" ALIAS "GdipPathIterNextMarkerPath" (BYVAL iterator AS LONG, resultCount AS LONG, BYVAL path AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterGetCount LIB "gdiplus.dll" ALIAS "GdipPathIterGetCount" (BYVAL iterator AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterGetSubpathCount LIB "gdiplus.dll" ALIAS "GdipPathIterGetSubpathCount" (BYVAL iterator AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterIsValid LIB "gdiplus.dll" ALIAS "GdipPathIterIsValid" (BYVAL iterator AS LONG, valid AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterHasCurve LIB "gdiplus.dll" ALIAS "GdipPathIterHasCurve" (BYVAL iterator AS LONG, hasCurve AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterRewind LIB "gdiplus.dll" ALIAS "GdipPathIterRewind" (BYVAL iterator AS LONG) AS LONG
' NOTE: The types parameter is treated as a byte array
DECLARE FUNCTION GdipPathIterEnumerate LIB "gdiplus.dll" ALIAS "GdipPathIterEnumerate" (BYVAL iterator AS LONG, resultCount AS LONG, pPoint AS POINTF, types AS ANY, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipPathIterCopyData LIB "gdiplus.dll" ALIAS "GdipPathIterCopyData" (BYVAL iterator AS LONG, resultCount AS LONG, pPoint AS POINTF, types AS ANY, BYVAL startIndex AS LONG, BYVAL endIndex AS LONG) AS LONG

' Matrix Functions (ALL)
DECLARE FUNCTION GdipCreateMatrix LIB "gdiplus.dll" ALIAS "GdipCreateMatrix" (matrix AS LONG) AS LONG
DECLARE FUNCTION GdipCreateMatrix2 LIB "gdiplus.dll" ALIAS "GdipCreateMatrix2" (BYVAL m11 AS SINGLE, BYVAL m12 AS SINGLE, BYVAL m21 AS SINGLE, BYVAL m22 AS SINGLE, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE, matrix AS LONG) AS LONG
DECLARE FUNCTION GdipCreateMatrix3 LIB "gdiplus.dll" ALIAS "GdipCreateMatrix3" (nRect AS RECTF, dstplg AS POINTF, matrix AS LONG) AS LONG
DECLARE FUNCTION GdipCreateMatrix3I LIB "gdiplus.dll" ALIAS "GdipCreateMatrix3I" (nRect AS RECTL, dstplg AS POINTL, matrix AS LONG) AS LONG
DECLARE FUNCTION GdipCloneMatrix LIB "gdiplus.dll" ALIAS "GdipCloneMatrix" (BYVAL matrix AS LONG, cloneMatrix AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteMatrix LIB "gdiplus.dll" ALIAS "GdipDeleteMatrix" (BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipSetMatrixElements LIB "gdiplus.dll" ALIAS "GdipSetMatrixElements" (BYVAL matrix AS LONG, BYVAL m11 AS SINGLE, BYVAL m12 AS SINGLE, BYVAL m21 AS SINGLE, BYVAL m22 AS SINGLE, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE) AS LONG
DECLARE FUNCTION GdipMultiplyMatrix LIB "gdiplus.dll" ALIAS "GdipMultiplyMatrix" (BYVAL matrix AS LONG, BYVAL matrix2 AS LONG, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipTranslateMatrix LIB "gdiplus.dll" ALIAS "GdipTranslateMatrix" (BYVAL matrix AS LONG, BYVAL offsetX AS SINGLE, BYVAL offsetY AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipScaleMatrix LIB "gdiplus.dll" ALIAS "GdipScaleMatrix" (BYVAL matrix AS LONG, BYVAL scaleX AS SINGLE, BYVAL scaleY AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipRotateMatrix LIB "gdiplus.dll" ALIAS "GdipRotateMatrix" (BYVAL matrix AS LONG, BYVAL angle AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipShearMatrix LIB "gdiplus.dll" ALIAS "GdipShearMatrix" (BYVAL matrix AS LONG, BYVAL shearX AS SINGLE, BYVAL shearY AS SINGLE, BYVAL order AS LONG) AS LONG
DECLARE FUNCTION GdipInvertMatrix LIB "gdiplus.dll" ALIAS "GdipInvertMatrix" (BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipTransformMatrixPoints LIB "gdiplus.dll" ALIAS "GdipTransformMatrixPoints" (BYVAL matrix AS LONG, pts AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipTransformMatrixPointsI LIB "gdiplus.dll" ALIAS "GdipTransformMatrixPointsI" (BYVAL matrix AS LONG, pts AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipVectorTransformMatrixPoints LIB "gdiplus.dll" ALIAS "GdipVectorTransformMatrixPoints" (BYVAL matrix AS LONG, pts AS POINTF, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipVectorTransformMatrixPointsI LIB "gdiplus.dll" ALIAS "GdipVectorTransformMatrixPointsI" (BYVAL matrix AS LONG, pts AS POINTL, BYVAL Count AS LONG) AS LONG
DECLARE FUNCTION GdipGetMatrixElements LIB "gdiplus.dll" ALIAS "GdipGetMatrixElements" (BYVAL matrix AS LONG, matrixOut AS SINGLE) AS LONG
DECLARE FUNCTION GdipIsMatrixInvertible LIB "gdiplus.dll" ALIAS "GdipIsMatrixInvertible" (BYVAL matrix AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsMatrixIdentity LIB "gdiplus.dll" ALIAS "GdipIsMatrixIdentity" (BYVAL matrix AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsMatrixEqual LIB "gdiplus.dll" ALIAS "GdipIsMatrixEqual" (BYVAL matrix AS LONG, BYVAL matrix2 AS LONG, result AS LONG) AS LONG

' Region Functions (ALL)
DECLARE FUNCTION GdipCreateRegion LIB "gdiplus.dll" ALIAS "GdipCreateRegion" (region AS LONG) AS LONG
DECLARE FUNCTION GdipCreateRegionRect LIB "gdiplus.dll" ALIAS "GdipCreateRegionRect" (nRect AS RECTF, region AS LONG) AS LONG
DECLARE FUNCTION GdipCreateRegionRectI LIB "gdiplus.dll" ALIAS "GdipCreateRegionRectI" (nRect AS RECTL, region AS LONG) AS LONG
DECLARE FUNCTION GdipCreateRegionPath LIB "gdiplus.dll" ALIAS "GdipCreateRegionPath" (BYVAL path AS LONG, region AS LONG) AS LONG
' NOTE: The regionData parameter is treated as a byte array
DECLARE FUNCTION GdipCreateRegionRgnData LIB "gdiplus.dll" ALIAS "GdipCreateRegionRgnData" (regionData AS ANY, BYVAL SIZE AS LONG, region AS LONG) AS LONG
DECLARE FUNCTION GdipCreateRegionHrgn LIB "gdiplus.dll" ALIAS "GdipCreateRegionHrgn" (BYVAL hRgn AS LONG, region AS LONG) AS LONG
DECLARE FUNCTION GdipCloneRegion LIB "gdiplus.dll" ALIAS "GdipCloneRegion" (BYVAL region AS LONG, cloneRegion AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteRegion LIB "gdiplus.dll" ALIAS "GdipDeleteRegion" (BYVAL region AS LONG) AS LONG
DECLARE FUNCTION GdipSetInfinite LIB "gdiplus.dll" ALIAS "GdipSetInfinite" (BYVAL region AS LONG) AS LONG
DECLARE FUNCTION GdipSetEmpty LIB "gdiplus.dll" ALIAS "GdipSetEmpty" (BYVAL region AS LONG) AS LONG
DECLARE FUNCTION GdipCombineRegionRect LIB "gdiplus.dll" ALIAS "GdipCombineRegionRect" (BYVAL region AS LONG, nRect AS RECTF, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipCombineRegionRectI LIB "gdiplus.dll" ALIAS "GdipCombineRegionRectI" (BYVAL region AS LONG, nRect AS RECTF, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipCombineRegionPath LIB "gdiplus.dll" ALIAS "GdipCombineRegionPath" (BYVAL region AS LONG, BYVAL path AS LONG, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipCombineRegionRegion LIB "gdiplus.dll" ALIAS "GdipCombineRegionRegion" (BYVAL region AS LONG, BYVAL region2 AS LONG, BYVAL CombineMd AS LONG) AS LONG
DECLARE FUNCTION GdipTranslateRegion LIB "gdiplus.dll" ALIAS "GdipTranslateRegion" (BYVAL region AS LONG, BYVAL dx AS SINGLE, BYVAL dy AS SINGLE) AS LONG
DECLARE FUNCTION GdipTranslateRegionI LIB "gdiplus.dll" ALIAS "GdipTranslateRegionI" (BYVAL region AS LONG, BYVAL dx AS LONG, BYVAL dy AS LONG) AS LONG
DECLARE FUNCTION GdipTransformRegion LIB "gdiplus.dll" ALIAS "GdipTransformRegion" (BYVAL region AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipGetRegionBounds LIB "gdiplus.dll" ALIAS "GdipGetRegionBounds" (BYVAL region AS LONG, BYVAL graphics AS LONG, nRect AS RECTF) AS LONG
DECLARE FUNCTION GdipGetRegionBoundsI LIB "gdiplus.dll" ALIAS "GdipGetRegionBoundsI" (BYVAL region AS LONG, BYVAL graphics AS LONG, nRect AS RECTL) AS LONG
DECLARE FUNCTION GdipGetRegionHRgn LIB "gdiplus.dll" ALIAS "GdipGetRegionHRgn" (BYVAL region AS LONG, BYVAL graphics AS LONG, hRgn AS LONG) AS LONG
DECLARE FUNCTION GdipIsEmptyRegion LIB "gdiplus.dll" ALIAS "GdipIsEmptyRegion" (BYVAL region AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsInfiniteRegion LIB "gdiplus.dll" ALIAS "GdipIsInfiniteRegion" (BYVAL region AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsEqualRegion LIB "gdiplus.dll" ALIAS "GdipIsEqualRegion" (BYVAL region AS LONG, BYVAL region2 AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipGetRegionDataSize LIB "gdiplus.dll" ALIAS "GdipGetRegionDataSize" (BYVAL region AS LONG, bufferSize AS LONG) AS LONG
' NOTE: The buffer parameter is treated as a byte array
DECLARE FUNCTION GdipGetRegionData LIB "gdiplus.dll" ALIAS "GdipGetRegionData" (BYVAL region AS LONG, buffer AS ANY, BYVAL bufferSize AS LONG, sizeFilled AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisibleRegionPoint LIB "gdiplus.dll" ALIAS "GdipIsVisibleRegionPoint" (BYVAL region AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisibleRegionPointI LIB "gdiplus.dll" ALIAS "GdipIsVisibleRegionPointI" (BYVAL region AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisibleRegionRect LIB "gdiplus.dll" ALIAS "GdipIsVisibleRegionRect" (BYVAL region AS LONG, BYVAL x AS SINGLE, BYVAL y AS SINGLE, BYVAL nWidth AS SINGLE, BYVAL Height AS SINGLE, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipIsVisibleRegionRectI LIB "gdiplus.dll" ALIAS "GdipIsVisibleRegionRectI" (BYVAL region AS LONG, BYVAL x AS LONG, BYVAL y AS LONG, BYVAL nWidth AS LONG, BYVAL Height AS LONG, BYVAL graphics AS LONG, result AS LONG) AS LONG
DECLARE FUNCTION GdipGetRegionScansCount LIB "gdiplus.dll" ALIAS "GdipGetRegionScansCount" (BYVAL region AS LONG, Ucount AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipGetRegionScans LIB "gdiplus.dll" ALIAS "GdipGetRegionScans" (BYVAL region AS LONG, rects AS RECTF, Count AS LONG, BYVAL matrix AS LONG) AS LONG
DECLARE FUNCTION GdipGetRegionScansI LIB "gdiplus.dll" ALIAS "GdipGetRegionScansI" (BYVAL region AS LONG, rects AS RECTL, Count AS LONG, BYVAL matrix AS LONG) AS LONG

' ImageAttributes APIs (ALL)
DECLARE FUNCTION GdipCreateImageAttributes LIB "gdiplus.dll" ALIAS "GdipCreateImageAttributes" (imageattr AS LONG) AS LONG
DECLARE FUNCTION GdipCloneImageAttributes LIB "gdiplus.dll" ALIAS "GdipCloneImageAttributes" (BYVAL imageattr AS LONG, cloneImageattr AS LONG) AS LONG
DECLARE FUNCTION GdipDisposeImageAttributes LIB "gdiplus.dll" ALIAS "GdipDisposeImageAttributes" (BYVAL imageattr AS LONG) AS LONG
DECLARE FUNCTION GdipSetImageAttributesToIdentity LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesToIdentity" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG) AS LONG
DECLARE FUNCTION GdipResetImageAttributes LIB "gdiplus.dll" ALIAS "GdipResetImageAttributes" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG) AS LONG
' NOTE: The colourMatrix and grayMatrix parameters expect a ColorMatrix structure or NULL
DECLARE FUNCTION GdipSetImageAttributesColorMatrix LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesColorMatrix" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG, BYVAL enableFlag AS LONG, colourMatrix AS ColorMatrix, grayMatrix AS ANY, BYVAL flags AS LONG) AS LONG
DECLARE FUNCTION GdipSetImageAttributesThreshold LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesThreshold" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG, BYVAL enableFlag AS LONG, BYVAL threshold AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetImageAttributesGamma LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesGamma" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG, BYVAL enableFlag AS LONG, BYVAL gamma AS SINGLE) AS LONG
DECLARE FUNCTION GdipSetImageAttributesNoOp LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesNoOp" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG, BYVAL enableFlag AS LONG) AS LONG
DECLARE FUNCTION GdipSetImageAttributesColorKeys LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesColorKeys" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG, BYVAL enableFlag AS LONG, BYVAL colorLow AS LONG, BYVAL colorHigh AS LONG) AS LONG
DECLARE FUNCTION GdipSetImageAttributesOutputChannel LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesOutputChannel" (BYVAL imageattr AS LONG, BYVAL ClrAdjstType AS LONG, BYVAL enableFlag AS LONG, BYVAL channelFlags AS LONG) AS LONG
DECLARE FUNCTION GdipSetImageAttributesOutputChannelColorProfile LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesOutputChannelColorProfile" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG, BYVAL enableFlag AS LONG, BYVAL colorProfileFilename AS STRING) AS LONG
DECLARE FUNCTION GdipSetImageAttributesRemapTable LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesRemapTable" (BYVAL imageattr AS LONG, BYVAL ClrAdjType AS LONG, BYVAL enableFlag AS LONG, BYVAL mapSize AS LONG, map AS ColorMap) AS LONG
DECLARE FUNCTION GdipSetImageAttributesWrapMode LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesWrapMode" (BYVAL imageattr AS LONG, BYVAL wrap AS LONG, BYVAL argb AS LONG, BYVAL bClamp AS LONG) AS LONG
DECLARE FUNCTION GdipSetImageAttributesICMMode LIB "gdiplus.dll" ALIAS "GdipSetImageAttributesICMMode" (BYVAL imageattr AS LONG, BYVAL bOn AS LONG) AS LONG
DECLARE FUNCTION GdipGetImageAttributesAdjustedPalette LIB "gdiplus.dll" ALIAS "GdipGetImageAttributesAdjustedPalette" (BYVAL imageattr AS LONG, colorPal AS ColorPalette, BYVAL ClrAdjType AS LONG) AS LONG

' FontFamily Functions (ALL)
DECLARE FUNCTION GdipCreateFontFamilyFromName LIB "gdiplus.dll" ALIAS "GdipCreateFontFamilyFromName" (BYVAL FontName AS STRING, BYVAL fontCollection AS LONG, fontFamily AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteFontFamily LIB "gdiplus.dll" ALIAS "GdipDeleteFontFamily" (BYVAL fontFamily AS LONG) AS LONG
DECLARE FUNCTION GdipCloneFontFamily LIB "gdiplus.dll" ALIAS "GdipCloneFontFamily" (BYVAL fontFamily AS LONG, clonedFontFamily AS LONG) AS LONG
DECLARE FUNCTION GdipGetGenericFontFamilySansSerif LIB "gdiplus.dll" ALIAS "GdipGetGenericFontFamilySansSerif" (nativeFamily AS LONG) AS LONG
DECLARE FUNCTION GdipGetGenericFontFamilySerif LIB "gdiplus.dll" ALIAS "GdipGetGenericFontFamilySerif" (nativeFamily AS LONG) AS LONG
DECLARE FUNCTION GdipGetGenericFontFamilyMonospace LIB "gdiplus.dll" ALIAS "GdipGetGenericFontFamilyMonospace" (nativeFamily AS LONG) AS LONG
' NOTE: name must be LF_FACESIZE in length or less
DECLARE FUNCTION GdipGetFamilyName LIB "gdiplus.dll" ALIAS "GdipGetFamilyName" (BYVAL family AS LONG, BYVAL FilName AS STRING, BYVAL language AS INTEGER) AS LONG
DECLARE FUNCTION GdipIsStyleAvailable LIB "gdiplus.dll" ALIAS "GdipIsStyleAvailable" (BYVAL family AS LONG, BYVAL style AS LONG, IsStyleAvailable AS LONG) AS LONG
DECLARE FUNCTION GdipFontCollectionEnumerable LIB "gdiplus.dll" ALIAS "GdipFontCollectionEnumerable" (BYVAL fontCollection AS LONG, BYVAL graphics AS LONG, numFound AS LONG) AS LONG
DECLARE FUNCTION GdipFontCollectionEnumerate LIB "gdiplus.dll" ALIAS "GdipFontCollectionEnumerate" (BYVAL fontCollection AS LONG, BYVAL numSought AS LONG, gpfamilies AS LONG, BYVAL numFound AS LONG, BYVAL graphics AS LONG) AS LONG
DECLARE FUNCTION GdipGetEmHeight LIB "gdiplus.dll" ALIAS "GdipGetEmHeight" (BYVAL family AS LONG, BYVAL style AS LONG, EmHeight AS INTEGER) AS LONG
DECLARE FUNCTION GdipGetCellAscent LIB "gdiplus.dll" ALIAS "GdipGetCellAscent" (BYVAL family AS LONG, BYVAL style AS LONG, CellAscent AS INTEGER) AS LONG
DECLARE FUNCTION GdipGetCellDescent LIB "gdiplus.dll" ALIAS "GdipGetCellDescent" (BYVAL family AS LONG, BYVAL style AS LONG, CellDescent AS INTEGER) AS LONG
DECLARE FUNCTION GdipGetLineSpacing LIB "gdiplus.dll" ALIAS "GdipGetLineSpacing" (BYVAL family AS LONG, BYVAL style AS LONG, LineSpacing AS INTEGER) AS LONG

' Font Functions (ALL)
DECLARE FUNCTION GdipCreateFontFromDC LIB "gdiplus.dll" ALIAS "GdipCreateFontFromDC" (BYVAL hdc AS LONG, createdfont AS LONG) AS LONG
DECLARE FUNCTION GdipCreateFontFromLogfontA LIB "gdiplus.dll" ALIAS "GdipCreateFontFromLogfontA" (BYVAL hdc AS LONG, lfont AS LOGFONTA, createdfont AS LONG) AS LONG
DECLARE FUNCTION GdipCreateFontFromLogfontW LIB "gdiplus.dll" ALIAS "GdipCreateFontFromLogfontW" (BYVAL hdc AS LONG, lfont AS LOGFONTW, createdfont AS LONG) AS LONG
DECLARE FUNCTION GdipCreateFont LIB "gdiplus.dll" ALIAS "GdipCreateFont" (BYVAL fontFamily AS LONG, BYVAL emSize AS SINGLE, BYVAL style AS LONG, BYVAL unit AS LONG, createdfont AS LONG) AS LONG
DECLARE FUNCTION GdipCloneFont LIB "gdiplus.dll" ALIAS "GdipCloneFont" (BYVAL curFont AS LONG, cloneFont AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteFont LIB "gdiplus.dll" ALIAS "GdipDeleteFont" (BYVAL curFont AS LONG) AS LONG
DECLARE FUNCTION GdipGetFamily LIB "gdiplus.dll" ALIAS "GdipGetFamily" (BYVAL curFont AS LONG, family AS LONG) AS LONG
DECLARE FUNCTION GdipGetFontStyle LIB "gdiplus.dll" ALIAS "GdipGetFontStyle" (BYVAL curFont AS LONG, style AS LONG) AS LONG
DECLARE FUNCTION GdipGetFontSize LIB "gdiplus.dll" ALIAS "GdipGetFontSize" (BYVAL curFont AS LONG, SIZE AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetFontUnit LIB "gdiplus.dll" ALIAS "GdipGetFontUnit" (BYVAL curFont AS LONG, unit AS LONG) AS LONG
DECLARE FUNCTION GdipGetFontHeight LIB "gdiplus.dll" ALIAS "GdipGetFontHeight" (BYVAL curFont AS LONG, BYVAL graphics AS LONG, Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetFontHeightGivenDPI LIB "gdiplus.dll" ALIAS "GdipGetFontHeightGivenDPI" (BYVAL curFont AS LONG, BYVAL dpi AS SINGLE, Height AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetLogFontA LIB "gdiplus.dll" ALIAS "GdipGetLogFontA" (BYVAL curFont AS LONG, BYVAL graphics AS LONG, lfont AS LOGFONTA) AS LONG
DECLARE FUNCTION GdipGetLogFontW LIB "gdiplus.dll" ALIAS "GdipGetLogFontW" (BYVAL curFont AS LONG, BYVAL graphics AS LONG, lfont AS LOGFONTW) AS LONG
DECLARE FUNCTION GdipNewInstalledFontCollection LIB "gdiplus.dll" ALIAS "GdipNewInstalledFontCollection" (fontCollection AS LONG) AS LONG
DECLARE FUNCTION GdipNewPrivateFontCollection LIB "gdiplus.dll" ALIAS "GdipNewPrivateFontCollection" (fontCollection AS LONG) AS LONG
DECLARE FUNCTION GdipDeletePrivateFontCollection LIB "gdiplus.dll" ALIAS "GdipDeletePrivateFontCollection" (fontCollection AS LONG) AS LONG
DECLARE FUNCTION GdipGetFontCollectionFamilyCount LIB "gdiplus.dll" ALIAS "GdipGetFontCollectionFamilyCount" (BYVAL fontCollection AS LONG, numFound AS LONG) AS LONG
DECLARE FUNCTION GdipGetFontCollectionFamilyList LIB "gdiplus.dll" ALIAS "GdipGetFontCollectionFamilyList" (BYVAL fontCollection AS LONG, BYVAL numSought AS LONG, gpfamilies AS LONG, numFound AS LONG) AS LONG
DECLARE FUNCTION GdipPrivateAddFontFile LIB "gdiplus.dll" ALIAS "GdipPrivateAddFontFile" (BYVAL fontCollection AS LONG, BYVAL FilName AS STRING) AS LONG
DECLARE FUNCTION GdipPrivateAddMemoryFont LIB "gdiplus.dll" ALIAS "GdipPrivateAddMemoryFont" (BYVAL fontCollection AS LONG, BYVAL memory AS LONG, BYVAL length AS LONG) AS LONG

' Text Functions (ALL)
DECLARE FUNCTION GdipDrawString LIB "gdiplus.dll" ALIAS "GdipDrawString" (BYVAL graphics AS LONG, BYVAL str AS STRING, BYVAL length AS LONG, BYVAL thefont AS LONG, layoutRect AS RECTF, BYVAL StringFormat AS LONG, BYVAL brush AS LONG) AS LONG
DECLARE FUNCTION GdipMeasureString LIB "gdiplus.dll" ALIAS "GdipMeasureString" (BYVAL graphics AS LONG, BYVAL str AS STRING, BYVAL length AS LONG, BYVAL thefont AS LONG, layoutRect AS RECTF, BYVAL StringFormat AS LONG, boundingBox AS RECTF, _
codepointsFitted AS LONG, linesFilled AS LONG) AS LONG
DECLARE FUNCTION GdipMeasureCharacterRanges LIB "gdiplus.dll" ALIAS "GdipMeasureCharacterRanges" (BYVAL graphics AS LONG, BYVAL str AS STRING, BYVAL length AS LONG, BYVAL thefont AS LONG, layoutRect AS RECTF, BYVAL StringFormat AS LONG, BYVAL regionCount _
AS LONG, regions AS LONG) AS LONG
DECLARE FUNCTION GdipDrawDriverString LIB "gdiplus.dll" ALIAS "GdipDrawDriverString" (BYVAL graphics AS LONG, BYVAL str AS STRING, BYVAL length AS LONG, BYVAL thefont AS LONG, BYVAL brush AS LONG, positions AS POINTF, BYVAL flags AS LONG, BYVAL matrix AS _
LONG) AS LONG
DECLARE FUNCTION GdipMeasureDriverString LIB "gdiplus.dll" ALIAS "GdipMeasureDriverString" (BYVAL graphics AS LONG, BYVAL str AS STRING, BYVAL length AS LONG, BYVAL thefont AS LONG, positions AS POINTF, BYVAL flags AS LONG, BYVAL matrix AS LONG, _
boundingBox AS RECTF) AS LONG

' String format Functions (ALL)
DECLARE FUNCTION GdipCreateStringFormat LIB "gdiplus.dll" ALIAS "GdipCreateStringFormat" (BYVAL formatAttributes AS LONG, BYVAL language AS INTEGER, StringFormat AS LONG) AS LONG
DECLARE FUNCTION GdipStringFormatGetGenericDefault LIB "gdiplus.dll" ALIAS "GdipStringFormatGetGenericDefault" (StringFormat AS LONG) AS LONG
DECLARE FUNCTION GdipStringFormatGetGenericTypographic LIB "gdiplus.dll" ALIAS "GdipStringFormatGetGenericTypographic" (StringFormat AS LONG) AS LONG
DECLARE FUNCTION GdipDeleteStringFormat LIB "gdiplus.dll" ALIAS "GdipDeleteStringFormat" (BYVAL StringFormat AS LONG) AS LONG
DECLARE FUNCTION GdipCloneStringFormat LIB "gdiplus.dll" ALIAS "GdipCloneStringFormat" (BYVAL StringFormat AS LONG, newFormat AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatFlags LIB "gdiplus.dll" ALIAS "GdipSetStringFormatFlags" (BYVAL StringFormat AS LONG, BYVAL flags AS LONG) AS LONG
DECLARE FUNCTION GdipGetStringFormatFlags LIB "gdiplus.dll" ALIAS "GdipGetStringFormatFlags" (BYVAL StringFormat AS LONG, flags AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatAlign LIB "gdiplus.dll" ALIAS "GdipSetStringFormatAlign" (BYVAL StringFormat AS LONG, BYVAL align AS LONG) AS LONG
DECLARE FUNCTION GdipGetStringFormatAlign LIB "gdiplus.dll" ALIAS "GdipGetStringFormatAlign" (BYVAL StringFormat AS LONG, align AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatLineAlign LIB "gdiplus.dll" ALIAS "GdipSetStringFormatLineAlign" (BYVAL StringFormat AS LONG, BYVAL align AS LONG) AS LONG
DECLARE FUNCTION GdipGetStringFormatLineAlign LIB "gdiplus.dll" ALIAS "GdipGetStringFormatLineAlign" (BYVAL StringFormat AS LONG, align AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatTrimming LIB "gdiplus.dll" ALIAS "GdipSetStringFormatTrimming" (BYVAL StringFormat AS LONG, BYVAL trimming AS LONG) AS LONG
DECLARE FUNCTION GdipGetStringFormatTrimming LIB "gdiplus.dll" ALIAS "GdipGetStringFormatTrimming" (BYVAL StringFormat AS LONG, trimming AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatHotkeyPrefix LIB "gdiplus.dll" ALIAS "GdipSetStringFormatHotkeyPrefix" (BYVAL StringFormat AS LONG, BYVAL hkPrefix AS LONG) AS LONG
DECLARE FUNCTION GdipGetStringFormatHotkeyPrefix LIB "gdiplus.dll" ALIAS "GdipGetStringFormatHotkeyPrefix" (BYVAL StringFormat AS LONG, hkPrefix AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatTabStops LIB "gdiplus.dll" ALIAS "GdipSetStringFormatTabStops" (BYVAL StringFormat AS LONG, BYVAL firstTabOffset AS SINGLE, BYVAL Count AS LONG, tabStops AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetStringFormatTabStops LIB "gdiplus.dll" ALIAS "GdipGetStringFormatTabStops" (BYVAL StringFormat AS LONG, BYVAL Count AS LONG, firstTabOffset AS SINGLE, tabStops AS SINGLE) AS LONG
DECLARE FUNCTION GdipGetStringFormatTabStopCount LIB "gdiplus.dll" ALIAS "GdipGetStringFormatTabStopCount" (BYVAL StringFormat AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatDigitSubstitution LIB "gdiplus.dll" ALIAS "GdipSetStringFormatDigitSubstitution" (BYVAL StringFormat AS LONG, BYVAL language AS INTEGER, BYVAL substitute AS LONG) AS LONG
DECLARE FUNCTION GdipGetStringFormatDigitSubstitution LIB "gdiplus.dll" ALIAS "GdipGetStringFormatDigitSubstitution" (BYVAL StringFormat AS LONG, language AS INTEGER, substitute AS LONG) AS LONG
DECLARE FUNCTION GdipGetStringFormatMeasurableCharacterRangeCount LIB "gdiplus.dll" ALIAS "GdipGetStringFormatMeasurableCharacterRangeCount" (BYVAL StringFormat AS LONG, Count AS LONG) AS LONG
DECLARE FUNCTION GdipSetStringFormatMeasurableCharacterRanges LIB "gdiplus.dll" ALIAS "GdipSetStringFormatMeasurableCharacterRanges" (BYVAL StringFormat AS LONG, BYVAL rangeCount AS LONG, ranges AS CharacterRange) AS LONG


