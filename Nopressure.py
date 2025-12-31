import os
import sys
import math
import struct
import numpy as np

# --- 1. 环境修复 ---
try:
    import PyQt5

    dirname = os.path.dirname(PyQt5.__file__)
    plugin_path = os.path.join(dirname, 'Qt5', 'plugins')
    if not os.path.exists(plugin_path):
        plugin_path = os.path.join(dirname, 'Qt', 'plugins')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
except Exception:
    pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel,
                             QFileDialog, QColorDialog, QComboBox, QFrame, QSizePolicy)
from PyQt5.QtGui import QPainter, QColor, QImage, QPixmap, QKeySequence, QPen, QCursor
from PyQt5.QtCore import Qt, QPoint, QRect, QPointF
from PyQt5.QtWidgets import QShortcut


# ==============================================================================
# 2. 核心算法 (ABR 解析)
# ==============================================================================
def decode_packbits_row(row_data, target_row_buf, width):
    ptr, col = 0, 0
    row_len = len(row_data)
    while ptr < row_len and col < width:
        n = int(row_data[ptr])
        ptr += 1
        if n < 128:
            count = n + 1
            write_len = min(count, width - col)
            if ptr + write_len > row_len: write_len = row_len - ptr
            if write_len > 0:
                target_row_buf[col: col + write_len] = np.frombuffer(row_data[ptr: ptr + write_len], dtype='u1')
            ptr += count;
            col += count
        elif n > 128:
            count = 257 - n
            if ptr < row_len:
                val = row_data[ptr]
                ptr += 1
                write_len = min(count, width - col)
                if write_len > 0: target_row_buf[col: col + write_len] = val
                col += count
    return col


def rle_decode_abr(data_bytes, h, w):
    table_size = h * 2
    if len(data_bytes) < table_size: return None, 0
    line_byte_counts = np.frombuffer(data_bytes[:table_size], dtype='>u2')
    offset = int(table_size)
    img_mat = np.zeros((h, w), dtype='u1')
    for i in range(h):
        byte_cnt = int(line_byte_counts[i])
        if byte_cnt == 0: continue
        end_pos = offset + byte_cnt
        if end_pos > len(data_bytes): break
        decode_packbits_row(data_bytes[offset: end_pos], img_mat[i], w)
        offset = end_pos
    return img_mat, offset


class IntegratedAbrParser:
    @staticmethod
    def load_abr(filepath):
        brushes = []
        if not os.path.exists(filepath): return brushes
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            minor_ver = struct.unpack('>H', data[2:4])[0]
            cursor = 4
            while cursor < len(data) - 12:
                if data[cursor:cursor + 4] != b'8BIM':
                    cursor += 1;
                    continue
                cursor += 4
                key = data[cursor:cursor + 4].decode('ascii', errors='ignore')
                cursor += 4
                block_len = struct.unpack('>I', data[cursor:cursor + 4])[0]
                cursor += 4
                block_end = cursor + block_len
                if key == 'samp':
                    samp_cursor = cursor
                    while samp_cursor < block_end:
                        if samp_cursor + 4 > block_end: break
                        item_len = struct.unpack('>I', data[samp_cursor:samp_cursor + 4])[0]
                        samp_cursor += 4
                        item_end = samp_cursor + item_len
                        skip_amt = 301 if minor_ver != 1 else 47
                        if skip_amt < item_len:
                            p = samp_cursor + skip_amt
                            top, left, bottom, right = struct.unpack('>IIII', data[p:p + 16])
                            h, w = bottom - top, right - left
                            comp = data[p + 18]
                            if 0 < w < 5000 and 0 < h < 5000:
                                payload = data[p + 19: item_end]
                                img_mat = None
                                if comp == 0:
                                    img_mat = np.frombuffer(payload[:h * w], dtype='u1').reshape((h, w))
                                elif comp == 1:
                                    img_mat, _ = rle_decode_abr(payload, h, w)
                                if img_mat is not None:
                                    corner_sum = int(img_mat[0, 0]) + int(img_mat[0, -1]) + int(img_mat[-1, 0]) + int(
                                        img_mat[-1, -1])
                                    alpha_mat = (255 - img_mat) if (corner_sum / 4) > 127 else img_mat
                                    bgra = np.zeros((h, w, 4), dtype='u1')
                                    bgra[..., 3] = alpha_mat
                                    brushes.append(QImage(bgra.data, w, h, QImage.Format_ARGB32).copy())
                        samp_cursor = item_end
                        if item_len % 4 != 0: samp_cursor += (4 - (item_len % 4)) % 4
                cursor = block_end
        except:
            pass
        return brushes


