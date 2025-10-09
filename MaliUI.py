# -*- coding: utf-8 -*-

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

import maya.OpenMayaUI as omui
import os, json, re

ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'icons'))
SAVE_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), 'material_library.json'))


# ---------------- Dialog: Add/Edit Material (UI-only) ----------------
class MaterialPropDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial=None, title="Add Material"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(360, 240)
        base = {"name": "", "color": "#777777", "icon": "", "assets": []}
        if initial: base.update(initial)
        self.data = base

        main = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_le = QtWidgets.QLineEdit(self.data["name"])
        form.addRow("Name:", self.name_le)

        color_row = QtWidgets.QHBoxLayout()
        self.color_le = QtWidgets.QLineEdit(self.data["color"])
        self.color_btn = QtWidgets.QPushButton("Pick Color")
        color_row.addWidget(self.color_le, 1)
        color_row.addWidget(self.color_btn)
        form.addRow("Color:", color_row)

        icon_row = QtWidgets.QHBoxLayout()
        self.icon_le = QtWidgets.QLineEdit(self.data.get("icon", ""))
        self.icon_btn = QtWidgets.QPushButton("Browse…")
        icon_row.addWidget(self.icon_le, 1)
        icon_row.addWidget(self.icon_btn)
        form.addRow("Icon:", icon_row)

        main.addLayout(form)

        self.preview = QtWidgets.QLabel()
        self.preview.setFixedSize(96, 96)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setStyleSheet("border:1px solid #444; background:#222; color:#ddd;")
        main.addWidget(self.preview, 0, QtCore.Qt.AlignLeft)
        self._update_preview()

        btns = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("OK")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        btns.addStretch(); btns.addWidget(ok_btn); btns.addWidget(cancel_btn)
        main.addLayout(btns)

        self.color_btn.clicked.connect(self.pick_color)
        self.icon_btn.clicked.connect(self.browse_icon)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        self.name_le.textChanged.connect(lambda _: self._update_preview())
        self.color_le.textChanged.connect(lambda _: self._update_preview())
        self.icon_le.textChanged.connect(lambda _: self._update_preview())

    def pick_color(self):
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.color_le.text() or "#777777"), self, "Pick Color")
        if c.isValid():
            self.color_le.setText(c.name()); self._update_preview()

    def browse_icon(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Icon", ICON_PATH, "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.icon_le.setText(path); self._update_preview()

    def _update_preview(self):
        icon_path = self.icon_le.text().strip()
        if icon_path and os.path.isfile(icon_path):
            pm = QtGui.QPixmap(icon_path).scaled(self.preview.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            canvas = QtGui.QPixmap(self.preview.size()); canvas.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(canvas); x=(canvas.width()-pm.width())//2; y=(canvas.height()-pm.height())//2
            p.drawPixmap(x, y, pm); p.end(); self.preview.setPixmap(canvas); return
        col = QtGui.QColor(self.color_le.text() or "#777777")
        pm = QtGui.QPixmap(self.preview.size()); pm.fill(col if col.isValid() else QtGui.QColor("#777777"))
        self.preview.setPixmap(pm)

    def get_data(self):
        return {
            "name": self.name_le.text().strip(),
            "color": self.color_le.text().strip() or "#777777",
            "icon": self.icon_le.text().strip(),
            "assets": list(self.data.get("assets", [])),
        }


# ---------------- Material Card (one item in the scroll area) ----------------
class MaterialCard(QtWidgets.QFrame):
    nameEditedLive = QtCore.Signal(object, str)   # (mat_ref, text)
    nameCommitted  = QtCore.Signal(object, str)   # (mat_ref, text)
    requestEdit    = QtCore.Signal(object)        # (mat_ref)

    def __init__(self, mat_ref: dict, parent=None):
        super().__init__(parent)
        self.mat = mat_ref
        self.mat.setdefault("assets", [])  # ensure exists

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("QFrame{border:1px solid #505050; border-radius:8px;}")
        main = QtWidgets.QVBoxLayout(self); main.setContentsMargins(10,10,10,10); main.setSpacing(8)

        # --- top: preview + name ---
        top = QtWidgets.QHBoxLayout(); main.addLayout(top)
        self.preview = QtWidgets.QLabel()
        self.preview.setFixedSize(180,150)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setStyleSheet("background:#2e2e2e;color:#eee;border:1px solid #555;")
        top.addWidget(self.preview, 0)

        right = QtWidgets.QVBoxLayout(); top.addLayout(right, 1)
        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(QtWidgets.QLabel("Name :"))
        self.name_le = QtWidgets.QLineEdit(self.mat["name"])
        name_row.addWidget(self.name_le, 1)
        right.addLayout(name_row)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_edit = QtWidgets.QPushButton("Edit Material (UI)")
        btn_row.addWidget(self.btn_edit)
        btn_row.addStretch(1)
        right.addLayout(btn_row)

        main.addWidget(self._hline())

        # --- Asset Used: vertical list (scroll up/down) ---
        header = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Asset Used")
        lbl.setStyleSheet("font-weight:600;")
        header.addWidget(lbl)
        header.addStretch()
        self.btn_add_asset = QtWidgets.QToolButton(); self.btn_add_asset.setText("Add…")
        self.btn_del_asset = QtWidgets.QToolButton(); self.btn_del_asset.setText("Remove")
        header.addWidget(self.btn_add_asset); header.addWidget(self.btn_del_asset)
        main.addLayout(header)

        self.asset_list = QtWidgets.QListWidget()
        self.asset_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.asset_list.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.SelectedClicked)
        self.asset_list.setMinimumHeight(120)
        main.addWidget(self.asset_list, 1)

        main.addWidget(self._hline())

        # signals
        self.btn_edit.clicked.connect(lambda: self.requestEdit.emit(self.mat))
        self.name_le.textEdited.connect(lambda t: self.nameEditedLive.emit(self.mat, t))
        self.name_le.editingFinished.connect(lambda: self.nameCommitted.emit(self.mat, self.name_le.text().strip()))
        self.btn_add_asset.clicked.connect(self._add_asset)
        self.btn_del_asset.clicked.connect(self._remove_asset)
        self.asset_list.itemChanged.connect(self._asset_renamed)

        self._refresh_preview()
        self._populate_assets()

    def _hline(self):
        line = QtWidgets.QFrame(); line.setFrameShape(QtWidgets.QFrame.HLine); line.setFrameShadow(QtWidgets.QFrame.Sunken); return line

    def _material_icon(self):
        icon_path = self.mat.get("icon") or ""
        if icon_path and os.path.isfile(icon_path):
            return QtGui.QIcon(icon_path)
        pm = QtGui.QPixmap(96, 96)
        col = QtGui.QColor(self.mat.get("color") or "#777777")
        pm.fill(col if col.isValid() else QtGui.QColor("#777777"))
        return QtGui.QIcon(pm)

    def _refresh_preview(self):
        icon = self._material_icon()
        pm = icon.pixmap(self.preview.size())
        canvas = QtGui.QPixmap(self.preview.size()); canvas.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(canvas); x=(canvas.width()-pm.width())//2; y=(canvas.height()-pm.height())//2
        p.drawPixmap(x, y, pm); p.end()
        self.preview.setPixmap(canvas)

    def _populate_assets(self):
        self.asset_list.blockSignals(True)
        self.asset_list.clear()
        for name in self.mat.get("assets", []):
            it = QtWidgets.QListWidgetItem(name)
            it.setFlags(it.flags() | QtCore.Qt.ItemIsEditable)
            self.asset_list.addItem(it)
        self.asset_list.blockSignals(False)

    def _add_asset(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "Add Asset", "Asset name:")
        if not ok or not text.strip():
            return
        name = text.strip()
        self.mat.setdefault("assets", []).append(name)
        it = QtWidgets.QListWidgetItem(name)
        it.setFlags(it.flags() | QtCore.Qt.ItemIsEditable)
        self.asset_list.addItem(it)
        self.asset_list.scrollToItem(it)

    def _remove_asset(self):
        sel = self.asset_list.selectedItems()
        if not sel: return
        names = [i.text() for i in sel]
        self.mat["assets"] = [n for n in self.mat.get("assets", []) if n not in names]
        for it in sel:
            row = self.asset_list.row(it)
            self.asset_list.takeItem(row)

    def _asset_renamed(self, item: QtWidgets.QListWidgetItem):
        # sync rename back to data
        names = []
        for i in range(self.asset_list.count()):
            names.append(self.asset_list.item(i).text())
        self.mat["assets"] = names

    # expose helpers for outer dialog
    def set_name(self, new_name: str):
        self.name_le.blockSignals(True); self.name_le.setText(new_name); self.name_le.blockSignals(False)

    def refresh(self):
        self._refresh_preview()
        self._populate_assets()


# ---------------- Main Dialog (scrollable cards) ----------------
class MaterialLibraryDialog(QtWidgets.QDialog):
    KIND_ROLE   = QtCore.Qt.UserRole
    KIND_ROOT   = "root"
    KIND_FOLDER = "folder"
    KIND_MAT    = "material"
    MAT_ID_ROLE = QtCore.Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 Material Library (UI Only)")
        self.resize(1120, 660)

        self.lib_data = {}
        self.folder_counter   = 1
        self.material_counter = 1

        self.current_folder = None
        self._tree_index = {}   # id(mat) -> QTreeWidgetItem
        self._card_index = {}   # id(mat) -> MaterialCard

        # ----- left: tree & controls -----
        left = QtWidgets.QWidget(); left_l = QtWidgets.QVBoxLayout(left)
        self.tree = QtWidgets.QTreeWidget(); self.tree.setHeaderHidden(True); self.tree.setIndentation(16)
        left_l.addWidget(self.tree)

        lb = QtWidgets.QHBoxLayout()
        self.btn_create_folder   = QtWidgets.QPushButton("Create Folder")
        self.btn_create_material = QtWidgets.QPushButton("Create Material")
        self.btn_add_material    = QtWidgets.QPushButton("Add Material…")
        self.btn_delete          = QtWidgets.QPushButton("Delete")
        lb.addWidget(self.btn_create_folder); lb.addWidget(self.btn_create_material); lb.addWidget(self.btn_add_material); lb.addWidget(self.btn_delete)
        left_l.addLayout(lb)

        # ----- right: scrollable material cards -----
        right = QtWidgets.QWidget(); right_l = QtWidgets.QVBoxLayout(right)
        right_l.addWidget(QtWidgets.QLabel("Materials Detail"))
        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True)
        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container); self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.cards_container)
        right_l.addWidget(self.scroll, 1)

        # bottom-right: Save
        right_l.addWidget(self._hline())
        btm = QtWidgets.QHBoxLayout() 
        self.btn_save = QtWidgets.QPushButton("Save")
        btm.addStretch(); btm.addWidget(self.btn_save)
        right_l.addLayout(btm)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(left); self.splitter.addWidget(right)
        self.splitter.setStretchFactor(1, 2)

        main = QtWidgets.QVBoxLayout(self); main.addWidget(self.splitter)

        # signals
        self.btn_create_folder.clicked.connect(self.on_create_folder)
        self.btn_create_material.clicked.connect(self.on_create_material)
        self.btn_add_material.clicked.connect(self.on_add_material)
        self.btn_delete.clicked.connect(self.on_delete)
        self.tree.itemClicked.connect(self.on_tree_clicked)
        self.tree.itemDoubleClicked.connect(self.on_tree_rename)
        self.btn_save.clicked.connect(self.on_save)

        # load & build
        self._try_load()
        if not os.path.isfile(SAVE_JSON):
            self._refresh_tree()

    # ---------- helpers ----------
    def _hline(self):
        line = QtWidgets.QFrame(); line.setFrameShape(QtWidgets.QFrame.HLine); line.setFrameShadow(QtWidgets.QFrame.Sunken); return line

    def _material_icon(self, m: dict):
        icon_path = m.get("icon") or ""
        if icon_path and os.path.isfile(icon_path): return QtGui.QIcon(icon_path)
        pm = QtGui.QPixmap(48, 48); col = QtGui.QColor(m.get("color") or "#777777")
        pm.fill(col if col.isValid() else QtGui.QColor("#777777")); return QtGui.QIcon(pm)

    def _unique_name(self, mats_list, desired, exclude=None):
        names = {id(x): x["name"] for x in mats_list}
        existing = set(names.values()) - ({exclude["name"]} if exclude else set())
        if desired not in existing: return desired
        i = 2
        while True:
            cand = f"{desired} ({i})"
            if cand not in existing: return cand
            i += 1

    # ---------- tree build ----------
    def _refresh_tree(self):
        self._tree_index.clear()
        self.tree.clear()
        root = QtWidgets.QTreeWidgetItem(["All Material"])
        root.setData(0, self.KIND_ROLE, self.KIND_ROOT)
        root.setFlags(root.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.tree.addTopLevelItem(root)

        for folder, mats in self.lib_data.items():
            f_item = QtWidgets.QTreeWidgetItem([folder])
            f_item.setData(0, self.KIND_ROLE, self.KIND_FOLDER)
            root.addChild(f_item)
            for m in mats:
                c_item = QtWidgets.QTreeWidgetItem([m["name"]])
                c_item.setData(0, self.KIND_ROLE, self.KIND_MAT)
                c_item.setData(0, self.MAT_ID_ROLE, id(m))
                c_item.setIcon(0, self._material_icon(m))
                f_item.addChild(c_item)
                self._tree_index[id(m)] = c_item

        self.tree.expandAll()

    def _rebuild_cards_for_folder(self, folder_name):
        self.current_folder = folder_name
        while self.cards_layout.count():
            it = self.cards_layout.takeAt(0)
            w = it.widget()
            if w: w.deleteLater()
        self._card_index.clear()

        for m in self.lib_data.get(folder_name, []):
            card = MaterialCard(m, self.cards_container)
            card.nameEditedLive.connect(self._card_name_live)
            card.nameCommitted.connect(self._card_name_commit)
            card.requestEdit.connect(self._card_edit_dialog)
            self.cards_layout.addWidget(card)
            self._card_index[id(m)] = card

        self.cards_layout.addStretch()

    # ---------- card callbacks ----------
    def _card_name_live(self, mat_ref, text):
        mat_ref["name"] = text
        item = self._tree_index.get(id(mat_ref))
        if item: item.setText(0, text)

    def _card_name_commit(self, mat_ref, text):
        mats = self.lib_data.get(self.current_folder, [])
        new = self._unique_name(mats, text or mat_ref["name"] or "Material", exclude=mat_ref)
        if new != text:
            card = self._card_index.get(id(mat_ref))
            if card: card.set_name(new)
        mat_ref["name"] = new
        item = self._tree_index.get(id(mat_ref))
        if item: item.setText(0, new)

    def _card_edit_dialog(self, mat_ref):
        dlg = MaterialPropDialog(self, initial=mat_ref, title="Edit Material")
        if dlg.exec_() != QtWidgets.QDialog.Accepted: return
        data = dlg.get_data()
        mats = self.lib_data.get(self.current_folder, [])
        data["name"] = self._unique_name(mats, data["name"] or "Material", exclude=mat_ref)
        mat_ref.update(data)
        item = self._tree_index.get(id(mat_ref))
        if item:
            item.setText(0, mat_ref["name"])
            item.setIcon(0, self._material_icon(mat_ref))
        card = self._card_index.get(id(mat_ref))
        if card:
            card.set_name(mat_ref["name"])
            card.refresh()

    # ---------- actions ----------
    def on_create_folder(self):
        name = f"Folder {self.folder_counter}"
        while name in self.lib_data:
            self.folder_counter += 1; name = f"Folder {self.folder_counter}"
        self.lib_data[name] = []; self.folder_counter += 1
        self._refresh_tree()

    def on_create_material(self):
        item = self.tree.currentItem()
        if not item: QtWidgets.QMessageBox.warning(self, "Create Material", "Select a folder first."); return
        kind = item.data(0, self.KIND_ROLE)
        folder = item.text(0) if kind == self.KIND_FOLDER else (item.parent().text(0) if kind == self.KIND_MAT else None)
        if not folder: QtWidgets.QMessageBox.warning(self, "Create Material", "Select a folder first."); return
        base = f"Material {self.material_counter}"
        name = self._unique_name(self.lib_data.setdefault(folder, []), base)
        mat = {"name": name, "color": "#777777", "icon": "", "assets": []}
        self.lib_data[folder].append(mat); self.material_counter += 1
        self._refresh_tree()
        self._rebuild_cards_for_folder(folder)
        card = self._card_index.get(id(mat))
        if card: self.scroll.ensureWidgetVisible(card)

    def on_add_material(self):
        item = self.tree.currentItem()
        if not item: QtWidgets.QMessageBox.warning(self, "Add Material", "Select a folder first."); return
        kind = item.data(0, self.KIND_ROLE)
        folder = item.text(0) if kind == self.KIND_FOLDER else (item.parent().text(0) if kind == self.KIND_MAT else None)
        if not folder: QtWidgets.QMessageBox.warning(self, "Add Material", "Select a folder first."); return

        dlg = MaterialPropDialog(self, title="Add Material")
        if dlg.exec_() != QtWidgets.QDialog.Accepted: return
        data = dlg.get_data()
        data["name"] = self._unique_name(self.lib_data.setdefault(folder, []), data["name"] or "Material")
        data.setdefault("assets", [])
        self.lib_data[folder].append(data)
        self._refresh_tree()
        self._rebuild_cards_for_folder(folder)
        card = self._card_index.get(id(data))
        if card: self.scroll.ensureWidgetVisible(card)

    def on_tree_clicked(self, item, _col):
        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_FOLDER:
            self._rebuild_cards_for_folder(item.text(0))
        elif kind == self.KIND_MAT:
            folder = item.parent().text(0)
            self._rebuild_cards_for_folder(folder)
            mat_id = item.data(0, self.MAT_ID_ROLE)
            card = self._card_index.get(mat_id)
            if card: self.scroll.ensureWidgetVisible(card)

    def on_tree_rename(self, item, _col):
        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_ROOT: return
        old = item.text(0)
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename", "New name:", text=old)
        if not ok or not new or new == old: return

        if kind == self.KIND_FOLDER:
            if new in self.lib_data:
                QtWidgets.QMessageBox.warning(self, "Rename", "Folder already exists."); return
            self.lib_data[new] = self.lib_data.pop(old)
            self._refresh_tree(); self._rebuild_cards_for_folder(new)
        else:
            folder = item.parent().text(0)
            mats = self.lib_data.get(folder, [])
            mat_id = item.data(0, self.MAT_ID_ROLE)
            ref = next((m for m in mats if id(m) == mat_id), None)
            if not ref: return
            new = self._unique_name(mats, new, exclude=ref)
            ref["name"] = new
            item.setText(0, new)
            card = self._card_index.get(mat_id)
            if card: card.set_name(new)

    def on_delete(self):
        item = self.tree.currentItem()
        if not item: return
        kind = item.data(0, self.KIND_ROLE)

        if kind == self.KIND_FOLDER:
            name = item.text(0)
            self.lib_data.pop(name, None)
            item.parent().removeChild(item)
            self._rebuild_cards_for_folder("")  # clear right
        elif kind == self.KIND_MAT:
            folder = item.parent().text(0)
            mat_id = item.data(0, self.MAT_ID_ROLE)
            mats = self.lib_data.get(folder, [])
            self.lib_data[folder] = [m for m in mats if id(m) != mat_id]
            item.parent().removeChild(item)
            self._rebuild_cards_for_folder(folder)
        else:
            QtWidgets.QMessageBox.information(self, "Delete", "Root cannot be deleted.")

    def on_save(self):
        try:
            with open(SAVE_JSON, "w", encoding="utf-8") as f:
                json.dump(self.lib_data, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(self, "Save", "Material Library saved.")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(e))

    # ---------- persistence ----------
    def _try_load(self):
        if not os.path.isfile(SAVE_JSON): return
        try:
            with open(SAVE_JSON, "r", encoding="utf-8") as f:
                self.lib_data = json.load(f)
            # migrate old records (no 'assets')
            for mats in self.lib_data.values():
                for m in mats:
                    m.setdefault("assets", [])
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Load failed", str(e))
        # counters
        max_f = 0; max_m = 0
        for name in self.lib_data.keys():
            mf = re.match(r'^Folder\s+(\d+)$', name)
            if mf: max_f = max(max_f, int(mf.group(1)))
        for mats in self.lib_data.values():
            for m in mats:
                mm = re.match(r'^Material\s+(\d+)$', m.get("name",""))
                if mm: max_m = max(max_m, int(mm.group(1)))
        self.folder_counter   = max(1, max_f+1)
        self.material_counter = max(1, max_m+1)
        self._refresh_tree()


# ---------- launcher ----------
def run():
    global ui
    try:
        ui.close()
    except Exception:
        pass
    ptr = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    ui = MaterialLibraryDialog(parent=ptr)
    ui.show()
