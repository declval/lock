from typing import Callable

from PySide6.QtCore import Property, QEasingCurve, QEvent, QPropertyAnimation, QSize, Qt, Slot
from PySide6.QtGui import QColor, QEnterEvent, QIcon, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QPushButton,
                               QScrollArea, QStatusBar, QToolBar, QVBoxLayout,
                               QWidget)
from nacl.exceptions import CryptoError

from helpers import layout_delete, line_edit_reset_color, password_generate, widget_center
import lock

MARGIN = 20
SPACING = 10

BUTTON_ANIMATION_DURATION = 200
BUTTON_ANIMATION_COLOR_STEP = 10

MAX_GENERATED_PASSWORD_LENGTH = 1024

SCROLL_TO_BOTTOM_ANIMATION_DURATION = 600

STATUSBAR_TIMEOUT = 4000

WINDOW_WIDTH = 450
WINDOW_HEIGHT = 450


class AnimatedPushButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)

        # Initialized after show() method is executed because self.get_color()
        # returns an incorrect result at this point
        self.initial_start_color = None
        self.initial_end_color = None

    def animation(self, lighten: bool) -> QPropertyAnimation:
        animation = QPropertyAnimation(self, b'color', self)
        animation.setDuration(BUTTON_ANIMATION_DURATION)
        start_color = self.get_color()
        if self.initial_start_color is None:
            self.initial_start_color = start_color
            self.initial_end_color = QColor(
                self.initial_start_color.red() + BUTTON_ANIMATION_COLOR_STEP,
                self.initial_start_color.green() + BUTTON_ANIMATION_COLOR_STEP,
                self.initial_start_color.blue() + BUTTON_ANIMATION_COLOR_STEP
            )
        if lighten:
            end_color = self.initial_end_color
        else:
            end_color = self.initial_start_color
        animation.setStartValue(start_color)
        animation.setEndValue(end_color)
        return animation

    def enterEvent(self, event: QEnterEvent) -> None:
        animation = self.animation(lighten=True)
        animation.start()
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        animation = self.animation(lighten=False)
        animation.start()
        return super().leaveEvent(event)

    def get_color(self) -> QColor:
        palette = self.palette()
        return palette.color(QPalette.ColorRole.Button)

    def set_color(self, color: QColor) -> None:
        property = 'background-color'
        value = f'rgb({color.red()}, {color.green()}, {color.blue()})'
        self.setStyleSheet(f'{property}: {value};')

    color = Property(QColor, get_color, set_color)


class FieldPair(QWidget):
    def __init__(self, main_window: QMainWindow, name: str = '', definition: str = '', password: bool = False) -> None:
        super().__init__()

        self.main_window = main_window

        self.icon_size = QSize(12, 12)
        self.copy_icon = QIcon(':/copy.svg')
        self.minus_icon = QIcon(':/minus.svg')

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING)

        self.name_line_edit = QLineEdit(name)
        self.name_line_edit.setPlaceholderText('Name')
        self.name_line_edit.textChanged.connect(line_edit_reset_color(self.name_line_edit))

        layout.addWidget(self.name_line_edit)

        self.definition_line_edit = QLineEdit(definition)
        self.definition_line_edit.textChanged.connect(line_edit_reset_color(self.definition_line_edit))

        layout.addWidget(self.definition_line_edit)

        copy_push_button = QPushButton()
        copy_push_button.setIcon(self.copy_icon)
        copy_push_button.setIconSize(self.icon_size)
        copy_push_button.setProperty('class', 'button-icon-only')

        def wrapper_copy_to_clipboard(definition_line_edit: QLineEdit) -> Callable[[], None]:
            return lambda: self.copy_to_clipboard(definition_line_edit)

        copy_push_button.clicked.connect(wrapper_copy_to_clipboard(self.definition_line_edit))

        layout.addWidget(copy_push_button)

        if password:
            self.name_line_edit.setReadOnly(True)
            self.definition_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.definition_line_edit.setPlaceholderText('Password')
        else:
            self.definition_line_edit.setPlaceholderText('Definition')

            minus_push_button = QPushButton()
            minus_push_button.setIcon(self.minus_icon)
            minus_push_button.setIconSize(self.icon_size)
            minus_push_button.setProperty('class', 'button-icon-only')

            def wrapper_minus(layout: QHBoxLayout) -> Callable[[], None]:
                return lambda: self.minus(layout)

            minus_push_button.clicked.connect(wrapper_minus(layout))

            layout.addWidget(minus_push_button)

        self.setLayout(layout)

    @Slot()
    def copy_to_clipboard(self, definition_line_edit: QLineEdit) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(definition_line_edit.text())
        self.main_window.statusBar().showMessage('Copied to clipboard', STATUSBAR_TIMEOUT)

    @Slot()
    def minus(self, layout: QHBoxLayout) -> None:
        layout_delete(layout)
        self.deleteLater()
        self.updateGeometry()


