"""
u1_process_mapping.py
=====================================================================
Bảng ánh xạ Process settings: Bambu Studio  ->  Snapmaker Orca (U1)

Nguồn dữ liệu: đối chiếu trực tiếp src/libslic3r/PrintConfig.cpp của
  - bambulab/BambuStudio        (master)
  - Snapmaker/OrcaSlicer        (main)

Nguyên tắc:
  1. Chỉ chuyển các key TỒN TẠI Ở CẢ HAI (98 key số/bool + enum).
  2. KHÔNG chuyển: key máy/hardware, filament_*, travel_speed (giới hạn U1).
  3. Enum: validate theo whitelist U1; map chuỗi nội bộ khác nhau.
  4. Vài key phải ĐỔI TÊN (Bambu key != U1 key).
  5. only_one_wall_top: chuyển ĐỔI KIỂU (Bambu enum -> U1 bool).
=====================================================================
"""

# ---------------------------------------------------------------------------
# (A) PROCESS_KEYS — các key có ở CẢ HAI bên, tên GIỐNG NHAU (copy thẳng)
#     Đã loại travel_speed và mọi key hardware/filament.
# ---------------------------------------------------------------------------
PROCESS_KEYS = {
    # --- Quality ---
    'layer_height', 'initial_layer_print_height', 'line_width', 'initial_layer_line_width',
    'outer_wall_line_width', 'inner_wall_line_width', 'top_surface_line_width',
    'sparse_infill_line_width', 'internal_solid_infill_line_width', 'support_line_width',
    'seam_position', 'seam_gap', 'wipe_speed',
    'slice_closing_radius', 'resolution', 'xy_hole_compensation', 'xy_contour_compensation',
    'elefant_foot_compensation', 'precise_z_height', 'ironing_type', 'wall_generator',
    'wall_sequence', 'is_infill_first', 'top_solid_infill_flow_ratio',
    'only_one_wall_first_layer', 'detect_overhang_wall',
    # --- Strength ---
    'wall_loops', 'alternate_extra_wall', 'detect_thin_wall', 'top_surface_pattern',
    'top_shell_layers', 'top_shell_thickness', 'bottom_surface_pattern', 'bottom_shell_layers',
    'bottom_shell_thickness', 'sparse_infill_density', 'fill_multiline', 'sparse_infill_pattern',
    'infill_direction', 'internal_solid_infill_pattern', 'filter_out_gap_fill', 'infill_wall_overlap',
    'minimum_sparse_infill_area', 'infill_combination', 'detect_narrow_internal_solid_infill',
    'ensure_vertical_shell_thickness',
    # --- Speed --- (KHÔNG có travel_speed)
    'initial_layer_speed', 'initial_layer_infill_speed',
    'outer_wall_speed', 'inner_wall_speed', 'small_perimeter_speed', 'small_perimeter_threshold',
    'sparse_infill_speed', 'internal_solid_infill_speed', 'top_surface_speed', 'gap_infill_speed',
    'enable_overhang_speed', 'overhang_1_4_speed', 'overhang_2_4_speed', 'overhang_3_4_speed',
    'overhang_4_4_speed', 'bridge_speed',
    # LƯU Ý: toàn bộ nhóm *_acceleration KHÔNG chuyển - giữ default U1
    # (gia tốc tune theo cơ khí từng máy, xem U1_ONLY_KEEP_DEFAULT)
    # --- Support ---
    'enable_support', 'support_type', 'support_style', 'support_threshold_angle',
    'support_on_build_plate_only', 'support_remove_small_overhang', 'raft_first_layer_density',
    'raft_first_layer_expansion', 'raft_layers', 'support_top_z_distance', 'support_bottom_z_distance',
    'support_base_pattern', 'support_base_pattern_spacing', 'support_angle',
    'support_interface_top_layers', 'support_interface_bottom_layers', 'support_interface_pattern',
    'support_interface_spacing', 'support_bottom_interface_spacing', 'support_expansion',
    'support_object_xy_distance', 'support_object_first_layer_gap', 'bridge_no_support',
    'tree_support_wall_count',
    # --- Other / bed adhesion ---
    'skirt_loops', 'skirt_height', 'skirt_distance', 'brim_type', 'brim_width', 'brim_object_gap',
    # --- Bổ sung (trước đây bị bỏ sót) ---
    # Quality / Precision
    'enable_arc_fitting', 'reduce_crossing_wall', 'max_travel_detour_distance',
    'precise_outer_wall',
    # Ironing
    'ironing_pattern', 'ironing_inset', 'ironing_flow', 'ironing_spacing', 'ironing_speed',
    # Fuzzy skin
    'fuzzy_skin', 'fuzzy_skin_thickness', 'fuzzy_skin_point_distance', 'fuzzy_skin_first_layer',
    # Bridge
    'max_bridge_length', 'bridge_flow', 'thick_bridges',
    # Scarf/seam slope
    'seam_slope_type', 'seam_slope_conditional', 'seam_slope_inner_walls',
    'seam_slope_min_length', 'seam_slope_start_height', 'seam_slope_entire_loop',
    'seam_slope_steps', 'scarf_angle_threshold',
    # Infill nâng cao (crosshatch/lockedzag)
    'skeleton_infill_density', 'skin_infill_density',
    'skeleton_infill_line_width', 'skin_infill_line_width',
    'infill_lock_depth', 'infill_shift_step',
    # Strength / shells
    'interface_shells',
    # Support
    'support_speed', 'support_interface_speed', 'independent_support_layer_height',
    'support_ironing_pattern', 'support_ironing_spacing', 'support_ironing_flow',
}

