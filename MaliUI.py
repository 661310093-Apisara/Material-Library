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

        self.data = initial.copy() if initial else {"name": "", "color": "#777777", "icon": ""}

        main = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.name_le = QtWidgets.QLineEdit(self.data["name"])
        form.addRow("Name:", self.name_le)

        # color picker
        color_row = QtWidgets.QHBoxLayout()
        self.color_le = QtWidgets.QLineEdit(self.data["color"])
        self.color_btn = QtWidgets.QPushButton("Pick Color")
        color_row.addWidget(self.color_le, 1)
        color_row.addWidget(self.color_btn)
        form.addRow("Color:", color_row)

        # icon picker
        icon_row = QtWidgets.QHBoxLayout()
        self.icon_le = QtWidgets.QLineEdit(self.data.get("icon", ""))
        self.icon_btn = QtWidgets.QPushButton("Browse…")
        icon_row.addWidget(self.icon_le, 1)
        icon_row.addWidget(self.icon_btn)
        form.addRow("Icon:", icon_row)

        main.addLayout(form)

        # preview
        self.preview = QtWidgets.QLabel()
        self.preview.setFixedSize(96, 96)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setStyleSheet("border:1px solid #444; background:#222; color:#ddd;")
        main.addWidget(self.preview, 0, QtCore.Qt.AlignLeft)
        self._update_preview()

        # buttons
        btns = QtWidgets.QHBoxLayout()
        self.ok_btn = QtWidgets.QPushButton("OK")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        btns.addStretch()
        btns.addWidget(self.ok_btn)
        btns.addWidget(self.cancel_btn)
        main.addLayout(btns)

        # signals
        self.color_btn.clicked.connect(self.pick_color)
        self.icon_btn.clicked.connect(self.browse_icon)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.name_le.textChanged.connect(lambda _: self._update_preview())
        self.color_le.textChanged.connect(lambda _: self._update_preview())
        self.icon_le.textChanged.connect(lambda _: self._update_preview())

    def pick_color(self):
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.color_le.text() or "#777777"), self, "Pick Color")
        if c.isValid():
            self.color_le.setText(c.name())
            self._update_preview()

    def browse_icon(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Icon", ICON_PATH, "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.icon_le.setText(path)
            self._update_preview()

    def _update_preview(self):
        icon_path = self.icon_le.text().strip()
        if icon_path and os.path.isfile(icon_path):
            pm = QtGui.QPixmap(icon_path).scaled(self.preview.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            canvas = QtGui.QPixmap(self.preview.size())
            canvas.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(canvas)
            x = (canvas.width() - pm.width()) // 2
            y = (canvas.height() - pm.height()) // 2
            painter.drawPixmap(x, y, pm)
            painter.end()
            self.preview.setPixmap(canvas)
            return

        col = QtGui.QColor(self.color_le.text() or "#777777")
        pm = QtGui.QPixmap(self.preview.size())
        pm.fill(col if col.isValid() else QtGui.QColor("#777777"))
        self.preview.setPixmap(pm)

    def get_data(self):
        return {
            "name": self.name_le.text().strip(),
            "color": self.color_le.text().strip() or "#777777",
            "icon": self.icon_le.text().strip(),
        }


# ---------------- Main Dialog: Material Library (UI-only) ----------------
class MaterialLibraryDialog(QtWidgets.QDialog):
    # item kinds
    KIND_ROLE   = QtCore.Qt.UserRole
    KIND_ROOT   = "root"
    KIND_FOLDER = "folder"
    KIND_MAT    = "material"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("🎨 Material Library (UI Only)")
        self.resize(1080, 640)

        # {'Folder 1': [ {'name': 'Mat A', 'color':'#aabbcc', 'icon':'...'}, ... ], ...}
        self.lib_data = {}
        # running numbers (never decrease)
        self.folder_counter   = 1
        self.material_counter = 1

        # pointers/state for live rename
        self._current_folder_name = None
        self._current_mat_ref     = None
        self._last_valid_name     = ""

        # layout + splitter
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)

        # ------------- left: tree -------------
        self.left_widget = QtWidgets.QWidget()
        self.left_layout = QtWidgets.QVBoxLayout(self.left_widget)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.left_layout.addWidget(self.tree)

        left_btns = QtWidgets.QHBoxLayout()
        self.btn_create_folder   = QtWidgets.QPushButton("Create Folder")
        self.btn_create_material = QtWidgets.QPushButton("Create Material")
        self.btn_add_material    = QtWidgets.QPushButton("Add Material…")
        left_btns.addWidget(self.btn_create_folder)
        left_btns.addWidget(self.btn_create_material)
        left_btns.addWidget(self.btn_add_material)
        self.left_layout.addLayout(left_btns)
        self.splitter.addWidget(self.left_widget)

        # ------------- right: detail + scroll list -------------
        self.right_widget = QtWidgets.QWidget()
        self.right_layout = QtWidgets.QVBoxLayout(self.right_widget)

        # Name / Preview / Buttons (detail of selected material)
        form = QtWidgets.QFormLayout()
        self.mat_name_le = QtWidgets.QLineEdit()
        form.addRow("Name :", self.mat_name_le)
        self.right_layout.addLayout(form)

        upper = QtWidgets.QHBoxLayout()
        self.preview = QtWidgets.QLabel("Material\nPreview")
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setFixedSize(220, 180)
        self.preview.setStyleSheet("background:#2e2e2e;color:#eee;border:1px solid #555;")
        upper.addWidget(self.preview)

        btns = QtWidgets.QVBoxLayout()
        self.btn_edit = QtWidgets.QPushButton("Edit Material (UI)")
        self.btn_select_obj = QtWidgets.QPushButton("Select Obj from this Material")
        self.btn_link = QtWidgets.QPushButton("Link Material")
        # Scene-related disabled in UI-only mode
        self.btn_select_obj.setEnabled(False)
        self.btn_link.setEnabled(False)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_select_obj)
        btns.addWidget(self.btn_link)
        btns.addStretch()
        upper.addLayout(btns)
        self.right_layout.addLayout(upper)

        # ---- NEW: Scrollable list of materials in selected folder ----
        self.right_layout.addWidget(self._hline())
        list_title = QtWidgets.QLabel("Materials in Folder")
        list_title.setStyleSheet("font-weight:600;")
        self.right_layout.addWidget(list_title)

        self.matlist = QtWidgets.QListWidget()
        self.matlist.setIconSize(QtCore.QSize(64, 64))
        self.matlist.setSpacing(6)
        self.matlist.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.matlist.setUniformItemSizes(True)  # smooth scroll
        # ใช้ขยายพื้นที่เองเพื่อให้เกิดสกรอลล์อัตโนมัติเมื่อรายการยาว
        self.right_layout.addWidget(self.matlist, 1)

        # bottom
        self.right_layout.addWidget(self._hline())
        bottom = QtWidgets.QHBoxLayout()
        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_save   = QtWidgets.QPushButton("Save")
        bottom.addStretch()
        bottom.addWidget(self.btn_delete)
        bottom.addWidget(self.btn_save)
        self.right_layout.addLayout(bottom)

        self.splitter.addWidget(self.right_widget)
        self.splitter.setStretchFactor(1, 2)

        # signals
        self.btn_create_folder.clicked.connect(self.on_create_folder)
        self.btn_create_material.clicked.connect(self.on_create_material)
        self.btn_add_material.clicked.connect(self.on_add_material)
        self.tree.itemClicked.connect(self.on_tree_clicked)
        self.tree.itemDoubleClicked.connect(self.on_tree_rename)
        self.btn_edit.clicked.connect(self.on_edit_material_ui)
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_save.clicked.connect(self.on_save)

        # LIVE RENAME (Name field)
        self.mat_name_le.textEdited.connect(self.on_name_edited_live)
        self.mat_name_le.editingFinished.connect(self.on_name_commit)

        # List interactions
        self.matlist.currentItemChanged.connect(self.on_matlist_item_changed)
        self.matlist.itemDoubleClicked.connect(self.on_matlist_item_double_clicked)

        # load existing
        self._try_load()
        if not os.path.isfile(SAVE_JSON):
            self._refresh_tree()
            self.folder_counter   = 1
            self.material_counter = 1

    # ---------- helpers ----------
    def _hline(self):
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line

    def _item_kind(self, item):
        return item.data(0, self.KIND_ROLE) if item else None

    def _material_icon(self, mat_dict):
        icon_path = mat_dict.get("icon") or ""
        if icon_path and os.path.isfile(icon_path):
            return QtGui.QIcon(icon_path)
        pm = QtGui.QPixmap(48, 48)
        col = QtGui.QColor(mat_dict.get("color") or "#777777")
        pm.fill(col if col.isValid() else QtGui.QColor("#777777"))
        return QtGui.QIcon(pm)

    def _refresh_tree(self):
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
                c_item.setIcon(0, self._material_icon(m))
                f_item.addChild(c_item)

        self.tree.expandAll()

    def _populate_matlist(self, folder_name):
        """เติมรายการวัสดุของโฟลเดอร์ลง QListWidget (scroll ได้)"""
        self.matlist.blockSignals(True)
        self.matlist.clear()
        for m in self.lib_data.get(folder_name, []):
            it = QtWidgets.QListWidgetItem(self._material_icon(m), m["name"])
            it.setData(self.KIND_ROLE, m)  # เก็บ ref dict
            self.matlist.addItem(it)
        self.matlist.blockSignals(False)

    def _select_tree_item_by_name(self, folder_name, mat_name):
        """เลือกไอเท็มใน Tree ให้ตรงกับโฟลเดอร์/วัสดุ"""
        root = self.tree.topLevelItem(0)
        if not root:
            return
        # หาโฟลเดอร์
        folder_item = None
        for i in range(root.childCount()):
            c = root.child(i)
            if c.text(0) == folder_name:
                folder_item = c
                break
        if not folder_item:
            return
        # หากชื่อวัสดุ -> เลือกวัสดุ, ถ้าไม่มีก็เลือกโฟลเดอร์
        if mat_name:
            for j in range(folder_item.childCount()):
                cc = folder_item.child(j)
                if cc.text(0) == mat_name:
                    self.tree.setCurrentItem(cc)
                    return
        self.tree.setCurrentItem(folder_item)

    def _set_material_preview(self, mat_dict):
        self.mat_name_le.setText(mat_dict["name"])
        icon = self._material_icon(mat_dict)
        pm = icon.pixmap(self.preview.size())
        if pm.isNull():
            self.preview.setText(f"Material\n{mat_dict['name']}")
            self.preview.setPixmap(QtGui.QPixmap())
        else:
            canvas = QtGui.QPixmap(self.preview.size())
            canvas.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(canvas)
            x = (canvas.width() - pm.width()) // 2
            y = (canvas.height() - pm.height()) // 2
            p.drawPixmap(x, y, pm)
            p.end()
            self.preview.setPixmap(canvas)

    def _unique_name(self, mats_list, desired):
        names = {m["name"] for m in mats_list}
        if desired not in names:
            return desired
        i = 2
        while True:
            cand = f"{desired} ({i})"
            if cand not in names:
                return cand
            i += 1

    def _get_mat_ref(self, folder_name, mat_name):
        mats = self.lib_data.get(folder_name, [])
        for m in mats:
            if m["name"] == mat_name:
                return m
        return None

    def _recalc_folder_counter(self):
        max_n = 0
        for name in self.lib_data.keys():
            m = re.match(r'^Folder\s+(\d+)$', name)
            if m:
                max_n = max(max_n, int(m.group(1)))
        self.folder_counter = max(max_n + 1, self.folder_counter, 1)

    def _recalc_material_counter(self):
        max_n = 0
        for mats in self.lib_data.values():
            for m in mats:
                mm = re.match(r'^Material\s+(\d+)$', m["name"])
                if mm:
                    max_n = max(max_n, int(mm.group(1)))
        self.material_counter = max(max_n + 1, self.material_counter, 1)

    def _bump_counter_from_name(self, name):
        mf = re.match(r'^Folder\s+(\d+)$', name)
        if mf:
            n = int(mf.group(1)) + 1
            if n > self.folder_counter:
                self.folder_counter = n
        mm = re.match(r'^Material\s+(\d+)$', name)
        if mm:
            n = int(mm.group(1)) + 1
            if n > self.material_counter:
                self.material_counter = n

    # ---------- actions ----------
    def on_create_folder(self):
        name = f"Folder {self.folder_counter}"
        while name in self.lib_data:
            self.folder_counter += 1
            name = f"Folder {self.folder_counter}"
        self.lib_data[name] = []
        self.folder_counter += 1
        self._refresh_tree()

    def on_create_material(self):
        item = self.tree.currentItem()
        kind = self._item_kind(item)
        if kind == self.KIND_MAT:
            folder_item = item.parent()
        elif kind == self.KIND_FOLDER:
            folder_item = item
        else:
            QtWidgets.QMessageBox.warning(self, "Create Material", "Select a folder first.")
            return

        folder = folder_item.text(0)

        base_name = f"Material {self.material_counter}"
        name = self._unique_name(self.lib_data.setdefault(folder, []), base_name)
        mat = {"name": name, "color": "#777777", "icon": ""}
        self.lib_data[folder].append(mat)
        self.material_counter += 1

        self._refresh_tree()
        # อัปเดตลิสต์ฝั่งขวาถ้าเลือกโฟลเดอร์นี้อยู่
        self._populate_matlist(folder)
        # เลือกวัสดุที่สร้างใหม่ทั้งในลิสต์และใน tree
        matches = self.matlist.findItems(name, QtCore.Qt.MatchExactly)
        if matches:
            self.matlist.setCurrentItem(matches[0])
        self._select_tree_item_by_name(folder, name)

        # ตั้ง state live-rename
        self._current_folder_name = folder
        self._current_mat_ref = mat
        self._last_valid_name = mat["name"]
        self._set_material_preview(mat)

    def on_add_material(self):
        item = self.tree.currentItem()
        kind = self._item_kind(item)

        if kind == self.KIND_MAT:
            folder_item = item.parent()
        elif kind == self.KIND_FOLDER:
            folder_item = item
        else:
            QtWidgets.QMessageBox.warning(self, "Add Material", "Select a folder first.")
            return

        folder = folder_item.text(0)

        dlg = MaterialPropDialog(self, title="Add Material")
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            QtWidgets.QMessageBox.warning(self, "Add Material", "Please enter a name.")
            return

        data["name"] = self._unique_name(self.lib_data.setdefault(folder, []), data["name"])
        self.lib_data[folder].append(data)
        self._bump_counter_from_name(data["name"])

        self._refresh_tree()
        self._populate_matlist(folder)
        matches = self.matlist.findItems(data["name"], QtCore.Qt.MatchExactly)
        if matches:
            self.matlist.setCurrentItem(matches[0])
        self._select_tree_item_by_name(folder, data["name"])

        self._current_folder_name = folder
        self._current_mat_ref = data
        self._last_valid_name = data["name"]
        self._set_material_preview(data)

    def on_tree_clicked(self, item, _col):
        kind = self._item_kind(item)
        if kind == self.KIND_FOLDER:
            folder = item.text(0)
            self._populate_matlist(folder)
            # reset detail
            self._current_folder_name = folder
            self._current_mat_ref = None
            self._last_valid_name = ""
            self.mat_name_le.clear()
            self.preview.setText("Material\nPreview")
            self.preview.setPixmap(QtGui.QPixmap())
            return

        if kind == self.KIND_MAT:
            folder = item.parent().text(0)
            self._populate_matlist(folder)  # ให้ลิสต์ฝั่งขวาตามโฟลเดอร์นี้
            meta = self._get_mat_ref(folder, item.text(0))
            self._current_folder_name = folder
            self._current_mat_ref = meta
            self._last_valid_name = meta["name"] if meta else ""
            # sync เลือกในลิสต์
            matches = self.matlist.findItems(item.text(0), QtCore.Qt.MatchExactly)
            if matches:
                self.matlist.blockSignals(True)
                self.matlist.setCurrentItem(matches[0])
                self.matlist.blockSignals(False)
            if meta:
                self._set_material_preview(meta)
            return

        # root
        self._populate_matlist("")  # ว่าง
        self._current_folder_name = None
        self._current_mat_ref = None
        self._last_valid_name = ""
        self.mat_name_le.clear()
        self.preview.setText("Material\nPreview")
        self.preview.setPixmap(QtGui.QPixmap())

    def on_tree_rename(self, item, _col):
        kind = self._item_kind(item)
        if kind == self.KIND_ROOT:
            return

        old = item.text(0)
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename", "New name:", text=old)
        if not ok or not new or new == old:
            return

        if kind == self.KIND_MAT:
            folder = item.parent().text(0)
            mats = self.lib_data.get(folder, [])
            new = self._unique_name(mats, new)
            ref = self._get_mat_ref(folder, old)
            if ref:
                ref["name"] = new
                self._bump_counter_from_name(new)
            self._refresh_tree()
            # อัปเดตลิสต์และซิงก์ selection
            self._populate_matlist(folder)
            matches = self.matlist.findItems(new, QtCore.Qt.MatchExactly)
            if matches:
                self.matlist.setCurrentItem(matches[0])
            self._select_tree_item_by_name(folder, new)
            # อัปเดตรายละเอียด
            if ref:
                self._current_folder_name = folder
                self._current_mat_ref = ref
                self._last_valid_name = ref["name"]
                self._set_material_preview(ref)

        elif kind == self.KIND_FOLDER:
            if new in self.lib_data:
                QtWidgets.QMessageBox.warning(self, "Rename", "Folder already exists.")
                return
            self.lib_data[new] = self.lib_data.pop(old)
            self._bump_counter_from_name(new)
            self._refresh_tree()
            self._populate_matlist(new)
            self._select_tree_item_by_name(new, None)
            # reset detail
            self._current_folder_name = new
            self._current_mat_ref = None
            self._last_valid_name = ""
            self.mat_name_le.clear()
            self.preview.setText("Material\nPreview")
            self.preview.setPixmap(QtGui.QPixmap())

    def on_edit_material_ui(self):
        # เปิดกล่องแก้ไขจาก selection ปัจจุบัน (จากลิสต์หรือ tree ก็ได้)
        item = self.tree.currentItem()
        if self._item_kind(item) != self.KIND_MAT:
            QtWidgets.QMessageBox.information(self, "Edit Material", "Select a material first.")
            return
        folder = item.parent().text(0)
        ref = self._get_mat_ref(folder, item.text(0))
        if not ref:
            return

        dlg = MaterialPropDialog(self, initial=ref, title="Edit Material")
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            QtWidgets.QMessageBox.warning(self, "Edit Material", "Please enter a name.")
            return

        data["name"] = self._unique_name([m for m in self.lib_data[folder] if m is not ref], data["name"])
        ref.update(data)
        self._bump_counter_from_name(data["name"])

        self._refresh_tree()
        self._populate_matlist(folder)
        # sync select
        matches = self.matlist.findItems(data["name"], QtCore.Qt.MatchExactly)
        if matches:
            self.matlist.setCurrentItem(matches[0])
        self._select_tree_item_by_name(folder, data["name"])

        self._current_folder_name = folder
        self._current_mat_ref = ref
        self._last_valid_name = ref["name"]
        self._set_material_preview(ref)

    # ====== LIVE RENAME from Name field ======
    def on_name_edited_live(self, text):
        if not self._current_mat_ref:
            return
        # update memory
        self._current_mat_ref["name"] = text
        # update tree current item
        titem = self.tree.currentItem()
        if titem and self._item_kind(titem) == self.KIND_MAT:
            titem.setText(0, text)
        # update list current item
        litem = self.matlist.currentItem()
        if litem:
            litem.setText(text)
        # (ไม่อัปเดต preview เพื่อไม่ให้ caret เด้ง)

    def on_name_commit(self):
        if not self._current_mat_ref:
            return
        text = self.mat_name_le.text().strip()
        if not text:
            text = self._last_valid_name
            self.mat_name_le.setText(text)

        mats = self.lib_data.get(self._current_folder_name, [])
        other_names = {m["name"] for m in mats if m is not self._current_mat_ref}
        if text in other_names:
            text = self._unique_name([m for m in mats if m is not self._current_mat_ref], text)

        self._current_mat_ref["name"] = text
        self._last_valid_name = text
        self._bump_counter_from_name(text)

        # sync UI: tree + list + preview
        titem = self.tree.currentItem()
        if titem and self._item_kind(titem) == self.KIND_MAT:
            titem.setText(0, text)
        litem = self.matlist.currentItem()
        if litem:
            litem.setText(text)

        icon = self._material_icon(self._current_mat_ref)
        pm = icon.pixmap(self.preview.size())
        if pm.isNull():
            self.preview.setText(f"Material\n{text}")
            self.preview.setPixmap(QtGui.QPixmap())
        else:
            canvas = QtGui.QPixmap(self.preview.size())
            canvas.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(canvas)
            x = (canvas.width() - pm.width()) // 2
            y = (canvas.height() - pm.height()) // 2
            p.drawPixmap(x, y, pm)
            p.end()
            self.preview.setPixmap(canvas)

    # ====== List interactions ======
    def on_matlist_item_changed(self, cur, prev):
        """เลือกวัสดุจากลิสต์ -> ซิงก์ไป Tree + แสดงรายละเอียด"""
        if not cur:
            return
        # หาโฟลเดอร์ปัจจุบันจาก selection ฝั่งซ้าย
        titem = self.tree.currentItem()
        folder = None
        if titem:
            kind = self._item_kind(titem)
            folder = titem.text(0) if kind == self.KIND_FOLDER else (titem.parent().text(0) if kind == self.KIND_MAT else None)
        if not folder:
            return
        name = cur.text()
        self._select_tree_item_by_name(folder, name)
        ref = self._get_mat_ref(folder, name)
        self._current_folder_name = folder
        self._current_mat_ref = ref
        self._last_valid_name = ref["name"] if ref else ""
        if ref:
            self._set_material_preview(ref)

    def on_matlist_item_double_clicked(self, item):
        """ดับเบิลคลิกที่รายการ -> เปิด Edit dialog"""
        self.on_edit_material_ui()

    def on_delete(self):
        item = self.tree.currentItem()
        if not item:
            return

        kind = self._item_kind(item)

        if kind == self.KIND_MAT:
            folder = item.parent().text(0)
            mats = self.lib_data.get(folder, [])
            self.lib_data[folder] = [m for m in mats if m["name"] != item.text(0)]
            item.parent().removeChild(item)
            # อัปเดตลิสต์ฝั่งขวา
            self._populate_matlist(folder)

        elif kind == self.KIND_FOLDER:
            name = item.text(0)
            self.lib_data.pop(name, None)
            item.parent().removeChild(item)  # parent is root
            # ถ้าลบโฟลเดอร์ที่แสดงอยู่ -> เคลียร์ลิสต์
            self.matlist.clear()

        elif kind == self.KIND_ROOT:
            QtWidgets.QMessageBox.information(self, "Delete", "Root cannot be deleted.")
            return

        # reset live-rename state
        self._current_folder_name = None
        self._current_mat_ref = None
        self._last_valid_name = ""
        self.mat_name_le.clear()
        self.preview.setText("Material\nPreview")
        self.preview.setPixmap(QtGui.QPixmap())

    def on_save(self):
        try:
            with open(SAVE_JSON, "w", encoding="utf-8") as f:
                json.dump(self.lib_data, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(self, "Save", "Material Library saved.")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(e))

    def _try_load(self):
        if not os.path.isfile(SAVE_JSON):
            return
        try:
            with open(SAVE_JSON, "r", encoding="utf-8") as f:
                self.lib_data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Load failed", str(e))
        self._recalc_folder_counter()
        self._recalc_material_counter()
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
