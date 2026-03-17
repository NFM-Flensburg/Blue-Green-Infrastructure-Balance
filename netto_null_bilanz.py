# -*- coding: utf-8 -*-
import os
import re
import datetime
import traceback

import pandas as pd
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject

from .netto_null_bilanz_dialog import NettoNullBilanzDialog
from . import script_core, plotting


def sanitize_project_name(name: str) -> str:
    """
    Windows-safe but Unicode-friendly filename component.
    Keeps umlauts; removes forbidden characters and trims.
    """
    name = (name or "").strip()
    if not name:
        return ""
    name = re.sub(r"\s+", "_", name, flags=re.UNICODE)          # whitespace -> _
    name = re.sub(r'[<>:"/\\\\|?*]', "", name)              # Windows forbidden
    name = "".join(ch for ch in name if ch >= " " and ch != "\x7f")  # control chars
    name = name.rstrip(" .")                                    # trailing dot/space
    return name


def normalize_key(s: str) -> str:
    """Normalization for matching layer values to CSV keys."""
    if s is None:
        return ""
    s = str(s).strip()
    if not s:
        return ""
    s = s.casefold()
    s = (
        s.replace("ä", "ae")
         .replace("ö", "oe")
         .replace("ü", "ue")
         .replace("ß", "ss")
    )
    s = s.replace("-", "_")
    s = re.sub(r"\s+", " ", s)
    return s


