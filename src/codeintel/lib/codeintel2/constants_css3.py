"""
CSS 3 definitions - requires CSS 1 and CSS 2 modules.
"""

import textwrap

from codeintel2.constants_css1 import CSS_ATTR_DICT as CSS1_SPECIFIC_ATTRS_DICT
from codeintel2.constants_css1 import CSS_PROPERTY_ATTRIBUTE_CALLTIPS_DICT as CSS1_SPECIFIC_CALLTIP_DICT
from codeintel2.constants_css2 import CSS2_SPECIFIC_ATTRS_DICT, CSS2_SPECIFIC_CALLTIP_DICT

CSS_PSEUDO_CLASS_NAMES = """
    root
    nth-child(
    nth-last-child(
    nth-of-type(
    nth-last-of-type(
    first-child
    last-child
    first-of-type
    last-of-type
    only-child
    only-of-type
    empty
    link
    visited
    active
    hover
    focus
    target
    lang(
    enabled
    disabled
    checked
    first-line
    first-letter
    before
    after
    not(
""".split()


CSS3_DATA = {
    'alignment-baseline': {
        'description': "",
        'values': {
            'after-edge': "The alignment point of the box is aligned with the 'after-edge' baseline of the line box.",
            'alphabetic': 'The alignment-point of the element being aligned is aligned with the lower baseline of the parent.',
            'baseline': 'The alignment-point of the element being aligned is aligned with the dominant baseline of the parent.',
            'before-edge': "The alignment point of the box is aligned with the 'before-edge' baseline of the line box.",
            'central': "The alignment point of the box is aligned with the 'central' baseline of the parent.",
            'hanging': 'The alignment-point of the element being aligned is aligned with the hanging baseline of the parent.',
            'ideographic': "The alignment-point of the element being aligned is aligned with the 'ideographic' baseline of the parent.",
            'mathematical': 'The alignment-point of the element being aligned is aligned with the mathematical baseline of the parent.',
            'middle': "The alignment point of the box is aligned with the 'middle' baseline of the parent.",
            'text-after-edge': "The alignment-point of the element being aligned is aligned with the 'text-after-edge' baseline of the parent.",
            'text-before-edge': "The alignment-point of the element being aligned is aligned with the 'text-before-edge' baseline of the parent.",
            'use-script': "If the element 'script' property value is 'auto', the alignment point of each glyph is aligned with the baseline-identifier of the script to which the glyph belongs. If the element 'script' property value is other than 'auto', the alignment point of each glyph is aligned with the baseline-identifier specified by the 'script' property. The baseline-identifier position is determined by using the relevant information related to the parent element dominant-baseline set. The alignment point of the element itself is aligned as for the 'baseline' value."
        }
    },

    'animation': {
        'description': "The animation CSS property is a shorthand property for animation-name, animation-duration, animation-timing-function, animation-delay, animation-iteration-count, animation-direction, animation-fill-mode and animation-play-state",
        'values': {
            'ease': "",
            'ease-in': "",
            'ease-out': "",
            'ease-in-out': "",
            'linear': "",
            'infinite': "The animation will repeat forever.",
            'normal': "The animation should play forward each cycle. In other words, each time the animation cycles, the animation will reset to the beginning state and start over again. This is the default animation direction setting.",
            'alternate': "The animation should reverse direction each cycle. When playing in reverse, the animation steps are performed backward. In addition, timing functions are also reversed; for example, an ease-in animation is replaced with an ease-out animation when played in reverse. The count to determine if it is an even or an odd iteration starts at one.",
            'reverse': "The animation plays backward each cycle. Each time the animation cycles, the animation resets to the end state and start over again.",
            'alternate-reverse': "The animation plays backward on the first play-through, then forward on the next, then continues to alternate. The count to determinate if it is an even or an odd iteration starts at one.",
            'none': "The animation will not apply any styles to the target before or after it is executing.",
            'forwards': "The target will retain the computed values set by the last keyframe encountered during execution. The last keyframe encountered depends on the value of animation-direction and animation-iteration-count",
            'backwards': "The animation will apply the values defined in the first relevant keyframe as soon as it is applied to the target, and retain this during the animation-delay period. The first relevant keyframe depends of the value of animation-direction",
            'both': "The animation will follow the rules for both forwards and backwards, thus extending the animation properties in both directions.",
            'running': "The animation is currently playing.",
            'paused': "The animation is currently paused."
        }
    },

    'animation-delay': {
        'description': "The animation-delay CSS property specifies when the animation should start. This lets the animation sequence begin some time after it's applied to an element.",
        'values': {
            '<time>': "The time offset from the time at which the animation is applied to the element at which the animation should begin. This may be specified in either seconds (by specifying s as the unit) or milliseconds (by specifying ms as the unit). If you don't specify a unit, the statement is invalid."
        }
    },

    'animation-direction': {
        'description': "The animation-direction CSS property indicates whether the animation should play in reverse on alternate cycles.",
        'values': {
            'normal': "The animation should play forward each cycle. In other words, each time the animation cycles, the animation will reset to the beginning state and start over again. This is the default animation direction setting.",
            'alternate': "The animation should reverse direction each cycle. When playing in reverse, the animation steps are performed backward. In addition, timing functions are also reversed; for example, an ease-in animation is replaced with an ease-out animation when played in reverse. The count to determine if it is an even or an odd iteration starts at one.",
            'reverse': "The animation plays backward each cycle. Each time the animation cycles, the animation resets to the end state and start over again.",
            'alternate-reverse': "The animation plays backward on the first play-through, then forward on the next, then continues to alternate. The count to determinate if it is an even or an odd iteration starts at one."
        }
    },

    'animation-duration': {
        'description': "The animation-duration CSS property specifies the length of time that an animation should take to complete one cycle.",
        'values': {
            '<time>': "The duration that an animation should take to complete one cycle. This may be specified in either seconds (by specifying s as the unit) or milliseconds (by specifying ms as the unit). If you don't specify a unit, the declaration will be invalid."
        }
    },

    'animation-iteration-count': {
        'description': "The animation-iteration-count CSS property defines the number of times an animation cycle should be played before stopping.",
        'values': {
            'infinite': "The animation will repeat forever.",
            '<number>': "The number of times the animation should repeat; this is 1 by default. Negative values are invalid. You may specify non-integer values to play part of an animation cycle (for example 0.5 will play half of the animation cycle)."
        }
    },

    'animation-name': {
        'description': "The animation-name CSS property specifies a list of animations that should be applied to the selected element. Each name indicates a @keyframes at-rule that defines the property values for the animation sequence.",
        'values': {
            'none': "Is a special keyword denoting no keyframes. It can be used to deactivate an animation without changing the ordering of the other identifiers, or to deactivate animations coming from the cascade.",
            '<custom-ident>': "A string identifying the animation. This identifier is composed by a combination of case-insensitive letters a to z, numbers 0 to 9, underscores (_), and/or dashes (-). The first non-dash character must be a letter (that is, no number at the beginning of it, even if preceded by a dash.) Also, two dashes are forbidden at the beginning of the identifier. It can't be none, unset, initial, or inherit in any combination of cases."
        }
    },

    'animation-play-state': {
        'description': "The animation-play-state CSS property determines whether an animation is running or paused. This can be queried to determine whether or not the animation is currently running. In addition, its value can be set to pause and resume playback of an animation. Resuming a paused animation will start the animation from where it left off at the time it was paused, rather than starting over from the beginning of the animation sequence.",
        'values': {
            'running': "The animation is currently playing.",
            'paused': "The animation is currently paused."
        }
    },

    'animation-timing-function': {
        'description': "The CSS animation-timing-function property specifies how a CSS animation should progress over the duration of each cycle. The possible values are one or several <timing-function>. For keyframed animations, the timing function applies between keyframes rather than over the entire animation. In other words, the timing function is applied at the start of the keyframe and at the end of the keyframe.",
        'values': {
            'linear': "",
            'ease': "",
            'ease-in': "",
            'ease-in-out': "",
            'cubic-bezier': ""
        }
    },
    'animation-fill-mode': {
        'description': "The animation-fill-mode CSS property specifies how a CSS animation should apply styles to its target before and after it is executing.",
        'values': {
            'none': "The animation will not apply any styles to the target before or after it is executing.",
            'forwards': "The target will retain the computed values set by the last keyframe encountered during execution. The last keyframe encountered depends on the value of animation-direction and animation-iteration-count",
            'backwards': "The animation will apply the values defined in the first relevant keyframe as soon as it is applied to the target, and retain this during the animation-delay period. The first relevant keyframe depends of the value of animation-direction",
            'both': "The animation will follow the rules for both forwards and backwards, thus extending the animation properties in both directions",
        }
    },
    'appearance': {
        'description': 'The appearance property is used to display an element using a platform-native styling based on the user operating system theme.',
        'values': {}
    },
    
    'backface-visibility': {
        'description': "The CSS backface-visibility property determines whether or not the back face of the element is visible when facing the user. The back face of an element is always a transparent background, letting, when visible, a mirror image of the front face be displayed.",
        'values': {
            "visible": "meaning that the back face is visible, allowing the front face to be displayed mirrored",
            "hidden": "meaning that the back face is not visible, hiding the front face"
        }
    },
    
    'background-clip': {
        'description': 'Determines the background painting area.',
        'values': {
            'border-box': "The background is painted within (clipped to) the border box.",
            'content-box': "The background is painted within (clipped to) the content box.",
            'padding-box': "The background is painted within (clipped to) the padding box."
        }
    },
    'background-origin': {
        'description': "The background-origin CSS property determines the background positioning area, that is the position of the origin of an image specified using the background-image CSS property.",
        'values': {
            'content-box': "The background is painted within (clipped to) the content box.",
            'border-box': "The background extends to the outside edge of the border (but underneath the border in z-ordering).",
            'padding-box': "No background is drawn below the border (background extends to the outside edge of the padding)."
        }
    },

    'background-size': {
        'description': "The background-size CSS property specifies the size of the background images. The size of the image can be fully constrained or only partially in order to preserve its intrinsic ratio.",
        'values': {
            '<length>': "A <length> value that scales the background image to the specified length in the corresponding dimension. Negative lengths are not allowed.",
            '<percentage>': "A <percentage> value that scales the background image in the corresponding dimension to the specified percentage of the background positioning area, which is determined by the value of background-origin.",
            'cover': "This keyword specifies that the background image should be scaled to be as small as possible while ensuring both its dimensions are greater than or equal to the corresponding dimensions of the background positioning area.",
            'contain': "This keyword specifies that the background image should be scaled to be as large as possible while ensuring both its dimensions are less than or equal to the corresponding dimensions of the background positioning area.",
            'auto': "The auto keyword that scales the background image in the corresponding direction such that its intrinsic proportion is maintained."
        }
    },

    'baseline-shift': {
        'description': "The baseline-shift attribute allows repositioning of the dominant-baseline relative to the dominant-baseline of the parent text content element. The shifted object might be a sub- or superscript.",
        'values': {
            '<length>': "The dominant-baseline is shifted in the shift direction (positive value) or opposite to the shift direction (negative value) of the parent text content element by the <length> value. A value of \"0cm\" is equivalent to \"baseline\".",
            '<percentage>': "The resulting value of the property is this percentage multiplied by the line-height of the <text> element. The dominant-baseline is shifted in the shift direction (positive value) or opposite to the shift direction (negative value) of the parent text content element by the resulting value. A value of \"0%\" is equivalent to \"baseline\".",
            'baseline': 'There is no baseline shift; the dominant-baseline remains in its original position.',
            'sub': 'The dominant-baseline is shifted to the default position for subscripts.',
            'super': 'The dominant-baseline is shifted to the default position for superscripts.'
        }
    },
    
    'border-image-source': {
        'description': "The border-image-source CSS property defines the <image> to use instead of the style of the border. If this property is set to none, the style defined by border-style is used instead.",
        'values': {
            'none': "Specifies that no image should be used for the border. Instead the style defined by border-style is used.",
            '<image>': "Image reference to use for the border."
        }
    },
    'border-image-width': {
        'description': "The border-image-width CSS property defines the width of the border. If specified it overrides the border-width property.",
        'values': {
            '<length>': "Represents the width of the border. It can be an absolute or relative length. This length must not be negative.",
            '<percentage>': "Represents the width of the border as a percentage of the element. The percentage must not be negative.",
            '<number>': "Represents a multiple of the computed value of the element's border-width property to be used as the border width. The number must not be negative.",
            'auto': "Causes the border image width to equal the intrinsic width or height (whichever is applicable) of the corresponding border-image-slice. If the image does not have the required intrinsic dimension then the corresponding computed border-width is used instead."
        }
    },
    'border-image-outset': {
        'description': "The border-image-outset property describes by what amount the border image area extends beyond the border box.",
        'values': {
            '<length>': "",
            '<number>': ""
        }
    },
    'border-image-slice': {
        'description': "The border-image-slice CSS property divides the image specified by border-image-source in nine regions: the four corners, the four edges and the middle. It does this by specifying 4 inwards offsets.",
        'values': {
            '<length>': "",
            '<number>': "",
            'fill': "Is a keyword whose presence forces the use of the middle image slice to be displayed over the background image, its size and height are resized like those of the top and left image slices, respectively.",
            "inherit": ""
        }
    },
    'border-image-repeat': {
        'description': "The border-image-repeat CSS property defines how the middle part of a border image is handled so that it can match the size of the border. It has a one-value syntax that describes the behavior of all the sides, and a two-value syntax that sets a different value for the horizontal and vertical behavior.",
        'values': {
            'stretch': "Keyword indicating that the image must be stretched to fill the gap between the two borders.",
            'repeat': "Keyword indicating that the image must be repeated until it fills the gap between the two borders.",
            'round': "Keyword indicating that the image must be repeated until it fills the gap between the two borders. If the image doesn't fit after being repeated for an integral number of times, the image is rescaled to fit.",
            "inherit": ""
        }
    },
    
    'border-bottom-left-radius': {
        'description': "The border-bottom-left-radius CSS property sets the rounding of the bottom-left corner of the element. The rounding can be a circle or an ellipse, or if one of the value is 0 no rounding is done and the corner is square.",
        'values': {},
    },
    'border-bottom-right-radius': {
        'description': "The border-bottom-right-radius CSS property sets the rounding of the bottom-right corner of the element. The rounding can be a circle or an ellipse, or if one of the value is 0 no rounding is done and the corner is square.",
        'values': {}
    },

    'border-image': {
        'description': "The border-image CSS property allows drawing an image on the borders of elements. This makes drawing complex looking widgets much simpler than it has been and removes the need for nine boxes in some cases. The border-image is used instead of the border styles given by the border-style properties.",
        'values': {
            'url(': "",
            '<height>': "",
            '<width>': "",
            'type': "One of the stretch, repeat, round, or space keywords denoting how the image is treated both horizontally and vertically.",
            'horizontal': "One of the stretch, repeat, round, or space keywords denoting how the image is treated horizontally.",
            'vertical': "One of the stretch, repeat, round, or space keywords denoting how the image is treated vertically.",
            'stretch': "Keyword indicating that the image must be stretched to fill the gap between the two borders.",
            'repeat': "Keyword indicating that the image must be repeated until it fills the gap between the two borders.",
            'round': "Keyword indicating that the image must be repeated until it fills the gap between the two borders. If the image doesn't fit after being repeated for an integral number of times, the image is rescaled to fit.",
            'space': "Keyword indicating that the image must be tiled to fill the area. If the image doesn't fill the area with a whole number of tiles, the extra space is distributed around the tiles.",
            'inherit': "Keyword indicating that all four values are inherited from their parents' calculated element value."
        }
    },

    'border-radius': {
        'description': "The border-radius CSS property allows Web authors to define how rounded border corners are. The curve of each corner is defined using one or two radii, defining its shape: circle or ellipse. This property is a shorthand to set the four properties border-top-left-radius, border-top-right-radius, border-bottom-right-radius and border-bottom-left-radius.",
        'values': {}
    },

    'border-top-left-radius': {
        'description': "The border-top-left-radius CSS property sets the rounding of the top-left corner of the element. The rounding can be a circle or an ellipse, or if one of the value is 0 no rounding is done and the corner is square.",
        'values': {}
    },

    'border-top-right-radius': {
        'description': "The border-top-right-radius CSS property sets the rounding of the top-right corner of the element. The rounding can be a circle or an ellipse, or if one of the value is 0 no rounding is done and the corner is square.",
        'values': {}
    },

    'box-align': {
        'description': "The CSS box-align property specifies how an element aligns its contents across (perpendicular to) the direction of its layout. The effect of this is only visible if there is extra space in the box. See Flexbox for more about the properties of flexbox elements.",
        'values': {
            'start': "The box aligns contents at the start, leaving any extra space at the end.",
            'center': "The box aligns contents in the center, dividing any extra space equally between the start and the end.",
            'end': "The box aligns contents at the end, leaving any extra space at the start.",
            'baseline': "The box aligns the baselines of the contents (lining up the text). This only applies if the box's orientation is horizontal.",
            'stretch': "The box stretches the contents so that there is no extra space in the box."
        }
    },

    'box-decoration-break': {
        'description': "The box-decoration-break CSS property specifies how the background, padding, border, border-image, box-shadow, margin and clip of an element is applied when the box for the element is fragmented.  Fragmentation occurs when an inline box wraps onto multiple lines, or when a block spans more than one column inside a column layout container, or spans a page break when printed.  Each piece of the rendering for the element is called a fragment.",
        'values': {
            'slice': "The element is rendered as if its box were not fragmented, and then the rendering for this hypothetical box is sliced into pieces for each line/column/page. Note that the hypothetical box can be different for each fragment since it uses its own height if the break occurs in the inline direction, and its own width if the break occurs in the block direction. See the CSS specification for details.",
            'clone': "Each box fragment is rendered independently with the specified border, padding and margin wrapping each fragment. The border-radius, border-image and box-shadow, are applied to each fragment independently. The background is drawn independently in each fragment which means that a background image with background-repeat: no-repeat may be repeated multiple times."
        }
    },

    'box-shadow': {
        'description': "The box-shadow property describes one or more shadow effects as a comma-separated list. It enables you to cast a drop shadow from the frame of almost any element. If a border-radius is specified on the element with a box shadow, the box shadow takes on the same rounded corners. The z-ordering of multiple box shadows is the same as multiple text shadows (the first specified shadow is on top).",
        'values': {
            'inset': "If not specified (default), the shadow is assumed to be a drop shadow (as if the box were raised above the content).",
            '<offset-x>': '',
            '<offset-y>': '',
            '<blur-radius>': '',
            '<spread-radius>': '',
            '<color>': ''
        }
    },

    'box-sizing': {
        'description': 'The box-sizing property is used to alter the default CSS box model used to calculate widths and heights of elements. It is possible to use this property to emulate the behavior of browsers that do not correctly support the CSS box model specification.',
        'values': {
            'border-box': "The width and height properties include the padding and border, but not the margin. This is the box model used by Internet Explorer when the document is in Quirks mode.",
            'padding-box': "The width and height properties include the padding size, and do not include the border or margin.",
            'content-box': 'This is the default style as specified by the CSS standard. The width and height properties are measured including only the content, but not the padding, border or margin'
        }
    },

    'column-count': {
        'description': "The column-count CSS property describes the number of columns of the element.",
        'values': {
            '<integer>': "Is a strictly positive <integer> describing the ideal number of columns into which the content of the element will be flowed. If the column-width is also set to a non-auto value, it merely indicates the maximum allowed number of columns.",
            'auto': "Is a keyword indicating that the number of columns should be determined by other CSS properties, like column-width."
        }
    },

    'column-fill': {
        'description': 'The column-fill CSS property controls how contents are partitioned into columns. Contents are either balanced, which means that contents in all columns will have the same height or, when using auto, just take up the room the content needs.',
        'values': {
            'auto': 'Is a keyword indicating that columns are filled sequentially.',
            'balance': 'Is a keyword indicating that content is equally divided between columns.'
        }
    },

    'column-gap': {
        'description': "The column-gap CSS property sets the size of the gap between columns for elements which are specified to be displayed as multi-column elements.",
        'values': {
            'normal': "Is a keyword indicating to use the browser-defined default spacing between columns. The specification, and most modern browsers follow it, recommends this keyword to be equal to a length of 1em.",
            '<length>': "Is a <length> value defining the size of the gap between columns. It must not be negative, but may be equal to 0."
        }
    },

    'column-rule': {
        'description': 'In multi-column layouts, the column-rule CSS property specifies a straight line, or "rule", to be drawn between each column. It is a convenient shorthand to avoid setting each of the individual column-rule-* properties separately : column-rule-width, column-rule-style and column-rule-color.',
        'values': {
            '<length>': 'Is a <length> or one of the three keywords, thin, medium or thick.',
            '<border-style>': "",
            '<color>': ""
        }
    },

    'column-rule-color': {
        'description': 'The column-rule-color CSS property lets you set the color of the "rule" or line drawn between columns in multi-column layouts.',
        'values': {
            '<color>': ""
        }
    },

    'column-rule-style': {
        'description': "The column-rule-style CSS property lets you set the style of the rule drawn between columns in multi-column layouts.",
        'values': {
            "none": "",
            "hidden": "",
            "dotted": "",
            "dashed": "",
            "solid": "",
            "double": "",
            "groove": "",
            "ridge": "",
            "inset": "",
            "outset": ""
        }
    },

    'column-rule-width': {
        'description': "The column-rule-width CSS property lets you set the width of the rule drawn between columns in multi-column layouts.",
        'values': {
            "<length>": "",
            "thin": "",
            "medium": "",
            "thick": ""
        }
    },

    'column-span': {
        'description': 'The column-span CSS property makes it possible for an element to span across all columns when its value is set to all. An element that spans more than one column is called a spanning element.',
        'values': {
            'none': "The element does not span multiple columns.",
            'all': 'The element spans across all columns. Content in the normal flow that appears before the element is automatically balanced across all columns before the element appears. The element establishes a new block formatting context.'
        }
    },

    'column-width': {
        'description': 'The column-width CSS property suggests an optimal column width. This is not a absolute value, but a mere hint to the browser, which will adjust the width of the column around that suggested value, allowing to achieve scalable designs that fit different screen sizes.',
        'values': {
            '<length>': 'Is a <length> value giving a hint of the optimal width of the column. The actual column width may be wider (to fill the available space), or narrower (only if the available space is smaller than the specified column width). The length must be strictly positive or the declaration is invalid.',
            'auto': "Is a keyword indicating that the width of the column should be determined by other CSS properties, like column-count."
        }
    },

    'columns': {
        'description': "The columns CSS property is a shorthand property allowing to set both the column-width and the column-count properties at the same time.",
        'values': {
            '<column-width>': "Is a <length> value giving a hint of the optimal width of the column.",
            '<column-count>': "Is a strictly positive <integer> describing the ideal number of columns into which the content of the element will be flowed. If the column-width is also set to a non-auto value, it merely indicates the maximum allowed number of columns."
        }
    },
    
    'content': {
        'description': "The content CSS property is used with the ::before and ::after pseudo-elements to generate content in an element. Objects inserted using the content property are anonymous replaced elements.",
        'values': {
            "none": "",
            "normal": "",
            "<string>": "",
            "url(": "",
            "<counter>": "",
            "attr(": "",
            "open-quote": "",
            "no-open-quote": "",
            "close-quote": "",
            "no-close-quote": ""
        }
    },

    'dominant-baseline': {
        'description': "The dominant-baseline attribute is used to determine or re-determine a scaled-baseline-table. ",
        'values': {
            'alphabetic': "The dominant baseline-identifier is set to the 'alphabetic' baseline, the\nderived baseline-table is constructed using the 'alphabetic' baseline-table\nin the nominal font, and the baseline-table font-size is changed to the value\nof the 'font-size' property on this element. (The 'alphabetic' baseline is\nthe standard baseline for Roman scripts.)",
            'auto': "If this property occurs on a block or inline-block element, then the user\nagent behavior depends on the value of the 'script' property. If the value of the script\nproperty is 'auto, the 'auto' value is equivalent to 'alphabetic' for\nhorizontal 'writing-mode' values and 'central' for\nvertical 'writing-mode' values. If the value of the\nscript property is other than 'auto', the 'auto' value is equivalent to\n'use-script'",
            'central': "The dominant baseline-identifier is set to be 'central'. The derived\nbaseline-table is constructed from the defined baselines in a baseline-table\nin the nominal font. That font baseline-table is chosen using the following\npriority order of baseline-table names: 'ideographic', 'alphabetic',\n'hanging'and'mathematical'. The baseline-table is changed to the value of\nthe 'font-size' property on this element.",
            'hanging': "The dominant baseline-identifier is set to the 'hanging' baseline, the\nderived baseline- table is constructed using the 'hanging' baseline-table in\nthe nominal font, and the baseline-table font-size is changed to the value of\nthe 'font-size' property on this element.",
            'ideographic': "The dominant baseline-identifier is set to the 'ideographic' baseline,\nthe derived baseline- table is constructed using the 'ideographic'\nbaseline-table in the nominal font, and the baseline-table font-size is\nchanged to the value of the 'font-size' property on this element.",
            'mathematical': "The dominant baseline-identifier is set to the 'mathematical' baseline,\nthe derived baseline- table is constructed using the 'mathematical'\nbaseline-table in the nominal font, and the baseline-table font-size is\nchanged to the value of the 'font-size' property on this element.",
            'middle': "The dominant baseline-identifier is set to be 'middle'. The derived\nbaseline-table is constructed from the defined baselines in a baseline-table\nin the nominal font. That font baseline-table is chosen using the following\npriority order of baseline-table names: 'alphabetic', 'ideographic',\n'hanging'and'mathematical'. The baseline-table is changed to the value of\nthe 'font-size' property on this element.",
            'no-change': 'The dominant baseline-identifier, the baseline-table and the\nbaseline-table font-size remain the same as that of the parent.',
            'reset-size': "The dominant baseline-identifier and the baseline table remain the same,\nbut the baseline-table font-size is changed to the value of the 'font-size' property on this element. This\nre-scales the baseline table for the current 'font-size'.",
            'text-after-edge': "The dominant baseline-identifier is set to be 'text-after-edge'. The\nderived baseline-table is constructed from the defined baselines in a\nbaseline-table in the nominal font. That font baseline-table is chosen using\nthe following priority order of baseline-table names: 'alphabetic',\n'ideographic', 'hanging'and'mathematical'. The baseline-table is changed to\nthe value of the 'font-size' property on this element.",
            'text-before-edge': "The dominant baseline-identifier is set to be 'text-before-edge'. The\nderived baseline-table is constructed from the defined baselines in a\nbaseline-table in the nominal font. That font baseline-table is chosen using\nthe following priority order of baseline-table names: 'alphabetic',\n'ideographic', 'hanging'and'mathematical'. The baseline-table is changed to\nthe value of the 'font-size' property on this element.",
            'use-script': "The dominant baseline-identifier is set using the computed value of the 'script' property. The 'writing-mode' value, whether horizontal or vertical is used to select the baseline-table\nthat correspond to that baseline-identifier. The baseline-table font-size\ncomponent is set to the value of the 'font-size' property on this element."
        }
    },

    'object-fit': {
        'description': "The object-fit CSS property specifies how the contents of a replaced element should be fitted to the box established by its used height and width.",
        'values': {
            'fill': "The replaced content is sized to fill the element's content box: the object's concrete object size is the element's used width and height.",
            'contain': "The replaced content is sized to maintain its aspect ratio while fitting within the element's content box: its concrete object size is resolved as a contain constraint against the element's used width and height.",
            'cover': "The replaced content is sized to maintain its aspect ratio while filling the element's entire content box: its concrete object size is resolved as a cover constraint against the element's used width and height.",
            'none': "The replaced content is not resized to fit inside the element's content box: the object's concrete object size is determined using the default sizing algorithm with no specified size, and a default object size equal to the replaced element's used width and height.",
            'scale-down': "The content is sized as if none or contain were specified, whichever would result in a smaller concrete object size."
        }
    },
    
    'filter': {
        'description': "The filter property provides for effects like blurring or color shifting on an element's rendering before the element is displayed. Filters are commonly used to adjust the rendering of an image, a background, or a border.",
        'values': {
            "url(": "",
            "blur(": "",
            "brightness(": "",
            "contrast(": "",
            "drop-shadow(": "",
            "grayscale(": "",
            "hue-rotate(": "",
            "invert(": "",
            "opacity(": "",
            "saturate(": "",
            "sepia(": "",
        }
    },
    
    'font-stretch': {
        'description': "The font-stretch property selects a normal, condensed, or expanded face from a font.",
        'values': {
            'ultra-condensed': 'Specifies a font face that is the most condensed from normal.',
            'extra-condensed': 'Specifies a font face that is very condensed from normal.',
            'condensed': 'Specifies a font face that is the condensed from normal.',
            'semi-condensed': 'Specifies a font face that is slighly more condensed from normal.',
            'semi-expanded': 'Specifies a font face that is slighly more expanded from normal.',
            'expanded': 'Specifies a font face that is the expanded from normal.',
            'extra-expanded': 'Specifies a font face that is very expanded from normal.',
            'ultra-expanded': 'Specifies a font face that is the most expanded from normal.',
            'normal': 'Specifies a font face that is more condensed than normal.',
        }
    },

    'grid-columns': {
        'description': 'No info found',
        'values': {}
    },

    'grid-rows': {
        'description': 'No info found',
        'values': {}
    },

    'opacity': {
        'description': 'The opacity CSS property specifies the transparency of an element, that is, the degree to which the background behind the element is overlaid.',
        'values': {
            '<alphavalue>': 'Syntactically a <number>. The uniform opacity setting to be applied across an entire object. Any values outside the range 0.0 (fully transparent) to 1.0 (fully opaque) will be clamped to this range. If the object is a container element, then the effect is as if the contents of the container element were blended against the current background using a mask where the value of each pixel of the mask is <alphavalue>.'
        }
    },

    'outline-offset': {
        'description': "The outline-offset CSS property is used to set space between an outline and the edge or border of an element. An outline is a line that is drawn around elements, outside the border edge.",
        'values': {
            "<length>": "The width of the space."
        }
    },

    'overflow-x': {
        'description': "The overflow-x property specifies whether to clip content, render a scroll bar, or display overflow content of a block-level element, when it overflows at the left and right edges.",
        'values': {
            'auto': "The behavior of the 'auto' value is UA-dependent, but should cause a scrolling mechanism to be provided for overflowing boxes.",
            'hidden': 'This value indicates that the content is clipped and that no scrolling mechanism should be provided to view the content outside the clipping region.',
            'scroll': "This value indicates that the content is clipped and that if the user agent uses a scrolling mechanism that is visible on the screen (such as a scroll bar or a panner), that mechanism should be displayed for a box whether or not any of its content is clipped. This avoids any problem with scrollbars appearing and disappearing in a dynamic environment. When this value is specified and the target medium is 'print', overflowing content may be printed.",
            'visible': 'This value indicates that content is not clipped, i.e., it may be rendered outside the content box.'
        }
    },

    'overflow-y': {
        'description': "The overflow-y property specifies whether to clip content, render a scroll bar, or display overflow content of a block-level element, when it overflows at the top and bottom edges.",
        'values': {
            'auto': "The behavior of the 'auto' value is UA-dependent, but should cause a scrolling mechanism to be provided for overflowing boxes.",
            'hidden': 'This value indicates that the content is clipped and that no scrolling mechanism should be provided to view the content outside the clipping region.',
            'scroll': "This value indicates that the content is clipped and that if the user agent uses a scrolling mechanism that is visible on the screen (such as a scroll bar or a panner), that mechanism should be displayed for a box whether or not any of its content is clipped. This avoids any problem with scrollbars appearing and disappearing in a dynamic environment. When this value is specified and the target medium is 'print', overflowing content may be printed.",
            'visible': 'This value indicates that content is not clipped, i.e., it may be rendered outside the content box.'
        }
    },
        
    'perspective': {
        "description": "The perspective CSS property determines the distance between the z=0 plane and the user in order to give to the 3D-positioned element some perspective. Each 3D element with z>0 becomes larger; each 3D-element with z<0 becomes smaller. The strength of the effect is determined by the value of this property.",
        "values": {
            "none": "",
            "<length>": ""
        }
    },
        
    'perspective-origin': {
        'description': "The perspective-origin CSS property determines the position the viewer is looking at. It is used as the vanishing point by the perspective property.",
        'values': {
            '<x-position>': "",
            '<y-position>': ""
        }
    },
        
    'resize': {
        'description': "The resize CSS property lets you control the resizability of an element.",
        'values': {
            'none': "The element offers no user-controllable method for resizing the element.",
            'both': "The element displays a mechanism for allowing the user to resize the element, which may be resized both horizontally and vertically.",
            'horizontal': "The element displays a mechanism for allowing the user to resize the element, which may only be resized horizontally.",
            'vertical': "The element displays a mechanism for allowing the user to resize the element, which may only be resized vertically."
        }
    },

    'text-align-last': {
        'description': "The text-align-last CSS property describes how the last line of a block or a line, right before a forced line break, is aligned.",
        'values': {
            "auto": "The affected line is aligned per the value of text-align, unless text-align is justify, in which case the effect is the same as setting text-align-last to left.",
            "start": "The same as left if direction is left-to-right and right if direction is right-to-left.",
            "end": "The same as right if direction is left-to-right and left if direction is right-to-left.",
            "left": "The inline contents are aligned to the left edge of the line box.", 
            "right": "The inline contents are aligned to the right edge of the line box.",
            "center": "The inline contents are centered within the line box.",
            "justify": "The text is justified. Text should line up their left and right edges to the left and right content edges of the paragraph."
        }
    },
        
    'text-overflow': {
        'description': "The text-overflow property determines how overflowed content that is not displayed is signaled to users. It can be clipped, display an ellipsis ('...', U+2026 Horizontal Ellipsis), or display a custom string.",
        'values': {
            'clip': "This keyword value indicates to truncate the text at the limit of the content area, therefore the truncation can happen in the middle of a character.",
            'ellipsis': "This keyword value indicates to display an ellipsis ('...', U+2026 Horizontal Ellipsis) to represent clipped text. The ellipsis is displayed inside the content area, decreasing the amount of text displayed. If there is not enough space to display the ellipsis, it is clipped.",
            '<string>': "The <string> to be used to represent clipped text. The string is displayed inside the content area, shortening more the size of the displayed text. If there is not enough place to display the string itself, it is clipped.",
            "inherit": ""
        }
    },
    
    'transform': {
        'description': "The <transform-function> CSS data type denotes a function to apply to an element's representation in order to modify it. Usually such transform may be expressed by matrices and the resulting images can be determined using matrix multiplication on each point.",
        'values': {
            'matrix(': "",
            'matrix3d(': "",
            'perspective(': "",
            'rotate(': "",
            'rotate3d(': "",
            'rotateX(': "",
            'rotateY(': "",
            'rotateZ(': "",
            'scale(': "",
            'scale3d(': "",
            'scaleX(': "",
            'scaleY(': "",
            'scaleZ(': "",
            'skew(': "",
            'skewX(': "",
            'skewY(': "",
            'translate(': "",
            'translate3d(': "",
            'translateX(': "",
            'translateY(': "",
            'translateZ(': "",
        }
    },
    
    'transform-origin': {
        'description': "The transform-origin property lets you modify the origin for transformations of an element. For example, the transform-origin of the rotate() function is the centre of rotation. (This property is applied by first translating the element by the negated value of the property, then applying the element's transform, then translating by the property value.)",
        'values': {
            '<x-offset>': "",
            '<offset-keyword>': "",
            '<y-offset>': "",
            '<x-offset-keyword>': "",
            '<y-offset-keyword>': "",
            '<z-offset>': ""
        }
    },
    
    'transform-style': {
        'description': "The transform-style CSS property determines if the children of the element are positioned in the 3D-space or are flattened in the plane of the element.",
        'values': {
            "preserve-3d": "Indicates that the children of the element should be positioned in the 3D-space.",
            "flat": "Indicates that the children of the element are lying in the plane of the element itself."
        }
    },

    'transition': {
        'description': 'The CSS transition property is a shorthand property for transition-property, transition-duration, transition-timing-function, and transition-delay. It enables you to define the transition between two states of an element. Different states may be defined using pseudo-classes like :hover or :active or dynamically set using JavaScript.',
        'values': {
            'all': "",
            '<single-transition-property>': "",
            '<time>': "",
            'linear': "",
            'ease': "",
            'ease-in': "",
            'ease-out': "",
            'ease-in-out': "",
            "<time>": ""
        }
    },

    'transition-delay': {
        'description': 'The transition-delay property specifies the amount of time to wait between a change being requested to a property that is to be transitioned and the start of the transition effect.',
        'values': {
            "<time>": ""
        }
    },

    'transition-duration': {
        'description': "The transition-duration CSS property specifies the number of seconds or milliseconds a transition animation should take to complete. By default, the value is 0s, meaning that no animation will occur.",
        'values': {
            "<time>": ""
        }
    },

    'transition-property': {
        'description': "The transition-property CSS property is used to specify the names of CSS properties to which a transition effect should be applied.",
        'values': {
            "<single-transition-property>": "",
            "none": "No properties will transition.",
            "all": "All properties that can have an animated transition will do so.",
            "IDENT": "A string identifying the property to which a transition effect should be applied when its value changes. This identifier is composed by case-insensitive letter a to z, numbers 0 to 9, an underscore (_) or a dash(-). The first non-dash character must be a letter (that is no number at the beginning of it, even preceded by a dash). Also two dashes are forbidden at the beginning of the identifier."
        }
    },

    'transition-timing-function': {
        'description': "The transition-timing-function property is used to describe how the intermediate values of the CSS properties being affected by a transition effect are calculated. This in essence lets you establish an acceleration curve, so that the speed of the transition can vary over its duration.",
        'values': {
            'cubic-bezier': 'Specifies a cubic-bezier curve. The four values specify points P 1 and P 2 of the curve as (x1, y1, x2, y2). All values must be in the range [0, 1] or the definition is invalid.',
            'ease': 'The ease function is equivalent to cubic-bezier(0.25, 0.1, 0.25, 1.0).',
            'ease-in': 'The ease-in function is equivalent to cubic-bezier(0.42, 0, 1.0, 1.0).',
            'ease-in-out': 'The ease-in-out function is equivalent to cubic-bezier(0.42, 0, 0.58, 1.0)',
            'ease-out': 'The ease-out function is equivalent to cubic-bezier(0, 0, 0.58, 1.0).',
            'linear': 'The linear function is equivalent to cubic-bezier(0.0, 0.0, 1.0, 1.0).'
        }
    },

    'word-break': {
        'description': "The word-break CSS property is used to specify whether to break lines within words.",
        'values': {
            'break-all': "As for 'break-strict', except CJK scripts break according to the rules for 'loose'.",
            'keep-all': "Same as 'normal' for all non-CJK scripts. However, sequences of CJK characters can no longer break on implied break points. This option should only be used where the presence of white space characters still creates line-breaking opportunities, as in Korean.",
            'normal': 'Breaks non-CJK scripts according to their own rules while using a strict set of line breaking restrictions for CJK scripts (Hangul, Japanese Kana, and CJK ideographs).'
        }
    },

    'word-wrap': {
        'description': "The word-wrap property is used to specify whether or not the browser may break lines within words in order to prevent overflow when an otherwise unbreakable string is too long to fit in its containing box.",
        'values': {
            'break-word': 'An unbreakable "word" may be broken at an arbitrary point if there are no otherwise-acceptable break points in the line. Shaping characters are still shaped as if the word were not broken, and grapheme clusters must together stay as one unit.',
            'normal': 'Lines may break only at allowed break points.'
        }
    },
    
    'word-spacing': {
        "description": "The word-spacing property specifies spacing behavior between tags and words.",
        'values': {
            "normal": "The normal inter-word space, as defined by the current font and/or the browser.",
            "<font-size>": ""
        }
    }
}






