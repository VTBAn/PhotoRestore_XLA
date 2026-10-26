import cv2
import numpy as np

from PySide6.QtGui import QImage

from .processing import qimage_to_bgr, bgr_to_qimage

def _validate_filter_input(image: QImage, kernel_size: int) -> None:
    """Kiểm tra ảnh và kích thước cửa sổ của M3."""
    if image.isNull():
        raise ValueError("Ảnh đầu vào không hợp lệ.")

    if kernel_size not in (3, 5, 7, 9):
        raise ValueError("Kích thước cửa sổ phải là 3, 5, 7 hoặc 9.")


def _filter_result_to_qimage(
    result: np.ndarray,
    is_gray: bool,
) -> QImage:
    """Cắt về [0, 255], đổi sang uint8 rồi chuyển về QImage."""
    result = np.clip(result, 0, 255).astype(np.uint8)
    result = np.ascontiguousarray(result)
    return bgr_to_qimage(result, is_gray)

def mean_filter(image: QImage, kernel_size: int = 3) -> QImage:
    """M3: lọc trung bình bằng cv2.blur."""
    _validate_filter_input(image, kernel_size)

    source, is_gray = qimage_to_bgr(image)
    result = cv2.blur(source, (kernel_size, kernel_size))

    return _filter_result_to_qimage(result, is_gray)


def gaussian_filter(
    image: QImage,
    kernel_size: int = 3,
    sigma: float = 1.0,
) -> QImage:
    """M3: lọc Gaussian, sigma trong [0.5, 5]."""
    _validate_filter_input(image, kernel_size)

    if not np.isfinite(sigma) or not 0.5 <= sigma <= 5.0:
        raise ValueError("Sigma phải nằm trong [0.5, 5].")

    source, is_gray = qimage_to_bgr(image)

    result = cv2.GaussianBlur(
        source,
        (kernel_size, kernel_size),
        sigmaX=sigma,
        sigmaY=sigma,
    )

    return _filter_result_to_qimage(result, is_gray)


def median_filter(image: QImage, kernel_size: int = 3) -> QImage:
    """M3: lọc trung vị bằng cv2.medianBlur."""
    _validate_filter_input(image, kernel_size)

    source, is_gray = qimage_to_bgr(image)
    result = cv2.medianBlur(source, kernel_size)

    return _filter_result_to_qimage(result, is_gray)


def laplacian_sharpen(
    image: QImage,
    c: float = 0.2,
) -> QImage:
    """M3: làm sắc nét theo công thức g = f - c * Laplacian(f)."""
    if image.isNull():
        raise ValueError("Ảnh đầu vào không hợp lệ.")

    if not np.isfinite(c) or not 0.0 <= c <= 1.0:
        raise ValueError("Hệ số c phải nằm trong [0, 1].")

    source, is_gray = qimage_to_bgr(image)

    # Dùng float32 để giữ giá trị âm của đạo hàm.
    source_float = source.astype(np.float32)

    laplacian = cv2.Laplacian(
        source_float,
        cv2.CV_32F,
        ksize=1,
    )

    result = source_float - c * laplacian

    return _filter_result_to_qimage(result, is_gray)


def unsharp_masking(
    image: QImage,
    kernel_size: int = 5,
    sigma: float = 1.0,
    k: float = 1.0,
) -> QImage:
    """M3: làm sắc nét bằng mặt nạ chi tiết."""
    _validate_filter_input(image, kernel_size)

    if not np.isfinite(sigma) or not 0.5 <= sigma <= 5.0:
        raise ValueError("Sigma phải nằm trong [0.5, 5].")

    if not np.isfinite(k) or not 0.0 <= k <= 3.0:
        raise ValueError("Hệ số k phải nằm trong [0, 3].")

    source, is_gray = qimage_to_bgr(image)
    source_float = source.astype(np.float32)

    blurred = cv2.GaussianBlur(
        source_float,
        (kernel_size, kernel_size),
        sigmaX=sigma,
        sigmaY=sigma,
    )

    detail_mask = source_float - blurred
    result = source_float + k * detail_mask

    return _filter_result_to_qimage(result, is_gray)