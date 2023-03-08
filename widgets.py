from typing import Callable

from PySide6.QtCore import (Property, QEasingCurve, QEvent, QPropertyAnimation,
                            QSize, QTimer, Qt, Slot)
from PySide6.QtGui import QCloseEvent, QColor, QEnterEvent, QIcon, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QPushButton, QScrollArea, QStatusBar, QToolBar,
                               QVBoxLayout, QWidget)
from nacl.exceptions import CryptoError

from helpers import password_generate, widget_center
from lock import DATABASE_PATH, PROGRAM_NAME, PasswordManager

BUTTON_ANIMATION_COLOR_DELTA = 10
BUTTON_ANIMATION_DURATION = 200

GENERATED_PASSWORD_LENGTH_MAX = 1024
GENERATED_PASSWORD_LENGTH_MIN = 4

ICON_SIZE = 12

LAYOUT_MARGIN = 20
LAYOUT_SPACING = 10

SCROLL_AREA_ANIMATION_DURATION = 600

STATUS_BAR_MESSAGE_TIMEOUT = 4000

WINDOW_HEIGHT = 480
WINDOW_WIDTH = 480


class AnimatedPushButton(QPushButton):

    def __init__(self, text: str = '') -> None:
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
            red = self.initial_start_color.red() + BUTTON_ANIMATION_COLOR_DELTA
            green = self.initial_start_color.green() + BUTTON_ANIMATION_COLOR_DELTA
            blue = self.initial_start_color.blue() + BUTTON_ANIMATION_COLOR_DELTA
            self.initial_end_color = QColor(
                red if red <= 255 else 255,
                green if green <= 255 else 255,
                blue if blue <= 255 else 255
            )
        if lighten:
            end_color = self.initial_end_color
        else:
            end_color = self.initial_start_color
        animation.setStartValue(start_color)
        animation.setEndValue(end_color)
        return animation

    def enterEvent(self, event: QEnterEvent) -> None:
        self.animation(lighten=True).start()
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.animation(lighten=False).start()
        return super().leaveEvent(event)

    def get_color(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.Button)

    def set_color(self, color: QColor) -> None:
        property = 'background-color'
        value = f'rgb({color.red()}, {color.green()}, {color.blue()})'
        self.setStyleSheet(f'{property}: {value};')

    color = Property(QColor, get_color, set_color)


class LineEdit(QLineEdit):

    def __init__(self, text: str = '') -> None:
        super().__init__(text)

        self.validation_state = ValidationState(self)
        self.textChanged.connect(self.validation_state.set_valid)


class Entry(QGroupBox):

    def __init__(self, title: str) -> None:
        super().__init__(title)

        self.saved_field_pair_removed = False

    def saved(self) -> bool:
        if self.saved_field_pair_removed:
            return False
        for field_pair in self.findChildren(FieldPair):
            if not field_pair.saved():
                return False
        return True


class ScrollArea(QScrollArea):

    def __init__(self) -> None:
        super().__init__()

        self.saved_entry_removed = False

    def saved(self) -> bool:
        if self.saved_entry_removed:
            return False
        for entry in self.findChildren(Entry):
            if not entry.saved():
                return False
        return True


