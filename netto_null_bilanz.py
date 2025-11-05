# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface
import os
import traceback 

from .netto_null_bilanz_dialog import NettoNullBilanzDialog
from . import script_core, plotting


class NettoNullBilanz:
    """Main QGIS plugin class for Netto Null Bilanzierung."""

    def __init__(self, iface):
        """
        Constructor for the plugin.
        :param iface: A QGIS interface instance that allows interaction with QGIS.
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        project = QgsProject.instance()
        project_path = project.fileName()
        if project_path:
            project_dir = os.path.dirname(project_path)
            self.output_dir = os.path.join(project_dir, "bgib-results")
        else:
            # fallback if no project is saved yet
            self.output_dir = os.path.expanduser("~/bgib-results")
        os.makedirs(self.output_dir, exist_ok=True)
        self.action = None
        self.dlg = None

    # ------------------------------------------------------------------

    def initGui(self):
        """Add the plugin action (menu and toolbar button) to QGIS."""
        icon = os.path.join(self.plugin_dir, "icons", "icon.png")

        self.action = QAction(QIcon(icon), u"Blue-Green Infrastructure Balance", self.iface.mainWindow())
        self.action.setToolTip("Run BGI Analysis")
        self.action.triggered.connect(self.run)

        # Add to QGIS toolbar and menu
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Blue-Green Infrastructure Balance", self.action)

    # ------------------------------------------------------------------

    def unload(self):
        """Remove the plugin action from QGIS toolbar and menu."""
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Blue-Green Infrastructure Balance", self.action)

    # ------------------------------------------------------------------

    def run(self):
        """Execute the main plugin logic via the dialog."""
        self.dlg = NettoNullBilanzDialog(self.plugin_dir)

        if not self.dlg.exec_():  # User pressed Cancel
            return

        # Retrieve parameters from dialog
        params = self.dlg.get_parameters()
        base_layer_name = params["base_layer_name"]
        base_field_name = params["base_field_name"]
        plan_layer_name = params["plan_layer_name"]
        plan_field_name = params["plan_field_name"]
        factors_csv = params["factors_csv"]
        output_csv_path = os.path.join(self.output_dir, "bgig_balance.csv")
        building_green = params["building_green"]
        building_green_layer_name = params["building_green_layer_name"]
        
        # Validate required inputs
        if not base_layer_name or not base_field_name or not plan_layer_name or not plan_field_name:
            QMessageBox.warning(
                None,
                "Missing Input",
                "Please make sure *before layer*, *before field*, *after layer* and *after field* are selected.",
            )
            return

        try:
            # Call the processing function in script_core
            results_info, df = script_core.main(
                base_layer_name=base_layer_name,
                base_field_name=base_field_name,
                planning_layer_name=plan_layer_name,
                plan_field_name=plan_field_name,
                factors_csv=factors_csv,
                output_csv_path=output_csv_path,
                building_green = building_green,
                building_green_layer_name=building_green_layer_name
            )
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Success")
            msg.setTextFormat(Qt.PlainText)  # prevents rich text parsing (no unwanted wrapping)
            msg.setText("✅ Results exported successfully!")
            text = "\n \n".join([f"{k}: {v}" for k, v in results_info.items()])
            msg.setInformativeText(text)
            msg.exec_()
            
            #QMessageBox.information(None, "Success", f"✅ Results exported successfully!\n\n{msg}")
            

        except Exception as e:
    	    traceback.print_exc()  # <-- Full traceback in the Python console
    	    QMessageBox.critical(None, "Error", f"❌ {str(e)}")

