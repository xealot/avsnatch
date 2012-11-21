import sys
from PySide import QtGui, QtCore

__author__ = 'trey'

class Example(QtGui.QWidget):

    def __init__(self):
        super(Example, self).__init__()

        self.initUI()

    def initUI(self):

        qbtn = QtGui.QPushButton('Quit', self)
        qbtn.clicked.connect(QtCore.QCoreApplication.instance().quit)
        qbtn.resize(qbtn.sizeHint())
        qbtn.move(50, 50)

        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Quit button')
        self.show()


def main():
    app = QtGui.QApplication(sys.argv)

    wid = QtGui.QWidget()
    wid.resize(250, 150)
    wid.setWindowTitle('Simple')
    ex = Example()
    wid.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