class CentralWidget(QWidget):

    def __init__(self, pm: PasswordManager, main_window: QMainWindow) -> None:
        super().__init__()

        self.pm = pm
        self.main_window = main_window

        self.plus_icon = QIcon(':/plus.svg')
        self.to_delete: list[str] = []

        layout = QVBoxLayout()
        layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        layout.setSpacing(LAYOUT_MARGIN)

        create_layout = QHBoxLayout()
        create_layout.setSpacing(LAYOUT_SPACING)

        name_line_edit = LineEdit()
        name_line_edit.setPlaceholderText('New entry name')

        def wrapper_create_new_entry(name_line_edit: LineEdit) -> Callable[[], None]:
            return lambda: self.create_new_entry(name_line_edit)

        name_line_edit.returnPressed.connect(wrapper_create_new_entry(name_line_edit))

        create_layout.addWidget(name_line_edit)

        create_push_button = AnimatedPushButton('Create')
        create_push_button.setProperty('class', 'button-alt')
        create_push_button.clicked.connect(wrapper_create_new_entry(name_line_edit))

        create_layout.addWidget(create_push_button)

        layout.addLayout(create_layout)

        self.scroll_area_widget_layout = QVBoxLayout()
        self.scroll_area_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area_widget_layout.setSpacing(LAYOUT_SPACING)

        self.scroll_area_widget_layout.addStretch()

        for entry_name in self.pm:
            entry = self.create_entry(entry_name, self.pm[entry_name])
            index = self.scroll_area_widget_layout.count() - 1
            self.scroll_area_widget_layout.insertWidget(index, entry)

        scroll_area_widget = QWidget()
        scroll_area_widget.setLayout(self.scroll_area_widget_layout)

        self.scroll_area = ScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(scroll_area_widget)
        self.scroll_area.setWidgetResizable(True)

        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def create_entry(self, entry_name: str, entry_value: dict[str, str]) -> Entry:
        entry = Entry(entry_name)

        entry_layout = QVBoxLayout()
        entry_layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        entry_layout.setSpacing(LAYOUT_SPACING)

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

                generate_push_button = AnimatedPushButton('Generate password')

                def wrapper_open_generate_password(password_line_edit: LineEdit) -> Callable[[], None]:
                    return lambda: self.open_generate_password(password_line_edit)

                generate_push_button.clicked.connect(wrapper_open_generate_password(field_pair.definition_line_edit))

                password_buttons_layout.addWidget(generate_push_button)

                field_pairs_layout.insertLayout(1, password_buttons_layout)
            else:
                field_pairs_layout.addWidget(field_pair)

        entry_layout.addLayout(field_pairs_layout)

        plus_push_button = AnimatedPushButton()
        plus_push_button.setIcon(self.plus_icon)
        plus_push_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        plus_push_button.setProperty('class', 'button-icon-only')

        def wrapper_plus(field_pairs_layout: QVBoxLayout) -> Callable[[], None]:
            return lambda: self.plus(field_pairs_layout)

        plus_push_button.clicked.connect(wrapper_plus(field_pairs_layout))

        entry_layout.addWidget(plus_push_button, 0, Qt.AlignmentFlag.AlignRight)

        save_push_button = AnimatedPushButton('Save')

        def wrapper_save(entry: Entry) -> Callable[[], None]:
            return lambda: self.save(entry)

        save_push_button.clicked.connect(wrapper_save(entry))

        entry_layout.addWidget(save_push_button)

        delete_push_button = AnimatedPushButton('Delete')
        delete_push_button.setProperty('class', 'button-warn')

        def wrapper_remove_entry(entry: Entry) -> Callable[[], None]:
            return lambda: self.remove_entry(entry)

        delete_push_button.clicked.connect(wrapper_remove_entry(entry))

        entry_layout.addWidget(delete_push_button)

        # Necessary to get rid of UI flicker when fields are removed with the minus button
        entry_layout.addStretch()

        entry.setLayout(entry_layout)
        return entry

    @Slot()
    def create_new_entry(self, name_line_edit: LineEdit) -> None:
        entry_name = name_line_edit.text()
        entry_names = [entry.title() for entry in self.findChildren(Entry)]
        if not entry_name or not entry_name.isalnum() or entry_name in entry_names:
            if not entry_name:
                self.main_window.statusBar().showMessage('Entry name is empty', STATUS_BAR_MESSAGE_TIMEOUT)
            elif not entry_name.isalnum():
                self.main_window.statusBar().showMessage('Entry name can only consist of alphanumeric characters', STATUS_BAR_MESSAGE_TIMEOUT)
            elif entry_name in entry_names:
                self.main_window.statusBar().showMessage(f'Entry {entry_name} already exists', STATUS_BAR_MESSAGE_TIMEOUT)
            else:
                raise RuntimeError('Unhandled condition')
            name_line_edit.validation_state.set_invalid()
            return
        entry = self.create_entry(entry_name, {'Password': ''})
        index =  self.scroll_area_widget_layout.count() - 1
        self.scroll_area_widget_layout.insertWidget(index, entry)
        self.scroll_area.widget().updateGeometry()
        name_line_edit.clear()

        # Animated scroll to bottom
        self.prev_max = 0
        def range_changed(min: int, max: int) -> None:
            if max > self.prev_max:
                self.prev_max = max

                vertical_scroll_bar = self.scroll_area.verticalScrollBar()

                animation = QPropertyAnimation(vertical_scroll_bar, b'value', vertical_scroll_bar)
                animation.setDuration(SCROLL_AREA_ANIMATION_DURATION)
                animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
                animation.setEndValue(max)
                animation.start()

                self.scroll_area.verticalScrollBar().rangeChanged.disconnect()
        if entry_names:
            self.scroll_area.verticalScrollBar().rangeChanged.connect(range_changed)

    @Slot()
    def open_generate_password(self, password_line_edit: LineEdit) -> None:
        self.generate_password = GeneratePassword(password_line_edit)
        self.generate_password.show()
        widget_center(self.generate_password)

    @Slot()
    def plus(self, field_pairs_layout: QVBoxLayout) -> None:
        field_pair = FieldPair(self.main_window)
        field_pairs_layout.addWidget(field_pair)
        self.scroll_area.widget().updateGeometry()

    @Slot()
    def save(self, entry: Entry) -> bool:
        is_empty = False

        field_pairs = entry.findChildren(FieldPair)

        result = {}

        for field_pair in field_pairs:
            if not field_pair.name_line_edit.text():
                field_pair.name_line_edit.validation_state.set_invalid()

            if not field_pair.definition_line_edit.text():
                field_pair.definition_line_edit.validation_state.set_invalid()

            if field_pair.name_line_edit.text() and field_pair.definition_line_edit.text():
                result[field_pair.name_line_edit.text()] = field_pair.definition_line_edit.text()
            else:
                is_empty = True

        if is_empty:
            self.main_window.statusBar().showMessage('Some fields are empty', STATUS_BAR_MESSAGE_TIMEOUT)
            return False

        entry.saved_field_pair_removed = False

        for field_pair in field_pairs:
            field_pair.saved_name = field_pair.name_line_edit.text()
            field_pair.saved_definition = field_pair.definition_line_edit.text()

        self.pm[entry.title()] = result

        self.main_window.statusBar().showMessage('Saved', STATUS_BAR_MESSAGE_TIMEOUT)
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

        for entry in self.findChildren(Entry):
            if not self.save(entry):
                is_saved = False

        if is_saved:
            self.scroll_area.saved_entry_removed = False
            self.main_window.statusBar().showMessage('Saved all', STATUS_BAR_MESSAGE_TIMEOUT)
        else:
            self.main_window.statusBar().showMessage('Some fields are empty', STATUS_BAR_MESSAGE_TIMEOUT)

    @Slot()
    def remove_entry(self, entry: Entry) -> None:
        if entry.title() in self.pm:
            self.scroll_area.saved_entry_removed = True
        self.to_delete.append(entry.title())
        entry.deleteLater()
        self.scroll_area.widget().updateGeometry()


