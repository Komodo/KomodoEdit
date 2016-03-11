"""
Microsoft CSS extensions.
"""

import textwrap

### START: Auto generated

CSS_MICROSOFT_DATA = {
    '-ms-accelerator': {
        'description': "Extension",
    },
    '-ms-background-position-x': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-background-position-y': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-behavior': {
        'description': "Extension",
    },
    '-ms-block-progression': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-filter': {
        'description': "Extension - Sets or retrieves the filter or collection of filters applied to the object.",
        'values': {
            'progid:DXImageTransform.Microsoft.Alpha': "Adjusts the opacity of the content of the object.",
            'progid:DXImageTransform.Microsoft.BasicImage': "Adjusts the color processing, image rotation, or opacity of the content of the object.",
            'progid:DXImageTransform.Microsoft.Blur': "Blurs the content of the object so that it appears out of focus.",
            'progid:DXImageTransform.Microsoft.Chroma': "Displays a specific color of the content of the object as transparent.",
            'progid:DXImageTransform.Microsoft.Compositor': "Displays new content of the object as a logical color combination of the new and original content. The color and alpha values of each version of the content are evaluated to determine the final color on the output image.",
            'progid:DXImageTransform.Microsoft.DropShadow': "Creates a solid silhouette of the content of the object, offset in the specified direction. This creates the illusion that the content is floating and casting a shadow.",
            'progid:DXImageTransform.Microsoft.Emboss': "Displays the content of the object as an embossed texture using grayscale values.",
            'progid:DXImageTransform.Microsoft.Engrave': "Displays the content of the object as an engraved texture using grayscale values.",
            'progid:DXImageTransform.Microsoft.Glow': "Adds radiance around the outside edges of the content of the object so that it appears to glow.",
            'progid:DXImageTransform.Microsoft.ICMFilter': "Converts the color content of the object based on an Image Color Management (ICM) profile. This enables improved display of specific content, or simulated display for hardware devices, such as printers or monitors.",
            'progid:DXImageTransform.Microsoft.Light': "Creates the effect of a light shining on the content of the object.",
            'progid:DXImageTransform.Microsoft.MaskFilter': "Displays transparent pixels of the object content as a color mask, and makes the nontransparent pixels transparent.",
            'progid:DXImageTransform.Microsoft.Matrix': "Resizes, rotates, or reverses the content of the object using matrix transformation.",
            'progid:DXImageTransform.Microsoft.MotionBlur': "Causes the content of the object to appear to be in motion.",
            'progid:DXImageTransform.Microsoft.Shadow': "Creates a solid silhouette of the content of the object, offset in the specified direction. This creates the illusion of a shadow.",
            'progid:DXImageTransform.Microsoft.Wave': "Performs a sine wave distortion of the content of the object  along the vertical axis.",
        }
    },
    '-ms-ime-mode': {
        'description': "Extension",
    },
    '-ms-layout-grid': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-layout-grid-char': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-layout-grid-line': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-layout-grid-mode': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-layout-grid-type': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-line-break': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-line-grid-mode': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-interpolation-mode': {
        'description': "Extension",
    },
    '-ms-overflow-x': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-overflow-y': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-scrollbar-3dlight-color': {
        'description': "Extension",
    },
    '-ms-scrollbar-arrow-color': {
        'description': "Extension",
    },
    '-ms-scrollbar-base-color': {
        'description': "Extension",
    },
    '-ms-scrollbar-darkshadow-color': {
        'description': "Extension",
    },
    '-ms-scrollbar-face-color': {
        'description': "Extension",
    },
    '-ms-scrollbar-highlight-color': {
        'description': "Extension",
    },
    '-ms-scrollbar-shadow-color': {
        'description': "Extension",
    },
    '-ms-scrollbar-track-color': {
        'description': "Extension",
    },
    '-ms-text-align-last': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-text-autospace': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-text-justify': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-text-kashida-space': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-text-overflow': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-text-underline-position': {
        'description': "Extension",
    },
    '-ms-word-break': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-word-wrap': {
        'description': "CSS3 - Working Draft",
    },
    '-ms-writing-mode': {
        'description': "CSS3 - Editor's Draft",
    },
    '-ms-zoom': {
        'description': "Extension",
    },
    # CSS3 flexbox properties
    '-ms-align-content': {
        'description': "The CSS align-content property aligns a flex container's lines within the flex container when there is extra space on the cross-axis.",
        'values': {
            'flex-start': "Lines are packed starting from the cross-start. Cross-start edge of the first line and cross-start edge of the flex container are flushed together. Each following line is flush with the preceding.",
            'flex-end': "Lines are packed starting from the cross-end. Cross-end of the last line and cross-end of the flex container are flushed together. Each preceding line is flushed with the following line.",
            'center': "Lines are packed toward the center of the flex container. The lines are flushed with each other and aligned in the center of the flex container. Space between the cross-start edge of the flex container and first line and between cross-end of the flex container and the last line is the same.",
            'space-between': "Lines are evenly distributed in the flex container. The spacing is done such as the space between two adjacent items is the same. Cross-start edge and cross-end edge of the flex container are flushed with respectively first and last line edges.",
            'space-around': "Lines are evenly distributed so that the space between two adjacent lines is the same. The empty space before the first and after the last lines equals half of the space between two adjacent lines.",
            'stretch': "Lines stretch to use the remaining space. The free-space is split equally between all the lines.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-align-items': {
        'description': "The CSS align-items property aligns flex items of the current flex line the same way as justify-content but in the perpendicular direction.",
        'values': {
            'flex-start': "The cross-start margin edge of the flex item is flushed with the cross-start edge of the line.",
            'flex-end': "The cross-end margin edge of the flex item is flushed with the cross-end edge of the line.",
            'center': "The flex item's margin box is centered within the line on the cross-axis. If the cross-size of the item is larger than the flex container, it will overflow equally in both directions.",
            'baseline': "All flex items are aligned such that their baselines align. The item with the largest distance between its cross-start margin edge and its baseline is flushed with the cross-start edge of the line.",
            'stretch': "Flex items are stretched such as the cross-size of the item's margin box is the same as the line while respecting width and height constraints.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-align-self': {
        'description': "The align-self CSS property aligns flex items of the current flex line overriding the align-items value. If any of the flex item's cross-axis margin is set to auto, then align-self is ignored.",
        'values': {
            'auto': "Computes to parent's align-items value or stretch if the element has no parent.",
            'flex-start': "The cross-start margin edge of the flex item is flushed with the cross-start edge of the line.",
            'flex-end': "The cross-end margin edge of the flex item is flushed with the cross-end edge of the line.",
            'center': "The flex item's margin box is centered within the line on the cross-axis. If the cross-size of the item is larger than the flex container, it will overflow equally in both directions.",
            'baseline': "All flex items are aligned such that their baselines align. The item with the largest distance between its cross-start margin edge and its baseline is flushed with the cross-start edge of the line.",
            'stretch': "Flex items are stretched such as the cross-size of the item's margin box is the same as the line while respecting width and height constraints.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-flex-basis': {
        'description': "The flex-basis CSS property specifies the flex basis which is the initial main size of a flex item. This property determines the size of the content-box unless specified otherwise using box-sizing.",
        'values': {
            '<width>': "Defined as a number followed by a absolute unit such as px, mm or pt, or a percentage of the parent flex container main size property. Negative values are invalid.",
            'fill': "",
            'max-content': "",
            'min-content': "",
            'fit-content': "",
            'content': "Indicates automatic sizing, based on the flex item's content.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-flex-direction': {
        'description': "The flex-direction CSS property specifies how flex items are placed in the flex container defining the main axis and the direction (normal or reversed).",
        'values': {
            'row': "The flex container's main-axis is defined to be the same as the text direction. The main-start and main-end points are the same as the content direction.",
            'row-reverse': "Behaves the same as row but the main-start and main-end points are permuted.",
            'column': "The flex container's main-axis is the same as the block-axis. The main-start and main-end points are the same as the before and after points of the writing-mode.",
            'column-reverse': "Behaves the same as column but the main-start and main-end are permuted.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-flex-wrap': {
        'description': "The CSS flex-wrap property specifies whether flex items are forced into a single line or can be wrapped onto multiple lines. If wrapping is allowed, this property also enables you to control the direction in which lines are stacked.",
        'values': {
            'nowrap': "The flex items are laid out in a single line which may cause the flex container to overflow. The cross-start is either equivalent to start or before depending flex-direction value.",
            'wrap': "The flex items break into multiple lines. The cross-start is either equivalent to start or before depending flex-direction value and the cross-end is the opposite of the specified cross-start.",
            'wrap-reverse': "Behaves the same as wrap but cross-start and cross-end are permuted.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-flex-flow': {
        'description': "The flex-flow CSS property is a shorthand property for flex-direction and flex-wrap individual properties.",
        'values': {
            '<flex-direction> || <flex wrap>': "See flex-direction and flex-wrap for details on the values.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-flex-grow': {
        'description': "The flex-grow CSS property specifies the flex grow factor of a flex item. It specifies what amount of space inside the flex container the item should take up.",
        'values': {
            '<number>': "Number. Negative values are invalid",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-flex-shrink': {
        'description': "The flex-shrink CSS property specifies the flex shrink factor of a flex item.",
        'values': {
            '<number>': "Number. Negative values are invalid.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-justify-content': {
        'description': "The CSS justify-content property defines how the browser distributes space between and around flex items along the main-axis of their container.",
        'values': {
            'flex-start': "The flex items are packed starting from the main-start. Margins of the first flex item is flushed with the main-start edge of the line and each following flex item is flushed with the preceding.",
            'flex-end': "The flex items are packed starting from the main-end. The margin edge of the last flex item is flushed with the main-end edge of the line and each preceding flex item is flushed with the following.",
            'center': "The flex items are packed toward the center of the line. The flex items are flushed with each other and aligned in the center of the line. Space between the main-start edge of the line and first item and between main-end and the last item of the line is the same.",
            'space-between': "Flex items are evenly distributed along the line. The spacing is done such as the space between two adjacent items is the same. Main-start edge and main-end edge are flushed with respectively first and last flex item edges.",
            'space-around': "Flex items are evenly distributed so that the space between two adjacent items is the same. The empty space before the first and after the last items equals half of the space between two adjacent items.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
    '-ms-order': {
        'description': "The CSS order property specifies the order used to lay out flex items in their flex container. Elements are laid out in the ascending order of the order value. Elements with the same order value are laid out in the order in which they appear in the source code.",
        'values': {
            '<integer>': "Represents the ordinal group the flex item has been assigned.",
            'inherit': "",
            'initial': "",
            'unset': ""
        }
    },
}

### END: Auto generated




CSS_MICROSOFT_SPECIFIC_ATTRS_DICT = {}
CSS_MICROSOFT_SPECIFIC_CALLTIP_DICT = {}
for attr, details in CSS_MICROSOFT_DATA.items():
    values = details.get("values", {})
    versions = details.get("versions", [])
    attr_completions = sorted(values.keys())
    if attr_completions:
        CSS_MICROSOFT_SPECIFIC_ATTRS_DICT[attr] = attr_completions
    else:
        CSS_MICROSOFT_SPECIFIC_ATTRS_DICT[attr] = None
    description = details.get("description", '')
    if versions:
        description += "\nVersions: %s\n" % (", ".join(versions))
    if description:
        desc_lines = textwrap.wrap(description, width=60)
        if values:
            desc_lines.append("")
            for value, attr_desc in values.items():
                attr_desc = "  %r: %s" % (value, attr_desc)
                attr_desc_lines = textwrap.wrap(attr_desc, width=50)
                for i in range(len(attr_desc_lines)):
                    attr_line = attr_desc_lines[i]
                    if i > 0:
                        attr_line = "        " + attr_line
                    desc_lines.append(attr_line)
        CSS_MICROSOFT_SPECIFIC_CALLTIP_DICT[attr] = "\n".join(desc_lines).encode("ascii", 'replace')