# ---------------------------------------------------------------------------
# (B) RENAME_MAP — Bambu key  ->  U1 key  (cùng nghĩa & cùng kiểu, khác tên)
#     Giá trị copy thẳng, chỉ đổi tên key.
# ---------------------------------------------------------------------------
RENAME_MAP = {
    'sparse_infill_anchor':      'infill_anchor',            # Sparse infill anchor length
    'sparse_infill_anchor_max':  'infill_anchor_max',        # Max length of infill anchor
    'sparse_infill_lattice_angle_1': 'lateral_lattice_angle_1',  # Bambu 2dlattice -> U1 lateral-lattice
    'sparse_infill_lattice_angle_2': 'lateral_lattice_angle_2',
    'role_base_wipe_speed':      'role_based_wipe_speed',    # Role-based wipe speed (lưu ý chữ 'd')
    'enable_support_ironing':    'support_ironing',          # Enable support ironing
    # tree_support_wall_count: cùng tên -> đã nằm trong PROCESS_KEYS
}

# ---------------------------------------------------------------------------
# (C) ENUM_WHITELIST — option HỢP LỆ của U1 cho từng key enum
#     (chuỗi nội bộ chính xác từ Snapmaker OrcaSlicer PrintConfig.cpp)
# ---------------------------------------------------------------------------
_SURFACE_PATTERNS = {
    'monotonic', 'monotonicline', 'rectilinear', 'alignedrectilinear',
    'concentric', 'hilbertcurve', 'archimedeanchords', 'octagramspiral',
}
ENUM_WHITELIST = {
    'sparse_infill_pattern': {
        'rectilinear', 'alignedrectilinear', 'zigzag', 'crosszag', 'lockedzag', 'line',
        'grid', 'triangles', 'tri-hexagon', 'cubic', 'adaptivecubic', 'quartercubic',
        'supportcubic', 'lightning', 'honeycomb', '3dhoneycomb', 'lateral-honeycomb',
        'lateral-lattice', 'crosshatch', 'tpmsd', 'tpmsfk', 'gyroid', 'concentric',
        'hilbertcurve', 'archimedeanchords', 'octagramspiral',
    },
    'top_surface_pattern':           _SURFACE_PATTERNS,
    'bottom_surface_pattern':        _SURFACE_PATTERNS,
    'internal_solid_infill_pattern': _SURFACE_PATTERNS,
    'seam_position':      {'nearest', 'aligned', 'aligned_back', 'back', 'random'},
    'wall_sequence':      {'inner wall/outer wall', 'outer wall/inner wall', 'inner-outer-inner wall'},
    'wall_generator':     {'classic', 'arachne'},
    'ironing_type':       {'no ironing', 'top', 'topmost', 'solid'},
    'support_type':       {'normal(auto)', 'tree(auto)', 'normal(manual)', 'tree(manual)'},
    'support_style':      {'default', 'grid', 'snug', 'organic', 'tree_slim', 'tree_strong', 'tree_hybrid'},
    'support_base_pattern':      {'default', 'rectilinear', 'rectilinear-grid', 'honeycomb', 'lightning', 'hollow'},
    'support_interface_pattern': {'auto', 'rectilinear', 'concentric', 'rectilinear_interlaced', 'grid'},
    'brim_type':          {'auto_brim', 'brim_ears', 'painted', 'outer_only', 'inner_only', 'outer_and_inner', 'no_brim'},
    'fuzzy_skin':         {'none', 'external', 'all', 'allwalls'},
    'ironing_pattern':         {'rectilinear', 'concentric'},
    'support_ironing_pattern': {'rectilinear', 'concentric'},
    'seam_slope_type':         {'none', 'external', 'all'},
}