class FieldPair(QWidget):

    def __init__(self, main_window: QMainWindow, name: str = '', definition: str = '', password: bool = False) -> None:
        super().__init__()

        self.main_window = main_window

        self.saved_name = name if name else None
        self.saved_definition = definition if definition else None

        self.copy_icon = QIcon(':/copy.svg')
        self.hide_icon = QIcon(':/hide.svg')
        self.minus_icon = QIcon(':/minus.svg')
        self.show_icon = QIcon(':/show.svg')

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)

        self.name_line_edit = LineEdit(name)
        self.name_line_edit.setPlaceholderText('Name')

        layout.addWidget(self.name_line_edit)

        self.definition_line_edit = LineEdit(definition)

        layout.addWidget(self.definition_line_edit)

        copy_push_button = AnimatedPushButton()
        copy_push_button.setIcon(self.copy_icon)
        copy_push_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        copy_push_button.setProperty('class', 'button-icon-only')

        def wrapper_copy_to_clipboard(definition_line_edit: LineEdit) -> Callable[[], None]:
            return lambda: self.copy_to_clipboard(definition_line_edit)

        copy_push_button.clicked.connect(wrapper_copy_to_clipboard(self.definition_line_edit))

        layout.addWidget(copy_push_button)

        if password:
            self.name_line_edit.setReadOnly(True)
            self.definition_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.definition_line_edit.setPlaceholderText('Password')

            self.show_hide_push_button = AnimatedPushButton('')
            self.show_hide_push_button.setIcon(self.show_icon)
            self.show_hide_push_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            self.show_hide_push_button.setProperty('class', 'button-icon-only')

            def wrapper_show_hide_password(password_line_edit: LineEdit) -> Callable[[], None]:
                return lambda: self.show_hide_password(password_line_edit)

            self.show_hide_push_button.clicked.connect(wrapper_show_hide_password(self.definition_line_edit))

            layout.addWidget(self.show_hide_push_button)
        else:
            self.definition_line_edit.setPlaceholderText('Definition')

            minus_push_button = AnimatedPushButton()
            minus_push_button.setIcon(self.minus_icon)
            minus_push_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            minus_push_button.setProperty('class', 'button-icon-only')
            minus_push_button.clicked.connect(self.minus)

            layout.addWidget(minus_push_button)

        self.setLayout(layout)

    def saved(self) -> bool:
        if self.saved_name is None or self.saved_definition is None:
            return False
        if self.saved_name != self.name_line_edit.text():
            return False
        if self.saved_definition != self.definition_line_edit.text():
            return False
        return True

    @Slot()
    def copy_to_clipboard(self, definition_line_edit: LineEdit) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(definition_line_edit.text())
        self.main_window.statusBar().showMessage('Copied to clipboard', STATUS_BAR_MESSAGE_TIMEOUT)

    @Slot()
    def minus(self) -> None:
        if self.saved_name is not None and self.saved_definition is not None:
            self.parent().saved_field_pair_removed = True

        self.deleteLater()
        self.updateGeometry()

    @Slot()
    def show_hide_password(self, password_line_edit: LineEdit) -> None:
        if password_line_edit.echoMode() == QLineEdit.EchoMode.Password:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_hide_push_button.setIcon(self.hide_icon)
        else:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_hide_push_button.setIcon(self.show_icon)


