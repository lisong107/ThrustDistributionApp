import sys
import socket
import struct
import math
from PyQt5.QtWidgets import *  # type: ignore
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QLinearGradient
from assign_force_vector import assign_force_vector


class UDPReceiver(QThread):
    received = pyqtSignal(bytes)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = True

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.port))

        while self.running:
            try:
                data, _ = self.sock.recvfrom(1024)
                self.received.emit(data)
            except OSError:
                break

    def stop(self):
        self.running = False
        self.sock.close()
        self.wait()


class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = [0.0] * 16  # 实际值
        self.target_values = [0.0] * 16  # 目标值
        self.data = [2.0] * 16  # 初始值，可来自实际推力
        self.min_len = 20
        self.max_len = 60

    def update_values(self, values):
        if len(values) == 16:
            self.values = values
            self.update()

    def update_targets(self, targets):
        if len(targets) == 16:
            self.target_values = targets
            self.update()

    def draw_label_box(self, painter, x, y, w, h, color, text):
        rect = QRectF(x - w / 2, y, w, h)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 1))  # type: ignore
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(Qt.black)  # type: ignore
        painter.drawText(rect, Qt.AlignCenter, text)  # type: ignore

    def draw_legend(self, painter, x, y, color, label):
        rect = QRectF(x, y, 20, 15)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 1))  # type: ignore
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(Qt.black)  # type: ignore
        painter.drawText(x + 25, y + 12, label)

    def value_to_length(self, val):
        min_val = min(self.data)
        max_val = max(self.data)
        if max_val == min_val:
            return (self.min_len + self.max_len) // 2
        return int(
            self.min_len
            + (val - min_val) / (max_val - min_val) * (self.max_len - self.min_len)
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = int(width / 2)
        center_y = int(height / 2)

        # 坐标轴
        axis_len = int(min(width, height) / 2 - 60)
        painter.setPen(QPen(Qt.black, 2))  # type: ignore
        painter.drawLine(
            center_x - axis_len, center_y, center_x + axis_len, center_y
        )  # X 轴
        painter.drawLine(
            center_x, center_y - axis_len, center_x, center_y + axis_len
        )  # Y 轴

        # 坐标原点标签
        painter.setFont(QFont("Arial", 12))
        painter.drawText(center_x + 5, center_y - 5, "O")

        # 圆圈排布参数
        circle_radius = 14
        layout_radius = min(width, height) / 2 - 80  # 圆圈环绕半径

        font_metrics = painter.fontMetrics()
        h = font_metrics.height()

        for i in range(16):
            # 顺时针编号，16号在正上方
            angle = -math.pi / 2 + 2 * math.pi * i / 16
            x = center_x + layout_radius * math.cos(angle)
            y = center_y + layout_radius * math.sin(angle)

            # 小圆圈
            painter.setBrush(Qt.white)  # type: ignore
            painter.setPen(QPen(Qt.black, 1))  # type: ignore
            painter.drawEllipse(
                QRectF(
                    x - circle_radius,
                    y - circle_radius,
                    2 * circle_radius,
                    2 * circle_radius,
                )
            )

            # 编号画在圆圈中心
            painter.drawText(
                QRectF(
                    x - circle_radius,
                    y - circle_radius,
                    2 * circle_radius,
                    2 * circle_radius,
                ),
                Qt.AlignCenter,  # type: ignore
                str(i + 1),
            )  # type: ignore

            # 显示目标/实际值
            val_target = f"{self.target_values[i]:.2f}"
            val_actual = f"{self.values[i]:.2f}"

            w = (
                max(
                    painter.fontMetrics().horizontalAdvance(val_target),
                    painter.fontMetrics().horizontalAdvance(val_actual),
                )
                + 10
            )

            self.draw_label_box(
                painter,
                x,
                y - circle_radius - h - 6,
                w,
                h,
                QColor(180, 220, 255),
                val_target,
            )
            self.draw_label_box(
                painter,
                x,
                y + circle_radius + 2,
                w,
                h,
                QColor(255, 200, 200),
                val_actual,
            )

        # 图例
        self.draw_legend(painter, 20, 20, QColor(180, 220, 255), "目标")
        self.draw_legend(painter, 20, 45, QColor(255, 200, 200), "实际")


class UDPTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDP 可视化控制工具")
        self.setGeometry(200, 200, 1280, 900)

        self.receiver = None

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 控制区
        control_layout = QVBoxLayout()
        self.ip_input = QLineEdit("127.0.0.1")
        self.port_input = QLineEdit("8080")
        self.target_port_input = QLineEdit("8081")

        control_layout.addWidget(QLabel("目标IP"))
        control_layout.addWidget(self.ip_input)
        control_layout.addWidget(QLabel("本地端口"))
        control_layout.addWidget(self.port_input)
        control_layout.addWidget(QLabel("目标端口"))
        control_layout.addWidget(self.target_port_input)

        self.sliders = []
        self.labels = []
        self.values = [0.0, 0.0, 0.0]
        names = ["推进力", "作用点X", "作用点Y"]

        for i, name in enumerate(names):
            label = QLabel(f"{name}: 0.00")
            slider = QSlider(Qt.Horizontal)  # type: ignore
            slider.setRange(0, 1000)
            slider.sliderReleased.connect(self.send_on_release(i))
            slider.valueChanged.connect(self.update_label(i))
            self.sliders.append(slider)
            self.labels.append(label)
            control_layout.addWidget(label)
            control_layout.addWidget(slider)

        self.toggle_btn = QPushButton("开始监听")
        self.toggle_btn.clicked.connect(self.toggle_listen)
        control_layout.addWidget(self.toggle_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout, 2)

        # 绘图区
        self.canvas = Canvas()
        main_layout.addWidget(self.canvas, 5)

    def update_label(self, idx):
        def inner(val):
            self.values[idx] = val / 10.0
            self.labels[idx].setText(
                f"{['推进力', '作用点X', '作用点Y'][idx]}: {self.values[idx]:.2f}"
            )

        return inner

    def send_on_release(self, idx):
        def inner():
            try:
                ip = self.ip_input.text()
                port = int(self.target_port_input.text())
                data = self.values
                packed = struct.pack("3f", *data)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(packed, (ip, port))
            except Exception as e:
                print("发送错误:", e)

        return inner

    def toggle_listen(self):
        if self.toggle_btn.text() == "开始监听":
            try:
                port = int(self.port_input.text())
                if not (0 < port < 65536):
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "错误", "请输入有效的本地端口号 (1-65535)")
                return

            self.receiver = UDPReceiver(port)
            self.receiver.received.connect(self.canvas.update_values)
            self.receiver.start()
            self.toggle_btn.setText("停止监听")
        else:
            if self.receiver:
                self.receiver.stop()
                self.receiver = None
            self.toggle_btn.setText("开始监听")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = UDPTool()
    ex.show()
    sys.exit(app.exec_())
