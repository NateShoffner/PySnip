# Copyright (c) Mathias Kaerlev 2011.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

"""
pyspades - map editor
"""

import sys
sys.path.append('..')

import math
from PySide import QtGui, QtCore
from PySide.QtCore import Qt
from PySide.QtGui import QPainter

from pyspades.load import VXLData, get_color_tuple

colors = {}

class LabeledSpinBox(QtGui.QWidget):
    def __init__(self, text, *arg, **kw):
        super(LabeledSpinBox, self).__init__(*arg, **kw)
        self.layout = QtGui.QHBoxLayout(self)
        self.label = QtGui.QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.spinbox = QtGui.QSpinBox()
        for item in (self.label, self.spinbox):
            self.layout.addWidget(item)

class LabeledWidget(QtGui.QWidget):
    def __init__(self, text, widget, *arg, **kw):
        super(LabeledWidget, self).__init__(*arg, **kw)
        self.layout = QtGui.QHBoxLayout(self)
        self.label = QtGui.QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.widget = widget
        for item in (self.label, self.widget):
            self.layout.addWidget(item)

class MapImage(QtGui.QImage):
    def __init__(self, overview, *arg, **kw):
        self.overview = overview
        super(MapImage, self).__init__(overview, *arg, **kw)

class EditWidget(QtGui.QWidget):
    scale = 1
    old_x = old_y = None
    image = None
    brush_size = 2.0
    settings = None
    freeze_image = None
    current_color = None
    x = y = 0
    def __init__(self, parent):
        super(EditWidget, self).__init__(parent)
        self.z_cache = {}
        self.map = self.parent().map
        self.set_z(63)
        self.update_scale()
        self.set_color(Qt.black)
        self.eraser = Qt.transparent
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
    
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Q:
            self.set_z(self.z + 1)
        elif key == Qt.Key_A:
            self.set_z(self.z - 1)
        elif key in xrange(Qt.Key_1, Qt.Key_9 + 1):
            self.brush_size = key - Qt.Key_0
        elif key == Qt.Key_Plus:
            self.brush_size += 1
        elif key == Qt.Key_Minus:
            self.brush_size -= 1
        elif key == Qt.Key_Z:
            color = QtGui.QColor(self.image.pixel(self.x, self.y))
            self.set_color(color)
        else:
            return
        self.brush_size = max(1, self.brush_size)
        self.settings.update_values()
    
    def toggle_freeze(self):
        if self.freeze_image is None:
            self.freeze_image = self.image
        else:
            self.freeze_image = None
            self.repaint()
    
    def update_scale(self):
        value = 512 * self.scale
        self.resize(value, value)
        
    def paintEvent(self, paintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.scale, self.scale)
        painter.drawRect(0, 0, 511, 511)
        painter.drawImage(0, 0, self.image)
        if self.freeze_image is not None and self.freeze_image is not self.image:
            painter.setOpacity(0.3)
            painter.drawImage(0, 0, self.freeze_image)
    
    def set_color(self, color):
        self.color = color
    
    def mousePressEvent(self, event):
        self.old_x = self.old_y = None
        button = event.button()
        self.update_mouse_position(event)
        if button == Qt.LeftButton:
            self.current_color = self.color
        elif button == Qt.RightButton:
            self.current_color = self.eraser
        else:
            self.current_color = None
            super(EditWidget, self).mousePressEvent(event)
            return
        self.draw_pencil(event)
    
    def mouseMoveEvent(self, event):
        self.update_mouse_position(event)
        if self.current_color is not None:
            self.draw_pencil(event)
        else:
            super(EditWidget, self).mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.current_color = None
    
    def update_mouse_position(self, event):
        value = 512.0 * self.scale
        x = int(event.x() / value * 512.0)
        y = int(event.y() / value * 512.0)
        x = max(0, min(511, x))
        y = max(0, min(511, y))
        self.x = x
        self.y = y
    
    def draw_pencil(self, event):
        x = self.x
        y = self.y
        if x in xrange(512) and y in xrange(512):
            old_x = self.old_x or x
            old_y = self.old_y or y
            color = self.current_color
            map = self.map
            z = self.z
            image = self.image
            painter = QPainter(image)
            if self.current_color is self.eraser:
                painter.setCompositionMode(QPainter.CompositionMode_Source)
            pen = QtGui.QPen(color)
            pen.setWidth(self.brush_size)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(old_x, old_y, x, y)
            self.repaint()
        self.old_x = x
        self.old_y = y
    
    def wheelEvent(self, wheelEvent):
        self.scale += (wheelEvent.delta() / 120.0) / 10.0
        self.update_scale()
        self.repaint()
    
    def set_z(self, z):
        map = self.map
        image = self.image
        if image is not None:
            map.set_overview(image.overview, self.z)
        self.z = max(0, min(63, z))
        try:
            image = self.z_cache[self.z]
        except KeyError:
            overview = map.get_overview(self.z)
            image = MapImage(overview, 512, 512,
                QtGui.QImage.Format_ARGB32)
            self.z_cache[self.z] = image
        self.image = image
        self.repaint()
    
    def save_overview(self):
        self.map.set_overview(self.image.overview, self.z)
    
    def map_updated(self):
        self.image = None
        self.z_cache = {}
        self.freeze_image = None
        self.map = self.parent().parent().parent().map
        self.set_z(self.z)