# ---------------------------------------------------------------------------
# (D) ENUM_MAP — chuỗi Bambu -> chuỗi U1 (cùng nghĩa, khác chuỗi nội bộ)
# ---------------------------------------------------------------------------
ENUM_MAP = {
    'sparse_infill_pattern':         {'zig-zag': 'zigzag',          # Bambu 'zig-zag' -> U1 'zigzag'
                                      '2dlattice': 'lateral-lattice'},  # Bambu '2D Lattice' -> U1 'Lateral Lattice'
    'top_surface_pattern':           {'zig-zag': 'monotonic'},     # U1 ko có zig-zag cho surface
    'bottom_surface_pattern':        {'zig-zag': 'monotonic'},
    'internal_solid_infill_pattern': {'zig-zag': 'monotonic'},
    'ironing_pattern':               {'zig-zag': 'rectilinear'},  # U1 ko có zig-zag cho ironing
    'support_ironing_pattern':       {'zig-zag': 'rectilinear'},
    'support_style':                 {'tree_organic': 'organic'},
    'fuzzy_skin':                    {'disabled_fuzzy': 'none'},
}

# ---------------------------------------------------------------------------
# (E) DROP_KEYS — có ở U1 nhưng KHÔNG có tương đương Bambu (giữ default U1)
#     Chỉ liệt kê để tài liệu hoá; converter đơn giản là không đụng tới.
# ---------------------------------------------------------------------------
U1_ONLY_KEEP_DEFAULT = {
    'bottom_solid_infill_flow_ratio',   # Bambu chỉ có top_solid_infill_flow_ratio
    'min_width_top_surface',            # 'One wall threshold' - Bambu dùng cơ chế khác
    'initial_layer_travel_speed',
    # Toàn bộ nhóm Acceleration: giữ default U1 (tune theo cơ khí máy)
    'default_acceleration', 'outer_wall_acceleration', 'inner_wall_acceleration',
    'bridge_acceleration', 'sparse_infill_acceleration',
    'internal_solid_infill_acceleration', 'initial_layer_acceleration',
    'top_surface_acceleration', 'travel_acceleration',
    'accel_to_decel_enable', 'accel_to_decel_factor',
    # + toàn bộ nhóm U1-only: jerk_*, accel_to_decel, bridge_flow_ratio, TPMS,
    #   multimaterial/prime tower... KHÔNG ghi đè.
}


# ===========================================================================
# HÀM CHUYỂN ĐỔI
# ===========================================================================
def _scalarize(val):
    """
    Bambu lưu nhiều setting per-extruder dạng mảng, ví dụ outer_wall_speed=['200'].
    Snapmaker U1 (process_settings) dùng CHUỖI đơn: '200'.
    - Mảng -> lấy phần tử đầu.
    - Số (int/float/bool) -> chuỗi, vì U1 config lưu mọi giá trị dạng string.
    """
    if isinstance(val, list):
        val = val[0] if val else ''
    if isinstance(val, bool):
        return '1' if val else '0'
    if isinstance(val, (int, float)):
        # bỏ '.0' thừa cho số nguyên (3.0 -> '3')
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        return str(val)
    return val


def convert_enum(key, bambu_val):
    """Trả (u1_val, ok). ok=False -> giữ default template U1."""
    v = str(_scalarize(bambu_val)).strip()
    v = ENUM_MAP.get(key, {}).get(v, v)          # đổi chuỗi nếu cần
    allowed = ENUM_WHITELIST.get(key)
    if allowed is None:
        return v, True
    return (v, True) if v in allowed else (None, False)


