from qgis.PyQt import QtWidgets
from qgis.core import QgsProject


class NettoNullBilanzDialog(QtWidgets.QDialog):
    """Dialog for collecting user input parameters for the Netto Null Bilanzierung plugin."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Netto Null Bilanzierung")
        self.resize(420, 250)

        layout = QtWidgets.QFormLayout(self)

        # --- Base layer selection ---
        self.base_layer_combo = QtWidgets.QComboBox()
        self.populate_layers(self.base_layer_combo)
        self.base_layer_combo.currentIndexChanged.connect(self.update_base_field_list)

        # --- Base field selection ---
        self.base_field_combo = QtWidgets.QComboBox()
        self.update_base_field_list()  # populate initially

        # --- Plan layer selection ---
        self.plan_layer_combo = QtWidgets.QComboBox()
        self.populate_layers(self.plan_layer_combo)
        self.plan_layer_combo.currentIndexChanged.connect(self.update_plan_field_list)

        # --- Plan field selection ---
        self.plan_field_combo = QtWidgets.QComboBox()
        self.update_plan_field_list()

        # --- Input CSV selection (optional) ---
        self.input_csv_path = QtWidgets.QLineEdit()
        self.input_csv_button = QtWidgets.QPushButton("Browse…")
        self.input_csv_button.clicked.connect(self.select_input_csv)

        input_csv_layout = QtWidgets.QHBoxLayout()
        input_csv_layout.addWidget(self.input_csv_path)
        input_csv_layout.addWidget(self.input_csv_button)

        # --- Output CSV selection ---
        self.output_path = QtWidgets.QLineEdit()
        self.output_button = QtWidgets.QPushButton("Browse…")
        self.output_button.clicked.connect(self.select_output)

        output_layout = QtWidgets.QHBoxLayout()
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.output_button)

        # --- Form layout ---
        layout.addRow("Base Layer:", self.base_layer_combo)
        layout.addRow("Base Field:", self.base_field_combo)
        layout.addRow("Plan Layer:", self.plan_layer_combo)
        layout.addRow("Plan Field:", self.plan_field_combo)
        layout.addRow("Factors CSV (optional):", input_csv_layout)
        layout.addRow("Output CSV:", output_layout)

        # --- Dialog buttons ---
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addRow(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    # ---------------------------------------------------------
    # Helper functions
    # ---------------------------------------------------------

    def populate_layers(self, combo):
        """Fill combo box with currently loaded vector layers."""
        combo.clear()
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            combo.addItem(layer.name())
        # Optional: preselect something sensible
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def update_base_field_list(self):
        """Update available fields when base layer changes."""
        self.base_field_combo.clear()
        layer_name = self.base_layer_combo.currentText()
        layer = self.get_layer_by_name(layer_name)
        if not layer:
            return
        for field in layer.fields():
            self.base_field_combo.addItem(field.name())
        # Optional preselect
        idx = self.base_field_combo.findText("field_name_material")
        if idx >= 0:
            self.base_field_combo.setCurrentIndex(idx)

    def update_plan_field_list(self):
        """Update available fields when plan layer changes."""
        self.plan_field_combo.clear()
        layer_name = self.plan_layer_combo.currentText()
        layer = self.get_layer_by_name(layer_name)
        if not layer:
            return
        for field in layer.fields():
            self.plan_field_combo.addItem(field.name())

    def get_layer_by_name(self, name):
        """Return a QgsVectorLayer by name."""
        layers = QgsProject.instance().mapLayersByName(name)
        return layers[0] if layers else None

    def select_output(self):
        """Open file dialog to select output CSV path."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Select Output CSV", "", "CSV Files (*.csv)"
        )
        if path:
            self.output_path.setText(path)

    def select_input_csv(self):
        """Open file dialog to select input CSV path."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Input CSV", "", "CSV Files (*.csv)"
        )
        if path:
            self.input_csv_path.setText(path)

    # ---------------------------------------------------------
    # Accessors for the collected values
    # ---------------------------------------------------------

    def get_parameters(self):
        """Return all selected parameters as a dict."""
        return {
            "base_layer_name": self.base_layer_combo.currentText(),
            "base_field_name": self.base_field_combo.currentText(),
            "plan_layer_name": self.plan_layer_combo.currentText(),
            "plan_field_name": self.plan_field_combo.currentText(),
            "input_csv_path": self.input_csv_path.text(),
            "output_path": self.output_path.text(),
        }

