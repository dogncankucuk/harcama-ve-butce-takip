"""Main window: transaction table, filter bar, chart panel, budget panel."""

import os

os.environ["QT_API"] = "pyside6"

from datetime import date

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import csv_io
import db
from ui.transaction_dialog import TransactionDialog

ALL_CATEGORIES_LABEL = "Tumu"
ALL_TYPES_LABEL = "Tumu"
TYPE_FILTER_ITEMS = [(ALL_TYPES_LABEL, None), ("Gider", "gider"), ("Gelir", "gelir")]
TYPE_DISPLAY = {"gider": "Gider", "gelir": "Gelir"}


def format_tl(amount_minor: int) -> str:
    tl = amount_minor / 100
    text = f"{tl:,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} TL"


class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setWindowTitle("Harcama & Butce Takip")
        self.resize(1100, 650)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        root_layout.addWidget(self._build_filter_bar())

        content_layout = QHBoxLayout()
        content_layout.addWidget(self._build_table_panel(), stretch=2)
        content_layout.addWidget(self._build_side_panel(), stretch=1)
        root_layout.addLayout(content_layout)

        self.refresh_all()

    # ---------- UI construction ----------

    def _build_filter_bar(self) -> QWidget:
        box = QGroupBox("Filtrele")
        layout = QHBoxLayout(box)

        layout.addWidget(QLabel("Kategori:"))
        self.filter_category = QComboBox()
        layout.addWidget(self.filter_category)

        layout.addWidget(QLabel("Tur:"))
        self.filter_type = QComboBox()
        for label, _ in TYPE_FILTER_ITEMS:
            self.filter_type.addItem(label)
        layout.addWidget(self.filter_type)

        self.filter_date_enabled = QCheckBox("Tarih Araligi")
        layout.addWidget(self.filter_date_enabled)

        self.filter_date_from = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_from.setDate(QDate.currentDate().addMonths(-1))
        layout.addWidget(self.filter_date_from)

        layout.addWidget(QLabel("-"))

        self.filter_date_to = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_to.setDate(QDate.currentDate())
        layout.addWidget(self.filter_date_to)

        layout.addWidget(QLabel("Not icinde ara:"))
        self.filter_search = QLineEdit()
        self.filter_search.setPlaceholderText("metin...")
        layout.addWidget(self.filter_search)

        apply_button = QPushButton("Uygula")
        apply_button.clicked.connect(self.refresh_table)
        layout.addWidget(apply_button)

        clear_button = QPushButton("Temizle")
        clear_button.clicked.connect(self._clear_filters)
        layout.addWidget(clear_button)

        return box

    def _build_table_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Tutar", "Tur", "Kategori", "Tarih", "Not"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        add_button = QPushButton("Ekle")
        add_button.clicked.connect(self._add_transaction)
        edit_button = QPushButton("Duzenle")
        edit_button.clicked.connect(self._edit_transaction)
        delete_button = QPushButton("Sil")
        delete_button.clicked.connect(self._delete_transaction)
        export_button = QPushButton("CSV Disa Aktar")
        export_button.clicked.connect(self._export_csv)
        import_button = QPushButton("CSV Ice Aktar")
        import_button.clicked.connect(self._import_csv)
        for b in (add_button, edit_button, delete_button, export_button, import_button):
            button_row.addWidget(b)
        layout.addLayout(button_row)

        return panel

    def _build_side_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(self._build_budget_panel())
        layout.addWidget(self._build_chart_panel())

        return panel

    def _build_budget_panel(self) -> QWidget:
        box = QGroupBox("Aylik Butce")
        layout = QVBoxLayout(box)

        set_row = QHBoxLayout()
        self.budget_edit = QDoubleSpinBox()
        self.budget_edit.setRange(0.0, 100_000_000.0)
        self.budget_edit.setDecimals(2)
        self.budget_edit.setSuffix(" TL")
        set_row.addWidget(self.budget_edit)
        save_budget_button = QPushButton("Kaydet")
        save_budget_button.clicked.connect(self._save_budget)
        set_row.addWidget(save_budget_button)
        layout.addLayout(set_row)

        self.budget_status_label = QLabel()
        self.budget_status_label.setWordWrap(True)
        layout.addWidget(self.budget_status_label)

        self.budget_warning_label = QLabel()
        self.budget_warning_label.setWordWrap(True)
        self.budget_warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.budget_warning_label)

        self.net_balance_label = QLabel()
        self.net_balance_label.setWordWrap(True)
        layout.addWidget(self.net_balance_label)

        return box

    def _build_chart_panel(self) -> QWidget:
        box = QGroupBox("Grafik")
        layout = QVBoxLayout(box)

        self.chart_type = QComboBox()
        self.chart_type.addItems(["Bu Ayin Kategori Dagilimi", "Aylik Toplamlar"])
        self.chart_type.currentIndexChanged.connect(self.refresh_chart)
        layout.addWidget(self.chart_type)

        self.canvas = FigureCanvas(Figure(figsize=(5, 3)))
        layout.addWidget(self.canvas)

        return box

    # ---------- data refresh ----------

    def refresh_all(self):
        self._refresh_category_filter()
        self.refresh_table()
        self.refresh_budget_status()
        self.refresh_chart()

    def _refresh_category_filter(self):
        current = self.filter_category.currentText()
        self.filter_category.blockSignals(True)
        self.filter_category.clear()
        self.filter_category.addItem(ALL_CATEGORIES_LABEL)
        self.filter_category.addItems(db.get_categories(self.conn))
        index = self.filter_category.findText(current)
        self.filter_category.setCurrentIndex(index if index >= 0 else 0)
        self.filter_category.blockSignals(False)

    def refresh_table(self):
        category = self.filter_category.currentText()
        category = None if category in ("", ALL_CATEGORIES_LABEL) else category
        transaction_type = TYPE_FILTER_ITEMS[self.filter_type.currentIndex()][1]
        date_from = self.filter_date_from.date().toString("yyyy-MM-dd") if self.filter_date_enabled.isChecked() else None
        date_to = self.filter_date_to.date().toString("yyyy-MM-dd") if self.filter_date_enabled.isChecked() else None
        search_text = self.filter_search.text().strip() or None

        transactions = db.get_transactions(
            self.conn,
            category=category,
            date_from=date_from,
            date_to=date_to,
            search_text=search_text,
            type=transaction_type,
        )

        self.table.setRowCount(0)
        for t in transactions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            amount_item = QTableWidgetItem(format_tl(t.amount_minor))
            amount_item.setData(Qt.UserRole, t.id)
            self.table.setItem(row, 0, amount_item)
            self.table.setItem(row, 1, QTableWidgetItem(TYPE_DISPLAY.get(t.type, t.type)))
            self.table.setItem(row, 2, QTableWidgetItem(t.category))
            self.table.setItem(row, 3, QTableWidgetItem(t.date))
            self.table.setItem(row, 4, QTableWidgetItem(t.note))

    def _clear_filters(self):
        self.filter_category.setCurrentIndex(0)
        self.filter_type.setCurrentIndex(0)
        self.filter_date_enabled.setChecked(False)
        self.filter_search.clear()
        self.refresh_table()

    def refresh_budget_status(self):
        current_month = date.today().strftime("%Y-%m")
        spent = db.get_month_spending(self.conn, current_month)
        budget = db.get_budget(self.conn)
        net = db.monthly_net(self.conn, current_month)

        self.budget_edit.blockSignals(True)
        self.budget_edit.setValue((budget or 0) / 100)
        self.budget_edit.blockSignals(False)

        if budget is None:
            self.budget_status_label.setText(f"Bu ay harcanan: {format_tl(spent)}. Henuz butce belirlenmedi.")
            self.budget_warning_label.setText("")
        else:
            self.budget_status_label.setText(f"Bu ay harcanan: {format_tl(spent)} / Butce: {format_tl(budget)}")
            if db.is_over_budget(spent, budget):
                over = spent - budget
                self.budget_warning_label.setText(f"UYARI: Aylik butceyi {format_tl(over)} astiniz!")
            else:
                self.budget_warning_label.setText("")

        self.net_balance_label.setText(f"Bu ay net bakiye (gelir - gider): {format_tl(net)}")

    def refresh_chart(self):
        ax = self.canvas.figure.gca()
        ax.clear()

        if self.chart_type.currentIndex() == 0:
            current_month = date.today().strftime("%Y-%m")
            totals = db.category_totals_for_month(self.conn, current_month, type="gider")
            if totals:
                categories = list(totals.keys())
                values = [totals[c] / 100 for c in categories]
                ax.bar(categories, values)
                ax.set_ylabel("TL")
                ax.set_title(f"{current_month} Gider Kategori Dagilimi")
                self.canvas.figure.autofmt_xdate(rotation=30)
            else:
                ax.set_title(f"{current_month} icin veri yok")
        else:
            totals = db.monthly_totals(self.conn)
            months = sorted(totals.keys())
            if months:
                income = [totals[m]["gelir"] / 100 for m in months]
                expense = [totals[m]["gider"] / 100 for m in months]
                ax.plot(months, income, marker="o", label="Gelir", color="green")
                ax.plot(months, expense, marker="o", label="Gider", color="red")
                ax.set_ylabel("TL")
                ax.set_title("Aylik Gelir/Gider")
                ax.legend()
                self.canvas.figure.autofmt_xdate(rotation=30)
            else:
                ax.set_title("Veri yok")

        self.canvas.draw_idle()

    # ---------- actions ----------

    def _selected_transaction_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _add_transaction(self):
        dialog = TransactionDialog(self, categories=db.get_categories(self.conn))
        if dialog.exec():
            t = dialog.get_transaction()
            db.add_transaction(self.conn, t.amount_minor, t.category, t.date, t.note, type=t.type)
            self.refresh_all()

    def _edit_transaction(self):
        transaction_id = self._selected_transaction_id()
        if transaction_id is None:
            QMessageBox.information(self, "Secim Yok", "Lutfen duzenlenecek bir islem secin.")
            return
        existing = next((t for t in db.get_transactions(self.conn) if t.id == transaction_id), None)
        if existing is None:
            return
        dialog = TransactionDialog(self, transaction=existing, categories=db.get_categories(self.conn))
        if dialog.exec():
            t = dialog.get_transaction()
            db.update_transaction(self.conn, transaction_id, t.amount_minor, t.category, t.date, t.note, type=t.type)
            self.refresh_all()

    def _delete_transaction(self):
        transaction_id = self._selected_transaction_id()
        if transaction_id is None:
            QMessageBox.information(self, "Secim Yok", "Lutfen silinecek bir islem secin.")
            return
        confirm = QMessageBox.question(self, "Onay", "Secili islemi silmek istediginize emin misiniz?")
        if confirm == QMessageBox.Yes:
            db.delete_transaction(self.conn, transaction_id)
            self.refresh_all()

    def _save_budget(self):
        amount_minor = round(self.budget_edit.value() * 100)
        if amount_minor <= 0:
            QMessageBox.warning(self, "Gecersiz Butce", "Lutfen 0'dan buyuk bir butce girin.")
            return
        db.set_budget(self.conn, amount_minor)
        self.refresh_budget_status()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV Disa Aktar", "", "CSV Dosyalari (*.csv)")
        if not path:
            return
        csv_io.export_csv(self.conn, path)
        QMessageBox.information(self, "Basarili", "Islemler CSV dosyasina aktarildi.")

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "CSV Ice Aktar", "", "CSV Dosyalari (*.csv)")
        if not path:
            return
        try:
            count = csv_io.import_csv(self.conn, path)
        except (ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Ice Aktarma Hatasi", f"CSV ice aktarilamadi: {exc}")
            return
        QMessageBox.information(self, "Basarili", f"{count} islem ice aktarildi.")
        self.refresh_all()