# ==============================================================================
# 3. 绘图引擎
# ==============================================================================
class ProCanvas(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app  # 引用主程序以便同步颜色
        self.setAttribute(Qt.WA_StaticContents)
        self.full_image = QImage(2000, 2000, QImage.Format_ARGB32_Premultiplied)
        self.full_image.fill(Qt.white)
        self.temp_image = None
        self.drawing = False
        self.brush_size = 40
        self.brush_color_opaque = QColor(0, 0, 0, 255)
        self.brush_shape = "圆"
        self.stroke_opacity = 1.0
        self.last_mapped_pos = None
        self.undo_stack = [self.full_image.copy()]
        self.redo_stack = []
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(0, 0)
        self.custom_tips = {}

    def get_canvas_rect(self):
        w, h = self.width(), self.height()
        side = min(w, h)
        return QRect((w - side) // 2, (h - side) // 2, side, side)

    def map_to_canvas(self, pos):
        rect = self.get_canvas_rect()
        if rect.width() <= 0 or not rect.contains(pos): return None
        lx = (pos.x() - rect.x()) * self.full_image.width() / rect.width()
        ly = (pos.y() - rect.y()) * self.full_image.height() / rect.height()
        return QPointF(lx, ly)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#e0e0e0"))
        target_rect = self.get_canvas_rect()
        painter.drawImage(target_rect, self.full_image, self.full_image.rect())
        if self.drawing and self.temp_image:
            painter.setOpacity(self.stroke_opacity)
            painter.drawImage(target_rect, self.temp_image, self.temp_image.rect())
        painter.setOpacity(1.0);
        painter.setPen(QColor("#999"));
        painter.drawRect(target_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.parent_app.pick_color_at_screen(event.globalPos())
        elif event.button() == Qt.LeftButton:
            m_pos = self.map_to_canvas(event.pos())
            if m_pos:
                self.drawing = True;
                self.last_mapped_pos = m_pos
                self.temp_image = QImage(self.full_image.size(), QImage.Format_ARGB32_Premultiplied)
                self.temp_image.fill(Qt.transparent)
                self.paint_stroke(m_pos, m_pos)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton:
            self.parent_app.pick_color_at_screen(event.globalPos())
        elif (event.buttons() & Qt.LeftButton) and self.drawing:
            m_pos = self.map_to_canvas(event.pos())
            if m_pos and self.last_mapped_pos:
                self.paint_stroke(self.last_mapped_pos, m_pos)
                self.last_mapped_pos = m_pos

    def paint_stroke(self, start_pos, end_pos):
        painter = QPainter(self.temp_image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        dx, dy = end_pos.x() - start_pos.x(), end_pos.y() - start_pos.y()
        dist = math.hypot(dx, dy)
        is_custom = self.brush_shape in self.custom_tips
        step = max(1, self.brush_size * 0.1)
        steps = max(1, int(dist / step))

        if is_custom:
            tip_mask = self.custom_tips[self.brush_shape]
            colored_tip = QImage(tip_mask.size(), QImage.Format_ARGB32_Premultiplied)
            colored_tip.fill(self.brush_color_opaque)
            mask_p = QPainter(colored_tip)
            mask_p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            mask_p.drawImage(0, 0, tip_mask)
            mask_p.end()

            draw_w = self.brush_size * 5
            for i in range(steps + 1):
                t = i / steps if steps > 0 else 0
                curr_x, curr_y = start_pos.x() + dx * t, start_pos.y() + dy * t
                brush_rect = QRect(0, 0, int(draw_w), int(draw_w))
                brush_rect.moveCenter(QPoint(int(curr_x), int(curr_y)))
                painter.drawImage(brush_rect, colored_tip)
        else:
            painter.setPen(Qt.NoPen);
            painter.setBrush(self.brush_color_opaque)
            draw_w = self.brush_size * 5
            for i in range(steps + 1):
                t = i / steps if steps > 0 else 0
                curr_x, curr_y = start_pos.x() + dx * t, start_pos.y() + dy * t
                brush_rect = QRect(0, 0, int(draw_w), int(draw_w))
                brush_rect.moveCenter(QPoint(int(curr_x), int(curr_y)))
                if self.brush_shape == "圆":
                    painter.drawEllipse(brush_rect)
                else:
                    painter.drawRect(brush_rect)
        painter.end();
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing and self.temp_image:
            p = QPainter(self.full_image)
            p.setOpacity(self.stroke_opacity)
            p.drawImage(0, 0, self.temp_image)
            p.end()
            self.undo_stack.append(self.full_image.copy())
            if len(self.undo_stack) > 50: self.undo_stack.pop(0)
            self.redo_stack.clear()
            self.temp_image = None
            self.drawing = False
            self.update()


# ==============================================================================
# 4. 参考图视图 (支持右键取色)
# ==============================================================================
class AspectLabel(QLabel):
    def __init__(self, parent_app):
        super().__init__("参考图 (W键显示)")
        self.parent_app = parent_app
        self.pix = None;
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored);
        self.setMinimumSize(0, 0)
        self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ddd;")

    def set_pixmap(self, pixmap):
        self.pix = pixmap; self.update_pixmap()

    def update_pixmap(self):
        if self.pix and not self.pix.isNull():
            scaled = self.pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            super().setPixmap(scaled)

    def resizeEvent(self, event):
        self.update_pixmap(); super().resizeEvent(event)

    # 在参考图上监听右键
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.parent_app.pick_color_at_screen(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton:
            self.parent_app.pick_color_at_screen(event.globalPos())


# ==============================================================================
# 5. 主窗口逻辑
# ==============================================================================
class DrawingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nopressure - Right Click to Pick Color")
        self.resize(1000, 600);
        self.base_color_val = QColor(0, 0, 0)
        self.init_ui()
        self.load_brushes()

    def init_ui(self):
        self.central_widget = QWidget();
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget);
        self.main_layout.setContentsMargins(0, 0, 0, 0);
        self.main_layout.setSpacing(0)

        self.toolbar = QFrame();
        self.toolbar.setFixedHeight(40);
        self.toolbar.setStyleSheet("background: white; border-bottom: 1px solid #ccc;")
        t_layout = QHBoxLayout(self.toolbar);
        t_layout.setContentsMargins(5, 0, 5, 0)

        def add_min(w): w.setMinimumSize(0, 0); w.setSizePolicy(QSizePolicy.Ignored,
                                                                QSizePolicy.Preferred); t_layout.addWidget(w); return w

        add_min(QLabel("B:"));
        self.size_slider = add_min(QSlider(Qt.Horizontal));
        self.size_slider.setRange(1, 200);
        self.size_slider.setValue(40)
        self.size_slider.valueChanged.connect(self.update_brush)

        add_min(QLabel("A:"));
        self.alpha_slider = add_min(QSlider(Qt.Horizontal));
        self.alpha_slider.setRange(0, 255);
        self.alpha_slider.setValue(255)
        self.alpha_slider.valueChanged.connect(self.update_brush)

        self.shape_box = add_min(QComboBox());
        self.shape_box.addItems(["圆", "方"])
        self.shape_box.currentTextChanged.connect(self.update_brush)

        self.color_btn = add_min(QPushButton("色"))
        self.color_btn.clicked.connect(self.pick_color_dialog)
        add_min(QPushButton("图")).clicked.connect(self.import_ref)
        self.main_layout.addWidget(self.toolbar)

        self.content_area = QWidget();
        self.content_layout = QHBoxLayout(self.content_area);
        self.content_layout.setContentsMargins(0, 0, 0, 0);
        self.content_layout.setSpacing(0)

        self.ref_view = AspectLabel(self)
        self.canvas_view = ProCanvas(self)
        self.content_layout.addWidget(self.ref_view, 1);
        self.content_layout.addWidget(self.canvas_view, 1)
        self.main_layout.addWidget(self.content_area)

        # 快捷键
        QShortcut(QKeySequence("Q"), self).activated.connect(
            lambda: self.toolbar.setVisible(not self.toolbar.isVisible()))
        QShortcut(QKeySequence("W"), self).activated.connect(self.toggle_reference)
        QShortcut(QKeySequence("C"), self).activated.connect(self.clear_action)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo_action)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.redo_action)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)
        self.update_brush()

    # --- 取色核心逻辑 ---
    def pick_color_at_screen(self, global_pos):
        """获取屏幕指定坐标的颜色并应用"""
        screen = QApplication.primaryScreen()
        if screen:
            # 抓取坐标下的 1x1 像素
            pixmap = screen.grabWindow(0, global_pos.x(), global_pos.y(), 1, 1)
            if not pixmap.isNull():
                img = pixmap.toImage()
                color = QColor(img.pixel(0, 0))
                self.base_color_val = color
                # 同步更新笔刷和UI反馈（可选：改变按钮颜色）
                self.update_brush()
                self.color_btn.setStyleSheet(f"background-color: {color.name()};")

    def load_brushes(self):
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(
            os.path.abspath(__file__))
        path = os.path.join(base_dir, "brushes")
        if not os.path.exists(path): os.makedirs(path); return
        for f in os.listdir(path):
            if f.lower().endswith(".abr"):
                tips = IntegratedAbrParser.load_abr(os.path.join(path, f))
                for i, tip in enumerate(tips):
                    name = f"{os.path.splitext(f)[0]}_{i + 1}"
                    self.canvas_view.custom_tips[name] = tip;
                    self.shape_box.addItem(name)

    def undo_action(self):
        if len(self.canvas_view.undo_stack) > 1:
            self.canvas_view.redo_stack.append(self.canvas_view.undo_stack.pop())
            self.canvas_view.full_image = self.canvas_view.undo_stack[-1].copy()
            self.canvas_view.update()

    def redo_action(self):
        if self.canvas_view.redo_stack:
            next_state = self.canvas_view.redo_stack.pop()
            self.canvas_view.undo_stack.append(next_state)
            self.canvas_view.full_image = next_state.copy()
            self.canvas_view.update()

    def clear_action(self):
        self.canvas_view.full_image.fill(Qt.white)
        self.canvas_view.undo_stack.append(self.canvas_view.full_image.copy())
        self.canvas_view.redo_stack.clear()
        self.canvas_view.update()

    def update_brush(self):
        self.canvas_view.brush_size = self.size_slider.value()
        self.canvas_view.brush_shape = self.shape_box.currentText()
        self.canvas_view.stroke_opacity = self.alpha_slider.value() / 255.0
        c = QColor(self.base_color_val);
        c.setAlpha(255)
        self.canvas_view.brush_color_opaque = c

    def pick_color_dialog(self):
        color = QColorDialog.getColor(self.base_color_val)
        if color.isValid():
            self.base_color_val = color
            self.update_brush()
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")

    def import_ref(self):
        p, _ = QFileDialog.getOpenFileName(self, "导入参考", "", "Images (*.png *.jpg *.bmp)")
        if p: self.ref_view.set_pixmap(QPixmap(p))

    def save_file(self):
        p, _ = QFileDialog.getSaveFileName(self, "保存", "art.png", "PNG (*.png)")
        if p: self.canvas_view.full_image.save(p)

    def toggle_reference(self):
        vis = self.ref_view.isVisible()
        self.ref_view.setVisible(not vis)


if __name__ == "__main__":
    app = QApplication(sys.argv);
    window = DrawingApp();
    window.show();
    sys.exit(app.exec_())