from qgis.PyQt import QtWidgets
from qgis.core import QgsProject
import csv
import os


class NettoNullBilanzDialog(QtWidgets.QDialog):
    """Dialog for Netto Null Bilanzierung plugin parameters."""

    def __init__(self, plugin_dir):
        """
        :param plugin_dir: path to plugin folder (used to locate data/factors.csv)
        """
        super().__init__()
        self.setWindowTitle("Blue-Green Infrastructure Balance")
        self.resize(520, 500)

        self.plugin_dir = plugin_dir
        self.beschreibung_values = []

        main_layout = QtWidgets.QVBoxLayout(self)

        # ============================================================
        # === FORM SECTION ===
        # ============================================================
        form_layout = QtWidgets.QFormLayout()

        # Base Layer + Field
        self.base_layer_combo = QtWidgets.QComboBox()
        self.populate_layers(self.base_layer_combo)
        self.base_layer_combo.currentIndexChanged.connect(self.update_base_field_list)

        self.base_field_combo = QtWidgets.QComboBox()
        self.update_base_field_list()

        # Plan Layer + Field
        self.plan_layer_combo = QtWidgets.QComboBox()
        self.populate_layers(self.plan_layer_combo)
        self.plan_layer_combo.currentIndexChanged.connect(self.update_plan_field_list)

        self.plan_field_combo = QtWidgets.QComboBox()
        self.update_plan_field_list()

        # Optional Building Green Layer
        self.building_green_layer_combo = QtWidgets.QComboBox()
        self.populate_layers(self.building_green_layer_combo)
        self.building_green_layer_combo.insertItem(0, "(None)")
        self.building_green_layer_combo.setCurrentIndex(0)
        

        form_layout.addRow("Before (layer):", self.base_layer_combo)
        form_layout.addRow("Before (field):", self.base_field_combo)
        form_layout.addRow("After (layer):", self.plan_layer_combo)
        form_layout.addRow("After (field):", self.plan_field_combo)
        form_layout.addRow("Building Green (optional):", self.building_green_layer_combo)

        main_layout.addLayout(form_layout)

        # ============================================================
        # === BUILDING GREEN SECTION ===
        # ============================================================
        group_box = QtWidgets.QGroupBox("Add additional changes such as green-roof etc. (optional)")
        vbox = QtWidgets.QVBoxLayout(group_box)

        # Table setup
        self.green_table = QtWidgets.QTableWidget(0, 3)
        self.green_table.setHorizontalHeaderLabels(["Base", "Plan", "Area in m²"])
        self.green_table.horizontalHeader().setStretchLastSection(True)

        # Buttons
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
        # === DIALOG BUTTONS ===
        # ============================================================
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # ============================================================
        # Load factors CSV automatically
        # ============================================================
        self.load_factors_csv()
        

    # ---------------------------------------------------------
    # Helper functions
    # ---------------------------------------------------------
    def populate_layers(self, combo):
        combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            combo.addItem(layer.name())
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def update_base_field_list(self):
        self.base_field_combo.clear()
        layer = self.get_layer_by_name(self.base_layer_combo.currentText())
        if layer:
            for f in layer.fields():
                self.base_field_combo.addItem(f.name())

    def update_plan_field_list(self):
        self.plan_field_combo.clear()
        layer = self.get_layer_by_name(self.plan_layer_combo.currentText())
        if layer:
            for f in layer.fields():
                self.plan_field_combo.addItem(f.name())

    def get_layer_by_name(self, name):
        layers = QgsProject.instance().mapLayersByName(name)
        return layers[0] if layers else None

    # ---------------------------------------------------------
    # File pickers
    # ---------------------------------------------------------
    def select_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select Output CSV", "", "CSV Files (*.csv)")
        if path:
            self.output_path.setText(path)

    # ---------------------------------------------------------
    # Building green table management
    # ---------------------------------------------------------
    def load_factors_csv(self):
        """Load 'Beschreibung' values from plugin's data/factors.csv."""
        path = os.path.join(self.plugin_dir, "data", "factors.csv")
        if not os.path.exists(path):
            self.beschreibung_values = []
            print(f"Factors CSV not found: {path}")
            return
        try:
            with open(path, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                self.beschreibung_values = sorted({r["Description"] for r in reader if "Description" in r})
        except Exception:
            self.beschreibung_values = []
            print(f"Failed to load CSV: {e}")

    def add_green_row(self):
        row = self.green_table.rowCount()
        self.green_table.insertRow(row)

        # Bestand combo
        bestand_combo = QtWidgets.QComboBox()
        bestand_combo.addItems(self.beschreibung_values)
        self.green_table.setCellWidget(row, 0, bestand_combo)

        # Planung combo
        planung_combo = QtWidgets.QComboBox()
        planung_combo.addItems(self.beschreibung_values)
        self.green_table.setCellWidget(row, 1, planung_combo)

        # Area input
        area_item = QtWidgets.QTableWidgetItem("0")
        self.green_table.setItem(row, 2, area_item)

    def remove_green_row(self):
        for idx in sorted({i.row() for i in self.green_table.selectedIndexes()}, reverse=True):
            self.green_table.removeRow(idx)

    # ---------------------------------------------------------
    # Collect parameters
    # ---------------------------------------------------------
    def get_parameters(self):
        building_green = []
        for r in range(self.green_table.rowCount()):
            bestand_combo = self.green_table.cellWidget(r, 0)
            planung_combo = self.green_table.cellWidget(r, 1)
            area_item = self.green_table.item(r, 2)
            try:
                area_val = float(area_item.text()) if area_item else 0.0
            except ValueError:
                area_val = 0.0
            building_green.append({
                "Before": bestand_combo.currentText() if bestand_combo else "",
                "After": planung_combo.currentText() if planung_combo else "",
                "Area": area_val
            })

        building_green_layer_name = (
            self.building_green_layer_combo.currentText()
            if self.building_green_layer_combo.currentText() != "(None)"
            else None
        )
        return {
            "base_layer_name": self.base_layer_combo.currentText(),
            "base_field_name": self.base_field_combo.currentText(),
            "plan_layer_name": self.plan_layer_combo.currentText(),
            "plan_field_name": self.plan_field_combo.currentText(),
            "building_green": building_green,
            "factors_csv": os.path.join(self.plugin_dir, "data", "factors.csv"),
            "building_green_layer_name": building_green_layer_name
        }