class GeneratePassword(QWidget):
    def __init__(self, password_line_edit: QLineEdit) -> None:
        super().__init__()

        program_icon = QIcon(':/icon.png')

        self.setFixedWidth(WINDOW_WIDTH)
        self.setWindowIcon(program_icon)
        self.setWindowTitle('Generate password')

        layout = QVBoxLayout()
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.setSpacing(SPACING)

        def wrapper_update_password(password_line_edit: QLineEdit) -> Callable[[], None]:
            return lambda: self.update_password(password_line_edit)

        self.length_line_edit = QLineEdit()
        self.length_line_edit.setPlaceholderText(f'Password length (up to and including {MAX_GENERATED_PASSWORD_LENGTH})')
        self.length_line_edit.returnPressed.connect(wrapper_update_password(password_line_edit))
        self.length_line_edit.textChanged.connect(line_edit_reset_color(self.length_line_edit))

        layout.addWidget(self.length_line_edit)

        self.choose_label = QLabel('Choose what characters a password should consist of:')

        layout.addWidget(self.choose_label)

        self.lowercase_checkbox = QCheckBox('Lowercase letters')
        self.lowercase_checkbox.setChecked(True)
        self.lowercase_checkbox.stateChanged.connect(lambda: self.choose_label.setStyleSheet('color: #535353;'))

        layout.addWidget(self.lowercase_checkbox)

        self.uppercase_checkbox = QCheckBox('Uppercase letters')
        self.uppercase_checkbox.setChecked(True)
        self.uppercase_checkbox.stateChanged.connect(lambda: self.choose_label.setStyleSheet('color: #535353;'))

        layout.addWidget(self.uppercase_checkbox)

        self.digits_checkbox = QCheckBox('Digits')
        self.digits_checkbox.setChecked(True)
        self.digits_checkbox.stateChanged.connect(lambda: self.choose_label.setStyleSheet('color: #535353;'))

        layout.addWidget(self.digits_checkbox)

        self.punctuation_checkbox = QCheckBox('Punctuation')
        self.punctuation_checkbox.stateChanged.connect(lambda: self.choose_label.setStyleSheet('color: #535353;'))

        layout.addWidget(self.punctuation_checkbox)

        generate_push_button = AnimatedPushButton('Generate')
        generate_push_button.clicked.connect(wrapper_update_password(password_line_edit))

        layout.addWidget(generate_push_button)

        self.setLayout(layout)

    @Slot()
    def update_password(self, password_line_edit: QLineEdit) -> None:
        errors = False

        try:
            password_length = int(self.length_line_edit.text())
            if password_length <= 0 or password_length > MAX_GENERATED_PASSWORD_LENGTH:
                self.length_line_edit.setStyleSheet('color: #c15959;')
                errors = True
        except ValueError:
            self.length_line_edit.setStyleSheet('color: #c15959;')
            errors = True

        if (not self.lowercase_checkbox.isChecked()
                and not self.uppercase_checkbox.isChecked()
                and not self.digits_checkbox.isChecked()
                and not self.punctuation_checkbox.isChecked()):
            self.choose_label.setStyleSheet('color: #c15959;')
            errors = True

        if errors:
            return

        password = password_generate(
            password_length,
            lowercase=self.lowercase_checkbox.isChecked(),
            uppercase=self.uppercase_checkbox.isChecked(),
            digits=self.digits_checkbox.isChecked(),
            punctuation=self.punctuation_checkbox.isChecked()
        )
        password_line_edit.setText(password)
        self.hide()
        layout_delete(self.layout())
        self.deleteLater()


