

from __future__ import annotations

from pathlib import Path
from typing import Optional

from Image_processing import processing
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSlider,
    QSpinBox, QDoubleSpinBox, QScrollArea, QStackedWidget, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

IMAGE_FILTER = "Ảnh (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)"


class ImageCanvas(QLabel):
    """Vùng xem ảnh hỗ trợ chọn vùng cắt hoặc lấy màu tại một điểm."""

    pixel_picked = Signal(int, int)
    selection_changed = Signal(QRect)

    def __init__(self) -> None:
        super().__init__("Mở ảnh để bắt đầu xử lý")
        self.setObjectName("imageCanvas")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(620, 470)
        self.setMouseTracking(True)
        self._image: Optional[QImage] = None
        self._display_rect = QRect()
        self._start = QPoint()
        self._selection = QRect()
        self._dragging = False
        self.mode = "view"  # view | crop | picker

    def set_image(self, image: Optional[QImage]) -> None:
        self._image = image.copy() if image is not None else None
        self._selection = QRect()
        self._refresh()

    def clear_selection(self) -> None:
        self._selection = QRect()
        self.selection_changed.emit(QRect())
        self.update()

    def selected_rect(self) -> QRect:
        return self._selection.normalized()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._refresh()

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._image is None or event.button() != Qt.MouseButton.LeftButton:
            return
        point = self._to_image_point(event.position().toPoint())
        if point is None:
            return
        if self.mode == "picker":
            self.pixel_picked.emit(point.x(), point.y())
            return
        if self.mode == "crop":
            self._start = point
            self._selection = QRect(point, point)
            self._dragging = True
            self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._image is None or self.mode != "crop" or not self._dragging:
            return
        point = self._to_image_point(event.position().toPoint())
        if point is None:
            return
        self._selection = QRect(self._start, point).normalized()
        self.selection_changed.emit(self._selection)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.mode == "crop" and event.button() == Qt.MouseButton.LeftButton:
            self._start = QPoint()
            self._dragging = False
            self._selection = self._selection.normalized()
            self.selection_changed.emit(self._selection)
            self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        if self._image is None or self._selection.isNull() or self._display_rect.isNull():
            return
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#2563eb"), 2, Qt.PenStyle.DashLine))
        painter.drawRect(self._to_canvas_rect(self._selection))

    def _refresh(self) -> None:
        if self._image is None or self._image.isNull():
            self.setPixmap(QPixmap())
            self.setText("Mở ảnh để bắt đầu xử lý")
            self._display_rect = QRect()
            return
        pixmap = QPixmap.fromImage(self._image)
        scaled = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._display_rect = QRect(x, y, scaled.width(), scaled.height())
        self.setPixmap(scaled)
        self.setText("")
        self.update()

    def _to_image_point(self, canvas_point: QPoint) -> Optional[QPoint]:
        if self._image is None or not self._display_rect.contains(canvas_point):
            return None
        x = (canvas_point.x() - self._display_rect.x()) * self._image.width() // self._display_rect.width()
        y = (canvas_point.y() - self._display_rect.y()) * self._image.height() // self._display_rect.height()
        return QPoint(min(max(x, 0), self._image.width() - 1), min(max(y, 0), self._image.height() - 1))

    def _to_canvas_rect(self, image_rect: QRect) -> QRect:
        if self._image is None:
            return QRect()
        left = self._display_rect.x() + image_rect.left() * self._display_rect.width() // self._image.width()
        top = self._display_rect.y() + image_rect.top() * self._display_rect.height() // self._image.height()
        width = max(1, image_rect.width() * self._display_rect.width() // self._image.width())
        height = max(1, image_rect.height() * self._display_rect.height() // self._image.height())
        return QRect(left, top, width, height)


class ResizeDialog(QDialog):
    """Nhập chiều rộng/cao hoặc tỉ lệ phần trăm, có tuỳ chọn giữ tỉ lệ."""

    def __init__(self, width: int, height: int, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Đổi kích thước ảnh")
        self._ratio = width / height
        self._original_width = width
        self._original_height = height
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(width)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(height)
        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(1, 500)
        self.percent_spin.setValue(100)
        self.keep_ratio = QCheckBox("Giữ tỉ lệ ảnh")
        self.keep_ratio.setChecked(True)
        form.addRow("Chiều rộng (px):", self.width_spin)
        form.addRow("Chiều cao (px):", self.height_spin)
        form.addRow("Hoặc tỉ lệ (%):", self.percent_spin)
        form.addRow("", self.keep_ratio)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.width_spin.valueChanged.connect(self._from_width)
        self.height_spin.valueChanged.connect(self._from_height)
        self.percent_spin.valueChanged.connect(self._from_percent)
        self._changing = False

    def _from_width(self, value: int) -> None:
        if self._changing or not self.keep_ratio.isChecked():
            return
        self._changing = True
        self.height_spin.setValue(max(1, round(value / self._ratio)))
        self._changing = False

    def _from_height(self, value: int) -> None:
        if self._changing or not self.keep_ratio.isChecked():
            return
        self._changing = True
        self.width_spin.setValue(max(1, round(value * self._ratio)))
        self._changing = False

    def _from_percent(self, value: int) -> None:
        if self._changing:
            return
        self._changing = True
        self.width_spin.setValue(max(1, round(self._original_width * value / 100)))
        self.height_spin.setValue(max(1, round(self._original_height * value / 100)))
        self._changing = False


class AdjustmentDialog(QDialog):
    """Bảng công cụ M2: mỗi thẻ tương ứng một lệnh của đề bài."""

    def __init__(self, window: "Window") -> None:
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Điều chỉnh độ sáng, tương phản và histogram")
        self.setMinimumWidth(530)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Mỗi thao tác áp dụng trực tiếp lên ảnh hiện tại. Dùng Ctrl+R để quay về ảnh gốc."))
        tabs = QTabWidget()
        tabs.addTab(self._simple_tab("Âm bản", "Đảo giá trị điểm ảnh theo công thức s = 255 - r.", window.apply_negative), "Âm bản")
        tabs.addTab(self._log_tab(), "Log [TC]")
        tabs.addTab(self._gamma_tab(), "Gamma [TC]")
        tabs.addTab(self._contrast_tab(), "Kéo giãn")
        tabs.addTab(self._histogram_tab(), "Histogram [TC]")
        tabs.addTab(self._clahe_tab(), "CLAHE")
        layout.addWidget(tabs)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        close.accepted.connect(self.accept)
        layout.addWidget(close)

    def _simple_tab(self, title: str, description: str, callback) -> QWidget:  # type: ignore[no-untyped-def]
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel(description))
        button = QPushButton(f"Áp dụng {title}")
        button.setObjectName("primaryButton")
        button.clicked.connect(callback)
        layout.addWidget(button)
        layout.addStretch()
        return tab

    def _log_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("s = c · log(1 + r), c = 255 / log(256).\nĐây là phần [TC] cần tự cài đặt."))
        button = QPushButton("Áp dụng biến đổi Log [TC]")
        button.clicked.connect(self.window.apply_log_transform)
        layout.addWidget(button)
        layout.addStretch()
        return tab

    def _gamma_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("s = 255 · (r / 255)^γ. γ < 1 làm sáng, γ > 1 làm tối."))
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.1, 3.0)
        self.gamma_spin.setSingleStep(0.1)
        self.gamma_spin.setValue(1.0)
        self.gamma_spin.setDecimals(1)
        layout.addWidget(self.gamma_spin)
        button = QPushButton("Áp dụng Gamma [TC]")
        button.clicked.connect(lambda: self.window.apply_gamma_transform(self.gamma_spin.value()))
        layout.addWidget(button)
        layout.addStretch()
        return tab

    def _contrast_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Chọn mức đen a và mức trắng b (0–255). Giá trị ngoài [a, b] được cắt về 0 hoặc 255."))
        form = QFormLayout()
        self.black_spin = QSpinBox()
        self.black_spin.setRange(0, 254)
        self.black_spin.setValue(30)
        self.white_spin = QSpinBox()
        self.white_spin.setRange(1, 255)
        self.white_spin.setValue(220)
        form.addRow("Mức đen a:", self.black_spin)
        form.addRow("Mức trắng b:", self.white_spin)
        layout.addLayout(form)
        button = QPushButton("Áp dụng kéo giãn tương phản")
        button.setObjectName("primaryButton")
        button.clicked.connect(lambda: self.window.apply_contrast_stretch(self.black_spin.value(), self.white_spin.value()))
        layout.addWidget(button)
        layout.addStretch()
        return tab

    def _histogram_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Cân bằng histogram thủ công theo CDF là phần [TC].\nNút bên dưới gọi hàm tự cài đặt; có thể dùng để so sánh với OpenCV sau khi hoàn thiện."))
        manual = QPushButton("Cân bằng histogram [TC]")
        manual.clicked.connect(self.window.apply_histogram_equalization)
        layout.addWidget(manual)
        compare = QPushButton("So sánh với OpenCV")
        compare.clicked.connect(self.window.compare_histogram_with_opencv)
        layout.addWidget(compare)
        layout.addStretch()
        return tab

    def _clahe_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Cân bằng histogram thích nghi cục bộ bằng cv2.createCLAHE."))
        form = QFormLayout()
        self.clip_spin = QSpinBox()
        self.clip_spin.setRange(1, 5)
        self.clip_spin.setValue(2)
        self.grid_spin = QSpinBox()
        self.grid_spin.setRange(4, 16)
        self.grid_spin.setValue(8)
        form.addRow("clipLimit:", self.clip_spin)
        form.addRow("Kích thước lưới:", self.grid_spin)
        layout.addLayout(form)
        button = QPushButton("Áp dụng CLAHE")
        button.setObjectName("primaryButton")
        button.clicked.connect(lambda: self.window.apply_clahe(self.clip_spin.value(), self.grid_spin.value()))
        layout.addWidget(button)
        layout.addStretch()
        return tab


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.project_dir = Path(__file__).resolve().parent.parent
        self.image: Optional[QImage] = None
        self.original_image: Optional[QImage] = None
        self.current_path: Optional[Path] = None
        self.setWindowTitle("PhotoRestore")
        self.resize(1280, 800)
        self.setMinimumSize(1050, 680)
        logo = self.project_dir / "uI" / "Background" / "Logo.png"
        if logo.exists():
            self.setWindowIcon(QIcon(str(logo)))
        self._create_actions()
        self._create_menu()
        self._create_ui()
        self._apply_style()

    def _create_actions(self) -> None:
        self.open_action = QAction("Mở ảnh...", self, shortcut="Ctrl+O", triggered=self.open_image)
        self.save_action = QAction("Lưu ảnh...", self, shortcut="Ctrl+S", triggered=self.save_image)
        self.reset_action = QAction("Khôi phục ảnh gốc", self, shortcut="Ctrl+R", triggered=self.reset_image)
        self.info_action = QAction("Thông tin ảnh", self, triggered=self.show_image_info)
        self.gray_action = QAction("Chuyển ảnh xám", self, triggered=self.convert_to_grayscale)
        self.crop_action = QAction("Cắt theo vùng chọn", self, triggered=self.toggle_crop_mode)
        self.resize_action = QAction("Đổi kích thước", self, triggered=self.resize_image)
        self.reduce_action = QAction("Giảm mức xám [TC]", self, triggered=self.reduce_levels)
        self.picker_action = QAction("Ống hút màu", self, triggered=self.toggle_picker_mode)
        self.adjust_action = QAction("Điều chỉnh ", self, shortcut="Ctrl+J", triggered=self.open_adjustment_dialog)

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Tệp")
        file_menu.addActions((self.open_action, self.save_action, self.reset_action))
        image_menu = self.menuBar().addMenu("Ảnh")
        image_menu.addActions((self.info_action, self.gray_action, self.crop_action, self.resize_action, self.reduce_action))
        adjust_menu = self.menuBar().addMenu("Điều chỉnh")
        adjust_menu.addAction(self.adjust_action)
        tools_menu = self.menuBar().addMenu("Công cụ")
        tools_menu.addAction(self.picker_action)

    def _create_ui(self) -> None:
        self._create_workspace_ui()
        return

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 16, 22, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("PhotoRestore")
        title.setObjectName("appTitle")
        
        heading.addWidget(title)
        header.addLayout(heading)
        header.addStretch()
        for text, action, object_name in (
            ("Mở ảnh", self.open_action, "primaryButton"),
            ("Lưu ảnh", self.save_action, "secondaryButton"),
        ):
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.clicked.connect(action.trigger)
            header.addWidget(button)
        layout.addLayout(header)

        tool_row = QHBoxLayout()
        for text, action in (
            ("Thông tin", self.info_action), ("Chuyển xám", self.gray_action),
            ("Chọn vùng cắt", self.crop_action), ("Đổi kích thước", self.resize_action),
            ("Giảm mức xám [TC]", self.reduce_action), ("Ống hút màu", self.picker_action),
            ("Điều chỉnh M2", self.adjust_action),
        ):
            button = QPushButton(text)
            button.setObjectName("toolButton")
            button.clicked.connect(action.trigger)
            tool_row.addWidget(button)
        layout.addLayout(tool_row)

        content = QHBoxLayout()
        self.canvas = ImageCanvas()
        self.canvas.pixel_picked.connect(self.pick_color)
        self.canvas.selection_changed.connect(self.update_selection_info)
        content.addWidget(self.canvas, 1)
        content.addWidget(self._create_side_panel())
        layout.addLayout(content, 1)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Sẵn sàng - mở một ảnh để bắt đầu.")

    def _create_side_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("sidePanel")
        panel.setFixedWidth(270)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        info_title = QLabel("Thông tin ảnh")
        info_title.setObjectName("panelTitle")
        layout.addWidget(info_title)
        self.info_label = QLabel("Chưa có ảnh")
        self.info_label.setObjectName("infoLabel")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        layout.addWidget(self._line())
        color_title = QLabel("Ống hút màu")
        color_title.setObjectName("panelTitle")
        layout.addWidget(color_title)
        self.color_swatch = QLabel()
        self.color_swatch.setObjectName("colorSwatch")
        self.color_swatch.setFixedHeight(42)
        layout.addWidget(self.color_swatch)
        self.color_label = QLabel("B: -\nG: -\nR: -")
        self.color_label.setObjectName("infoLabel")
        layout.addWidget(self.color_label)
        layout.addWidget(self._line())
        selection_title = QLabel("Vùng cắt")
        selection_title.setObjectName("panelTitle")
        layout.addWidget(selection_title)
        self.selection_label = QLabel("Chưa chọn vùng nào")
        self.selection_label.setObjectName("infoLabel")
        self.selection_label.setWordWrap(True)
        layout.addWidget(self.selection_label)
        self.apply_crop_button = QPushButton("Áp dụng cắt")
        self.apply_crop_button.setObjectName("primaryButton")
        self.apply_crop_button.clicked.connect(self.apply_crop)
        layout.addWidget(self.apply_crop_button)
        layout.addStretch()
        self.mode_label = QLabel("Chế độ: Xem ảnh")
        self.mode_label.setObjectName("modeLabel")
        layout.addWidget(self.mode_label)
        return panel

    @staticmethod
    def _line() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line

    def _create_workspace_ui(self) -> None:
        """điều hướng, canvas, bảng công cụ."""
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 16, 20, 18)
        root_layout.setSpacing(14)

        header = QHBoxLayout()
        identity = QVBoxLayout()
        title = QLabel("PhotoRestore")
        title.setObjectName("appTitle")
        subtitle = QLabel("Đồ án xử lý ảnh số · Không gian làm việc")
        subtitle.setObjectName("subtitle")
        identity.addWidget(title)
        identity.addWidget(subtitle)
        header.addLayout(identity)
        header.addStretch()
        for text, action, name in (
            ("Mở ảnh", self.open_action, "primaryButton"),
            ("Lưu vào Output", self.save_action, "secondaryButton"),
            ("Khôi phục", self.reset_action, "secondaryButton"),
        ):
            button = QPushButton(text)
            button.setObjectName(name)
            button.clicked.connect(action.trigger)
            header.addWidget(button)
        root_layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._create_module_navigation())

        workspace = QFrame()
        workspace.setObjectName("workspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(14, 14, 14, 14)
        workspace_layout.setSpacing(10)
        self.workspace_title = QLabel("Ảnh và thao tác cơ bản")
        self.workspace_title.setObjectName("workspaceTitle")
        self.workspace_note = QLabel("Chọn công cụ trong bảng bên phải hoặc từ menu Ảnh.")
        self.workspace_note.setObjectName("workspaceNote")
        workspace_layout.addWidget(self.workspace_title)
        workspace_layout.addWidget(self.workspace_note)
        self.canvas = ImageCanvas()
        self.canvas.pixel_picked.connect(self.pick_color)
        self.canvas.selection_changed.connect(self.update_selection_info)
        workspace_layout.addWidget(self.canvas, 1)
        body.addWidget(workspace, 1)
        body.addWidget(self._create_inspector())
        root_layout.addLayout(body, 1)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Sẵn sàng - mở một ảnh để bắt đầu.")
        self.select_module(0)

    def _create_module_navigation(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("moduleNav")
        panel.setFixedWidth(190)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)
        label = QLabel("CÁC MÔ-ĐUN")
        label.setObjectName("navTitle")
        layout.addWidget(label)
        self.module_buttons: list[QPushButton] = []
        module_names = [
            "Ảnh cơ bản",
            "Điều chỉnh ảnh",
            "Sắp phát triển",
            "Sắp phát triển",
            "Sắp phát triển",
            "Sắp phát triển",
            "Sắp phát triển",
            "Sắp phát triển",
        ]
        for index, name in enumerate(module_names):
            button = QPushButton(name)
            button.setObjectName("moduleButton")
            button.setCheckable(True)
            button.setMinimumHeight(42)
            button.clicked.connect(lambda checked=False, item=index: self.select_module(item))
            self.module_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()
        hint = QLabel("Mỗi mô-đun dùng cùng một canvas và bảng công cụ, nên có thể mở rộng mà không làm giao diện rối.")
        hint.setObjectName("navHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return panel

    def _create_inspector(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("inspector")
        panel.setFixedWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.inspector_title = QLabel()
        self.inspector_title.setObjectName("inspectorTitle")
        self.inspector_description = QLabel()
        self.inspector_description.setObjectName("inspectorDescription")
        self.inspector_description.setWordWrap(True)
        title_box = QVBoxLayout()
        title_box.setContentsMargins(16, 16, 16, 8)
        title_box.addWidget(self.inspector_title)
        title_box.addWidget(self.inspector_description)
        layout.addLayout(title_box)
        scroll = QScrollArea()
        scroll.setObjectName("toolScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.module_stack = QStackedWidget()
        self.module_stack.addWidget(self._create_m1_tools())
        self.module_stack.addWidget(self._create_m2_tools())
        for number in range(3, 9):
            self.module_stack.addWidget(self._create_placeholder_tools(number))
        scroll.setWidget(self.module_stack)
        layout.addWidget(scroll, 1)
        return panel

    def _create_m1_tools(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(10)
        for text, action in (
            ("Thông tin ảnh", self.info_action),
            ("Chuyển ảnh xám", self.gray_action),
            ("Chọn vùng cắt", self.crop_action),
            ("Đổi kích thước", self.resize_action),
            ("Giảm mức xám [TC]", self.reduce_action),
            ("Ống hút màu", self.picker_action),
        ):
            button = QPushButton(text)
            button.setObjectName("toolButton")
            button.setMinimumHeight(38)
            button.clicked.connect(action.trigger)
            layout.addWidget(button)
        layout.addWidget(self._line())
        layout.addWidget(self._section_label("Thông tin ảnh"))
        self.info_label = QLabel("Chưa có ảnh")
        self.info_label.setObjectName("infoLabel")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        layout.addWidget(self._section_label("Vùng cắt"))
        self.selection_label = QLabel("Chưa chọn vùng nào")
        self.selection_label.setObjectName("infoLabel")
        self.selection_label.setWordWrap(True)
        layout.addWidget(self.selection_label)
        self.apply_crop_button = QPushButton("Áp dụng cắt")
        self.apply_crop_button.setObjectName("primaryButton")
        self.apply_crop_button.clicked.connect(self.apply_crop)
        layout.addWidget(self.apply_crop_button)
        layout.addWidget(self._section_label("Ống hút màu"))
        self.color_swatch = QLabel()
        self.color_swatch.setObjectName("colorSwatch")
        self.color_swatch.setFixedHeight(32)
        layout.addWidget(self.color_swatch)
        self.color_label = QLabel("B: -\nG: -\nR: -")
        self.color_label.setObjectName("infoLabel")
        layout.addWidget(self.color_label)
        self.mode_label = QLabel("Chế độ: Xem ảnh")
        self.mode_label.setObjectName("modeLabel")
        layout.addWidget(self.mode_label)
        layout.addStretch()
        return page

    def _create_m2_tools(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(10)
        negative = QPushButton("Âm bản")
        negative.setObjectName("toolButton")
        negative.clicked.connect(self.apply_negative)
        layout.addWidget(negative)
        log = QPushButton("Biến đổi Log [TC]")
        log.setObjectName("toolButton")
        log.clicked.connect(self.apply_log_transform)
        layout.addWidget(log)
        layout.addWidget(self._section_label("Gamma [TC]"))
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.1, 3.0)
        self.gamma_spin.setSingleStep(0.1)
        self.gamma_spin.setValue(1.0)
        self.gamma_spin.setPrefix("γ = ")
        layout.addWidget(self.gamma_spin)
        gamma = QPushButton("Áp dụng Gamma [TC]")
        gamma.setObjectName("toolButton")
        gamma.clicked.connect(lambda: self.apply_gamma_transform(self.gamma_spin.value()))
        layout.addWidget(gamma)
        layout.addWidget(self._section_label("Kéo giãn tương phản"))
        form = QFormLayout()
        self.black_spin = QSpinBox()
        self.black_spin.setRange(0, 254)
        self.black_spin.setValue(30)
        self.white_spin = QSpinBox()
        self.white_spin.setRange(1, 255)
        self.white_spin.setValue(220)
        form.addRow("Mức đen a:", self.black_spin)
        form.addRow("Mức trắng b:", self.white_spin)
        layout.addLayout(form)
        contrast = QPushButton("Áp dụng tương phản")
        contrast.setObjectName("primaryButton")
        contrast.clicked.connect(lambda: self.apply_contrast_stretch(self.black_spin.value(), self.white_spin.value()))
        layout.addWidget(contrast)
        layout.addWidget(self._section_label("Cân bằng histogram [TC]"))
        equalize = QPushButton("Cân bằng histogram [TC]")
        equalize.setObjectName("toolButton")
        equalize.clicked.connect(self.apply_histogram_equalization)
        layout.addWidget(equalize)
        opencv = QPushButton("So sánh với OpenCV")
        opencv.setObjectName("toolButton")
        opencv.clicked.connect(self.compare_histogram_with_opencv)
        layout.addWidget(opencv)
        layout.addWidget(self._section_label("CLAHE"))
        clahe_form = QFormLayout()
        self.clip_spin = QSpinBox()
        self.clip_spin.setRange(1, 5)
        self.clip_spin.setValue(2)
        self.grid_spin = QSpinBox()
        self.grid_spin.setRange(4, 16)
        self.grid_spin.setValue(8)
        clahe_form.addRow("clipLimit:", self.clip_spin)
        clahe_form.addRow("Lưới:", self.grid_spin)
        layout.addLayout(clahe_form)
        clahe = QPushButton("Áp dụng CLAHE")
        clahe.setObjectName("primaryButton")
        clahe.clicked.connect(lambda: self.apply_clahe(self.clip_spin.value(), self.grid_spin.value()))
        layout.addWidget(clahe)
        layout.addStretch()
        return page

    def _create_placeholder_tools(self, module_number: int) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 16)
        message = QLabel(f"M{module_number} chưa được triển khai.\n\nKhu vực này đã được dành sẵn để thêm các nút thao tác, tham số và mô tả của mô-đun tiếp theo.")
        message.setObjectName("placeholderText")
        message.setWordWrap(True)
        layout.addWidget(message)
        layout.addStretch()
        return page

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def select_module(self, index: int) -> None:
        self.module_stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.module_buttons):
            button.setChecked(button_index == index)
        titles = [
            ("Ảnh và thao tác cơ bản", "Thông tin ảnh, ảnh xám, cắt, đổi kích thước, giảm mức xám và ống hút màu."),
            ("Điều chỉnh độ sáng, tương phản và histogram", "Âm bản, Log, Gamma, kéo giãn tương phản, cân bằng histogram và CLAHE."),
        ]
        title, note = titles[index] if index < 2 else (f"M{index + 1} · Sẵn sàng phát triển", "Canvas được dùng chung; hãy thêm công cụ của mô-đun vào bảng bên phải.")
        self.workspace_title.setText(title)
        self.workspace_note.setText(note)
        self.inspector_title.setText(title)
        self.inspector_description.setText(note)


    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", IMAGE_FILTER)
        if not path:
            return
        image = processing.load_image(path)
        if image.isNull():
            QMessageBox.warning(self, "Không thể mở ảnh", "Tệp ảnh không hợp lệ hoặc không thể đọc.")
            return
        self.current_path = Path(path)
        self.original_image = image.copy()
        self.image = image.copy()
        self.canvas.mode = "view"
        self.canvas.set_image(self.image)
        self._refresh_info()
        self.statusBar().showMessage(f"Đã mở: {self.current_path.name}")

    def save_image(self) -> None:
        if not self._require_image():
            return
        try:
            target = processing.save_image_to_output(self.image, self.current_path.name if self.current_path else "photo")
        except OSError as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
            return
        self.statusBar().showMessage(f"Đã lưu ảnh: Output/{target.name}")

    def reset_image(self) -> None:
        if self.original_image is None:
            return
        self.image = self.original_image.copy()
        self.canvas.mode = "view"
        self.canvas.set_image(self.image)
        self._refresh_info()
        self.statusBar().showMessage("Đã khôi phục ảnh gốc.")

    def show_image_info(self) -> None:
        if not self._require_image():
            return
        QMessageBox.information(self, "Thông tin ảnh", self._image_info_text())

    def convert_to_grayscale(self) -> None:
        if not self._require_image():
            return
        self.image = processing.convert_to_grayscale(self.image)
        self._refresh_image("Đã chuyển ảnh sang mức xám.")

    def toggle_crop_mode(self) -> None:
        if not self._require_image():
            return
        self.canvas.mode = "view" if self.canvas.mode == "crop" else "crop"
        self.canvas.clear_selection()
        self._update_mode_label()

    def apply_crop(self) -> None:
        if not self._require_image():
            return
        rect = self.canvas.selected_rect().intersected(self.image.rect())
        if rect.width() < 2 or rect.height() < 2:
            QMessageBox.information(self, "Chưa chọn vùng", "Kéo chuột trên ảnh để chọn vùng cần cắt.")
            return
        self.image = processing.crop_image(self.image, rect)
        self.canvas.mode = "view"
        self._refresh_image(f"Đã cắt vùng {rect.width()} × {rect.height()} px.")

    def resize_image(self) -> None:
        if not self._require_image():
            return
        dialog = ResizeDialog(self.image.width(), self.image.height(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        width, height = dialog.width_spin.value(), dialog.height_spin.value()
        self.image = processing.resize_image(self.image, width, height)
        self._refresh_image(f"Đã đổi kích thước thành {width} × {height} px.")

    def toggle_picker_mode(self) -> None:
        if not self._require_image():
            return
        self.canvas.mode = "view" if self.canvas.mode == "picker" else "picker"
        self._update_mode_label()

    def pick_color(self, x: int, y: int) -> None:
        if self.image is None:
            return
        color = self.image.pixelColor(x, y)
        self.color_swatch.setStyleSheet(f"background: rgb({color.red()}, {color.green()}, {color.blue()}); border-radius: 6px;")
        self.color_label.setText(f"Tọa độ: ({x}, {y})\nB: {color.blue()}\nG: {color.green()}\nR: {color.red()}")
        self.statusBar().showMessage(f"Đã lấy màu tại ({x}, {y}).")

    def update_selection_info(self, rect: QRect) -> None:
        if rect.isNull() or rect.width() < 2 or rect.height() < 2:
            self.selection_label.setText("Chưa chọn vùng nào")
            return
        self.selection_label.setText(f"x1={rect.left()}, y1={rect.top()}\nx2={rect.right()}, y2={rect.bottom()}\nKích thước: {rect.width()} × {rect.height()} px")

    def reduce_levels(self) -> None:
        """Giao diện cho phần [TC]: giảm mức xám bằng thanh trượt số mức L."""
        if not self._require_image():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Giảm mức xám [TC]")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Chọn số mức xám L. Phần thuật toán giảm mức xám do bạn tự cài đặt."))
        label = QLabel("L = 128")
        slider = QSlider(Qt.Orientation.Horizontal)
        levels = [2, 4, 8, 16, 32, 64, 128]
        slider.setRange(0, len(levels) - 1)
        slider.setValue(len(levels) - 1)
        slider.valueChanged.connect(lambda index: label.setText(f"L = {levels[index]}"))
        layout.addWidget(label)
        layout.addWidget(slider)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = processing.reduce_gray_levels(self.image, levels[slider.value()])
            if result is None:
                QMessageBox.information(self, "Phần tự code", "Hãy cài đặt reduce_gray_levels() để tạo ảnh kết quả.")
            else:
                self.image = result
                self._refresh_image(f"Đã giảm mức xám còn L = {levels[slider.value()]}.")

    # ===== M2 - Điều chỉnh độ sáng, tương phản và histogram =====
    def open_adjustment_dialog(self) -> None:
        self.select_module(1)

    def apply_negative(self) -> None:
        if not self._require_image():
            return
        self.image = processing.invert_image(self.image)
        self._refresh_image("Đã áp dụng âm bản: s = 255 - r.")

    def apply_log_transform(self) -> None:
        """Gọi phần [TC] biến đổi log và chỉ cập nhật UI khi có ảnh trả về."""
        if not self._require_image():
            return
        result = processing.log_transform(self.image)
        self._apply_tc_result(result, "biến đổi Log")

    def apply_gamma_transform(self, gamma: float) -> None:
        """Gọi phần [TC] biến đổi gamma và chỉ cập nhật UI khi có ảnh trả về."""
        if not self._require_image():
            return
        result = processing.gamma_transform(self.image, gamma)
        self._apply_tc_result(result, f"biến đổi Gamma (γ = {gamma:.1f})")

    def apply_contrast_stretch(self, black: int, white: int) -> None:
        if not self._require_image():
            return
        if black >= white:
            QMessageBox.warning(self, "Giá trị không hợp lệ", "Mức đen a phải nhỏ hơn mức trắng b.")
            return
        self.image = processing.stretch_contrast(self.image, black, white)
        self._refresh_image(f"Đã kéo giãn tương phản với a = {black}, b = {white}.")

    def apply_histogram_equalization(self) -> None:
        """Gọi phần [TC] cân bằng histogram theo CDF."""
        if not self._require_image():
            return
        result = processing.equalize_histogram_manual(self.image)
        self._apply_tc_result(result, "cân bằng histogram")

    def compare_histogram_with_opencv(self) -> None:
        """Tạo ảnh tham chiếu OpenCV để đối chiếu kết quả hàm [TC]."""
        if not self._require_image():
            return
        self.image = processing.equalize_histogram_opencv(self.image)
        self._refresh_image("Đã áp dụng cân bằng histogram OpenCV để so sánh.")

    def apply_clahe(self, clip_limit: int, grid_size: int) -> None:
        if not self._require_image():
            return
        self.image = processing.apply_clahe(self.image, float(clip_limit), grid_size)
        self._refresh_image(f"Đã áp dụng CLAHE: clipLimit={clip_limit}, lưới={grid_size}×{grid_size}.")

    def _apply_tc_result(self, result: Optional[QImage], operation_name: str) -> None:
        if result is None or result.isNull():
            QMessageBox.information(self, "Phần tự code", f"Hãy cài đặt hàm {operation_name} để tạo ảnh kết quả.")
            return
        self.image = result.copy()
        self._refresh_image(f"Đã áp dụng {operation_name}.")

    def _refresh_image(self, message: str) -> None:
        self.canvas.mode = "view"
        self.canvas.set_image(self.image)
        self._refresh_info()
        self.statusBar().showMessage(message)

    def _refresh_info(self) -> None:
        self.info_label.setText(self._image_info_text() if self.image is not None else "Chưa có ảnh")
        self._update_mode_label()

    def _image_info_text(self) -> str:
        if self.image is None:
            return "Chưa có ảnh"
        info = processing.image_info(self.image)
        return (f"Rộng × cao: {info['width']} × {info['height']} px\n"
                f"Số kênh: {info['channels']}\nKiểu dữ liệu: {info['dtype']}\n"
                f"Dung lượng chưa nén: {info['raw_bytes']:,} byte")

    def _update_mode_label(self) -> None:
        names = {"view": "Xem ảnh", "crop": "Chọn vùng cắt - kéo chuột trên ảnh", "picker": "Ống hút màu - nhấp vào ảnh"}
        self.mode_label.setText(f"Chế độ: {names[self.canvas.mode]}")

    def _require_image(self) -> bool:
        if self.image is not None and not self.image.isNull():
            return True
        QMessageBox.information(self, "Chưa có ảnh", "Hãy mở ảnh trước khi dùng chức năng này.")
        return False

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background: #f5f7fb; color: #1f2937; }
            QMenuBar { background: white; padding: 4px 10px; }
            QMenuBar::item { padding: 6px 10px; border-radius: 4px; }
            QMenuBar::item:selected { background: #e7efff; }
            #appTitle { color: #173b78; font-size: 27px; font-weight: 700; }
            #subtitle, #modeLabel { color: #64748b; font-size: 13px; }
            #primaryButton { background: #2563eb; color: white; border: 0; border-radius: 7px; padding: 9px 14px; font-weight: 700; }
            #primaryButton:hover { background: #1d4ed8; }
            #secondaryButton { background: white; color: #2563eb; border: 1px solid #9ab8fa; border-radius: 7px; padding: 9px 14px; font-weight: 700; }
            #secondaryButton:hover { background: #eaf1ff; }
            #toolButton { background: white; border: 1px solid #d5dfef; border-radius: 7px; padding: 8px 10px; color: #29446e; font-weight: 600; }
            #toolButton:hover { background: #eaf1ff; border-color: #8dadf0; }
            #moduleNav, #workspace, #inspector { background: white; border: 1px solid #dbe4f1; border-radius: 10px; }
            #navTitle { color: #718096; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; padding: 2px 5px 8px 5px; }
            #moduleButton { background: transparent; border: 0; border-radius: 7px; color: #42526b; padding: 8px; text-align: left; }
            #moduleButton:hover { background: #eef4ff; }
            #moduleButton:checked { background: #2563eb; color: white; font-weight: 700; }
            #navHint, #placeholderText { color: #718096; font-size: 12px; line-height: 1.45; }
            #workspaceTitle, #inspectorTitle { color: #1e3a6d; font-size: 17px; font-weight: 700; }
            #workspaceNote, #inspectorDescription { color: #6b7a90; font-size: 12px; }
            #sectionLabel { color: #46648f; font-size: 12px; font-weight: 700; padding-top: 5px; }
            #toolScroll { background: transparent; }
            #sidePanel { background: white; border: 1px solid #dbe4f1; border-radius: 10px; }
            #panelTitle { color: #1e3a6d; font-size: 15px; font-weight: 700; }
            #infoLabel { color: #475569; line-height: 1.4; }
            #colorSwatch { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; }
            #separator { color: #dce5f1; }
            #imageCanvas { background: white; border: 2px dashed #c8d6eb; border-radius: 10px; color: #74839a; font-size: 15px; }
            QStatusBar { background: white; color: #64748b; border-top: 1px solid #dbe4f1; }
        """)
