from typing import Callable

from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QLayout,
                               QLineEdit, QMainWindow, QPushButton, QScrollArea,
                               QStatusBar, QToolBar, QVBoxLayout, QWidget)
from nacl.exceptions import CryptoError

from helpers import layout_delete, widget_center
import lock

MARGIN = 20
SPACING = 10


class CentralWidget(QWidget):

    def __init__(self, pm: lock.PasswordManager, main_window: QMainWindow) -> None:
        super().__init__()

        self.pm = pm
        self.main_window = main_window

        self.contents = self.pm.read()
        self.icon_size = QSize(12, 12)
        self.minus_icon = QIcon(str(lock.PROGRAM_DIR_PATH / 'minus-solid.svg'))
        self.plus_icon = QIcon(str(lock.PROGRAM_DIR_PATH / 'plus-solid.svg'))
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

        def wrapper_text_changed(name_line_edit: QLineEdit) -> Callable[[], None]:
            return lambda: name_line_edit.setStyleSheet('color: #535353;')

        name_line_edit.textChanged.connect(wrapper_text_changed(name_line_edit))

        create_layout.addWidget(name_line_edit)

        create_push_button = QPushButton('Create')
        create_push_button.setProperty('class', 'button-alt')
        create_push_button.clicked.connect(wrapper_create_new_entry(name_line_edit))

        create_layout.addWidget(create_push_button)

        layout.addLayout(create_layout)

        self.scroll_area_widget_layout = QVBoxLayout()
        self.scroll_area_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area_widget_layout.setSpacing(SPACING)

        self.scroll_area_widget_layout.addStretch()

        for entry_name, entry_value in self.contents.items():
            entry_group_box = self.create_entry(entry_name, entry_value)
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
            field_pair_layout = QHBoxLayout()

            name_line_edit = QLineEdit(entry_value_name)

            field_pair_layout.addWidget(name_line_edit)

            definition_line_edit = QLineEdit(entry_value_definition)

            if entry_value_name == 'Password':
                name_line_edit.setReadOnly(True)
                definition_line_edit.setEchoMode(QLineEdit.EchoMode.Password)

            field_pair_layout.addWidget(definition_line_edit)

            if entry_value_name == 'Password':
                spacer_push_button = QPushButton('')
                spacer_push_button.setProperty('class', 'spacer')

                field_pair_layout.addWidget(spacer_push_button)

                field_pairs_layout.insertLayout(0, field_pair_layout)

                buttons_layout = QHBoxLayout()

                buttons_layout.addStretch()

                copy_push_button = QPushButton('Copy')

                def wrapper_copy_password_to_clipboard(password_line_edit: QLineEdit) -> Callable[[], None]:
                    return lambda: self.copy_password_to_clipboard(password_line_edit)

                copy_push_button.clicked.connect(wrapper_copy_password_to_clipboard(definition_line_edit))

                buttons_layout.addWidget(copy_push_button)

                show_push_button = QPushButton('Show')

                def wrapper_show_hide_password(password_line_edit: QLineEdit) -> Callable[[], None]:
                    return lambda: self.show_hide_password(password_line_edit)

                show_push_button.clicked.connect(wrapper_show_hide_password(definition_line_edit))

                buttons_layout.addWidget(show_push_button)

                spacer_push_button = QPushButton('')
                spacer_push_button.setProperty('class', 'spacer')

                buttons_layout.addWidget(spacer_push_button)

                field_pairs_layout.insertLayout(1, buttons_layout)
            else:
                minus_push_button = QPushButton()
                minus_push_button.setIcon(self.minus_icon)
                minus_push_button.setIconSize(self.icon_size)
                minus_push_button.setProperty('class', 'button-icon-only')

                def wrapper_minus(field_pair_layout: QHBoxLayout) -> Callable[[], None]:
                    return lambda: self.minus(field_pair_layout)

                minus_push_button.clicked.connect(wrapper_minus(field_pair_layout))

                field_pair_layout.addWidget(minus_push_button)

                field_pairs_layout.addLayout(field_pair_layout)

        entry_layout.addLayout(field_pairs_layout)

        plus_push_button = QPushButton()
        plus_push_button.setIcon(self.plus_icon)
        plus_push_button.setIconSize(self.icon_size)
        plus_push_button.setProperty('class', 'button-icon-only')

        def wrapper_plus(field_pairs_layout: QVBoxLayout) -> Callable[[], None]:
            return lambda: self.plus(field_pairs_layout)

        plus_push_button.clicked.connect(wrapper_plus(field_pairs_layout))

        entry_layout.addWidget(plus_push_button, 0, Qt.AlignmentFlag.AlignRight)

        save_push_button = QPushButton('Save')

        def wrapper_save(entry_group_box: QGroupBox) -> Callable[[], None]:
            return lambda: self.save(entry_group_box)

        save_push_button.clicked.connect(wrapper_save(entry_group_box))

        entry_layout.addWidget(save_push_button)

        delete_push_button = QPushButton('Delete')
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
    def copy_password_to_clipboard(self, password_line_edit: QLineEdit) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(password_line_edit.text())
        self.main_window.statusBar().showMessage('Password copied to the clipboard', lock.STATUSBAR_TIMEOUT)

    @Slot()
    def create_new_entry(self, name_line_edit: QLineEdit) -> None:
        entry_name = name_line_edit.text()
        entry_names = [entry_group_box.title() for entry_group_box in self.findChildren(QGroupBox)]
        if not entry_name or (entry_name in self.contents and entry_name in entry_names) or entry_name in entry_names:
            name_line_edit.setStyleSheet('color: #c15959;')
            return
        name_line_edit.setStyleSheet('color: #535353;')
        entry_group_box = self.create_entry(entry_name, {'Password': ''})
        index =  self.scroll_area_widget_layout.count() - 1
        self.scroll_area_widget_layout.insertWidget(index, entry_group_box)
        name_line_edit.clear()

    @Slot()
    def delete(self, entry_group_box: QGroupBox) -> None:
        self.to_delete.append(entry_group_box.title())
        entry_group_box.deleteLater()

    @Slot()
    def minus(self, field_pair_layout: QHBoxLayout) -> None:
        layout_delete(field_pair_layout)

    @Slot()
    def plus(self, field_pairs_layout: QVBoxLayout) -> None:
        field_pair_layout = QHBoxLayout()

        name_line_edit = QLineEdit()
        name_line_edit.setPlaceholderText('Name')

        field_pair_layout.addWidget(name_line_edit)

        definition_line_edit = QLineEdit()
        definition_line_edit.setPlaceholderText('Definition')

        field_pair_layout.addWidget(definition_line_edit)

        minus_push_button = QPushButton()
        minus_push_button.setIcon(self.minus_icon)
        minus_push_button.setIconSize(self.icon_size)
        minus_push_button.setProperty('class', 'button-icon-only')

        def wrapper_minus(field_pair_layout: QHBoxLayout) -> Callable[[], None]:
            return lambda: self.minus(field_pair_layout)

        minus_push_button.clicked.connect(wrapper_minus(field_pair_layout))

        field_pair_layout.addWidget(minus_push_button)

        field_pairs_layout.addLayout(field_pair_layout)

    @Slot()
    def save(self, entry_group_box: QGroupBox) -> bool:
        is_empty = False

        line_edits = entry_group_box.findChildren(QLineEdit)

        result = {}

        for i in range(0, len(line_edits), 2):
            name_line_edit = line_edits[i]
            definition_line_edit = line_edits[i+1]

            if name_line_edit.text():
                name_line_edit.setStyleSheet('color: #535353;')
            else:
                name_line_edit.setStyleSheet('color: #c15959;')

            if definition_line_edit.text():
                definition_line_edit.setStyleSheet('color: #535353;')
            else:
                definition_line_edit.setStyleSheet('color: #c15959;')

            if name_line_edit.text() and definition_line_edit.text():
                result[name_line_edit.text()] = definition_line_edit.text()
            else:
                is_empty = True

        if is_empty:
            self.main_window.statusBar().showMessage('Some fields are empty', lock.STATUSBAR_TIMEOUT)
            return False

        try:
            self.pm.update(entry_group_box.title(), result)
        except lock.EntryDoesNotExistError:
            self.pm.create(entry_group_box.title(), result)

        self.main_window.statusBar().showMessage('Saved', lock.STATUSBAR_TIMEOUT)
        return True

    @Slot()
    def save_all(self):
        for entry_name in self.to_delete:
            try:
                self.pm.delete(entry_name, False)
            except lock.EntryDoesNotExistError:
                pass
        self.to_delete.clear()

        is_saved = True

        for entry_group_box in self.findChildren(QGroupBox):
            if not self.save(entry_group_box):
                is_saved = False

        if is_saved:
            self.main_window.statusBar().showMessage('Saved all', lock.STATUSBAR_TIMEOUT)
        else:
            self.main_window.statusBar().showMessage('Some fields are empty', lock.STATUSBAR_TIMEOUT)

    @Slot()
    def show_hide_password(self, password_line_edit: QLineEdit) -> None:
        if password_line_edit.echoMode() == QLineEdit.EchoMode.Password:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)