class CentralWidget(QWidget):

    def __init__(self, pm: lock.PasswordManager, main_window: QMainWindow) -> None:
        super().__init__()

        self.pm = pm
        self.main_window = main_window

        self.icon_size = QSize(12, 12)
        self.plus_icon = QIcon(':/plus.svg')
        self.to_delete: list[str] = []

        layout = QVBoxLayout()
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.setSpacing(MARGIN)

        create_layout = QHBoxLayout()
        create_layout.setSpacing(SPACING)

        name_line_edit = QLineEdit()
        name_line_edit.setPlaceholderText('New entry name')

        def wrapper_create_new_entry(name_line_edit: QLineEdit) -> Callable[[], None]:
            return lambda: self.create_new_entry(name_line_edit)

        name_line_edit.returnPressed.connect(wrapper_create_new_entry(name_line_edit))
        name_line_edit.textChanged.connect(line_edit_reset_color(name_line_edit))

        create_layout.addWidget(name_line_edit)

        create_push_button = AnimatedPushButton('Create')
        create_push_button.setProperty('class', 'button-alt')
        create_push_button.clicked.connect(wrapper_create_new_entry(name_line_edit))

        create_layout.addWidget(create_push_button)

        layout.addLayout(create_layout)

        self.scroll_area_widget_layout = QVBoxLayout()
        self.scroll_area_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area_widget_layout.setSpacing(SPACING)

        self.scroll_area_widget_layout.addStretch()

        for entry_name in self.pm:
            entry_group_box = self.create_entry(entry_name, self.pm[entry_name])
            index =  self.scroll_area_widget_layout.count() - 1
            self.scroll_area_widget_layout.insertWidget(index, entry_group_box)

        scroll_area_widget = QWidget()
        scroll_area_widget.setLayout(self.scroll_area_widget_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(scroll_area_widget)
        self.scroll_area.setWidgetResizable(True)

        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def create_entry(self, entry_name: str, entry_value: dict[str, str]) -> QGroupBox:
        entry_group_box = QGroupBox(entry_name)

        entry_layout = QVBoxLayout()
        entry_layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        entry_layout.setSpacing(SPACING)

        field_pairs_layout = QVBoxLayout()

        for entry_value_name, entry_value_definition in entry_value.items():
            field_pair = FieldPair(
                self.main_window,
                entry_value_name,
                entry_value_definition,
                True if entry_value_name == 'Password' else False
            )

            if entry_value_name == 'Password':
                field_pairs_layout.insertWidget(0, field_pair)

                password_buttons_layout = QHBoxLayout()

                password_buttons_layout.addStretch()

                generate_push_button = AnimatedPushButton('Generate')

                def wrapper_open_generate_password(password_line_edit: QLineEdit) -> Callable[[], None]:
                    return lambda: self.open_generate_password(password_line_edit)

                generate_push_button.clicked.connect(wrapper_open_generate_password(field_pair.definition_line_edit))

                password_buttons_layout.addWidget(generate_push_button)

                show_push_button = AnimatedPushButton('Show')

                def wrapper_show_hide_password(password_line_edit: QLineEdit) -> Callable[[], None]:
                    return lambda: self.show_hide_password(password_line_edit)

                show_push_button.clicked.connect(wrapper_show_hide_password(field_pair.definition_line_edit))

                password_buttons_layout.addWidget(show_push_button)

                field_pairs_layout.insertLayout(1, password_buttons_layout)
            else:
                field_pairs_layout.addWidget(field_pair)

        entry_layout.addLayout(field_pairs_layout)

        plus_push_button = QPushButton()
        plus_push_button.setIcon(self.plus_icon)
        plus_push_button.setIconSize(self.icon_size)
        plus_push_button.setProperty('class', 'button-icon-only')

        def wrapper_plus(field_pairs_layout: QVBoxLayout) -> Callable[[], None]:
            return lambda: self.plus(field_pairs_layout)

        plus_push_button.clicked.connect(wrapper_plus(field_pairs_layout))

        entry_layout.addWidget(plus_push_button, 0, Qt.AlignmentFlag.AlignRight)

        save_push_button = AnimatedPushButton('Save')

        def wrapper_save(entry_group_box: QGroupBox) -> Callable[[], None]:
            return lambda: self.save(entry_group_box)

        save_push_button.clicked.connect(wrapper_save(entry_group_box))

        entry_layout.addWidget(save_push_button)

        delete_push_button = AnimatedPushButton('Delete')
        delete_push_button.setProperty('class', 'button-warn')

        def wrapper_delete(entry_group_box: QGroupBox) -> Callable[[], None]:
            return lambda: self.delete(entry_group_box)

        delete_push_button.clicked.connect(wrapper_delete(entry_group_box))

        entry_layout.addWidget(delete_push_button)

        # Necessary to get rid of UI flicker when fields are removed with the minus button
        entry_layout.addStretch()

        entry_group_box.setLayout(entry_layout)
        return entry_group_box

    @Slot()
    def create_new_entry(self, name_line_edit: QLineEdit) -> None:
        entry_name = name_line_edit.text()
        entry_names = [entry_group_box.title() for entry_group_box in self.findChildren(QGroupBox)]
        if not entry_name or not entry_name.isalnum() or entry_name in entry_names:
            if not entry_name:
                self.main_window.statusBar().showMessage('Entry name is empty', STATUSBAR_TIMEOUT)
            if not entry_name.isalnum():
                self.main_window.statusBar().showMessage('Entry name can only consist of alphanumeric characters', STATUSBAR_TIMEOUT)
            if entry_name in entry_names:
                self.main_window.statusBar().showMessage(f'Entry {entry_name} already exists', STATUSBAR_TIMEOUT)
            name_line_edit.setStyleSheet('color: #c15959;')
            return
        entry_group_box = self.create_entry(entry_name, {'Password': ''})
        index =  self.scroll_area_widget_layout.count() - 1
        self.scroll_area_widget_layout.insertWidget(index, entry_group_box)
        self.scroll_area.widget().updateGeometry()
        name_line_edit.clear()

        # Animated scroll to bottom
        self.prev_max = 0
        def range_changed(min: int, max: int) -> None:
            if max > self.prev_max:
                self.prev_max = max

                vertical_scroll_bar = self.scroll_area.verticalScrollBar()

                animation = QPropertyAnimation(vertical_scroll_bar, b'value', vertical_scroll_bar)
                animation.setDuration(SCROLL_TO_BOTTOM_ANIMATION_DURATION)
                animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
                animation.setEndValue(max)
                animation.start()

                self.scroll_area.verticalScrollBar().rangeChanged.disconnect()
        if entry_names:
            self.scroll_area.verticalScrollBar().rangeChanged.connect(range_changed)

    @Slot()
    def delete(self, entry_group_box: QGroupBox) -> None:
        self.to_delete.append(entry_group_box.title())
        entry_group_box.deleteLater()

    @Slot()
    def open_generate_password(self, password_line_edit: QLineEdit) -> None:
        self.generate_password = GeneratePassword(password_line_edit)
        self.generate_password.show()
        widget_center(self.generate_password)

    @Slot()
    def plus(self, field_pairs_layout: QVBoxLayout) -> None:
        field_pair = FieldPair(self.main_window)
        field_pairs_layout.addWidget(field_pair)
        self.scroll_area.widget().updateGeometry()

    @Slot()
    def save(self, entry_group_box: QGroupBox) -> bool:
        is_empty = False

        field_pairs = entry_group_box.findChildren(FieldPair)

        result = {}

        for field_pair in field_pairs:
            if not field_pair.name_line_edit.text():
                field_pair.name_line_edit.setStyleSheet('color: #c15959;')

            if not field_pair.definition_line_edit.text():
                field_pair.definition_line_edit.setStyleSheet('color: #c15959;')

            if field_pair.name_line_edit.text() and field_pair.definition_line_edit.text():
                result[field_pair.name_line_edit.text()] = field_pair.definition_line_edit.text()
            else:
                is_empty = True

        if is_empty:
            self.main_window.statusBar().showMessage('Some fields are empty', STATUSBAR_TIMEOUT)
            return False

        self.pm[entry_group_box.title()] = result

        self.main_window.statusBar().showMessage('Saved', STATUSBAR_TIMEOUT)
        return True

    @Slot()
    def save_all(self):
        for entry_name in self.to_delete:
            try:
                del self.pm[entry_name]
            except KeyError:
                pass
        self.to_delete.clear()

        is_saved = True

        for entry_group_box in self.findChildren(QGroupBox):
            if not self.save(entry_group_box):
                is_saved = False

        if is_saved:
            self.main_window.statusBar().showMessage('Saved all', STATUSBAR_TIMEOUT)
        else:
            self.main_window.statusBar().showMessage('Some fields are empty', STATUSBAR_TIMEOUT)

    @Slot()
    def show_hide_password(self, password_line_edit: QLineEdit) -> None:
        if password_line_edit.echoMode() == QLineEdit.EchoMode.Password:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)


