"""Add/edit dialog for a single transaction."""

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)

from models import Transaction

DEFAULT_CATEGORIES = ["Yemek", "Ulasim", "Market", "Eglence", "Fatura", "Saglik", "Diger"]


class TransactionDialog(QDialog):
    """Modal dialog to create or edit a Transaction. Result is read via get_transaction()."""

    def __init__(self, parent=None, transaction: Transaction | None = None, categories: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Islem Duzenle" if transaction else "Yeni Islem")
        self._transaction_id = transaction.id if transaction else None

        self.amount_edit = QDoubleSpinBox()
        self.amount_edit.setRange(0.01, 10_000_000.0)
        self.amount_edit.setDecimals(2)
        self.amount_edit.setSuffix(" TL")
        self.amount_edit.setValue(transaction.amount_minor / 100 if transaction else 0.01)

        self.type_edit = QComboBox()
        self.type_edit.addItem("Gider", userData="gider")
        self.type_edit.addItem("Gelir", userData="gelir")
        if transaction:
            index = self.type_edit.findData(transaction.type)
            self.type_edit.setCurrentIndex(index if index >= 0 else 0)

        self.category_edit = QComboBox()
        self.category_edit.setEditable(True)
        all_categories = sorted(set(DEFAULT_CATEGORIES) | set(categories or []))
        self.category_edit.addItems(all_categories)
        if transaction:
            self.category_edit.setCurrentText(transaction.category)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        if transaction:
            self.date_edit.setDate(QDate.fromString(transaction.date, "yyyy-MM-dd"))
        else:
            self.date_edit.setDate(QDate.currentDate())

        self.note_edit = QLineEdit(transaction.note if transaction else "")

        form = QFormLayout()
        form.addRow("Tutar:", self.amount_edit)
        form.addRow("Tur:", self.type_edit)
        form.addRow("Kategori:", self.category_edit)
        form.addRow("Tarih:", self.date_edit)
        form.addRow("Not:", self.note_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.setLayout(form)

    def _on_accept(self):
        category = self.category_edit.currentText().strip()
        if not category:
            QMessageBox.warning(self, "Eksik Bilgi", "Kategori bos olamaz.")
            return
        try:
            date.fromisoformat(self.date_edit.date().toString("yyyy-MM-dd"))
        except ValueError:
            QMessageBox.warning(self, "Gecersiz Tarih", "Lutfen gecerli bir tarih secin.")
            return
        self.accept()

    def get_transaction(self) -> Transaction:
        amount_minor = round(self.amount_edit.value() * 100)
        category = self.category_edit.currentText().strip()
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        note = self.note_edit.text().strip()
        transaction_type = self.type_edit.currentData()
        return Transaction(
            id=self._transaction_id,
            amount_minor=amount_minor,
            category=category,
            date=date_str,
            note=note,
            type=transaction_type,
        )
