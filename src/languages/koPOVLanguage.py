# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

from xpcom import components, ServerException

from koLanguageServiceBase import *

class koPOVLanguage(KoLanguageBase):
    name = "POVRay"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{51280a18-bb91-4be2-bd59-b96b3f63b386}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_POV_DEFAULT',),
        'keywords': ('SCE_POV_WORD2',
                     'SCE_POV_WORD3',
                     'SCE_POV_WORD4',
                     'SCE_POV_WORD5',
                     'SCE_POV_WORD6',
                     'SCE_POV_WORD7',
                     'SCE_POV_WORD8',),
        'identifiers': ('SCE_POV_IDENTIFIER',),
        'comments': ('SCE_POV_COMMENT',
                     'SCE_POV_COMMENTLINE',),
        'numbers': ('SCE_POV_NUMBER',),
        'strings': ('SCE_POV_STRING',),
        'stringeol': ('SCE_POV_STRINGEOL',),
        'operators': ('SCE_POV_OPERATOR',),
        'directives': ('SCE_POV_DIRECTIVE',),
        'directives_bad': ('SCE_POV_BADDIRECTIVE',),
        'labels': ('SCE_ADA_LABEL',),
        }

    defaultExtension = '.pov'
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_POV)
            self._lexer.supportsFolding = 1
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.setKeywords(3, self._keywords4)
            self._lexer.setKeywords(4, self._keywords5)
        return self._lexer
    
    _keywords = """declare local include undef fopen fclose read write default version 
        case range break debug error warning 
        if ifdef ifndef switch while macro else end""".split()
    
    # keywords2 is for Objects & CSG & Appearance (xxx {})
    _keywords2 = """camera light_source light_group
        object blob sphere cylinder box cone height_field julia_fractal
        lathe prism sphere_sweep superellipsoid sor text torus
        bicubic_patch disc mesh mesh2 polygon triangle smooth_triangle
        plane poly cubic quartic quadric isosurface parametric
        union intersection difference merge function array spline
        vertex_vectors normal_vectors uv_vectors face_indices normal_indices uv_indices
        texture texture_list interior_texture
        texture_map material_map image_map color_map colour_map pigment_map
        normal_map slope_map bump_map density_map
        pigment normal material interior finish reflection irid slope pigment_pattern image_pattern
        warp media scattering density background fog sky_sphere rainbow
        global_settings radiosity photons pattern
        transform looks_like projected_through contained_by clipped_by bounded_by""".split()
    
    # keywords3 is for Types & Modifiers & Items
    _keywords3 = """linear_spline quadratic_spline cubic_spline natural_spline bezier_spline b_spline
        read write append inverse open
        perspective orthographic fisheye ultra_wide_angle omnimax panoramic
        spherical spotlight jitter circular orient
        media_attenuation media_interaction shadowless parallel
        refraction collect pass_through global_lights hierarchy sturm smooth
        gif tga iff pot png pgm ppm jpeg tiff sys ttf
        quaternion hypercomplex linear_sweep conic_sweep
        type all_intersections split_union cutaway_textures
        no_shadow no_image no_reflection double_illuminate hollow
        uv_mapping all use_index use_color use_colour no_bump_scale
        conserve_energy fresnel
        average agate boxed bozo bumps cells crackle cylindrical density_file dents
        facets granite leopard marble onion planar quilted radial ripples spotted waves wood wrinkles
        solid use_alpha interpolate magnet noise_generator toroidal
        ramp_wave triangle_wave sine_wave scallop_wave cubic_wave poly_wave
        once map_type method fog_type hf_gray_16 charset ascii utf8
        rotate scale translate matrix location right up direction sky
        angle look_at aperture blur_samples focal_point confidence variance
        radius falloff tightness point_at area_light adaptive fade_distance fade_power
        threshold strength water_level tolerance max_iteration precision slice
        u_steps v_steps flatness inside_vector
        accuracy max_gradient evaluate max_trace precompute
        target ior dispersion dispersion_samples caustics
        color colour rgb rgbf rgbt rgbft red green blue filter transmit gray hf
        fade_color fade_colour quick_color quick_colour
        brick checker hexagon brick_size mortar bump_size
        ambient diffuse brilliance crand phong phong_size metallic specular
        roughness reflection_exponent exponent thickness
        gradient spiral1 spiral2 agate_turb form metric
        offset df3 coords size mandel exterior julia
        control0 control1 altitude turbulence octaves omega lambda
        repeat flip black-hole orientation dist_exp major_radius
        frequency phase intervals samples ratio absorption emission aa_threshold aa_level
        eccentricity extinction distance turb_depth fog_offset fog_alt width arc_angle falloff_angle
        adc_bailout ambient_light assumed_gamma irid_wavelength number_of_waves
        always_sample brigthness count error_bound gray_threshold load_file
        low_error_factor max_sample minimum_reuse nearest_count
        pretrace_end pretrace_start recursion_limit save_file
        spacing gather max_trace_level autostop expand_thresholds""".split()
            
    # keywords4 is for Predefined Identifiers
    _keywords4 = """x y z t u v
        yes no true false on off
        clock clock_delta clock_on final_clock final_frame frame_number
        image_height image_width initial_clock initial_frame pi version""".split()
    
    # keywords5 is for Predefined Functions
    _keywords5 = """abs acos acosh asc asin asinh atan atanh atan2
        ceil cos cosh defined degrees dimensions dimension_size div exp file_exists floor
        inside int ln log max min mod pow prod radians rand seed select sin sinh sqrt strcmp
        strlen sum tan tanh val vdot vlength min_extent max_extent trace vaxis_rotate
        vcross vrotate vnormalize vturbulence chr concat str strlwr strupr substr vstr
        sqr cube reciprocal pwr""".split()
