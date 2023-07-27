import sys
import os
from pathlib import Path
import webbrowser
from tempfile import NamedTemporaryFile
from copy import deepcopy, copy

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QFileDialog,
    QTableWidgetItem,
    QErrorMessage,
    QListWidgetItem,
    QMessageBox,
    QHeaderView,
)
from PyQt5.QtGui import QFont, QIcon, QCloseEvent
from PyQt5.uic import loadUi
from PyQt5.QtCore import (
    Qt,
    QTranslator,
    QLibraryInfo,
    QEvent,
    QObject,
    QTimer,
)

from window_ui import Ui_MainWindow

from model import List
from utils import create_report


REFRESHING_GOING_ON = False


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(
            QIcon(str(Path(__file__).parent / "icons/appicon.png"))
        )
        self.setWindowState(Qt.WindowMaximized)
        self.setupUi(self)
        self.connectSignalsSlots()
        self.actions_ = []
        self.undos = []
        self.list: List
        self.saved = True
        try:
            self.list = List.from_file(sys.argv[1])
        except IndexError:
            self.new()
        self.title.installEventFilter(self)
        self.refreshUi()

    def refreshUi(self):
        global REFRESHING_GOING_ON
        REFRESHING_GOING_ON = True

        ull_name = (
            Path(self.list.path).name if self.list.path else "Neue Liste"
        )
        self.setWindowTitle(
            f"{ull_name}[*] - Urlaubsliste Deluxe (Retro Edition)"
        )
        if self.list.path:
            self.setWindowFilePath(self.list.path)
        self.setWindowModified(not self.saved)
        self.title.setText(self.list.orm.name)
        self.actionUndo.setEnabled(True if self.actions_ else False)
        self.actionRedo.setEnabled(True if self.undos else False)

        # Reset table
        self.table.setColumnCount(0)
        self.table.setRowCount(0)

        # Define table size
        self.table.setColumnCount(len(self.list.categories))
        longest_category_length = 0
        for category in self.list.categories:
            category_length = self.list.get_amount_of_items_for_category(
                category
            )
            if category_length > longest_category_length:
                longest_category_length = category_length
        # +2 because there should be one extra for adding new items and
        # because the category itself isn't included in the
        # `longest_category_length`
        self.table.setRowCount(longest_category_length + 1)

        self.table.setHorizontalHeaderLabels(self.list.categories)

        # Fill by category
        for x, category in enumerate(self.list.categories):
            items = self.list.get_items_for_category(category)
            # Set item fields
            for y, item in enumerate(items):
                tItem = QTableWidgetItem(item)
                self.table.setItem(y, x, tItem)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        REFRESHING_GOING_ON = False

    def save_table_to_list(self):
        self.actions_.append(deepcopy(self.list))
        self.undos.clear()
        for column, category in enumerate(self.list.categories):
            items = []
            for row in range(self.table.rowCount()):
                item = self.table.item(row, column)
                if item is None or item.text() == "":
                    continue
                items.append(item.text())
            self.list.raw["structure"]["categories"][category] = items

    def connectSignalsSlots(self):
        self.actionBeenden.triggered.connect(self.close)
        self.actionListentitelAndern.triggered.connect(self.changeName)
        self.actionOffnen.triggered.connect(self.open)
        self.actionNeueUrlaubsliste.triggered.connect(self.new)
        self.actionListeSpeichern.triggered.connect(self.save)
        self.actionListeSpeichernUnter.triggered.connect(self.save_as)
        self.actionBasisListenVerwalten.triggered.connect(self.manageBaseList)
        self.actionAnsichtNeuLaden.triggered.connect(self.refreshUi)
        self.actionEditorOffnen.triggered.connect(self.openEditor)
        self.actionVorschau.triggered.connect(self.openPreview)
        self.actionDrucken.triggered.connect(self.printList)
        self.actionUndo.triggered.connect(self.undo)
        self.actionRedo.triggered.connect(self.redo)

        self.table.itemChanged.connect(self.itemChanged)

    def undo(self):
        self.undos.append(deepcopy(self.list))
        try:
            self.list = self.actions_.pop()
        except IndexError:  # Nothing to undo
            pass
        self.refreshUi()

    def redo(self):
        self.actions_.append(deepcopy(self.list))
        try:
            self.list = self.undos.pop()
        except IndexError:  # Nothing to redo
            pass
        self.refreshUi()

    def openPreview(self, print=False):
        dialog = PreviewDialog(self, print)
        dialog.exec()

    def printList(self):
        tempfile = NamedTemporaryFile("wb", suffix=".pdf", delete=False)
        try:
            create_report(
                List(self.list.get_raw_extended_with_parent()), tempfile
            )
        except ValueError:
            error_box = QErrorMessage(self)
            error_box.showMessage(
                "Es gibt nichts zu drucken, die Liste ist leer."
            )
            return
        tempfile.close()
        webbrowser.WindowsDefault().open(tempfile.name)

    def itemChanged(self, item: QTableWidgetItem):
        if REFRESHING_GOING_ON:
            return
        self.update_list()

    def update_list(self):
        self.saved = False
        self.save_table_to_list()
        self.refreshUi()

    def openEditor(self):
        dialog = EditorDialog(self)
        if dialog.exec():
            self.actions_.append(deepcopy(self.list))
            self.undos.clear()
            list_content = [
                dialog.list.item(x).text() for x in range(dialog.list.count())
            ]
            categories_to_be_checked = self.list.categories
            for oldName, newName in dialog.renames.items():
                if newName not in list_content:
                    continue
                try:
                    self.list.rename_category(oldName, newName)
                except KeyError:
                    # Renamed item was just created in the editor session
                    self.list.add_category(newName)
                list_content.remove(newName)
                try:
                    categories_to_be_checked.remove(oldName)
                except ValueError:
                    # Renamed item was just created in the editor session
                    pass
            for category in copy(list_content):
                if category not in self.list.categories:
                    self.list.add_category(category)
                    list_content.remove(category)
            for category in copy(categories_to_be_checked):
                if category not in list_content:
                    self.list.remove_category(category)
                    categories_to_be_checked.remove(category)
            # Now, bring the categories in right order
            list_content = [
                dialog.list.item(x).text() for x in range(dialog.list.count())
            ]
            saved_categories = self.list.categories
            if list_content != saved_categories:
                # Only reorder if there's a need to
                for key in list_content:
                    self.list.orm.structure.categories[
                        key] = self.list.orm.structure.categories.pop(key)
            self.saved = False
            self.refreshUi()

    def eventFilter(self, obj: QObject, event: QEvent):
        if obj == self.title and event.type() == QEvent.MouseButtonDblClick:
            self.changeName()
        return False

    def wannaSaveMessageBox(self) -> int:
        messagebox = QMessageBox(self)
        messagebox.setIcon(QMessageBox.Question)
        messagebox.setWindowTitle("Änderungen speichern?")
        messagebox.setText(
            "Ihr Dokument enthält nicht gespeicherte Inhalte. "
            "Möchten sie vor dem Verlassen speichern?"
        )
        messagebox.setStandardButtons(
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel
        )
        messagebox.setDefaultButton(QMessageBox.StandardButton.Save)
        return messagebox.exec()

    def closeEvent(self, event: QCloseEvent):
        if not self.saved:
            response = self.wannaSaveMessageBox()
            if response == QMessageBox.StandardButton.Save:
                self.save()
            elif response == QMessageBox.StandardButton.Discard:
                pass  # Just close
            else:
                event.ignore()

    def changeName(self):
        dialog = ChangeNameDialog(self)
        if dialog.exec():
            self.actions_.append(deepcopy(self.list))
            self.undos.clear()
            self.list.change_name(dialog.lineEdit.text())
            self.saved = False
        self.refreshUi()

    def open(self, any_file=False, force=False, **kwargs):
        fileDialog = QFileDialog(self)
        if any_file:
            fileDialog.setFileMode(QFileDialog.FileMode.AnyFile)
        else:
            fileDialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        fileDialog.setNameFilter(
            "Urlaubsliste (*.ull);;JSON in ULL Format (*.json)"
        )
        fileDialog.setDirectory(
            os.path.expanduser("~/Documents/Urlaubslisten")
        )
        fileDialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        if fileDialog.exec():
            if not self.saved:
                response = self.wannaSaveMessageBox()
                if response == QMessageBox.StandardButton.Save:
                    self.save()
                elif response == QMessageBox.StandardButton.Discard:
                    pass  # Just go on
                else:
                    return
            file = fileDialog.selectedFiles()[0]
            self.list = List.from_file(file)
            self.saved = True
        else:
            if force:
                kwargs["force_action"]()
        self.refreshUi()

    def new(self):
        if not self.saved:
            response = self.wannaSaveMessageBox()
            if response == QMessageBox.StandardButton.Save:
                self.save()
            elif response == QMessageBox.StandardButton.Discard:
                pass  # Just go on...
            else:
                return
        self.list = List.new("Neue Liste")
        self.saved = True
        self.refreshUi()

    def save(self):
        return self.save_as(self.list.path)

    def save_as(self, path=None):
        # HACK (False,) argument of the library ignored
        path = None if path is False else path
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self,
                caption="Liste Speichern",
                directory=os.path.expanduser("~/Documents/Urlaubslisten"),
                filter="Urlaubsliste (*.ull);;JSON (*.json)",
            )
        if not path:
            return
        self.save_table_to_list()
        with open(path, mode="w") as fp:
            fp.write(self.list.serialize())
        self.list.path = path
        self.saved = True
        self.refreshUi()

    def manageBaseList(self):
        dialog = ManageBaseList(self)
        copy = deepcopy(self.list)
        if dialog.exec():
            self.saved = False
        if self.list.parent != copy.parent:
            self.actions_.append(copy)
            self.undos.clear()
        self.refreshUi()


