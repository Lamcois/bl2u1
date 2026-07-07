import os
import sys
import zipfile
import re
import json
import uuid
import time
import logging
import posixpath
import tempfile
import webbrowser
import xml.etree.ElementTree as ET
from threading import Timer
from werkzeug.utils import secure_filename as _werkzeug_secure
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from u1_process_mapping import merge_process_settings, build_process_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resource_path(rel: str) -> str:
    """
    Trả về đường dẫn tuyệt đối tới file dữ liệu đi kèm.
    - Khi chạy dạng .py  : cạnh file app.py
    - Khi đóng gói PyInstaller onefile: trong thư mục tạm sys._MEIPASS
    """
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


app = Flask(
    __name__,
    template_folder=resource_path('templates'),
    static_folder=resource_path('static'),
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Uploads phải nằm ở nơi GHI ĐƯỢC (exe có thể đặt trong thư mục chỉ đọc)
UPLOAD_FOLDER            = os.path.join(tempfile.gettempdir(), 'bl2u1_uploads')
FILAMENT_PROFILES_FILE   = resource_path('filament_types.3mf')
TARGET_FILAMENTS         = 4     # U1 hardware supports 4 extruders
MAX_FILE_AGE_HOURS       = 8
DEFAULT_FILAMENT_PROFILE = 'Snapmaker PLA SnapSpeed @U1'

app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except OSError as e:
    raise RuntimeError(f"Cannot create upload directory: {e}") from e

_SESSION_RE = re.compile(r'^[0-9a-f]{32}$')
_COLOR_RE   = re.compile(r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$')

# Maps session_id -> original filename (without .3mf extension)
_session_names: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Filament profiles (loaded once at startup)
# ---------------------------------------------------------------------------
AVAILABLE_FILAMENTS: list[dict] = []
try:
    with zipfile.ZipFile(FILAMENT_PROFILES_FILE, 'r') as z:
        settings = json.loads(z.read('Metadata/project_settings.config').decode('utf-8'))
        for t, sid in zip(settings.get('filament_type', []), settings.get('filament_settings_id', [])):
            AVAILABLE_FILAMENTS.append({'type': t, 'settings_id': sid})
    logger.info("Loaded %d filament profiles", len(AVAILABLE_FILAMENTS))
except Exception as e:
    logger.warning("Could not load filament profiles (%s) -- using fallback defaults", e)
    AVAILABLE_FILAMENTS = [
        {'type': 'PLA',  'settings_id': DEFAULT_FILAMENT_PROFILE},
        {'type': 'PETG', 'settings_id': 'Snapmaker PETG HF'},
        {'type': 'ABS',  'settings_id': 'Generic ABS'},
        {'type': 'TPU',  'settings_id': 'Generic TPU'},
    ]

_VALID_TYPES = {f['type'] for f in AVAILABLE_FILAMENTS}

# ---------------------------------------------------------------------------
# Background cleanup (every hour instead of on every request)
# ---------------------------------------------------------------------------
def cleanup_old_files() -> None:
    now    = time.time()
    cutoff = MAX_FILE_AGE_HOURS * 3600
    try:
        for name in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, name)
            if os.path.isfile(path) and (now - os.path.getmtime(path)) > cutoff:
                os.remove(path)
                logger.debug("Deleted old upload: %s", name)
    except Exception as e:
        logger.error("Cleanup error: %s", e)


def _schedule_cleanup(interval: int = 3600) -> None:
    cleanup_old_files()
    # Also purge stale entries from _session_names
    for name in list(_session_names):
        path = _safe_path(f'{name}_input.3mf')
        if path is None or not os.path.exists(path):
            _session_names.pop(name, None)
    t = Timer(interval, _schedule_cleanup, [interval])
    t.daemon = True          # don't prevent process exit
    t.start()


_schedule_cleanup()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def normalize_color(color: str) -> str:
    if not color:
        return '#000000'
    c = color.lstrip('#')
    if len(c) == 8:
        c = c[:6]
    if len(c) != 6:
        return '#000000'
    try:
        int(c, 16)
    except ValueError:
        return '#000000'
    return f'#{c.upper()}'


def parse_bambu_filaments(filepath: str) -> list[dict]:
    filaments: list[dict] = []
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            names = z.namelist()
            if 'Metadata/slice_info.config' in names:
                root = ET.fromstring(z.read('Metadata/slice_info.config').decode('utf-8'))
                for fil in root.findall('.//filament'):
                    filaments.append({
                        'id':    fil.get('id'),
                        'color': normalize_color(fil.get('color', '')),
                        'type':  fil.get('type') or 'PLA',
                    })
            if not filaments and 'Metadata/project_settings.config' in names:
                cfg    = json.loads(z.read('Metadata/project_settings.config').decode('utf-8'))
                colors = cfg.get('filament_colour', [])
                types  = cfg.get('filament_type', [])
                for i, color in enumerate(colors):
                    filaments.append({
                        'id':    str(i + 1),
                        'color': normalize_color(color),
                        'type':  types[i] if i < len(types) else 'PLA',
                    })
    except Exception as e:
        logger.error("Error parsing filaments from %s: %s", filepath, e)
    return filaments


def _safe_path(filename: str) -> str | None:
    safe_dir  = os.path.realpath(UPLOAD_FOLDER)
    candidate = os.path.realpath(os.path.join(safe_dir, filename))
    return candidate if candidate.startswith(safe_dir + os.sep) else None

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(_e):
    return jsonify({'error': 'File is too large. Maximum size is 200 MB.'}), 413


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/filament-types')
def get_filament_types():
    return jsonify(AVAILABLE_FILAMENTS)


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not file.filename.lower().endswith('.3mf'):
        return jsonify({'error': 'Only .3mf files are accepted'}), 400

    # Store the original name (sanitised, without extension) for the download
    raw_name = file.filename.rsplit('.', 1)[0] if '.' in file.filename else file.filename
    safe_name = _werkzeug_secure(raw_name) or 'converted'

    session_id     = uuid.uuid4().hex          # 32 hex chars, full 128-bit entropy
    _session_names[session_id] = safe_name
    input_filename = f'{session_id}_input.3mf'
    filepath       = _safe_path(input_filename)
    if filepath is None:
        return jsonify({'error': 'Internal path error'}), 500

    file.save(filepath)

    # Validate ZIP magic bytes
    with open(filepath, 'rb') as f:
        magic = f.read(4)
    if magic != b'PK\x03\x04':
        os.remove(filepath)
        return jsonify({'error': 'Uploaded file is not a valid 3MF/ZIP archive'}), 400

    filaments = parse_bambu_filaments(filepath)
    return jsonify({'session_id': session_id, 'filaments': filaments})


@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON body'}), 400

    session_id = data.get('session_id', '')
    if not _SESSION_RE.fullmatch(session_id):
        return jsonify({'error': 'Invalid session ID'}), 400

    input_path  = _safe_path(f'{session_id}_input.3mf')
    output_path = _safe_path(f'{session_id}_U1_Ready.3mf')
    if input_path is None or output_path is None:
        return jsonify({'error': 'Internal path error'}), 500

    if not os.path.exists(input_path):
        return jsonify({'error': 'Session expired or file not found. Please re-upload.'}), 404

    user_colors = data.get('colors', {})
    if not isinstance(user_colors, dict):
        return jsonify({'error': '"colors" must be a JSON object'}), 400

    # Parse filaments once and reuse throughout
    original_filaments = parse_bambu_filaments(input_path)
    if not original_filaments:
        return jsonify({'error': 'Could not parse filaments from the uploaded file'}), 400

    valid_ids = {f['id'] for f in original_filaments}

    for fid, conf in user_colors.items():
        if fid not in valid_ids:
            return jsonify({'error': f'Unknown filament ID: {fid}'}), 400
        if not isinstance(conf, dict):
            return jsonify({'error': 'Each filament entry must be a JSON object'}), 400
        color = conf.get('color', '')
        ftype = conf.get('type', '')
        if not _COLOR_RE.match(color):
            return jsonify({'error': f'Invalid color: {color}'}), 400
        if ftype not in _VALID_TYPES:
            return jsonify({'error': f'Invalid filament type: {ftype}'}), 400

    # --- Đọc file gốc để lấy orig_settings và kiểm tra enable_support ---
    try:
        with zipfile.ZipFile(input_path, 'r') as z:
            orig_settings = json.loads(z.read('Metadata/project_settings.config').decode('utf-8'))
    except Exception as e:
        logger.error("Could not read project settings [%s]: %s", session_id, e)
        return jsonify({'error': 'Could not read project settings from the uploaded file'}), 500

    # Xác định hỗ trợ dựa trên key enable_support (có trong Bambu)
    has_support = str(orig_settings.get('enable_support', '0')) == '1'
    template    = resource_path('u1_template_supports.3mf' if has_support else 'u1_template.3mf')

    try:
        with zipfile.ZipFile(template, 'r') as z:
            tmpl_names  = set(z.namelist())
            u1_settings = json.loads(z.read('Metadata/project_settings.config').decode('utf-8'))
            # Snapmaker Orca reads the active Process from process_settings_1.config,
            # NOT from project_settings.config. Bambu files don't have this file,
            # so we must take it from the U1 template and inject the Bambu values.
            u1_process = None
            if 'Metadata/process_settings_1.config' in tmpl_names:
                u1_process = json.loads(
                    z.read('Metadata/process_settings_1.config').decode('utf-8'))
            # Extra U1-only members that the Bambu input lacks but Orca expects
            # (machine settings, process settings). Copy them verbatim.
            u1_extra_members = {}
            for nm in tmpl_names:
                if nm.startswith('Metadata/machine_settings') or \
                   nm.startswith('Metadata/process_settings'):
                    u1_extra_members[nm] = z.read(nm)
    except Exception as e:
        logger.error("Could not read template %s: %s", template, e)
        return jsonify({'error': 'Server template missing -- please contact the administrator'}), 500

    # ------------------------------------------------------------------
    # Build the modified archive
    # ------------------------------------------------------------------
    try:
        with zipfile.ZipFile(input_path, 'r') as zin, \
             zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:

            # ---- slice_info.config ----------------------------------------
            xml_str = zin.read('Metadata/slice_info.config').decode('utf-8')
            xml_str = re.sub(
                r'key="printer_model_id" value="[^"]*"',
                'key="printer_model_id" value="Snapmaker U1"',
                xml_str,
            )
            root = ET.fromstring(xml_str)

            # Thay đổi printer_settings_id của tất cả plate
            for plate in root.findall('.//plate'):
                if 'printer_settings_id' in plate.attrib:
                    plate.set('printer_settings_id', 'Snapmaker U1')

            filaments_parent = root.find('.//plate') or root

            # GIỮ NGUYÊN toàn bộ filament gốc (U1/Snapmaker Orca hỗ trợ
            # filament mapping lúc in nên project được phép >4 màu).
            # Không xóa, không pad, không đổi id -> dữ liệu sơn màu trên
            # mesh (mmu_segmentation) vẫn khớp tuyệt đối.
            # Chỉ áp thay đổi màu/loại cho filament người dùng chỉnh trong UI.
            for node in filaments_parent.findall('filament'):
                fid = node.get('id')
                if fid in user_colors:
                    conf = user_colors[fid]
                    node.set('color', conf['color'])
                    node.set('type',  conf['type'])

            modified_slice_info = ET.tostring(root, encoding='utf-8', xml_declaration=True)

            # ---- model_settings.config ------------------------------------
            # Id filament giữ nguyên nên KHÔNG cần remap extruder nữa.
            modified_model_settings = zin.read('Metadata/model_settings.config')

            # ---- project_settings.config ----------------------------------
            combined   = u1_settings.copy()
            new_colors: list[str] = []
            new_types:  list[str] = []

            # Giữ đủ MỌI filament gốc theo đúng thứ tự id.
            # Filament nào người dùng chỉnh thì lấy màu/loại mới,
            # còn lại giữ nguyên màu/loại ban đầu của file Bambu.
            for fil in original_filaments:
                fid = fil['id']
                if fid in user_colors:
                    color = user_colors[fid]['color']
                    ftype = user_colors[fid]['type']
                else:
                    color = fil['color']
                    ftype = fil['type']
                color = (color + 'FF') if len(color) == 7 else color  # ensure RGBA
                new_colors.append(color.upper())
                new_types.append(ftype)

            n_filaments = max(len(new_colors), 1)

            combined['filament_colour'] = new_colors
            combined['filament_type']   = new_types

            profile_map     = {f['type']: f['settings_id'] for f in AVAILABLE_FILAMENTS}
            default_profile = AVAILABLE_FILAMENTS[0]['settings_id'] if AVAILABLE_FILAMENTS else DEFAULT_FILAMENT_PROFILE
            combined['filament_settings_id'] = [
                profile_map.get(t, default_profile) for t in new_types
            ]

            # Normalise all filament_* arrays theo số filament thực tế
            # (template U1 thường chỉ có 4 phần tử -> nhân bản phần tử cuối
            #  khi project nhiều màu hơn, cắt bớt khi ít màu hơn)
            for key, val in combined.items():
                if key.startswith('filament_') and isinstance(val, list) and 0 < len(val) != n_filaments:
                    if len(val) < n_filaments:
                        val.extend([val[-1]] * (n_filaments - len(val)))
                    else:
                        combined[key] = val[:n_filaments]

            # ---- Merge Process settings from the Bambu file --------------
            combined = merge_process_settings(combined, orig_settings, logger=logger)

            # Đặt tên custom để Orca không ghi đè khi đổi máy
            custom_name = f"Converted_{session_id[:8]}"
            combined['print_settings_id'] = custom_name

            combined_bytes = json.dumps(combined, indent=4, ensure_ascii=False).encode('utf-8')

            # ---- Process settings_1.config --------------------------------
            if u1_process is not None:
                u1_process = merge_process_settings(u1_process, orig_settings, logger=logger)
            else:
                u1_process = build_process_settings(combined)
                logger.info("Template has no process_settings_1.config -> built one "
                            "with %d keys", len(u1_process))
            # Ghi đè tên để thành custom
            u1_process['name'] = custom_name
            process_bytes = json.dumps(
                u1_process, indent=4, ensure_ascii=False).encode('utf-8')
            u1_extra_members['Metadata/process_settings_1.config'] = process_bytes

            # ---- Copy all members, sanitising paths (Zip Slip defence) ----
            written = set()
            for item in zin.infolist():
                safe_name = posixpath.normpath(item.filename).lstrip('/')
                if safe_name.startswith('..'):
                    logger.warning("Skipping suspicious ZIP entry: %s", item.filename)
                    continue

                if item.filename == 'Metadata/project_settings.config':
                    zout.writestr(item, combined_bytes)
                elif item.filename == 'Metadata/slice_info.config':
                    zout.writestr(item, modified_slice_info)
                elif item.filename == 'Metadata/model_settings.config':
                    zout.writestr(item, modified_model_settings)
                elif item.filename in u1_extra_members:
                    # If the Bambu file somehow already has this name, prefer the
                    # merged U1 version.
                    zout.writestr(item, u1_extra_members[item.filename])
                else:
                    zout.writestr(item, zin.read(item.filename))
                written.add(item.filename)

            # ---- Add U1-only members that the Bambu input didn't contain -----
            for nm, data in u1_extra_members.items():
                if nm not in written:
                    zout.writestr(nm, data)

        return jsonify({
            'download_url': f'/download/{session_id}_U1_Ready.3mf',
            'download_name': f'{_session_names.get(session_id, "converted")}-U1.3mf',
        })

    except Exception as e:
        logger.error("Conversion error [%s]: %s", session_id, e, exc_info=True)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return jsonify({'error': 'Conversion failed. Please check your file and try again.'}), 500


@app.route('/download/<filename>')
def download_file(filename: str):
    # Strict allowlist: only session-prefixed output files
    if not re.fullmatch(r'[0-9a-f]{32}_U1_Ready\.3mf', filename):
        return jsonify({'error': 'Invalid filename'}), 400
    filepath = _safe_path(filename)
    if filepath is None or not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    # Use original filename if available
    session_id = filename[:32]
    download_name = f'{_session_names.get(session_id, "converted")}-U1.3mf'
    return send_file(filepath, as_attachment=True, download_name=download_name)


if __name__ == '__main__':
    frozen = getattr(sys, 'frozen', False)          # True khi chạy dạng .exe PyInstaller

    url = 'http://127.0.0.1:8080'
    print('\n  BambuLab -> Snapmaker U1 Converter')
    print(f'  Đang chạy tại: {url}')
    print('  Đóng cửa sổ này hoặc bấm Ctrl+C để tắt.\n')

    # Tự mở browser sau 1 giây (chỉ khi chạy dạng exe)
    if frozen:
        Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(debug=False, port=8080)