CSS3_SPECIFIC_ATTRS_DICT = {}
CSS3_SPECIFIC_CALLTIP_DICT = {}
for attr, details in CSS3_DATA.items():
    values = details.get("values", {})
    attr_completions = sorted(values.keys())
    if attr_completions:
        CSS3_SPECIFIC_ATTRS_DICT[attr] = attr_completions
    else:
        CSS3_SPECIFIC_ATTRS_DICT[attr] = []
    description = details.get("description")
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
        CSS3_SPECIFIC_CALLTIP_DICT[attr] = "\n".join(desc_lines).encode("ascii", 'replace')

removed_css2_items = ["azimuth", "clip", "pointer-events"]

maybe_removed_css2_items = [
    "border-collapse", "border-spacing", "bottom",
    "direction", "elevation", "empty-cells", "left", "marker-offset",
    "pitch", "pitch-range", "play-during", "position",
    "richness", "right","speak-header", "speak-numeral",
    "speak-punctuation", "speech-rate", "stress",
    "table-layout", "text-transform", "top",
    "unicode-bidi", "volume", "z-index",
]

CSS_ATTR_DICT = CSS1_SPECIFIC_ATTRS_DICT.copy()
CSS_ATTR_DICT.update(CSS2_SPECIFIC_ATTRS_DICT)
CSS_ATTR_DICT.update(CSS3_SPECIFIC_ATTRS_DICT)