class PreviewDialog(QDialog):
    def __init__(self, parent=None, print=False):
        super().__init__(parent)
        loadUi(Path(__file__).parent / "ui/preview.ui", self)
        self.setWindowTitle("Preview")
        self.setWindowState(Qt.WindowMaximized)
        self.setWindowIcon(
            QIcon(str(Path(__file__).parent / "icons/appicon.png"))
        )
        self.printButton.clicked.connect(self.print)
        self.refreshUi()
        if print:
            QTimer.singleShot(0, self.print)

    def print(self):
        tempfile = NamedTemporaryFile("wb", suffix=".pdf", delete=False)
        try:
            create_report(self.list, tempfile)
        except ValueError:
            error_box = QErrorMessage(self)
            error_box.showMessage(
                "Es gibt nichts zu drucken, die Liste ist leer."
            )
            return
        tempfile.close()
        webbrowser.WindowsDefault().open(tempfile.name)
        # XXX THE FOLLOWING WAS SUPPOSED TO WORK WELL, HOWEVER AT THE
        # XXX painter.drawImage() LINE THE PROG TERMINATES WITHOUT ERRORS.
        # XXX THAT's WHY WE ARE REDIRECTING TO WINDOWS DEFAULT NOW.
        """dialog = QPrintDialog(self)
        if dialog.exec() == QDialog.Accepted:
            file = BytesIO()
            self.create_report(file)
            printer = dialog.printer()
            painter = QPainter()
            images = convert_from_bytes(file.getvalue(), dpi=300)
            for image in images:
                image.save("c:/users/dominik/downloads/img.png")
                painter.begin(dialog.printer())
                painter.drawImage(
                    QPoint(0, 0), QImage(
                        image.tobytes(),
                        image.width,
                        image.height,
                        QImage.Format.Format_RGB888,
                    )
                )
                painter.end()
                if image != images[-1]:
                    printer.newPage()
            file.close()"""

    def refreshUi(self):
        self.title.setText(self.parent().title.text())

        # Reset table
        self.table.setColumnCount(0)
        self.table.setRowCount(0)

        self.list = List(self.parent().list.get_raw_extended_with_parent())

        # Define table size
        self.table.setColumnCount(len(self.list.categories))
        longest_category_length = 0
        for category in self.list.categories:
            category_length = (
                self.list.get_amount_of_items_for_category(category)
            )
            if category_length > longest_category_length:
                longest_category_length = category_length
        # +2 because there should be one extra for adding new items and
        # because the category itself isn't included in the
        # `longest_category_length`
        self.table.setRowCount(longest_category_length + 1)

        self.table.setHorizontalHeaderLabels(self.list.categories)

        # Fill by category
        for x, category in enumerate(self.list.categories):
            items = self.list.get_items_for_category(category)
            # Set item fields
            for y, item in enumerate(items):
                tItem = QTableWidgetItem(item)
                self.table.setItem(y, x, tItem)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)


