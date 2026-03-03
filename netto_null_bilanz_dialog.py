
# -*- coding: utf-8 -*-
from qgis.PyQt import QtCore, QtWidgets
from qgis.core import QgsProject
import csv
import os


class NettoNullBilanzDialog(QtWidgets.QDialog):
    """
    Dialog for Blue-Green Infrastructure Balance plugin parameters.

    Key features:
    - Robust layer/field syncing with default field re-apply after layer changes
    - Optional custom factors CSV upload (falls back to plugin data/factors.csv)
    - Optional building-green layer + field
    - In-dialog log output (messages appended from the plugin while running)
    """
    run_requested = QtCore.pyqtSignal(dict)

    def __init__(self, plugin_dir: str):
        super().__init__()
        self.setWindowTitle("Blue-Green Infrastructure Balance")
        self.resize(640, 640)

        self.plugin_dir = plugin_dir
        self.default_factors_csv = os.path.join(self.plugin_dir, "data", "factors.csv")
        self.custom_factors_csv = None

        self.beschreibung_values = []
        self._load_default_descriptions()

        main_layout = QtWidgets.QVBoxLayout(self)

        # ============================================================
        # === PROJECT / CSV SECTION
        # ============================================================
        top_form = QtWidgets.QFormLayout()

        self.project_title_edit = QtWidgets.QLineEdit()
        self.project_title_edit.setPlaceholderText("z.B. München_Süd (wird als Projektname/Prefix verwendet)")
        top_form.addRow("Projekt (Titel / Prefix):", self.project_title_edit)

        # Factors CSV selector
        factors_row = QtWidgets.QHBoxLayout()
        self.factors_path_edit = QtWidgets.QLineEdit()
        self.factors_path_edit.setReadOnly(True)
        self.factors_path_edit.setText(self.default_factors_csv)

        self.factors_browse_btn = QtWidgets.QPushButton("CSV auswählen… (optional)")
        self.factors_clear_btn = QtWidgets.QPushButton("Zurücksetzen")
        self.factors_browse_btn.clicked.connect(self._pick_factors_csv)
        self.factors_clear_btn.clicked.connect(self._clear_factors_csv)

        factors_row.addWidget(self.factors_path_edit, 1)
        factors_row.addWidget(self.factors_browse_btn)
        factors_row.addWidget(self.factors_clear_btn)
        top_form.addRow("Factors CSV:", factors_row)

        main_layout.addLayout(top_form)

        # ============================================================
        # === LAYER/FIELD SECTION
        # ============================================================
        form_layout = QtWidgets.QFormLayout()

        # Base Layer + Field
        self.base_layer_combo = QtWidgets.QComboBox()
        self._populate_layers(self.base_layer_combo)
        self.base_layer_combo.currentIndexChanged.connect(self._update_base_field_list)

        self.base_field_combo = QtWidgets.QComboBox()

        # Plan Layer + Field
        self.plan_layer_combo = QtWidgets.QComboBox()
        self._populate_layers(self.plan_layer_combo)
        self.plan_layer_combo.currentIndexChanged.connect(self._update_plan_field_list)

        self.plan_field_combo = QtWidgets.QComboBox()

        # Optional Building Green Layer + Field
        self.building_green_layer_combo = QtWidgets.QComboBox()
        self._populate_layers(self.building_green_layer_combo)
        self.building_green_layer_combo.insertItem(0, "(None)")
        self.building_green_layer_combo.setCurrentIndex(0)
        self.building_green_layer_combo.currentIndexChanged.connect(self._update_building_green_field_list)

        self.building_green_field_combo = QtWidgets.QComboBox()

        # Initial field fills + defaults
        self._update_base_field_list()
        self._update_plan_field_list()
        self._update_building_green_field_list()

        form_layout.addRow("Before (layer):", self.base_layer_combo)
        form_layout.addRow("Before (field):", self.base_field_combo)
        form_layout.addRow("After (layer):", self.plan_layer_combo)
        form_layout.addRow("After (field):", self.plan_field_combo)
        form_layout.addRow("Building Green (optional layer):", self.building_green_layer_combo)
        form_layout.addRow("Building Green (optional field):", self.building_green_field_combo)

        main_layout.addLayout(form_layout)

        # ============================================================
        # === BUILDING GREEN TABLE SECTION
        # ============================================================
        group_box = QtWidgets.QGroupBox("Add additional changes such as green-roof etc. (optional)")
        vbox = QtWidgets.QVBoxLayout(group_box)

        self.green_table = QtWidgets.QTableWidget(0, 3)
        self.green_table.setHorizontalHeaderLabels(["Base", "Plan", "Area in m²"])
        self.green_table.horizontalHeader().setStretchLastSection(True)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_row_btn = QtWidgets.QPushButton("➕ Add Row")
        self.remove_row_btn = QtWidgets.QPushButton("🗑 Remove Selected")
        self.add_row_btn.clicked.connect(self._add_green_row)
        self.remove_row_btn.clicked.connect(self._remove_green_row)
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.remove_row_btn)

        vbox.addWidget(self.green_table)
        vbox.addLayout(btn_layout)
        main_layout.addWidget(group_box)

        # ============================================================
        # === LOG OUTPUT
        # ============================================================
        self.log_output = QtWidgets.QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Log / Status…")
        main_layout.addWidget(self.log_output, 1)

        # ============================================================
        # === BUTTONS
        # ============================================================
        btns = QtWidgets.QHBoxLayout()
        self.run_btn = QtWidgets.QPushButton("▶ Run")
        self.close_btn = QtWidgets.QPushButton("Close")
        self.run_btn.clicked.connect(self._emit_run)
        self.close_btn.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(self.run_btn)
        btns.addWidget(self.close_btn)
        main_layout.addLayout(btns)

    # ---------------------------------------------------------
    # Public helpers for plugin
    # ---------------------------------------------------------
    def append_log(self, text: str):
        if not text:
            return
        self.log_output.appendPlainText(text)

    def clear_log(self):
        self.log_output.setPlainText("")

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------
    def _populate_layers(self, combo: QtWidgets.QComboBox):
        combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            combo.addItem(layer.name())
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def _get_layer_by_name(self, name: str):
        layers = QgsProject.instance().mapLayersByName(name)
        return layers[0] if layers else None

    def _set_default_field(self, combo: QtWidgets.QComboBox, default_name: str):
        idx = combo.findText(default_name)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif combo.count() > 0:
            combo.setCurrentIndex(0)

    def _update_base_field_list(self):
        self.base_field_combo.blockSignals(True)
        current = self.base_field_combo.currentText()
        self.base_field_combo.clear()
        layer = self._get_layer_by_name(self.base_layer_combo.currentText())
        if layer:
            for f in layer.fields():
                self.base_field_combo.addItem(f.name())

        # keep previous if still present, else default
        if current and self.base_field_combo.findText(current) >= 0:
            self.base_field_combo.setCurrentIndex(self.base_field_combo.findText(current))
        else:
            self._set_default_field(self.base_field_combo, "Flächentyp")

        self.base_field_combo.blockSignals(False)

    def _update_plan_field_list(self):
        self.plan_field_combo.blockSignals(True)
        current = self.plan_field_combo.currentText()
        self.plan_field_combo.clear()
        layer = self._get_layer_by_name(self.plan_layer_combo.currentText())
        if layer:
            for f in layer.fields():
                self.plan_field_combo.addItem(f.name())

        if current and self.plan_field_combo.findText(current) >= 0:
            self.plan_field_combo.setCurrentIndex(self.plan_field_combo.findText(current))
        else:
            self._set_default_field(self.plan_field_combo, "Flächentyp")

        self.plan_field_combo.blockSignals(False)

    def _update_building_green_field_list(self):
        self.building_green_field_combo.blockSignals(True)
        current = self.building_green_field_combo.currentText()
        self.building_green_field_combo.clear()

        if self.building_green_layer_combo.currentText() != "(None)":
            layer = self._get_layer_by_name(self.building_green_layer_combo.currentText())
            if layer:
                for f in layer.fields():
                    self.building_green_field_combo.addItem(f.name())

        if current and self.building_green_field_combo.findText(current) >= 0:
            self.building_green_field_combo.setCurrentIndex(self.building_green_field_combo.findText(current))
        else:
            self._set_default_field(self.building_green_field_combo, "Massnahme")

        self.building_green_field_combo.blockSignals(False)

    def _load_default_descriptions(self):
        """Load description values for the manual building-green table combos."""
        path = self.default_factors_csv
        self.beschreibung_values = []
        if not os.path.exists(path):
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                self.beschreibung_values = sorted({r.get("Description", "").strip() for r in reader if r.get("Description")})
        except Exception:
            self.beschreibung_values = []

    def _pick_factors_csv(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Factors CSV", "", "CSV Files (*.csv)")
        if path:
            self.custom_factors_csv = path
            self.factors_path_edit.setText(path)
            # refresh building-green manual combo values based on selected file
            self._load_descriptions_from_selected()

    def _clear_factors_csv(self):
        self.custom_factors_csv = None
        self.factors_path_edit.setText(self.default_factors_csv)
        self._load_default_descriptions()

    def _load_descriptions_from_selected(self):
        path = self.custom_factors_csv or self.default_factors_csv
        self.beschreibung_values = []
        if not os.path.exists(path):
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                self.beschreibung_values = sorted({r.get("Description", "").strip() for r in reader if r.get("Description")})
        except Exception:
            self.beschreibung_values = []

    def _add_green_row(self):
        row = self.green_table.rowCount()
        self.green_table.insertRow(row)

        before_combo = QtWidgets.QComboBox()
        before_combo.addItems(self.beschreibung_values)
        self.green_table.setCellWidget(row, 0, before_combo)

        after_combo = QtWidgets.QComboBox()
        after_combo.addItems(self.beschreibung_values)
        self.green_table.setCellWidget(row, 1, after_combo)

        self.green_table.setItem(row, 2, QtWidgets.QTableWidgetItem("0"))

    def _remove_green_row(self):
        for idx in sorted({i.row() for i in self.green_table.selectedIndexes()}, reverse=True):
            self.green_table.removeRow(idx)

    def _emit_run(self):
        self.run_requested.emit(self.get_parameters())

    # ---------------------------------------------------------
    # Collect parameters
    # ---------------------------------------------------------
    def get_parameters(self) -> dict:
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
                "Area": area_val,
            })

        bg_layer_name = self.building_green_layer_combo.currentText()
        if bg_layer_name == "(None)":
            bg_layer_name = None

        return {
            "project_title": self.project_title_edit.text().strip(),
            "base_layer_name": self.base_layer_combo.currentText(),
            "base_field_name": self.base_field_combo.currentText(),
            "plan_layer_name": self.plan_layer_combo.currentText(),
            "plan_field_name": self.plan_field_combo.currentText(),
            "building_green": building_green,
            "building_green_layer_name": bg_layer_name,
            "building_green_field_name": self.building_green_field_combo.currentText(),
            "factors_csv": self.custom_factors_csv or self.default_factors_csv,
        }
