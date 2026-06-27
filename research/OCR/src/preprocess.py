import cv2
import numpy as np

# cv2.rotate codes for each clockwise angle
_ORIENT_CODES: dict[int, int | None] = {
    0: None,
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def to_grayscale(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def adaptive_threshold(img: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )


def deskew(img: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(img, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is None:
        return img
    angles = []
    for rho, theta in lines[:, 0]:
        angle = np.degrees(theta) - 90
        if abs(angle) <= 45:
            angles.append(angle)
    if not angles:
        return img
    skew = float(np.median(angles))
    if abs(skew) <= 1.0:
        return img
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), skew, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)


def detect_orientation(img: np.ndarray) -> int:
    """Return the clockwise rotation angle (0, 90, 180, or 270) to apply to make
    text horizontal and upright, chosen by maximising horizontal projection-profile
    variance on a downsampled binary image.
    """
    gray = to_grayscale(img) if img.ndim == 3 else img
    # Downsample to max 600 px on the longest side for speed
    h, w = gray.shape[:2]
    scale = min(1.0, 600.0 / max(h, w, 1))
    if scale < 1.0:
        gray = cv2.resize(gray, (max(1, int(w * scale)), max(1, int(h * scale))))
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    best_angle, best_var = 0, -1.0
    for angle, code in _ORIENT_CODES.items():
        candidate = cv2.rotate(binary, code) if code is not None else binary
        profile = np.sum(candidate, axis=1, dtype=np.float64)
        var = float(np.var(profile))
        if var > best_var:
            best_var = var
            best_angle = angle
    return best_angle


def correct_orientation(img: np.ndarray) -> np.ndarray:
    """Rotate *img* clockwise by the detected orientation angle to make text upright.
    Works on both colour (BGR) and grayscale images.
    """
    angle = detect_orientation(img)
    if angle == 0:
        return img
    return cv2.rotate(img, _ORIENT_CODES[angle])


def preprocess(img: np.ndarray) -> np.ndarray:
    gray = to_grayscale(img)
    thresh = adaptive_threshold(gray)
    return deskew(thresh)