CSS_PROPERTY_ATTRIBUTE_CALLTIPS_DICT = CSS1_SPECIFIC_CALLTIP_DICT.copy()
CSS_PROPERTY_ATTRIBUTE_CALLTIPS_DICT.update(CSS2_SPECIFIC_CALLTIP_DICT)
CSS_PROPERTY_ATTRIBUTE_CALLTIPS_DICT.update(CSS3_SPECIFIC_CALLTIP_DICT)

# Remove the css 2 properties that are no longer in css 3.
for name in removed_css2_items:
    CSS_ATTR_DICT.pop(name, None)
    CSS_PROPERTY_ATTRIBUTE_CALLTIPS_DICT.pop(name, None)

for property, calltip in CSS_PROPERTY_ATTRIBUTE_CALLTIPS_DICT.items():
    if property not in CSS3_SPECIFIC_CALLTIP_DICT:
        if property in CSS2_SPECIFIC_CALLTIP_DICT:
            calltip += "\n(CSS2, CSS3)"
        else:
            calltip += "\n(CSS1, CSS2, CSS3)"
    else:
        calltip += "\n(CSS3)"
    CSS_PROPERTY_ATTRIBUTE_CALLTIPS_DICT[property] = calltip



# Note: The CSS3 color names below are not used yet.
css3_color_names = [
    'aliceblue',
    'antiquewhite',
    'aqua',
    'aquamarine',
    'azure',
    'beige',
    'bisque',
    'black',
    'blanchedalmond',
    'blue',
    'blueviolet',
    'brown',
    'burlywood',
    'cadetblue',
    'chartreuse',
    'chocolate',
    'coral',
    'cornflowerblue',
    'cornsilk',
    'crimson',
    'cyan',
    'darkblue',
    'darkcyan',
    'darkgoldenrod',
    'darkgray',
    'darkgreen',
    'darkgrey',
    'darkkhaki',
    'darkmagenta',
    'darkolivegreen',
    'darkorange',
    'darkorchid',
    'darkred',
    'darksalmon',
    'darkseagreen',
    'darkslateblue',
    'darkslategray',
    'darkslategrey',
    'darkturquoise',
    'darkviolet',
    'deeppink',
    'deepskyblue',
    'dimgray',
    'dimgrey',
    'dodgerblue',
    'firebrick',
    'floralwhite',
    'forestgreen',
    'fuchsia',
    'gainsboro',
    'ghostwhite',
    'gold',
    'goldenrod',
    'gray',
    'green',
    'greenyellow',
    'grey',
    'honeydew',
    'hotpink',
    'indianred',
    'indigo',
    'ivory',
    'khaki',
    'lavender',
    'lavenderblush',
    'lawngreen',
    'lemonchiffon',
    'lightblue',
    'lightcoral',
    'lightcyan',
    'lightgoldenrodyellow',
    'lightgray',
    'lightgreen',
    'lightgrey',
    'lightpink',
    'lightsalmon',
    'lightseagreen',
    'lightskyblue',
    'lightslategray',
    'lightslategrey',
    'lightsteelblue',
    'lightyellow',
    'lime',
    'limegreen',
    'linen',
    'magenta',
    'maroon',
    'mediumaquamarine',
    'mediumblue',
    'mediumorchid',
    'mediumpurple',
    'mediumseagreen',
    'mediumslateblue',
    'mediumspringgreen',
    'mediumturquoise',
    'mediumvioletred',
    'midnightblue',
    'mintcream',
    'mistyrose',
    'moccasin',
    'navajowhite',
    'navy',
    'oldlace',
    'olive',
    'olivedrab',
    'orange',
    'orangered',
    'orchid',
    'palegoldenrod',
    'palegreen',
    'paleturquoise',
    'palevioletred',
    'papayawhip',
    'peachpuff',
    'per',
    'pink',
    'plum',
    'powderblue',
    'purple',
    'red',
    'rosybrown',
    'royalblue',
    'saddlebrown',
    'salmon',
    'sandybrown',
    'seagreen',
    'seashell',
    'sienna',
    'silver',
    'skyblue',
    'slateblue',
    'slategray',
    'slategrey',
    'snow',
    'springgreen',
    'steelblue',
    'tan',
    'teal',
    'thistle',
    'tomato',
    'turquoise',
    'violet',
    'wheat',
    'white',
    'whitesmoke',
    'yellow',
    'yellowgreen',
]

# Add the css3 named colors.
#from codeintel2.util import CompareNPunctLast
#for attr, values in CSS_ATTR_DICT.items():
#    if '#' in values or 'rbg(' in values:
#        CSS_ATTR_DICT[attr] = sorted(values + css3_color_names,
#                                     cmp=CompareNPunctLast)
