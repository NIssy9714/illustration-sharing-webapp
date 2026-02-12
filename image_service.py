"""
画像アップロード・検証・保存・サムネイル生成を行うサービスモジュール。

担当: 拡張子・MIME・Pillow 検証、保存、サムネイル生成。app.py の投稿処理から委譲される。
"""

import os
import uuid

from PIL import Image
from werkzeug.utils import secure_filename

# 許可する拡張子
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# デフォルトの画像サイズ上限（幅・高さ）
DEFAULT_MAX_DIMENSIONS = (4000, 4000)

# デフォルトのサムネイルサイズ
DEFAULT_THUMBNAIL_SIZE = (300, 300)


def allowed_file(filename: str) -> bool:
    """担当: 拡張子が許可リストに含まれるか判定する。"""
    if not filename or "." not in filename:
        return False
    file_extension = filename.rsplit(".", 1)[1].lower()
    return file_extension in ALLOWED_EXTENSIONS


def _verify_image(stream) -> Image.Image:
    """担当: Pillow で open + verify() により画像の正当性を検証し、検証済みの Image を返す。無効な場合は Exception。"""
    stream.seek(0)
    image = Image.open(stream)
    image.verify()
    stream.seek(0)
    return Image.open(stream)


def _ensure_saveable_mode(image: Image.Image) -> Image.Image:
    """担当: RGBA/P などを保存可能なモード（例: RGB）に変換する。"""
    if image.mode in ("RGBA", "P"):
        return image.convert("RGB")
    return image


def _save_image(image: Image.Image, filepath: str) -> None:
    """担当: 画像を指定パスに保存する（モード変換は _ensure_saveable_mode に委譲）。"""
    image_to_save = _ensure_saveable_mode(image)
    image_to_save.save(filepath)


def create_thumbnail(
    image: Image.Image,
    thumbnail_dir: str,
    filename: str,
    size: tuple[int, int] = DEFAULT_THUMBNAIL_SIZE,
) -> None:
    """担当: 指定サイズのサムネイルを生成し thumbnail_dir に保存する。"""
    os.makedirs(thumbnail_dir, exist_ok=True)
    thumbnail_path = os.path.join(thumbnail_dir, filename)
    thumb = image.copy()
    thumb.thumbnail(size)
    if thumb.mode in ("RGBA", "P"):
        thumb = thumb.convert("RGB")
    thumb.save(thumbnail_path)


def process_uploaded_image(
    file_storage,
    upload_base_dir: str = "static/uploads",
    max_dimensions: tuple[int, int] = DEFAULT_MAX_DIMENSIONS,
    thumbnail_size: tuple[int, int] = DEFAULT_THUMBNAIL_SIZE,
) -> tuple[str | None, str | None]:
    """担当: アップロード画像の検証・保存・サムネイル生成を一括で行う。成功時 (ファイル名, None)、失敗時 (None, エラーメッセージ)。"""
    if file_storage is None:
        return None, "画像ファイルが選択されていません"

    filename_original = getattr(file_storage, "filename", "") or ""
    if not filename_original.strip():
        return None, "画像ファイルが選択されていません"

    if not allowed_file(filename_original):
        return None, "画像ファイル（png,jpg,jpeg,gif,webp）をアップロードしてください"

    mimetype = getattr(file_storage, "content_type", None) or getattr(
        file_storage,
        "mimetype",
        None,
    )
    if not (mimetype and mimetype.startswith("image/")):
        return None, "画像ファイルをアップロードしてください"

    safe_name = secure_filename(filename_original)
    _, ext = os.path.splitext(safe_name)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_base_dir, filename)

    try:
        image = _verify_image(file_storage.stream)
    except Exception:
        return None, "有効な画像ファイルをアップロードしてください"

    max_w, max_h = max_dimensions
    if image.width > max_w or image.height > max_h:
        return None, f"画像のサイズが大きすぎます（最大 {max_w}x{max_h}）。"

    os.makedirs(upload_base_dir, exist_ok=True)

    try:
        _save_image(image, filepath)
    except Exception:
        return None, "有効な画像ファイルをアップロードしてください"

    thumbnail_dir = os.path.join(upload_base_dir, "thumbs")
    try:
        create_thumbnail(image, thumbnail_dir, filename, thumbnail_size)
    except Exception:
        pass  # サムネイル失敗は無視（本体は保存済み）

    return filename, None