class Label(QLabel):

    def __init__(self, text: str) -> None:
        super().__init__(text)

        self.validation_state = ValidationState(self)


class GeneratePassword(QWidget):

    def __init__(self, password_line_edit: LineEdit) -> None:
        super().__init__()

        program_icon = QIcon(':/icon.png')

        self.setFixedWidth(WINDOW_WIDTH)
        self.setWindowIcon(program_icon)
        self.setWindowTitle('Generate password')

        layout = QVBoxLayout()
        layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        layout.setSpacing(LAYOUT_SPACING)

        self.length_line_edit = LineEdit()
        self.length_line_edit.setPlaceholderText(f'Password length ({GENERATED_PASSWORD_LENGTH_MIN} to {GENERATED_PASSWORD_LENGTH_MAX} characters)')

        def wrapper_update_password(password_line_edit: LineEdit) -> Callable[[], None]:
            return lambda: self.update_password(password_line_edit)

        self.length_line_edit.returnPressed.connect(wrapper_update_password(password_line_edit))

        layout.addWidget(self.length_line_edit)

        self.choose_label = Label('Choose what characters a password should consist of:')

        layout.addWidget(self.choose_label)

        self.lowercase_checkbox = QCheckBox('Lowercase letters')
        self.lowercase_checkbox.setChecked(True)
        self.lowercase_checkbox.stateChanged.connect(self.choose_label.validation_state.set_valid)

        layout.addWidget(self.lowercase_checkbox)

        self.uppercase_checkbox = QCheckBox('Uppercase letters')
        self.uppercase_checkbox.setChecked(True)
        self.uppercase_checkbox.stateChanged.connect(self.choose_label.validation_state.set_valid)

        layout.addWidget(self.uppercase_checkbox)

        self.digits_checkbox = QCheckBox('Digits')
        self.digits_checkbox.setChecked(True)
        self.digits_checkbox.stateChanged.connect(self.choose_label.validation_state.set_valid)

        layout.addWidget(self.digits_checkbox)

        self.punctuation_checkbox = QCheckBox('Punctuation')
        self.punctuation_checkbox.stateChanged.connect(self.choose_label.validation_state.set_valid)

        layout.addWidget(self.punctuation_checkbox)

        generate_push_button = AnimatedPushButton('Generate')
        generate_push_button.clicked.connect(wrapper_update_password(password_line_edit))

        layout.addWidget(generate_push_button)

        self.setLayout(layout)

    @Slot()
    def update_password(self, password_line_edit: LineEdit) -> None:
        errors = False

        try:
            password_length = int(self.length_line_edit.text())
            if password_length < GENERATED_PASSWORD_LENGTH_MIN or password_length > GENERATED_PASSWORD_LENGTH_MAX:
                self.length_line_edit.validation_state.set_invalid()
                errors = True
        except ValueError:
            self.length_line_edit.validation_state.set_invalid()
            errors = True

        if (not self.lowercase_checkbox.isChecked()
                and not self.uppercase_checkbox.isChecked()
                and not self.digits_checkbox.isChecked()
                and not self.punctuation_checkbox.isChecked()):
            self.choose_label.validation_state.set_invalid()
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
        self.deleteLater()


