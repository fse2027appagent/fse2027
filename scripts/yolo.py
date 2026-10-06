import os.path
import cv2
from ultralytics import YOLO
from config import load_config
from object.bounds import Bounds
from image_utils import ImageUtils

configs = load_config()


class MauYolo:

    def __init__(self):
        # 初始化yolo
        self.yolo = YOLO(os.path.join(configs['MODEL_PATH'], 'yolo/best.pt'))
        self.yolo2 = YOLO(os.path.join(configs['MODEL_PATH'], 'yolo/best2.pt'))

    def detect(self, image):
        results = self.yolo.predict(image, verbose=False)

        result = results[0]
        type_dict = result.names
        boxes = result.boxes
        res_plotted1 = result.plot()
        ret = []
        for box in boxes:
            ret.append({
                'type': type_dict[int(box.cls[0])],
                'box': [int(i) for i in box.xyxy[0].tolist()],
                'conf': float(box.conf)
            })

        res_plotted2 = None

        results = self.yolo2.predict(image, verbose=False)
        result = results[0]
        type_dict = result.names
        boxes = result.boxes
        res_plotted2 = result.plot()
        for box in boxes:
            ret.append({
                'type': type_dict[int(box.cls[0])],
                'box': [int(i) for i in box.xyxy[0].tolist()],
                'conf': float(box.conf)
            })
        return ret, res_plotted1, res_plotted2

    def extract_component(self, image, save=None):
        ret, rp1, rp2 = self.detect(image)


        if save is not None:
            # cv2.imwrite(save, rp1)
            pass

        res = []

        for item in ret:
            res.append({
                'type': item['type'],
                'bounds': Bounds(item['box'])
            })

        return res


mau_yolo = MauYolo()


def test_yolo(image_path):
    image = cv2.imread(image_path)

    res, res1, res2 = mau_yolo.detect(image)
    ImageUtils.show_image(res1)
    ImageUtils.show_image(res2)
    # cv2.imwrite('../test_output1/douyin1.png', rp)


if __name__ == '__main__':
    # 示例调用
    test_yolo('../0.png')