class MainWindow(QMainWindow):
    def __init__(self, pm: lock.PasswordManager) -> None:
        super().__init__()

        program_icon = QIcon(str(lock.PROGRAM_ICON_PATH))

        self.setFixedWidth(lock.WINDOW_WIDTH)
        self.setFixedHeight(lock.WINDOW_HEIGHT)
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.setWindowIcon(program_icon)
        self.setWindowTitle(lock.PROGRAM_NAME)

        central_widget = CentralWidget(pm, self)

        self.setCentralWidget(central_widget)

        save_all_push_button = QPushButton('Save all')
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

        program_icon = QIcon(str(lock.PROGRAM_ICON_PATH))

        self.setFixedWidth(lock.WINDOW_WIDTH)
        self.setWindowIcon(program_icon)
        self.setWindowTitle(lock.PROGRAM_NAME)

        layout = QHBoxLayout()
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.setSpacing(SPACING)

        self.password_line_edit = QLineEdit()
        self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_line_edit.setPlaceholderText('Database password')
        self.password_line_edit.returnPressed.connect(self.run)

        def wrapper_text_changed(password_line_edit: QLineEdit) -> Callable[[], None]:
            return lambda: password_line_edit.setStyleSheet('color: #535353;')

        self.password_line_edit.textChanged.connect(wrapper_text_changed(self.password_line_edit))

        layout.addWidget(self.password_line_edit)

        continue_push_button = QPushButton('Continue')
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
            pm = lock.PasswordManager(lock.DATABASE_PATH, True, self.password_line_edit.text())
        except CryptoError:
            self.password_line_edit.setStyleSheet('color: #c15959;')
            return

        self.hide()

        main_window = MainWindow(pm)
        main_window.show()
        widget_center(self.app, main_window)