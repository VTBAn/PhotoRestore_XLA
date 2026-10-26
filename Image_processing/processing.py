"""Các thao tác xử lý ảnh cho PhotoRestore.

Mô-đun này không chứa thành phần giao diện. Những hàm có hậu tố [TC] là
phần sinh viên tự cài đặt theo yêu cầu bài tập lớn.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "Output"


def load_image(path: str | Path) -> QImage:
    """Đọc ảnh từ đĩa và trả về bản sao QImage độc lập."""
    return QImage(str(path)).copy()


def save_image_to_output(image: QImage, source_name: str = "photo") -> Path:
    """Lưu ảnh PNG vào Output/ và trả về đường dẫn tệp vừa tạo."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(source_name).stem or "photo"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = OUTPUT_DIR / f"{stem}_result_{timestamp}.png"
    if not image.save(str(target), "PNG"):
        raise OSError(f"Không thể lưu ảnh vào: {target}")
    return target


def image_info(image: QImage) -> dict[str, int | str]:
    """Trả về thông tin theo yêu cầu M1."""
    channels = max(1, image.depth() // 8)
    return {
        "width": image.width(),
        "height": image.height(),
        "channels": channels,
        "dtype": "uint8",
        "raw_bytes": image.width() * image.height() * channels,
    }


def convert_to_grayscale(image: QImage) -> QImage:
    """Chuyển ảnh xám bằng cv2.cvtColor (M1)."""
    bgr, is_gray = qimage_to_bgr(image)
    if is_gray:
        return image.copy()
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return bgr_to_qimage(gray, is_gray=True)


def crop_image(image: QImage, rect: QRect) -> QImage:
    """Cắt ảnh theo vùng chọn x1:y2, x1:x2 (M1)."""
    return image.copy(rect.intersected(image.rect()))


def resize_image(image: QImage, width: int, height: int) -> QImage:
    """Đổi kích thước bằng nội suy chất lượng cao."""
    return image.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)


def invert_image(image: QImage) -> QImage:
    """Âm bản M2: s = 255 - r."""
    result = image.copy()
    result.invertPixels()
    return result


def stretch_contrast(image: QImage, black: int, white: int) -> QImage:
    """Kéo giãn tương phản M2 và cắt kết quả trong khoảng [0, 255]."""
    if not 0 <= black < white <= 255:
        raise ValueError("Cần có 0 <= mức đen < mức trắng <= 255.")
    bgr, is_gray = qimage_to_bgr(image)
    result = np.clip((bgr.astype(np.float32) - black) * 255.0 / (white - black), 0, 255).astype(np.uint8)
    return bgr_to_qimage(result, is_gray)


def equalize_histogram_opencv(image: QImage) -> QImage:
    """Tạo kết quả tham chiếu bằng cv2.equalizeHist để so sánh với phần [TC]."""
    bgr, is_gray = qimage_to_bgr(image)
    if is_gray:
        return bgr_to_qimage(cv2.equalizeHist(bgr), is_gray=True)
    return bgr_to_qimage(cv2.merge([cv2.equalizeHist(channel) for channel in cv2.split(bgr)]), is_gray=False)


def apply_clahe(image: QImage, clip_limit: float, grid_size: int) -> QImage:
    """Cân bằng histogram thích nghi M2 bằng cv2.createCLAHE."""
    if not 1 <= clip_limit <= 5 or not 4 <= grid_size <= 16:
        raise ValueError("clipLimit phải trong [1, 5] và kích thước lưới trong [4, 16].")
    bgr, is_gray = qimage_to_bgr(image)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    if is_gray:
        return bgr_to_qimage(clahe.apply(bgr), is_gray=True)
    return bgr_to_qimage(cv2.merge([clahe.apply(channel) for channel in cv2.split(bgr)]), is_gray=False)


# ===== PHẦN [TC] - SINH VIÊN TỰ CÀI ĐẶT =====
def reduce_gray_levels(image: QImage, levels: int) -> Optional[QImage]:
    """M1: giảm mức xám còn L mức; trả về ảnh kết quả hoặc None."""
    return None


def log_transform(image: QImage) -> Optional[QImage]:
    """M2: s = c * log(1 + r); trả về ảnh kết quả hoặc None."""
    return None


def gamma_transform(image: QImage, gamma: float) -> Optional[QImage]:
    """M2: s = 255 * (r / 255)^gamma; trả về ảnh kết quả hoặc None."""
    return None


def equalize_histogram_manual(image: QImage) -> Optional[QImage]:
    """M2: cân bằng histogram thủ công theo CDF; trả về ảnh kết quả hoặc None."""
    return None


def qimage_to_bgr(image: QImage) -> tuple[np.ndarray, bool]:
    """Chuyển QImage sang mảng OpenCV BGR."""
    if image.format() == QImage.Format.Format_Grayscale8:
        gray = image.copy()
        data = np.frombuffer(gray.bits(), dtype=np.uint8).reshape(gray.height(), gray.bytesPerLine())
        return data[:, :gray.width()].copy(), True
    rgb = image.convertToFormat(QImage.Format.Format_RGB888)
    data = np.frombuffer(rgb.bits(), dtype=np.uint8).reshape(rgb.height(), rgb.bytesPerLine())
    rgb_array = data[:, :rgb.width() * 3].reshape(rgb.height(), rgb.width(), 3)
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR), False


def bgr_to_qimage(image: np.ndarray, is_gray: bool) -> QImage:
    """Chuyển ảnh OpenCV BGR hoặc xám về QImage."""
    if is_gray:
        return QImage(image.data, image.shape[1], image.shape[0], image.strides[0], QImage.Format.Format_Grayscale8).copy()
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888).copy()

#--------------------------------M3(Quân Bảo)--------------------------------
conssajsadjksadjlksad
sadjaklsdjaskjd
sdlsalkdjaslkdjsa
sadlksadjklaajajajajajjajajaa
sdklsakdlajdsakjdslka
asdsadasdadadsa
adadada
Falsefa
f
af
afa
fafaf
and


#----------------------------------------------------------------------------
als;faslf
à
á
fa
sd
fas
fwa
f
à
a
fe
áef