def merge_process_settings(combined: dict, orig_settings: dict, logger=None) -> dict:
    """
    combined      : dict lấy từ template U1 (u1_settings.copy())
    orig_settings : dict project_settings.config của file Bambu
    Trả về combined đã merge các process setting hợp lệ.
    """
    def log(msg, *a):
        if logger:
            logger.info(msg, *a)

    # 1) Key cùng tên
    for k in PROCESS_KEYS:
        if k not in orig_settings:
            continue
        if k in ENUM_WHITELIST:
            val, ok = convert_enum(k, orig_settings[k])
            if ok:
                combined[k] = val
            else:
                log("Enum %s='%s' không được U1 hỗ trợ -> giữ default", k, orig_settings[k])
        else:
            combined[k] = _scalarize(orig_settings[k])

    # 2) Key phải đổi tên
    for b_key, u1_key in RENAME_MAP.items():
        if b_key in orig_settings:
            combined[u1_key] = _scalarize(orig_settings[b_key])

    # 3) only_one_wall_top: Bambu enum (top_one_wall_type) -> U1 bool
    if 'top_one_wall_type' in orig_settings:
        t = str(orig_settings['top_one_wall_type']).strip().lower()
        # 'none' -> tắt; 'top surfaces'/'topmost surface' -> bật
        combined['only_one_wall_top'] = '0' if t in ('none', '') else '1'

    return combined