class ScrollArea(QtGui.QScrollArea):
    old_x = old_y = None
    
    def __init__(self, *arg, **kw):
        super(ScrollArea, self).__init__(*arg, **kw)
        self.setFocusPolicy(Qt.StrongFocus)
    
    def keyPressEvent(self, event):
        self.widget().keyPressEvent(event)
    
    def wheelEvent(self, wheelEvent):
        self.widget().wheelEvent(wheelEvent)
    
    def mousePressEvent(self, event):
        self.old_x = event.x()
        self.old_y = event.y()
    
    def mouseMoveEvent(self, event):
        button = event.buttons()
        x = event.x()
        y = event.y()
        if button == Qt.MiddleButton:
            dx = -(x - self.old_x)
            dy = -(y - self.old_y)
            vertical_bar = self.verticalScrollBar()
            horizontal_bar = self.horizontalScrollBar()
            vertical_bar.setValue(vertical_bar.value() + dy)
            horizontal_bar.setValue(horizontal_bar.value() + dx)
        self.old_x = x
        self.old_y = y

class Settings(QtGui.QWidget):
    def __init__(self, editor, *arg, **kw):
        self.editor = editor
        editor.settings = self
        super(Settings, self).__init__(*arg, **kw)
        layout = QtGui.QVBoxLayout(self)
        
        self.z_value = LabeledSpinBox('Current Z')
        self.z_value.spinbox.setRange(0, 63)
        self.z_value.spinbox.valueChanged.connect(self.set_z)
        layout.addWidget(self.z_value)

        self.brush_size = LabeledSpinBox('Brush size')
        self.brush_size.spinbox.valueChanged.connect(self.set_brush_size)
        self.brush_size.spinbox.setRange(0, 999)
        layout.addWidget(self.brush_size)
        
        self.freeze_button = QtGui.QPushButton('Toggle freeze')
        self.freeze_button.clicked.connect(self.freeze_image)
        layout.addWidget(self.freeze_button)
        
        self.color_button = QtGui.QPushButton('Set color')
        self.color_button.clicked.connect(self.set_color)
        layout.addWidget(self.color_button)
        
        self.update_values()
    
    def set_brush_size(self):
        self.editor.brush_size = self.brush_size.spinbox.value()
    
    def set_z(self):
        self.editor.set_z(self.z_value.spinbox.value())
    
    def freeze_image(self):
        self.editor.toggle_freeze()
    
    def set_color(self):
        color = QtGui.QColorDialog.getColor(
            Qt.white, self, 'Select a color',
            QtGui.QColorDialog.ShowAlphaChannel
        )
        self.editor.set_color(color)
    
    def update_values(self):
        editor = self.editor
        self.z_value.spinbox.setValue(editor.z)
        self.brush_size.spinbox.setValue(editor.brush_size)

class MapEditor(QtGui.QMainWindow):
    def __init__(self, *arg, **kw):
        super(MapEditor, self).__init__(*arg, **kw)

        menu = self.menuBar()
        
        self.file = menu.addMenu('&File')
        
        self.new_action = QtGui.QAction('&New', self,
            triggered = self.new_selected)
        self.file.addAction(self.new_action)
        
        self.load_action = QtGui.QAction('&Load', self,
            triggered = self.load_selected)
        self.file.addAction(self.load_action)
        
        self.save_action = QtGui.QAction('&Save', self, 
            shortcut=QtGui.QKeySequence.Save, triggered = self.save_selected)
        self.file.addAction(self.save_action)
        
        self.map = VXLData()
        
        self.scroll_view = ScrollArea(self)
        self.edit_widget = EditWidget(self)
        self.scroll_view.setWidget(self.edit_widget)
        self.setCentralWidget(self.scroll_view)
        self.scroll_view.setAlignment(Qt.AlignCenter)
        
        self.settings_dock = QtGui.QDockWidget(self)
        self.settings_dock.setWidget(Settings(self.edit_widget))
        self.settings_dock.setWindowTitle('Settings')
        
        for item in (self.settings_dock,):
            self.addDockWidget(Qt.RightDockWidgetArea, item)

        self.setWindowTitle('pyspades map editor')
    
    def new_selected(self):
        self.map = VXLData()
        self.map_updated()
    
    def load_selected(self):
        name = QtGui.QFileDialog.getOpenFileName(self,
            'Select map file', filter = '*.vxl')[0]
        if not name:
            return
        self.map = VXLData(open(name, 'rb'))
        self.map_updated()
    
    def map_updated(self):
        self.edit_widget.map_updated()
    
    def save_selected(self):
        name = QtGui.QFileDialog.getSaveFileName(self,
            'Select map file', filter = '*.vxl')[0]
        if not name:
            return
        self.edit_widget.save_overview()
        open(name, 'wb').write(self.map.generate())

def main():
    app = QtGui.QApplication(sys.argv)
    editor = MapEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()