class MainWindow(QMainWindow):

    def __init__(self, pm: PasswordManager) -> None:
        super().__init__()

        program_icon = QIcon(':/icon.png')

        self.setFixedWidth(WINDOW_WIDTH)
        self.setFixedHeight(WINDOW_HEIGHT)
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.setWindowIcon(program_icon)
        self.setWindowTitle(PROGRAM_NAME)

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

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.centralWidget().scroll_area.saved():
            QApplication.closeAllWindows()
            return

        unsaved_dialog = UnsavedDialog()
        QTimer.singleShot(0, lambda: widget_center(unsaved_dialog))
        dialog_code = unsaved_dialog.exec()
        if dialog_code != QDialog.DialogCode.Accepted:
            event.ignore()
            return
        QApplication.closeAllWindows()


class PasswordWidget(QWidget):

    def __init__(self, app: QApplication) -> None:
        super().__init__()

        self.app = app

        program_icon = QIcon(':/icon.png')

        self.setFixedWidth(WINDOW_WIDTH)
        self.setWindowIcon(program_icon)
        self.setWindowTitle(PROGRAM_NAME)

        layout = QVBoxLayout()
        layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        layout.setSpacing(LAYOUT_SPACING)

        continue_push_button_text = 'Decrypt'

        if DATABASE_PATH.exists():
            label = QLabel(f'<div>Enter a password for a database at {DATABASE_PATH}</div>')
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setProperty('class', 'info')
            layout.addWidget(label)
        else:
            continue_push_button_text = 'Create'
            label = QLabel('<div style="margin-bottom: 10px;">Database does not exist yet</div>'
                          f'<div style="font-size: 10px;">It will be created at {DATABASE_PATH}</div>')
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setProperty('class', 'info')
            layout.addWidget(label)

        self.password_line_edit = LineEdit()
        self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_line_edit.setPlaceholderText('Database password')
        self.password_line_edit.returnPressed.connect(self.run)

        layout.addWidget(self.password_line_edit)

        continue_push_button = AnimatedPushButton(continue_push_button_text)
        continue_push_button.setProperty('class', 'button-alt')
        continue_push_button.clicked.connect(self.run)

        layout.addWidget(continue_push_button)

        self.setLayout(layout)

    @Slot()
    def run(self) -> None:
        if not self.password_line_edit.text():
            self.password_line_edit.validation_state.set_invalid()
            return

        try:
            pm = PasswordManager(DATABASE_PATH, self.password_line_edit.text())
        except CryptoError:
            self.password_line_edit.validation_state.set_invalid()
            return

        self.hide()
        self.deleteLater()

        main_window = MainWindow(pm)
        main_window.show()
        widget_center(main_window)


class UnsavedDialog(QDialog):

    def __init__(self):
        super().__init__()

        program_icon = QIcon(':/icon.png')

        self.setFixedWidth(WINDOW_WIDTH)
        self.setWindowIcon(program_icon)
        self.setWindowTitle('Unsaved changes')

        layout = QVBoxLayout()
        layout.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        layout.setSpacing(LAYOUT_SPACING)

        label = QLabel('You have unsaved changes. Are you sure you want to exit?')
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setProperty('class', 'info')

        layout.addWidget(label)

        buttons_layout = QHBoxLayout()

        yes_push_button = AnimatedPushButton('Yes')
        yes_push_button.clicked.connect(self.accept)

        buttons_layout.addWidget(yes_push_button)

        no_push_button = AnimatedPushButton('No')
        no_push_button.setDefault(True)
        no_push_button.clicked.connect(self.reject)

        buttons_layout.addWidget(no_push_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)


class ValidationState():

    def __init__(self, widget: Label | LineEdit) -> None:
        self.widget = widget

    def set_invalid(self) -> None:
        self.widget.setProperty('class', 'invalid')
        self.widget.setStyle(QApplication.style())

    def set_valid(self) -> None:
        self.widget.setProperty('class', '')
        self.widget.setStyle(QApplication.style())
