from xml.dom.minidom import Document
from xml.sax.handler import ContentHandler
from xml.sax import parseString


class XmlDictHandler(ContentHandler):
    def __init__(self):
        self.dict = {}

    def startElement(self, name, attrs):
        pass

    def endElement(self, name):
        pass

    def characters(self, content):
        pass


class XmlToDict(object):
    def __init__(self, xml):
        self.xml = xml

    def as_dict(self):
        h = XmlDictHandler()
        parseString(self.xml, h)
        return h.dict


class DictToXml(object):
    def __init__(self, dict, root=None):
        self.doc = Document()
        self.dict = dict
        if root is None:
            if len(dict) != 1:
                raise Exception('No root element provided and dict contains more than one key')
            root = dict.keys()[0]
        self.root = self.doc.createElement(root)
        self.doc.appendChild(self.root)

    def as_xml(self):
        return self.doc.toxml()


def dumps(s):
    return DictToXml(s).as_xml()

def loads(s):
    return XmlToDict(s).as_dict()
