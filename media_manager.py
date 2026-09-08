"""
Media Manager - Handles temporary storage and Cloudinary uploads for complaint evidence.
Supports images (JPG, PNG, GIF, WebP) and videos (MP4, MOV, AVI, WebM).
Max 2 files per complaint, each up to 50 MB.
"""

import os
import uuid
import shutil
import cloudinary
import cloudinary.uploader
from config import Config

# Allowed extensions and their resource types
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.webm', '.mkv'}
ALLOWED_EXTS = IMAGE_EXTS | VIDEO_EXTS

MAX_FILES        = 2
MAX_FILE_BYTES   = 50 * 1024 * 1024   # 50 MB per file
TEMP_UPLOAD_DIR  = os.path.join('static', 'uploads', 'temp')


def _configure():
    cloudinary.config(
        cloud_name  = Config.CLOUDINARY_CLOUD_NAME,
        api_key     = Config.CLOUDINARY_API_KEY,
        api_secret  = Config.CLOUDINARY_API_SECRET,
        secure      = True,
    )


def is_cloudinary_configured() -> bool:
    return bool(Config.CLOUDINARY_CLOUD_NAME
                and Config.CLOUDINARY_API_KEY
                and Config.CLOUDINARY_API_SECRET)


def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTS


def save_temp_files(files) -> tuple[str, list[dict]]:
    """
    Save up to MAX_FILES uploaded FileStorage objects to a temp directory.
    Returns (temp_id, [{'path': ..., 'ext': ..., 'original_name': ...}, ...])
    """
    temp_id = str(uuid.uuid4())
    temp_dir = os.path.join(TEMP_UPLOAD_DIR, temp_id)
    os.makedirs(temp_dir, exist_ok=True)

    saved = []
    for i, f in enumerate(files[:MAX_FILES]):
        if not f or not f.filename:
            continue
        if not allowed_file(f.filename):
            continue
        ext = os.path.splitext(f.filename.lower())[1]
        dest = os.path.join(temp_dir, f'file_{i}{ext}')
        f.save(dest)
        # Enforce size limit after save
        if os.path.getsize(dest) > MAX_FILE_BYTES:
            os.remove(dest)
            continue
        saved.append({'path': dest, 'ext': ext, 'original_name': f.filename})

    return temp_id, saved


def upload_complaint_media(temp_id: str, ref_no: str) -> list[str]:
    """
    Upload temp files for a complaint to Cloudinary.
    Returns list of secure URLs. Cleans up temp files on success.
    Falls back to local static URLs if Cloudinary is not configured.
    """
    temp_dir = os.path.join(TEMP_UPLOAD_DIR, temp_id)
    if not os.path.isdir(temp_dir):
        return []

    files = sorted(os.listdir(temp_dir))
    if not files:
        _cleanup(temp_dir)
        return []

    if is_cloudinary_configured():
        return _upload_to_cloudinary(temp_dir, files, ref_no)
    else:
        return _serve_locally(temp_dir, files, ref_no)


def _upload_to_cloudinary(temp_dir: str, files: list, ref_no: str) -> list[str]:
    _configure()
    urls = []
    for filename in files:
        path = os.path.join(temp_dir, filename)
        ext  = os.path.splitext(filename)[1].lower()
        resource_type = 'video' if ext in VIDEO_EXTS else 'image'
        try:
            result = cloudinary.uploader.upload(
                path,
                folder        = f'complaints/{ref_no}',
                resource_type = resource_type,
                use_filename  = True,
                unique_filename = True,
            )
            url = result.get('secure_url', '')
            if url:
                urls.append(url)
        except Exception as e:
            print(f'[ERROR] Cloudinary upload failed for {filename}: {e}')
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
    _cleanup(temp_dir)
    return urls


def _serve_locally(temp_dir: str, files: list, ref_no: str) -> list[str]:
    """Fallback: move files to static/uploads/complaints/<ref_no>/ and return local URLs."""
    dest_dir = os.path.join('static', 'uploads', 'complaints', ref_no)
    os.makedirs(dest_dir, exist_ok=True)
    urls = []
    for filename in files:
        src = os.path.join(temp_dir, filename)
        dst = os.path.join(dest_dir, filename)
        shutil.move(src, dst)
        urls.append(f'/static/uploads/complaints/{ref_no}/{filename}')
    _cleanup(temp_dir)
    return urls


def cleanup_temp(temp_id: str):
    """Remove temp directory unconditionally (e.g., if user abandons flow)."""
    temp_dir = os.path.join(TEMP_UPLOAD_DIR, temp_id)
    _cleanup(temp_dir)


def _cleanup(directory: str):
    try:
        if os.path.isdir(directory):
            shutil.rmtree(directory)
    except Exception:
        pass


def get_media_type(url: str) -> str:
    """Return 'video' or 'image' based on URL extension or Cloudinary resource path."""
    ext = os.path.splitext(url.lower().split('?')[0])[1]
    if ext in VIDEO_EXTS:
        return 'video'
    # Cloudinary video URLs may have /video/ in path
    if '/video/' in url:
        return 'video'
    return 'image'