# ===========================================================================
# (F) FALLBACK: bộ key chuẩn của process_settings_1.config (Snapmaker U1, Orca).
#     Dùng khi template U1 KHÔNG chứa sẵn process_settings_1.config -> app tự
#     dựng file này bằng cách lọc các key process từ project_settings đã merge.
# ===========================================================================
PROCESS_CONFIG_KEYS = {
    'accel_to_decel_enable', 'accel_to_decel_factor', 'align_infill_direction_to_model', 
    'alternate_extra_wall', 'bottom_shell_layers', 'bottom_shell_thickness', 
    'bottom_solid_infill_flow_ratio', 'bottom_surface_density', 'bottom_surface_pattern', 
    'bridge_acceleration', 'bridge_angle', 'bridge_density', 'bridge_flow', 'bridge_no_support', 
    'bridge_speed', 'brim_ears_detection_length', 'brim_ears_max_angle', 'brim_object_gap', 
    'brim_type', 'brim_width', 'calib_flowrate_topinfill_special_order', 'compatible_printers', 
    'compatible_printers_condition', 'counterbore_hole_bridging', 'default_acceleration', 
    'default_jerk', 'default_junction_deviation', 'delta_temperature', 
    'detect_narrow_internal_solid_infill', 'detect_overhang_wall', 'detect_thin_wall', 
    'dithering_local_z_infill', 'dithering_local_z_mode', 'dithering_local_z_whole_objects', 
    'dont_filter_internal_bridges', 'draft_shield', 'elefant_foot_compensation', 
    'elefant_foot_compensation_layers', 'enable_arc_fitting', 'enable_extra_bridge_layer', 
    'enable_overhang_speed', 'enable_prime_tower', 'enable_support', 'enforce_support_layers', 
    'ensure_vertical_shell_thickness', 'exclude_object', 'extra_perimeters_on_overhangs', 
    'extra_solid_infills', 'extrusion_rate_smoothing_external_perimeter_only', 'filename_format', 
    'fill_multiline', 'filter_out_gap_fill', 'flush_into_infill', 'flush_into_objects', 
    'flush_into_support', 'from', 'fuzzy_skin', 'fuzzy_skin_first_layer', 'fuzzy_skin_mode', 
    'fuzzy_skin_noise_type', 'fuzzy_skin_octaves', 'fuzzy_skin_persistence', 
    'fuzzy_skin_point_distance', 'fuzzy_skin_scale', 'fuzzy_skin_thickness', 'gap_fill_target', 
    'gap_infill_speed', 'gcode_add_line_number', 'gcode_comments', 'gcode_label_objects', 
    'hole_to_polyhole', 'hole_to_polyhole_threshold', 'hole_to_polyhole_twisted', 
    'independent_support_layer_height', 'infill_anchor', 'infill_anchor_max', 'infill_combination', 
    'infill_combination_max_layer_height', 'infill_direction', 'infill_jerk', 'infill_lock_depth', 
    'infill_overhang_angle', 'infill_shift_step', 'infill_wall_overlap', 'inherits', 
    'initial_layer_acceleration', 'initial_layer_infill_speed', 'initial_layer_jerk', 
    'initial_layer_line_width', 'initial_layer_min_bead_width', 'initial_layer_print_height', 
    'initial_layer_speed', 'initial_layer_travel_speed', 'inner_wall_acceleration', 
    'inner_wall_jerk', 'inner_wall_line_width', 'inner_wall_speed', 'interface_shells', 
    'interlocking_beam', 'interlocking_beam_layer_count', 'interlocking_beam_width', 
    'interlocking_boundary_avoidance', 'interlocking_depth', 'interlocking_orientation', 
    'internal_bridge_angle', 'internal_bridge_density', 'internal_bridge_flow', 
    'internal_bridge_speed', 'internal_solid_infill_acceleration', 
    'internal_solid_infill_line_width', 'internal_solid_infill_pattern', 
    'internal_solid_infill_speed', 'ironing_angle', 'ironing_flow', 'ironing_inset', 
    'ironing_pattern', 'ironing_spacing', 'ironing_speed', 'ironing_type', 'is_infill_first', 
    'lateral_lattice_angle_1', 'lateral_lattice_angle_2', 'layer_height', 'line_width', 
    'local_z_wipe_tower_purge_lines', 'make_overhang_printable', 'make_overhang_printable_angle', 
    'make_overhang_printable_hole_size', 'max_bridge_length', 'max_travel_detour_distance', 
    'max_volumetric_extrusion_rate_slope', 'max_volumetric_extrusion_rate_slope_segment_length', 
    'min_bead_width', 'min_feature_size', 'min_length_factor', 'min_skirt_length', 
    'min_width_top_surface', 'minimum_sparse_infill_area', 
    'mmu_segmented_region_interlocking_depth', 'mmu_segmented_region_max_width', 'name', 'notes', 
    'only_one_wall_first_layer', 'only_one_wall_top', 'ooze_prevention', 'outer_wall_acceleration', 
    'outer_wall_jerk', 'outer_wall_line_width', 'outer_wall_speed', 'overhang_1_4_speed', 
    'overhang_2_4_speed', 'overhang_3_4_speed', 'overhang_4_4_speed', 'overhang_reverse', 
    'overhang_reverse_internal_only', 'overhang_reverse_threshold', 'post_process', 
    'precise_outer_wall', 'precise_z_height', 'preheat_steps', 'preheat_time', 
    'prime_tower_brim_chamfer', 'prime_tower_brim_chamfer_max_width', 'prime_tower_brim_width', 
    'prime_tower_width', 'prime_volume', 'print_flow_ratio', 'print_order', 'print_sequence', 
    'print_settings_id', 'raft_contact_distance', 'raft_expansion', 'raft_first_layer_density', 
    'raft_first_layer_expansion', 'raft_layers', 'reduce_crossing_wall', 
    'reduce_infill_retraction', 'resolution', 'role_based_wipe_speed', 'scarf_angle_threshold', 
    'scarf_joint_flow_ratio', 'scarf_joint_speed', 'scarf_overhang_threshold', 'seam_gap', 
    'seam_position', 'seam_slope_conditional', 'seam_slope_entire_loop', 'seam_slope_inner_walls', 
    'seam_slope_min_length', 'seam_slope_start_height', 'seam_slope_steps', 'seam_slope_type', 
    'single_extruder_multi_material_priming', 'single_loop_draft_shield', 
    'skeleton_infill_density', 'skeleton_infill_line_width', 'skin_infill_density', 
    'skin_infill_depth', 'skin_infill_line_width', 'skirt_distance', 'skirt_height', 'skirt_loops', 
    'skirt_speed', 'skirt_start_angle', 'skirt_type', 'slice_closing_radius', 'slicing_mode', 
    'slow_down_layers', 'slowdown_for_curled_perimeters', 'small_area_infill_flow_compensation', 
    'small_area_infill_flow_compensation_model', 'small_perimeter_speed', 
    'small_perimeter_threshold', 'solid_infill_direction', 'solid_infill_filament', 
    'solid_infill_rotate_template', 'sparse_infill_acceleration', 'sparse_infill_density', 
    'sparse_infill_filament', 'sparse_infill_line_width', 'sparse_infill_pattern', 
    'sparse_infill_rotate_template', 'sparse_infill_speed', 'spiral_finishing_flow_ratio', 
    'spiral_mode', 'spiral_mode_max_xy_smoothing', 'spiral_mode_smooth', 
    'spiral_starting_flow_ratio', 'staggered_inner_seams', 'standby_temperature_delta', 
    'support_angle', 'support_base_pattern', 'support_base_pattern_spacing', 
    'support_bottom_interface_spacing', 'support_bottom_z_distance', 
    'support_critical_regions_only', 'support_expansion', 'support_filament', 
    'support_interface_bottom_layers', 'support_interface_filament', 
    'support_interface_loop_pattern', 'support_interface_not_for_body', 
    'support_interface_pattern', 'support_interface_spacing', 'support_interface_speed', 
    'support_interface_top_layers', 'support_ironing', 'support_ironing_flow', 
    'support_ironing_pattern', 'support_ironing_spacing', 'support_line_width', 
    'support_object_first_layer_gap', 'support_object_xy_distance', 'support_on_build_plate_only', 
    'support_remove_small_overhang', 'support_speed', 'support_style', 'support_threshold_angle', 
    'support_threshold_overlap', 'support_top_z_distance', 'support_type', 
    'symmetric_infill_y_axis', 'thick_bridges', 'thick_internal_bridges', 'timelapse_type', 
    'top_bottom_infill_wall_overlap', 'top_shell_layers', 'top_shell_thickness', 
    'top_solid_infill_flow_ratio', 'top_surface_acceleration', 'top_surface_density', 
    'top_surface_jerk', 'top_surface_line_width', 'top_surface_pattern', 'top_surface_speed', 
    'travel_acceleration', 'travel_jerk', 'travel_speed', 'travel_speed_z', 
    'tree_support_adaptive_layer_height', 'tree_support_angle_slow', 'tree_support_auto_brim', 
    'tree_support_branch_angle', 'tree_support_branch_angle_organic', 
    'tree_support_branch_diameter', 'tree_support_branch_diameter_angle', 
    'tree_support_branch_diameter_organic', 'tree_support_branch_distance', 
    'tree_support_branch_distance_organic', 'tree_support_brim_width', 'tree_support_tip_diameter', 
    'tree_support_top_rate', 'tree_support_wall_count', 'version', 'wall_direction', 
    'wall_distribution_count', 'wall_filament', 'wall_generator', 'wall_loops', 'wall_sequence', 
    'wall_transition_angle', 'wall_transition_filter_deviation', 'wall_transition_length', 
    'wipe_before_external_loop', 'wipe_on_loops', 'wipe_speed', 'wipe_tower_bridging', 
    'wipe_tower_cone_angle', 'wipe_tower_extra_flow', 'wipe_tower_extra_rib_length', 
    'wipe_tower_extra_spacing', 'wipe_tower_filament', 'wipe_tower_fillet_wall', 
    'wipe_tower_max_purge_speed', 'wipe_tower_no_sparse_layers', 'wipe_tower_rib_width', 
    'wipe_tower_rotation_angle', 'wipe_tower_wall_type', 'wiping_volumes_extruders', 
    'xy_contour_compensation', 'xy_hole_compensation', 
}


def build_process_settings(merged_project: dict) -> dict:
    """
    Dựng nội dung process_settings_1.config từ project_settings đã merge.
    Chỉ lấy các key thuộc PROCESS_CONFIG_KEYS và có mặt trong merged_project.
    Mọi giá trị được scalar-hoá (mảng->chuỗi, số->chuỗi) cho khớp định dạng U1.
    """
    out = {}
    for k in PROCESS_CONFIG_KEYS:
        if k in merged_project:
            v = merged_project[k]
            out[k] = _scalarize(v) if not isinstance(v, list) or len(v) <= 1 else _scalarize(v)
    # Metadata profile: giữ nguyên nếu project có, nếu không dùng giá trị an toàn.
    out['compatible_printers'] = merged_project.get(
        'compatible_printers', ['Snapmaker U1 0.4 nozzle'])
    out['compatible_printers_condition'] = merged_project.get(
        'compatible_printers_condition', '')
    out['inherits'] = merged_project.get('inherits', '')
    return out