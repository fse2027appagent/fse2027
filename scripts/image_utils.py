import base64
import os.path

import cv2
from object.bounds import Bounds


class ImageUtils:
    RED_COLOR = (0, 0, 255)

    DEFAULT_THICKNESS = 3

    def __init__(self):
        pass

    # 画边框
    @staticmethod
    def draw_bounds(image, bounds: Bounds):
        left_upper = (bounds.x1, bounds.y1)
        right_lower = (bounds.x2, bounds.y2)
        # BGR格式，红色为(0, 0, 255)
        color = ImageUtils.RED_COLOR
        # 线宽
        thickness = ImageUtils.DEFAULT_THICKNESS
        cv2.rectangle(image, left_upper, right_lower, color, thickness)

    # 展示图片
    @staticmethod
    def show_image(image):
        cv2.imshow('image', image)
        cv2.waitKey(0)  # 等待按键后关闭窗口
        cv2.destroyAllWindows()

    # jpg转png
    @staticmethod
    def convert_jpg_to_png(file_path):
        if file_path.endswith('jpg'):
            image = cv2.imread(file_path)
            png_file_path = file_path.replace(".jpg", ".png")
            cv2.imwrite(png_file_path, image)
            os.remove(file_path)

    #  base 64 编码格式
    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def convert_cv2_to_base64(cv2_image):
        # 1. 将cv2图像数据转换为字节流
        success, buffer = cv2.imencode('.png', cv2_image)
        if not success:
            raise RuntimeError("无法将图像编码为字节流")

        # 2. 对字节流进行base64编码
        img_str = base64.b64encode(buffer)

        # 3. 返回base64编码后的字符串
        return img_str.decode('utf-8')

    @staticmethod
    def count_component_num(dir):
        count = 0
        for page in os.listdir(dir):
            com_dir = os.path.join(dir, page, 'components')
            for file in os.listdir(com_dir):
                if file.endswith('.png'):
                    count = count + 1
        return count


def jpg2png(dir):
    import os
    for file in os.listdir(dir):
        ImageUtils.convert_jpg_to_png(os.path.join(dir, file))


def count_nums():
    from config import config
    dir = os.path.join(config.get_value('PATH', 'data_path'), 'note_out1')
    print(ImageUtils.count_component_num(dir))
    dir = os.path.join(config.get_value('PATH', 'data_path'), 'test_output1')
    print(ImageUtils.count_component_num(dir))


if __name__ == '__main__':
    count_nums()
