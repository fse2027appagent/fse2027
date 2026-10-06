from object.component import Component
import cv2
import os
import json
import subprocess
import sys

from image_utils import ImageUtils


def boxes_overlap(box1, box2, threshold1=0.05, threshold2=0.5, threshold3=0.1, flag = True):
    """
    判断两个矩形是否重叠
    threshold: IoU（交并比）阈值，默认为0.3
    """
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2

    tmp1 = (x2 - x1) * (y2 - y1)

    tmp2 = (x4 - x3) * (y4 - y3)

    area1 = min(tmp1, tmp2)

    area2 = max(tmp1, tmp2)

    # 计算交集区域
    inter_x1 = max(x1, x3)
    inter_y1 = max(y1, y3)
    inter_x2 = min(x2, x4)
    inter_y2 = min(y2, y4)

    inter_area = float(max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1))

    if inter_area == 0:
        return False

    if inter_area / area2 < threshold1 and flag:
        return False

    if inter_area / area1 > threshold3 and flag is False:
        return True

    if inter_area / area1 > threshold2:
        return True

    # 计算并集
    area1 = (x2 - x1) * (y2 - y1)
    area2 = (x4 - x3) * (y4 - y3)
    union_area = area1 + area2 - inter_area

    iou = inter_area / union_area
    return iou >= threshold2

def filter_boxes_keep_smallest(components, image_height):
    boxes = []

    for c in components:
        box = c.get_bounds().to_list()

        # 尺寸过滤
        if box[3] * 33 < image_height:
            continue

        area = (box[2] - box[0]) * (box[3] - box[1])
        boxes.append((area, c, box))

    # 按面积从小到大排序
    boxes.sort(key=lambda x: x[0])

    result = []

    for _, comp, box in boxes:

        overlap = False

        for existing in result:
            if boxes_overlap(box, existing.get_bounds().to_list()):
                overlap = True
                break

        if not overlap:
            result.append(comp)

    return result


class Page:

    def __init__(self, path):
        self.id = -1
        self.name = 'new page'
        self.ocr_res = []
        self.yolo_res = []
        self.components = []
        self.image = None
        self.init_by_img(path)

    def get_components(self):
        return self.components

    def init_by_img(self, img_path):
        self._image_path = os.path.abspath(img_path)
        self.image = cv2.imread(img_path)
        if self.image is not None:
            file_name = os.path.basename(img_path)
            self.name = os.path.splitext(file_name)[0]
            self.detect_component()

    # 识别截图中的所有文字
    def detect_text_raw(self, img_path):
        """Run PaddleOCR in an isolated Python process.

        Ultralytics/PyTorch and PaddleOCR can abort with a native mutex error
        when both initialise in one Apple-Silicon process.  An exception
        handler in Python cannot recover from that abort, so process isolation
        is required rather than merely changing detection order.
        """
        worker = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ocr_worker.py")
        result = subprocess.run(
            [sys.executable, worker, os.path.abspath(img_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=True,
        )
        try:
            all_text = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OCR worker returned invalid JSON: {exc}") from exc

        cur_id = 0
        for text_info in all_text:
            from object.bounds import Bounds
            tmp_bounds = Bounds(text_info['bounds'])
            h, w = self.image.shape[:2]
            x1 = max(0, min(tmp_bounds.x1, w - 1))
            y1 = max(0, min(tmp_bounds.y1, h - 1))
            x2 = max(0, min(tmp_bounds.x2, w))
            y2 = max(0, min(tmp_bounds.y2, h))
            tmp_w = x2 - x1
            tmp_h = y2 - y1
            if tmp_w <= 0 or tmp_h <= 0:
                continue
            tmp_img = self.image[y1:y2, x1:x2]
            if tmp_img.size == 0:
                continue
            component = Component()
            component.set_id(cur_id)
            component.set_type('text')
            component.set_bounds(tmp_bounds)
            component.set_desc(text_info['text'])
            component.set_image(tmp_img)
            self.ocr_res.append(component)
            cur_id = cur_id + 1

    # 识别截图中的所有组件
    def detect_component_raw(self):
        from yolo import mau_yolo

        # res, res_plotted = mau_yolo.detect(self.__image)
        all_comp = mau_yolo.extract_component(self.image)
        cur_id = 0
        for comp in all_comp:
            tmp_bounds = comp['bounds']
            tmp_img = self.image[tmp_bounds.y1: tmp_bounds.y2, tmp_bounds.x1: tmp_bounds.x2]
            component = Component()
            component.set_id(cur_id)
            component.set_type('not_sure')
            component.set_bounds(tmp_bounds)
            component.set_image(tmp_img)
            self.yolo_res.append(component)
            cur_id = cur_id + 1

    # yolo和ocr结合
    def detect_component(self):
        # YOLO 必须在 OCR 之前运行，否则 PaddlePaddle 加载后会与 PyTorch YOLO 冲突
        # (ARM64 Mac 上 PaddlePaddle 和 PyTorch 存在资源竞争)
        try:
            self.detect_component_raw()
        except Exception as e:
            print(f"YOLO detection failed: {e}")
        try:
            self.detect_text_raw(self._image_path)
        except Exception as e:
            print(f"OCR detection failed: {e}")
        self.components = filter_boxes_keep_smallest(
            self.yolo_res,
            self.image.shape[0]
        )

        for text in self.ocr_res:
            if text.get_bounds().to_list()[3] * 34 < self.image.shape[0]:
                continue
            if not any(boxes_overlap(text.get_bounds().to_list(), m.get_bounds().to_list(), flag=False) \
                       for m in self.components):
                self.components.append(text)

        # Fallback: 使用 ADB UI hierarchy 当 YOLO 不可用时
        if not self.yolo_res:
            self._detect_by_adb_xml()

    def _detect_by_adb_xml(self):
        try:
            from and_controller import list_all_devices, AndroidController, traverse_tree
            from object.component import Component
            from object.bounds import Bounds
            devices = list_all_devices()
            if not devices:
                return
            controller = AndroidController(devices[0])
            xml_path = controller.get_xml("page_xml", "/tmp")
            if xml_path == "ERROR" or not os.path.exists(xml_path):
                return
            elem_list = []
            traverse_tree(xml_path, elem_list, "clickable", False)
            traverse_tree(xml_path, elem_list, "focusable", False)
            cur_id = len(self.components)
            for elem in elem_list:
                bbox = elem.bbox
                x1, y1 = bbox[0][0], bbox[0][1]
                x2, y2 = bbox[1][0], bbox[1][1]
                if x2 <= x1 or y2 <= y1:
                    continue
                comp = Component()
                comp.set_id(cur_id)
                comp.set_type('xml_ui')
                comp.set_bounds(Bounds([x1, y1, x2, y2]))
                comp.set_desc(elem.uid[:50] if elem.uid else 'ui_element')
                self.components.append(comp)
                cur_id += 1
        except Exception as e:
            print(f"ADB XML fallback failed: {e}")


if __name__ == '__main__':
    page = Page("../../5.png")
    print(page.image.shape)
    for com in page.components:
        ImageUtils.draw_bounds(page.image, com.get_bounds())
    ImageUtils.show_image(page.image)
