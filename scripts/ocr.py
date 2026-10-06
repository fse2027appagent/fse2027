import os
import cv2
from paddleocr import PaddleOCR
from config import load_config
from object.bounds import Bounds

configs = load_config()


class MauOcr:

    def __init__(self):
        # 初始化 PaddleOCR
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
        )

    def extract_text_all(self, image):
        # OCR 识别
        result = self.ocr.ocr(image)
        if result == [None] or len(result) == 0:
            return None

        ocr_result = result[0]
        # PaddleOCR 3.x returns OCRResult object (dict-like)
        if hasattr(ocr_result, 'keys'):
            texts = ocr_result.get('rec_texts', [])
            polys = ocr_result.get('dt_polys', [])
        else:
            # PaddleOCR 2.x format
            texts = []
            polys = []
            for line in result[0]:
                texts.append(line[1][0])
                polys.append(line[0])

        # 提取文本及其坐标信息
        text_infos = []
        for i, text in enumerate(texts):
            coords = polys[i]
            if hasattr(coords, 'tolist'):
                coords = coords.tolist()
            bounds = Bounds([
                coords[0][0],
                coords[0][1],
                coords[2][0],
                coords[2][1]
            ])
            text_infos.append({
                'text': text,
                'bounds': bounds
            })

        return text_infos

    def extract_text_part(self, image, w, h):
        text_info = self.extract_text_all(image)
        if text_info is None:
            return None, None

        text = ''
        bounds = Bounds([w, h, 0, 0])

        for info in text_info:
            text = text + info['text']
            bounds.combine(info['bounds'])

        return text, bounds


_mau_ocr = None


def get_ocr():
    """Create PaddleOCR lazily.

    Importing this module must not initialise PaddleOCR: AppAgent loads YOLO
    (PyTorch) before OCR, and on Apple Silicon the two native runtimes are not
    safe to initialise in the same process.
    """
    global _mau_ocr
    if _mau_ocr is None:
        _mau_ocr = MauOcr()
    return _mau_ocr


def test_text_all(image_path):
    image = cv2.imread(image_path)

    text_info = get_ocr().extract_text_all(image)

    # 输出每个文本和坐标信息
    for item in text_info:
        print(f"文本: {item['text']}, 坐标: {item['bounds']}")


def test_text_part(image_path):
    image = cv2.imread(image_path)
    h, w, _ = image.shape

    text, bounds = get_ocr().extract_text_part(image, w, h)
    print(text)
    print(bounds.to_list())


if __name__ == '__main__':
    # 示例调用
    test_text_all("../1.png")
