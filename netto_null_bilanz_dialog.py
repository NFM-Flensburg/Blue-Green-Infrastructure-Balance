# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProject, QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox
import csv
import os


class NettoNullBilanzDialog(QtWidgets.QDialog):
    """
    Dialog for Blue-Green Infrastructure Balance parameters.

    Key behavior:
      - Dialog stays open
      - Clicking "Run" emits run_requested(params: dict)
      - A log box at the bottom can be appended to via append_log()
    """

    run_requested = QtCore.pyqtSignal(dict)

    def __init__(self, plugin_dir: str):
        super().__init__()
        self.setWindowTitle("Blue-Green Infrastructure Balance")
        self.resize(640, 650)

        self.plugin_dir = plugin_dir
        self.beschreibung_values = []
        self._default_factors_csv = os.path.join(self.plugin_dir, "data", "factors.csv")
        self._factors_csv_path = self._default_factors_csv

        main_layout = QtWidgets.QVBoxLayout(self)

        # ============================================================
        # === PROJECT SETTINGS ===
        # ============================================================
        project_box = QtWidgets.QGroupBox("Projekt")
        project_layout = QtWidgets.QFormLayout(project_box)

        self.project_title_edit = QtWidgets.QLineEdit()
        self.project_title_edit.setPlaceholderText(
            "z.B. Mömax (wird für Ergebnisordner/Dateien verwendet)"
        )

        project_layout.addRow("Projektname:", self.project_title_edit)
        main_layout.addWidget(project_box)

        # ============================================================
        # === FACTORS CSV (optional override) ===
        # ============================================================
        factors_box = QtWidgets.QGroupBox("Faktoren (CSV)")
        factors_layout = QtWidgets.QGridLayout(factors_box)

        self.factors_path_edit = QtWidgets.QLineEdit()
        self.factors_path_edit.setReadOnly(True)
        self.factors_path_edit.setText(self._factors_csv_path)

        self.btn_choose_factors = QtWidgets.QPushButton("CSV auswählen… (optional)")
        self.btn_use_default_factors = QtWidgets.QPushButton("Standard verwenden")

        self.btn_choose_factors.clicked.connect(self._pick_factors_csv)
        self.btn_use_default_factors.clicked.connect(self._use_default_factors_csv)

        factors_layout.addWidget(QtWidgets.QLabel("Faktoren CSV:"), 0, 0)
        factors_layout.addWidget(self.factors_path_edit, 0, 1, 1, 2)
        factors_layout.addWidget(self.btn_choose_factors, 1, 1)
        factors_layout.addWidget(self.btn_use_default_factors, 1, 2)

        main_layout.addWidget(factors_box)

        # ============================================================
        # === FORM SECTION (layers/fields) ===
        # ============================================================
        form_box = QtWidgets.QGroupBox("Layer & Felder")
        form_layout = QtWidgets.QFormLayout(form_box)

        # Before Layer + Field (nur Polygon-Layer)
        self.base_layer_combo = QgsMapLayerComboBox()
        self.base_layer_combo.setProject(QgsProject.instance())
        self.base_layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.base_layer_combo.layerChanged.connect(self.update_base_field_list)

        self.base_field_combo = QtWidgets.QComboBox()
        self.update_base_field_list()

        # After Layer + Field (nur Polygon-Layer)
        self.plan_layer_combo = QgsMapLayerComboBox()
        self.plan_layer_combo.setProject(QgsProject.instance())
        self.plan_layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.plan_layer_combo.layerChanged.connect(self.update_plan_field_list)

        self.plan_field_combo = QtWidgets.QComboBox()
        self.update_plan_field_list()

        # Optional Building Green Layer + Field
        # -> absichtlich OHNE Polygon-Filter, damit auch Excel/CSV/Tabellen sichtbar sind
        self.building_green_layer_combo = QgsMapLayerComboBox()
        self.building_green_layer_combo.setProject(QgsProject.instance())
        self.building_green_layer_combo.setAllowEmptyLayer(True)
        self.building_green_layer_combo.setCurrentIndex(-1)
        self.building_green_layer_combo.layerChanged.connect(self.update_building_green_field_list)

        self.building_green_field_combo = QtWidgets.QComboBox()
        self.update_building_green_field_list()

        # Set defaults after initial population
        self._set_default_field(self.base_field_combo, "Flächentyp")
        self._set_default_field(self.plan_field_combo, "Flächentyp")
        self._set_default_field(self.building_green_field_combo, "Massnahme")

        form_layout.addRow("Before (layer):", self.base_layer_combo)
        form_layout.addRow("Before (field):", self.base_field_combo)
        form_layout.addRow("After (layer):", self.plan_layer_combo)
        form_layout.addRow("After (field):", self.plan_field_combo)
        form_layout.addRow("Optional: Building Green (layer):", self.building_green_layer_combo)
        form_layout.addRow("Optional: Building Green (field):", self.building_green_field_combo)

        main_layout.addWidget(form_box)

        # ============================================================
        # === BUILDING GREEN TABLE SECTION (manual rows) ===
        # ============================================================
        group_box = QtWidgets.QGroupBox("Zusätzliche Änderungen (z.B. Gründach) – manuell (optional)")
        vbox = QtWidgets.QVBoxLayout(group_box)

        self.green_table = QtWidgets.QTableWidget(0, 3)
        self.green_table.setHorizontalHeaderLabels(["Before", "After", "Area in m²"])
        self.green_table.horizontalHeader().setStretchLastSection(True)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_row_btn = QtWidgets.QPushButton("➕ Add Row")
        self.remove_row_btn = QtWidgets.QPushButton("🗑 Remove Selected")

        self.add_row_btn.clicked.connect(self.add_green_row)
        self.remove_row_btn.clicked.connect(self.remove_green_row)
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.remove_row_btn)

        vbox.addWidget(self.green_table)
        vbox.addLayout(btn_layout)
        main_layout.addWidget(group_box)

        # ============================================================
        # === LOG OUTPUT ===
        # ============================================================
        log_box = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout(log_box)
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Hier erscheinen Validierung, Warnungen und Prozess-Output…")
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_box)

        # ============================================================
        # === DIALOG BUTTONS (Run / Close) ===
        # ============================================================
        buttons = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("▶ Run")
        self.btn_close = QtWidgets.QPushButton("Close")

        self.btn_run.clicked.connect(self._on_run_clicked)
        self.btn_close.clicked.connect(self.close)

        buttons.addStretch(1)
        buttons.addWidget(self.btn_run)
        buttons.addWidget(self.btn_close)
        main_layout.addLayout(buttons)

        # ============================================================
        # Load factors CSV values for manual building-green table combos
        # ============================================================
        self.load_factors_csv_values()

    # ---------------------------------------------------------
    # Logging helpers for plugin
    # ---------------------------------------------------------
    def clear_log(self):
        self.log_text.clear()

    def append_log(self, text: str):
        self.log_text.appendPlainText(str(text))

    # ---------------------------------------------------------
    # CSV handling
    # ---------------------------------------------------------
    def _pick_factors_csv(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select factors CSV", "", "CSV Files (*.csv)"
        )
        if path:
            self._factors_csv_path = path
            self.factors_path_edit.setText(path)
            self.load_factors_csv_values()

    def _use_default_factors_csv(self):
        self._factors_csv_path = self._default_factors_csv
        self.factors_path_edit.setText(self._factors_csv_path)
        self.load_factors_csv_values()

    def load_factors_csv_values(self):
        """Load 'Description' values from the currently selected factors CSV."""
        path = self._factors_csv_path
        if not os.path.exists(path):
            self.beschreibung_values = []
            self.append_log(f"⚠ Factors CSV not found: {path}")
            return

        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                self.beschreibung_values = sorted(
                    {
                        r.get("Description", "").strip()
                        for r in reader
                        if r.get("Description")
                    }
                )
        except Exception as e:
            self.beschreibung_values = []
            self.append_log(f"⚠ Failed to load factors CSV: {e}")

    # ---------------------------------------------------------
    # Layer helpers
    # ---------------------------------------------------------
    def _current_layer(self, combo):
        try:
            return combo.currentLayer()
        except Exception:
            return None

    def _set_default_field(self, combo: QtWidgets.QComboBox, default_name: str):
        idx = combo.findText(default_name)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif combo.count() > 0:
            combo.setCurrentIndex(0)

    def update_base_field_list(self):
        self.base_field_combo.blockSignals(True)
        current = self.base_field_combo.currentText()
        self.base_field_combo.clear()

        layer = self._current_layer(self.base_layer_combo)
        if layer:
            for f in layer.fields():
                self.base_field_combo.addItem(f.name())

        idx = self.base_field_combo.findText(current)
        if idx >= 0:
            self.base_field_combo.setCurrentIndex(idx)
        else:
            self._set_default_field(self.base_field_combo, "Flächentyp")

        self.base_field_combo.blockSignals(False)

    def update_plan_field_list(self):
        self.plan_field_combo.blockSignals(True)
        current = self.plan_field_combo.currentText()
        self.plan_field_combo.clear()

        layer = self._current_layer(self.plan_layer_combo)
        if layer:
            for f in layer.fields():
                self.plan_field_combo.addItem(f.name())

        idx = self.plan_field_combo.findText(current)
        if idx >= 0:
            self.plan_field_combo.setCurrentIndex(idx)
        else:
            self._set_default_field(self.plan_field_combo, "Flächentyp")

        self.plan_field_combo.blockSignals(False)

    def update_building_green_field_list(self):
        self.building_green_field_combo.blockSignals(True)
        current = self.building_green_field_combo.currentText()
        self.building_green_field_combo.clear()

        layer = self._current_layer(self.building_green_layer_combo)
        if layer:
            for f in layer.fields():
                self.building_green_field_combo.addItem(f.name())

        idx = self.building_green_field_combo.findText(current)
        if idx >= 0:
            self.building_green_field_combo.setCurrentIndex(idx)
        else:
            self._set_default_field(self.building_green_field_combo, "Massnahme")

        self.building_green_field_combo.blockSignals(False)

    # ---------------------------------------------------------
    # Building-green table management
    # ---------------------------------------------------------
    def add_green_row(self):
        row = self.green_table.rowCount()
        self.green_table.insertRow(row)

        before_combo = QtWidgets.QComboBox()
        before_combo.addItems(self.beschreibung_values)
        self.green_table.setCellWidget(row, 0, before_combo)

        after_combo = QtWidgets.QComboBox()
        after_combo.addItems(self.beschreibung_values)
        self.green_table.setCellWidget(row, 1, after_combo)

        area_item = QtWidgets.QTableWidgetItem("0")
        self.green_table.setItem(row, 2, area_item)

    def remove_green_row(self):
        for idx in sorted({i.row() for i in self.green_table.selectedIndexes()}, reverse=True):
            self.green_table.removeRow(idx)

    # ---------------------------------------------------------
    # Run trigger
    # ---------------------------------------------------------
    def _on_run_clicked(self):
        params = self.get_parameters()
        self.run_requested.emit(params)

    # ---------------------------------------------------------
    # Collect parameters
    # ---------------------------------------------------------
    def get_parameters(self):
        building_green = []

        for r in range(self.green_table.rowCount()):
            before_combo = self.green_table.cellWidget(r, 0)
            after_combo = self.green_table.cellWidget(r, 1)
            area_item = self.green_table.item(r, 2)

            try:
                area_val = float(area_item.text()) if area_item else 0.0
            except ValueError:
                area_val = 0.0

            building_green.append({
                "Before": before_combo.currentText() if before_combo else "",
                "After": after_combo.currentText() if after_combo else "",
                "Area": area_val
            })

        base_layer = self._current_layer(self.base_layer_combo)
        plan_layer = self._current_layer(self.plan_layer_combo)
        building_green_layer = self._current_layer(self.building_green_layer_combo)

        return {
            "project_title": self.project_title_edit.text().strip(),

            # Namen für Kompatibilität mit bestehendem Code
            "base_layer_name": base_layer.name() if base_layer else "",
            "base_field_name": self.base_field_combo.currentText(),

            "plan_layer_name": plan_layer.name() if plan_layer else "",
            "plan_field_name": self.plan_field_combo.currentText(),

            "building_green": building_green,
            "building_green_layer_name": building_green_layer.name() if building_green_layer else None,
            "building_green_field_name": self.building_green_field_combo.currentText(),
            "factors_csv": self._factors_csv_path,

            # optional robuster für spätere Weiterentwicklung
            "base_layer": base_layer,
            "plan_layer": plan_layer,
            "building_green_layer": building_green_layer,
        }