class NettoNullBilanz:
    """Main QGIS plugin class."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dlg = None

    # ------------------------------------------------------------------
    # QGIS integration
    # ------------------------------------------------------------------
    def initGui(self):
        icon = os.path.join(self.plugin_dir, "icons", "icon.png")
        self.action = QAction(QIcon(icon), "Blue-Green Infrastructure Balance", self.iface.mainWindow())
        self.action.setToolTip("Run BGI Analysis")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Blue-Green Infrastructure Balance", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Blue-Green Infrastructure Balance", self.action)

    # ------------------------------------------------------------------
    # Dialog lifecycle
    # ------------------------------------------------------------------
    def run(self):
        """Open dialog non-destructively (keeps it open after runs)."""
        if self.dlg is None:
            self.dlg = NettoNullBilanzDialog(self.plugin_dir)
            self.dlg.run_requested.connect(self._run_with_params)
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _project_dir(self):
        project = QgsProject.instance()
        project_path = project.fileName()
        if project_path:
            return os.path.dirname(project_path), project_path
        return os.path.expanduser("~"), ""

    def _write_log(self, log_path: str, text: str, overwrite: bool = True) -> None:
        """Write Windows-Notepad friendly log (UTF-8 BOM + CRLF)."""
        mode = "w" if overwrite else "a"
        normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = normalized.replace("\n", "\r\n")
        if not normalized.endswith("\r\n"):
            normalized += "\r\n"

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, mode=mode, encoding="utf-8-sig", newline="") as f:
            f.write(normalized)

    def _make_log_text(self, *, project_title, project_path, output_dir, output_csv_path, factors_csv,
                       base_layer_name, base_field_name, plan_layer_name, plan_field_name,
                       building_green_layer_name, building_green_field_name,
                       validation_text, warnings, status, results_info=None, error=None) -> str:
        lines = []
        lines.append("========================================")
        lines.append("Blue-Green Infrastructure Balance – Log")
        lines.append("========================================")
        lines.append(f"Timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"Status: {status}")
        lines.append(f"Projekt: {project_title}")
        lines.append(f"Project path: {project_path}")
        lines.append(f"Output dir: {output_dir}")
        lines.append("")

        lines.append("----------------------------------------")
        lines.append("Inputs:")
        lines.append("----------------------------------------")
        lines.append(f"  Base layer: {base_layer_name} | Field: {base_field_name}")
        lines.append(f"  Plan layer: {plan_layer_name} | Field: {plan_field_name}")
        lines.append(f"  Building-green layer: {building_green_layer_name} | Field: {building_green_field_name}")
        lines.append(f"  Factors CSV: {factors_csv}")
        lines.append("")

        lines.append("----------------------------------------")
        lines.append("Outputs:")
        lines.append("----------------------------------------")
        lines.append(f"  Output CSV: {output_csv_path}")
        lines.append("")

        lines.append("----------------------------------------")
        lines.append("Warnings:")
        lines.append("----------------------------------------")
        if warnings:
            for w in warnings:
                lines.append(f"  - {w}")
        else:
            lines.append("  (none)")
        lines.append("")

        if results_info:
            lines.append("----------------------------------------")
            lines.append("Results:")
            lines.append("----------------------------------------")
            for k, v in results_info.items():
                lines.append(f"  {k}: {v}")
            lines.append("")

        if error:
            lines.append("----------------------------------------")
            lines.append("Error:")
            lines.append("----------------------------------------")
            lines.append(str(error))
            lines.append("")

        if validation_text:
            lines.append("----------------------------------------")
            lines.append("Validation report:")
            lines.append("----------------------------------------")
            lines.append("")
            for line in str(validation_text).splitlines():
                lines.append("  " + line)
            lines.append("")

        return "\n".join(lines)

    def _validate_matching(self, *, base_layer_name, base_field_name, plan_layer_name, plan_field_name,
                           factors_csv, project_title, building_green_layer_name=None, building_green_field_name=None):
        """
        Strict validation that all unique values in Base / Plan / (optional) Building-green
        exist in the factors CSV column 'Description' (after normalization).
        """
        warnings = []
        lines = []
        lines.append(f"Projekt: {project_title}")
        lines.append(f"Factors CSV: {factors_csv}")
        lines.append("Normalization: trim + casefold + ä->ae ö->oe ü->ue ß->ss + '-'->'_'")
        lines.append("")

        if not os.path.exists(factors_csv):
            raise ValueError(f"Factors CSV not found: {factors_csv}")

        df_f = pd.read_csv(factors_csv, sep=";")
        df_f.columns = [c.strip() for c in df_f.columns]
        if not {"Description", "BFF_2020"}.issubset(df_f.columns):
            raise ValueError("Factor CSV must contain columns: 'Description' and 'BFF_2020'")

        csv_keys_raw = [str(x).strip() for x in df_f["Description"].dropna().tolist()]
        csv_keys_norm = {normalize_key(x): x for x in csv_keys_raw if normalize_key(x)}
        if not csv_keys_norm:
            raise ValueError("Factors CSV contains no usable 'Description' values.")

        def unique_values(layer_name: str, field_name: str):
            layer_list = QgsProject.instance().mapLayersByName(layer_name)
            if not layer_list:
                raise ValueError(f"Layer not found: {layer_name}")
            lyr = layer_list[0]
            field_names = [f.name() for f in lyr.fields()]
            if field_name not in field_names:
                raise ValueError(f"Field '{field_name}' not found in layer '{layer_name}'. Available: {field_names}")

            vals = set()
            for feat in lyr.getFeatures():
                v = feat[field_name]
                if v is None:
                    continue
                s = str(v).strip()
                if s:
                    vals.add(s)
            return vals

        base_vals = unique_values(base_layer_name, base_field_name)
        plan_vals = unique_values(plan_layer_name, plan_field_name)

        bg_vals = set()
        bg_used = bool(building_green_layer_name) and building_green_layer_name != "(None)"
        if bg_used:
            if not building_green_field_name:
                raise ValueError("Building-green layer selected, but building-green field is empty.")
            bg_vals = unique_values(building_green_layer_name, building_green_field_name)

        base_missing = sorted([v for v in base_vals if normalize_key(v) not in csv_keys_norm])
        plan_missing = sorted([v for v in plan_vals if normalize_key(v) not in csv_keys_norm])
        bg_missing = sorted([v for v in bg_vals if normalize_key(v) not in csv_keys_norm]) if bg_used else []

        all_layer_norms = {normalize_key(v) for v in (list(base_vals) + list(plan_vals) + list(bg_vals)) if normalize_key(v)}
        unused = sorted([csv_keys_norm[k] for k in csv_keys_norm.keys() if k not in all_layer_norms])
        if unused:
            warnings.append(f"{len(unused)} CSV keys unused (present in CSV but not in selected layers).")

        lines.append(f"Base layer '{base_layer_name}' / field '{base_field_name}': {len(base_vals)} unique values")
        if base_missing:
            lines.append("❌ Missing in CSV (Base) (first 200):")
            for v in base_missing[:200]:
                lines.append(f"  - {v}")
        else:
            lines.append("✅ All Base values found in CSV.")
        lines.append("")

        lines.append(f"Plan layer '{plan_layer_name}' / field '{plan_field_name}': {len(plan_vals)} unique values")
        if plan_missing:
            lines.append("❌ Missing in CSV (Plan) (first 200):")
            for v in plan_missing[:200]:
                lines.append(f"  - {v}")
        else:
            lines.append("✅ All Plan values found in CSV.")
        lines.append("")

        if bg_used:
            lines.append(f"Building-green layer '{building_green_layer_name}' / field '{building_green_field_name}': {len(bg_vals)} unique values")
            if bg_missing:
                lines.append("❌ Missing in CSV (Building-green) (first 200):")
                for v in bg_missing[:200]:
                    lines.append(f"  - {v}")
            else:
                lines.append("✅ All Building-green values found in CSV.")
            lines.append("")
        else:
            lines.append("Building-green: (not used)")
            lines.append("")

        if unused:
            lines.append("⚠ CSV entries unused (first 200):")
            for v in unused[:200]:
                lines.append(f"  - {v}")
            lines.append("")

        report = "\n".join(lines)

        if base_missing or plan_missing or bg_missing:
            raise ValueError(report)

        return warnings, report

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------
    def _run_with_params(self, params: dict):
        # Start fresh in the dialog log area
        try:
            self.dlg.clear_log()
        except Exception:
            pass

        base_layer_name = params.get("base_layer_name", "")
        base_field_name = params.get("base_field_name", "")
        plan_layer_name = params.get("plan_layer_name", "")
        plan_field_name = params.get("plan_field_name", "")
        factors_csv = params.get("factors_csv", "")
        building_green = params.get("building_green", [])
        building_green_layer_name = params.get("building_green_layer_name")
        building_green_field_name = params.get("building_green_field_name")

        project_title = sanitize_project_name(params.get("project_title") or "") or "UnnamedProject"

        project_dir, project_path = self._project_dir()
        output_dir = os.path.join(project_dir, f"Results_BlueGreenBalance__{project_title}")
        os.makedirs(output_dir, exist_ok=True)

        output_csv_path = os.path.join(output_dir, f"{project_title}__bgig_balance.csv")
        log_path = os.path.join(output_dir, f"{project_title}__bgig_log.txt")

        if not base_layer_name or not base_field_name or not plan_layer_name or not plan_field_name:
            QMessageBox.warning(None, "Missing Input",
                                "Please select *before layer/field* and *after layer/field*.")
            return

        self.dlg.append_log(f"Projekt: {project_title}")
        self.dlg.append_log(f"Output dir: {output_dir}")
        self.dlg.append_log("")

        # Validation
        self.dlg.append_log("Validating inputs…")
        try:
            warnings, validation_text = self._validate_matching(
                base_layer_name=base_layer_name,
                base_field_name=base_field_name,
                plan_layer_name=plan_layer_name,
                plan_field_name=plan_field_name,
                factors_csv=factors_csv,
                project_title=project_title,
                building_green_layer_name=building_green_layer_name,
                building_green_field_name=building_green_field_name,
            )
            self.dlg.append_log("✅ Validation OK")
        except Exception as e:
            self.dlg.append_log("❌ Validation failed")
            self.dlg.append_log(str(e))

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Validation failed")
            msg.setText("❌ Input validation failed. Please fix the issues and run again.")
            msg.setTextFormat(Qt.PlainText)
            msg.setDetailedText(str(e))
            msg.exec_()

            log_text = self._make_log_text(
                project_title=project_title, project_path=project_path, output_dir=output_dir,
                output_csv_path=output_csv_path, factors_csv=factors_csv,
                base_layer_name=base_layer_name, base_field_name=base_field_name,
                plan_layer_name=plan_layer_name, plan_field_name=plan_field_name,
                building_green_layer_name=building_green_layer_name,
                building_green_field_name=building_green_field_name,
                validation_text=str(e), warnings=[], status="validation_failed", error=str(e)
            )
            self._write_log(log_path, log_text, overwrite=True)
            return

        # Run processing
        self.dlg.append_log("Running calculation…")
        try:
            def log_cb(t: str):
                self.dlg.append_log(t)

            results_info, df = script_core.main(
                base_layer_name=base_layer_name,
                base_field_name=base_field_name,
                planning_layer_name=plan_layer_name,
                plan_field_name=plan_field_name,
                factors_csv=factors_csv,
                output_csv_path=output_csv_path,
                building_green=building_green,
                building_green_layer_name=building_green_layer_name,
                building_green_field_name=building_green_field_name,
                log_cb=log_cb,
            )

            try:
                # repo's plotting signature appears to be waterfall(df, project_title, out_dir)
                plotting.waterfall(df, project_title, output_dir)
                plotting.waterfall_short(df, project_title, output_dir)
                plotting.sankey_plot(df, project_title, output_dir)
            except Exception as pe:
                warnings = warnings or []
                warnings.append(f"Plotting failed: {pe}")
                self.dlg.append_log(f"⚠ Plotting failed: {pe}")

            self.dlg.append_log("")
            self.dlg.append_log("✅ Done.")
            self.dlg.append_log(f"Total balance: {results_info.get('Total balance', '')}")
            self.dlg.append_log(f"Results path: {results_info.get('Results path', '')}")

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Success")
            msg.setTextFormat(Qt.PlainText)
            msg.setText("✅ Results exported successfully!")
            msg.setInformativeText("\n".join([f"{k}: {v}" for k, v in results_info.items()]))
            msg.setDetailedText(validation_text)
            msg.exec_()

            total_balance = None
            try:
                total_balance = float(df["BFF_Area"].sum())
            except Exception:
                total_balance = None

            log_text = self._make_log_text(
                project_title=project_title, project_path=project_path, output_dir=output_dir,
                output_csv_path=output_csv_path, factors_csv=factors_csv,
                base_layer_name=base_layer_name, base_field_name=base_field_name,
                plan_layer_name=plan_layer_name, plan_field_name=plan_field_name,
                building_green_layer_name=building_green_layer_name,
                building_green_field_name=building_green_field_name,
                validation_text=validation_text, warnings=warnings, status="success",
                results_info={**results_info, "total_balance_m2": total_balance},
            )
            self._write_log(log_path, log_text, overwrite=True)

        except Exception as e:
            traceback.print_exc()
            self.dlg.append_log("❌ Error during processing")
            self.dlg.append_log(str(e))
            QMessageBox.critical(None, "Error", f"❌ {str(e)}")

            log_text = self._make_log_text(
                project_title=project_title, project_path=project_path, output_dir=output_dir,
                output_csv_path=output_csv_path, factors_csv=factors_csv,
                base_layer_name=base_layer_name, base_field_name=base_field_name,
                plan_layer_name=plan_layer_name, plan_field_name=plan_field_name,
                building_green_layer_name=building_green_layer_name,
                building_green_field_name=building_green_field_name,
                validation_text="", warnings=warnings, status="failed", error=str(e),
            )
            try:
                self._write_log(log_path, log_text, overwrite=True)
            except Exception:
                pass