class ItemEditor(QDialog):
    def __init__(self, parent, category: str):
        super().__init__(parent)
        self.category = category
        loadUi(Path(__file__).parent / "ui/item_editor.ui", self)
        self.setWindowTitle("Item Editor")
        self.setWindowIcon(
            QIcon(str(Path(__file__).parent / "icons/appicon.png"))
        )
        self.items = self.parent().parent().list.orm.structure.categories[
            self.category
        ]
        self.refreshUi()

    def refreshUi(self):
        if self.parent().parent().list.categories:
            self.list.clear()
            for item in self.items:
                list_item = QListWidgetItem(item)
                self.list.addItem(list_item)


class EditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(Path(__file__).parent / "ui/editor.ui", self)
        self.setWindowTitle("Editor")
        self.setWindowIcon(
            QIcon(str(Path(__file__).parent / "icons/appicon.png"))
        )
        self.createCategoryButton.clicked.connect(self.createCategory)
        self.list.itemChanged.connect(self.itemChanged)
        self.delCategoryButton.clicked.connect(self.deleteCategory)
        self.openItemEditorButton.clicked.connect(self.openItemEditor)
        self.renames = {}
        self.originalNames = {}
        self.categories = self.parent().list.categories
        self.new_category_counter = 1
        self.refreshUi()

    def openItemEditor(self):
        selected = self.list.selectedItems()
        try:
            category = selected[0].text()
        except IndexError:
            error_box = QErrorMessage(self)
            error_box.showMessage(
                "Bitte wähle zuerst eine Liste aus."
            )
            return
        if category not in self.parent().list.categories:
            error_box = QErrorMessage(self)
            error_box.showMessage(
                "Die Kategorie ist leer."
            )
            return
        if not self.parent().list.orm.structure.categories[category]:
            error_box = QErrorMessage(self)
            error_box.showMessage(
                "Die Kategorie ist leer."
            )
            return
        dialog = ItemEditor(self, category)
        if dialog.exec():
            dialog_list_items = [
                dialog.list.item(x).text() for x in range(dialog.list.count())
            ]
            self.parent().list.orm.structure.categories[
                category
            ] = dialog_list_items

    def refreshUi(self):
        if self.parent().list.categories:
            self.list.clear()
            for item in self.categories:
                list_item = QListWidgetItem(item)
                list_item.setFlags(list_item.flags() | Qt.ItemIsEditable)
                list_item.setData(Qt.UserRole, item)
                self.list.addItem(list_item)
                self.originalNames[id(list_item)] = item

    def deleteCategory(self):
        selected = self.list.selectedItems()
        for item in selected:
            self.list.takeItem(self.list.row(item))

    def createCategory(self):
        item = QListWidgetItem()
        item.setText(f"Neue Kategorie {self.new_category_counter}")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.originalNames[id(item)] = item.text()
        self.list.addItem(item)
        self.new_category_counter += 1

    def itemChanged(self, item: QListWidgetItem):
        new_name = item.text()
        old_name = self.originalNames[id(item)]
        self.renames[old_name] = new_name


class ChangeNameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(Path(__file__).parent / "ui/change_name_dialog.ui", self)
        self.setWindowTitle("Listenname bearbeiten")
        self.setWindowIcon(
            QIcon(str(Path(__file__).parent / "icons/appicon.png"))
        )


class ManageBaseList(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(Path(__file__).parent / "ui/edit_parent_dialog.ui", self)
        self.setWindowTitle("Basis Liste Wählen")

        self.selectListButton.clicked.connect(self.selectParentList)
        self.deleteParentButton.clicked.connect(self.deleteParentList)
        self.refreshUi()

    def refreshUi(self):
        self.label_2.setText(str(self.parent().list.parent))

    def selectParentList(self):
        fileDialog = QFileDialog(self)
        fileDialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        fileDialog.setNameFilter(
            "Urlaubsliste (*.ull);;JSON in ULL Format (*.json)")
        fileDialog.setDirectory(
            os.path.expanduser("~/Documents/Urlaubslisten"))
        fileDialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        if fileDialog.exec():
            file = fileDialog.selectedFiles()[0]
            try:
                self.parent().list.change_baselist(file)
            except FileNotFoundError:
                error_box = QErrorMessage(self)
                error_box.showMessage("Die Datei wurde nicht gefunden.")
            except ValueError:
                error_box = QErrorMessage(self)
                error_box.showMessage(
                    "Die ausgewählte Liste trägt den gleichen Namen"
                    " wie die geöffnete. \nDies passiert für gewöhnlich,"
                    " wenn die die geöffnete Liste, bzw. eine Kopie von"
                    " ihr ausgewählt wird. Bitte wählen sie eine andere Liste."
                )
            self.refreshUi()

    def deleteParentList(self):
        self.parent().list.remove_baselist()
        self.refreshUi()


if __name__ == "__main__":
    if not (
        list_dir := Path(os.path.expanduser("~/Documents/Urlaubslisten"))
    ).exists():
        list_dir.mkdir()
    app = QApplication(sys.argv)
    app.setApplicationName("Urlaubsliste Deluxe")
    app.setFont(QFont("Calibri", 10))
    locale = 'de_DE'
    translator = QTranslator()
    translator.load(
        'qtbase_' + locale, QLibraryInfo.location(
            QLibraryInfo.TranslationsPath
        )
    )
    app.installTranslator(translator)
    win = Window()
    win.show()
    sys.exit(app.exec())
