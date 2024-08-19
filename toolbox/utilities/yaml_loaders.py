import yaml
import os
from toolbox import INPUT_DIR
class BasicLoader(yaml.Loader):

    def __init__(self, stream):

        self._root = os.path.split(stream.name)[0]

        super().__init__(stream)

    def include(self, node):

        filename = os.path.join(self._root, self.construct_scalar(node))

        with open(filename, 'r') as f:
            return yaml.load(f, self.__class__)


BasicLoader.add_constructor('!include', BasicLoader.include)

class SmartLoader(yaml.Loader):

    def __init__(self, stream):

        self._root = os.path.split(stream.name)[0]

        super().__init__(stream)

    def include(self, node):
        if os.path.split(node.value)[0] == "":
            filename = os.path.join(self._root, self.construct_scalar(node))
        else:
            if os.path.isfile(node.value):
                filename = self.construct_scalar(node)

        with open(filename, 'r') as f:
            return yaml.load(f, self.__class__)


SmartLoader.add_constructor('!include', SmartLoader.include)

class SuperSmartLoader(yaml.Loader):

    def __init__(self, stream):

        self._root = os.path.split(stream.name)[0]

        super().__init__(stream)

    def include(self, node):
        if os.path.split(node.value)[0] == "":
            filename = os.path.join(self._root, self.construct_scalar(node))
        else:
            if os.path.isfile(node.value):
                filename = self.construct_scalar(node)
            else:
                # filename = os.path.join(INPUT_DIR,self.construct_scalar(node))
                if os.path.isfile(os.path.join(INPUT_DIR,self.construct_scalar(node))):
                    filename = os.path.join(INPUT_DIR,self.construct_scalar(node))
        # print(filename)
        with open(filename, 'r') as f:
            return yaml.load(f, self.__class__)


SuperSmartLoader.add_constructor('!include', SuperSmartLoader.include)