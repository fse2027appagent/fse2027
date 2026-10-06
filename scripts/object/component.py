from object.bounds import Bounds
import xml.etree.ElementTree as ET


class Component:

    def __init__(self):
        self.__id = -1
        self.__type = ''
        self.__bounds = Bounds()
        self.__path = ''
        self.__desc = ''
        self.__image = None

    def set_id(self, id):
        self.__id = id

    def set_type(self, type):
        self.__type = type

    def set_bounds(self, bounds : Bounds):
        self.__bounds = bounds

    def set_path(self, path):
        self.__path = path

    def set_desc(self, desc):
        self.__desc = desc

    def set_image(self, image):
        self.__image = image

    def get_id(self):
        return self.__id

    def get_type(self):
        return self.__type

    def get_bounds(self):
        return self.__bounds

    def get_path(self):
        return self.__path

    def get_desc(self):
        return self.__desc

    def get_image(self):
        return self.__image

    def get_xml_elem(self):
        child = ET.Element('component')
        child.set('id', str(self.__id))
        child.set('type', self.get_type())
        child.set('bounds', self.__bounds.to_list())
        child.set('path', self.get_path())
        child.set('desc', self.get_desc())
        return child

    def predict_desc(self):
        pass
