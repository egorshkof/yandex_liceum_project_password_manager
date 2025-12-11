from PyQt6.QtWidgets import QMessageBox, QFileDialog, QLineEdit
from PyQt6.QtWidgets import QDialog, QTableWidgetItem
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWidgets import QHeaderView, QDialogButtonBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from manager import Ui_MainWindow
from form import Ui_Form

import webbrowser
import sqlite3
import sys
import csv


class PasswordManager(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('Password manager')
        self.setWindowIcon(QIcon('icon.ico'))
        # / open / copy /
        self.open_url_button.clicked.connect(self.open_url)
        self.copyButton_login.clicked.connect(self.copy_login)
        self.copyButton_password.clicked.connect(self.copy_password)
        # / deleting / editing / adding /
        self.deleteButton.clicked.connect(self.delete_entry)
        self.editButton.clicked.connect(self.edit_entry)
        self.addButton.clicked.connect(self.add_entry)
        # / searching /
        self.searchButton.clicked.connect(self.search)
        self.passwordTable.itemSelectionChanged.connect(self.show_selected_password)
        # / show password /
        self.showButton.clicked.connect(self.toggle_password_visibility)
        self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
        # / table /
        self.passwordTable.setColumnCount(2)
        self.passwordTable.setHorizontalHeaderLabels(['Service', 'URL'])
        header = self.passwordTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # / menu /
        self.actionExport_to_csv.triggered.connect(self.export_to_csv)
        self.actionImport_from_csv.triggered.connect(self.import_from_csv)
        self.actionDelete_all.triggered.connect(self.delete_all)
        self.actionAbout.triggered.connect(self.show_about)
        self.actionHotkeys.triggered.connect(self.show_hotkeys)
        self.actionGitHub.triggered.connect(self.open_github)
        # / hotkeys /
        self.addButton.setShortcut(QKeySequence("Ctrl+N"))
        self.editButton.setShortcut(QKeySequence("Ctrl+E"))
        self.deleteButton.setShortcut(QKeySequence("Delete"))
        self.open_url_action()
        # / database /
        self.db_path = 'passwords.db'
        self.con = sqlite3.connect(self.db_path)
        self.cur = self.con.cursor()

    def search(self):
        """Searching in database"""
        self.passwordTable.setRowCount(0)
        search_text = self.searchLineEdit.text()
        result = self.cur.execute("""SELECT service, url 
                                     FROM passwords""").fetchall()

        if search_text:
            result = [row for row in result if search_text.lower() in row[0].lower()]
        self.update_table(result)

    def update_table(self, data):
        """Update table with new data"""
        for row_num, row_data in enumerate(data):
            self.passwordTable.insertRow(row_num)
            for col_num, elem in enumerate(row_data):
                self.passwordTable.setItem(row_num, col_num, QTableWidgetItem(str(elem)))

    def show_selected_password(self):
        """Show login and password"""
        selected_items = self.passwordTable.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        service = self.passwordTable.item(row, 0).text()
        self.cur.execute("""SELECT url, login, password 
                                  FROM passwords 
                                  WHERE service = ?""",
                         (service,))
        result = self.cur.fetchone()

        if result:
            url, login, password = result
            self.URLedit.setText(url)
            self.loginEdit.setText(login)
            self.passwordEdit.setText(password)
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)

    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.passwordEdit.echoMode() == QLineEdit.EchoMode.Password:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)

    def add_entry(self):
        """Open form for adding new service"""
        self.editing_form = InputForm('Add new service', '', '', '', '')
        self.editing_form.buttonBox.accepted.connect(lambda: self.save_entry(self.editing_form, False))
        self.editing_form.buttonBox.rejected.connect(self.editing_form.close)
        self.editing_form.show()

    def edit_entry(self):
        """Open form for editing current service"""
        selected_items = self.passwordTable.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        current_service = self.passwordTable.item(row, 0).text()

        self.editing_form = InputForm('Edit service',
                                      current_service,
                                      self.URLedit.text(),
                                      self.loginEdit.text(),
                                      self.passwordEdit.text())
        self.editing_form.old_service = current_service
        self.editing_form.buttonBox.accepted.connect(lambda: self.save_entry(self.editing_form, True))
        self.editing_form.buttonBox.rejected.connect(self.editing_form.close)
        self.editing_form.show()

    def save_entry(self, form, is_edit_mode):
        """Save data from form"""
        service = form.ServiceEdit.text().strip()
        url = form.URLedit.text().strip()
        login = form.loginEdit.text().strip()
        password = form.passwordEdit.text().strip()

        try:
            if is_edit_mode:
                old_service = form.old_service
                self.cur.execute("""UPDATE passwords
                                    SET service = ?, url = ?, login = ?, password = ?
                                    WHERE service = ?""",
                                 (service, url, login, password, old_service))
                self.URLedit.setText(url)
                self.loginEdit.setText(login)
                self.passwordEdit.setText(password)
            else:
                self.cur.execute("""INSERT INTO passwords (service, url, login, password)
                                    VALUES (?, ?, ?, ?)""",
                                 (service, url, login, password))
            self.con.commit()
            self.search()
            form.close()
        except sqlite3.Error as e:
            print(e)

    def delete_entry(self):
        """Delete selected entry with confirmation"""
        selected_items = self.passwordTable.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        service = self.passwordTable.item(row, 0).text()

        reply = QMessageBox.question(self, 'Confirm deletion',
                                     'Are you sure you want to delete this entry?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.cur.execute("DELETE FROM passwords WHERE service = ?",
                                 (service,))
                self.con.commit()
                self.search()
                self.URLedit.clear()
                self.loginEdit.clear()
                self.passwordEdit.clear()
            except sqlite3.Error as e:
                print(e)

    def export_to_csv(self):
        """Export all passwords to .csv file"""
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как CSV",
                                              "passwords_export.csv", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            self.cur.execute("SELECT service, url, login, password FROM passwords")
            rows = self.cur.fetchall()
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(['Service', 'URL', 'Login', 'Password'])
                writer.writerows(rows)
            QMessageBox.information(self, "Success", f"Data successfully exported to\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: \n{e}")

    def delete_all(self):
        """Delete all passwords with confirmation"""
        reply = QMessageBox.question(self, 'Confirmation',
                                     'Are you sure you want to delete all entries?\n\nThis action cannot be canceled!',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.cur.execute("DELETE FROM passwords")
                self.con.commit()
                self.search()
                self.URLedit.clear()
                self.loginEdit.clear()
                self.passwordEdit.clear()
                QMessageBox.information(self, "Success", "All entries was deleted")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Error", f"Can't delete data:\n{e}")

    def import_from_csv(self):
        """Import passwords from .csv file"""
        path, _ = QFileDialog.getOpenFileName(self, "Choose CSV-file for import",
                                              "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter=';')
                next(reader, None)
                imported_count = 0
                for row in reader:
                    if len(row) < 4:
                        continue
                    service = row[0].strip()
                    url = row[1].strip()
                    login = row[2].strip()
                    password = row[3].strip()

                    if not service or not password:
                        continue
                    self.cur.execute("SELECT 1 FROM passwords WHERE service = ?",
                                     (service,))
                    if self.cur.fetchone():
                        continue
                    self.cur.execute("""INSERT INTO passwords (service, url, login, password)
                                        VALUES (?, ?, ?, ?)""",
                                     (service, url, login, password))
                    imported_count += 1

                self.con.commit()
                self.search()

                QMessageBox.information(self, "Import completed",
                                        f"Successfully added records imported: {imported_count}")
        except Exception as e:
            QMessageBox.critical(self, "Import error", f"Failed to import data: \n\n{e}")

    def show_hotkeys(self):
        QMessageBox.information(self, "Горячие клавиши",
                                "<b>Ctrl + N</b> — Добавить запись<br>"
                                "<b>Ctrl + E</b> — Редактировать<br>"
                                "<b>Del</b> — Удалить выделенную<br>"
                                "<b>Enter</b> — Открыть URL")

    def open_url_action(self):
        """Enter - open URL"""
        action = QAction(self.passwordTable)
        action.setShortcut(Qt.Key.Key_Enter)
        action.triggered.connect(self.open_url)
        self.passwordTable.addAction(action)

    def open_github(self):
        webbrowser.open("https://github.com/egorshkof/yandex_liceum_project_password_manager")

    def show_about(self):
        QMessageBox.about(self, "О программе",
                          "<h2>Password Manager v1.0.0</h2>"
                          "<p><b>Автор:</b> Егор</p>"
                          "<p><b>Группа:</b> Д2 / Яндекс.Лицей</p>"
                          "<p>Менеджер паролей на PyQt</p>"
                          "<p>Особенности:</p>"
                          "<ul>"
                          "<li>Добавление / редактирование / удаление записей</li>"
                          "<li>Поиск и сортировка</li>"
                          "<li>Импорт и экспорт в CSV</li>"
                          "<li>Валидация полей</li>"
                          "<li>Копирование в буфер</li>"
                          "<li>Открытие ссылок</li>"
                          "</ul>")

    def open_url(self):
        """Open URL of service in default browser"""
        url = self.URLedit.text()
        if url:
            webbrowser.open_new_tab(url)

    def copy_login(self):
        """Copy login"""
        login = self.loginEdit.text()
        if login:
            QApplication.clipboard().setText(login)

    def copy_password(self):
        """Copy password"""
        password = self.passwordEdit.text()
        if password:
            QApplication.clipboard().setText(password)


class InputForm(QDialog, Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon('icon.ico'))
        # / unpacking /
        name, service, url, login, password = args
        self.setWindowTitle(name)
        # / line edits /
        self.ServiceEdit.setText(service)
        self.URLedit.setText(url)
        self.loginEdit.setText(login)
        self.passwordEdit.setText(password)
        # / checking /
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.ServiceEdit.textChanged.connect(self.check_service_field)
        self.check_service_field()
        # / reject /
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def check_service_field(self):
        """Turn on OK button if Service is not empty"""
        is_not_empty = bool(self.ServiceEdit.text().strip())
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(is_not_empty)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PasswordManager()
    ex.show()
    sys.exit(app.exec())