class MainWindow(QMainWindow):
    def __init__(self, pm: lock.PasswordManager) -> None:
        super().__init__()

        program_icon = QIcon(':/icon.png')

        self.setFixedWidth(WINDOW_WIDTH)
        self.setFixedHeight(WINDOW_HEIGHT)
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.setWindowIcon(program_icon)
        self.setWindowTitle(lock.PROGRAM_NAME)

        central_widget = CentralWidget(pm, self)

        self.setCentralWidget(central_widget)

        save_all_push_button = AnimatedPushButton('Save all')
        save_all_push_button.clicked.connect(central_widget.save_all)

        tool_bar = QToolBar()
        tool_bar.addWidget(save_all_push_button)
        tool_bar.setMovable(False)

        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, tool_bar)

        status_bar = QStatusBar()
        status_bar.setSizeGripEnabled(False)

        self.setStatusBar(status_bar)


class PasswordWidget(QWidget):

    def __init__(self, app: QApplication) -> None:
        super().__init__()

        self.app = app

        program_icon = QIcon(':/icon.png')

        self.setFixedWidth(WINDOW_WIDTH)
        self.setWindowIcon(program_icon)
        self.setWindowTitle(lock.PROGRAM_NAME)

        layout = QVBoxLayout()
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.setSpacing(SPACING)

        continue_push_button_text = 'Decrypt'

        if lock.DATABASE_PATH.exists():
            label = QLabel(f'<div>Enter a password for a database at {lock.DATABASE_PATH}</div>')
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setProperty('class', 'info')
            layout.addWidget(label)
        else:
            continue_push_button_text = 'Create'
            label = QLabel('<div style="margin-bottom: 10px;">Database does not exist yet</div>'
                          f'<div style="font-size: 10px;">It will be created at {lock.DATABASE_PATH}</div>')
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setProperty('class', 'info')
            layout.addWidget(label)

        self.password_line_edit = QLineEdit()
        self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_line_edit.setPlaceholderText('Database password')
        self.password_line_edit.returnPressed.connect(self.run)
        self.password_line_edit.textChanged.connect(line_edit_reset_color(self.password_line_edit))

        layout.addWidget(self.password_line_edit)

        continue_push_button = AnimatedPushButton(continue_push_button_text)
        continue_push_button.setProperty('class', 'button-alt')
        continue_push_button.clicked.connect(self.run)

        layout.addWidget(continue_push_button)

        self.setLayout(layout)

    @Slot()
    def run(self) -> None:
        if not self.password_line_edit.text():
            self.password_line_edit.setStyleSheet('color: #c15959;')
            return

        try:
            pm = lock.PasswordManager(lock.DATABASE_PATH, self.password_line_edit.text())
        except CryptoError:
            self.password_line_edit.setStyleSheet('color: #c15959;')
            return

        self.hide()
        layout_delete(self.layout())
        self.deleteLater()

        main_window = MainWindow(pm)
        main_window.show()
        widget_center(main_window)
