# -*- coding: utf-8 -*-
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except Exception:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

import os, sys, json, re
import maya.OpenMayaUI as omui

# -- import MaliUtil ทั้งแบบแพ็กเกจและแบบสคริปต์เดี่ยว --
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)
try:
    from . import MaliUtil as mu   # type: ignore
except Exception:
    import MaliUtil as mu

SAVE_JSON       = os.path.join(THIS_DIR, 'material_library.json')
DEFAULT_SIZE    = QtCore.QSize(750, 750)
LEFT_PANEL_W    = 50
TREE_ICON_SIZE  = QtCore.QSize(28, 28)

def _qicon_from_b64(b64str: str) -> QtGui.QIcon:
    """Icon จาก base64; ถ้า MaliUtil มีให้ก็ใช้จากนั้นก่อน"""
    if hasattr(mu, "qicon_from_b64"):
        try:
            return mu.qicon_from_b64(b64str)
        except Exception:
            pass
    if not b64str:
        return QtGui.QIcon()
    try:
        ba = QtCore.QByteArray.fromBase64(QtCore.QByteArray(b64str.encode('utf-8')))
        pm = QtGui.QPixmap(); pm.loadFromData(ba)
        return QtGui.QIcon(pm) if not pm.isNull() else QtGui.QIcon()
    except Exception:
        return QtGui.QIcon()

# ---------------- Dialog: Add Material ----------------
class MaterialPropDialog(QtWidgets.QDialog):
    """หน้าต่าง Add Material: ชื่อมาจาก Hypershade และเป็น Read-Only"""
    def __init__(self, parent=None, initial=None, title="Add Material"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(420, 260)

        base = {"name": "", "thumb_b64": "", "assets": []}
        if initial:
            base.update(initial)
        else:
            if hasattr(mu, "get_selected_material_name"):
                guess = mu.get_selected_material_name() or ""
                if guess:
                    base["name"] = guess
        self.data = base

        main = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.name_le = QtWidgets.QLineEdit(self.data.get("name",""))
        self.name_le.setReadOnly(True)
        self.name_le.setEnabled(False)
        form.addRow("Name:", self.name_le)
        main.addLayout(form)

        img_row = QtWidgets.QHBoxLayout()
        if hasattr(mu, "ImagePreview"):
            self.preview = mu.ImagePreview(200,160,self)
            self.preview.set_image_b64(self.data.get("thumb_b64",""))
        else:
            self.preview = QtWidgets.QLabel("No Preview")
            self.preview.setMinimumSize(200,160)
            self.preview.setAlignment(QtCore.Qt.AlignCenter)
            self.preview.setStyleSheet("background:#2b2b2b;border:1px solid #555;color:#aaa;")
        img_row.addWidget(self.preview, 0)

        pick_btn = QtWidgets.QPushButton("Add Image")
        img_row.addWidget(pick_btn, 1)
        main.addLayout(img_row)

        btns = QtWidgets.QHBoxLayout(); btns.addStretch(1)
        ok_btn, cancel_btn = QtWidgets.QPushButton("OK"), QtWidgets.QPushButton("Cancel")
        btns.addWidget(ok_btn); btns.addWidget(cancel_btn)
        main.addLayout(btns)

        pick_btn.clicked.connect(self._pick_image)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def _pick_image(self):
        b64 = ""
        if hasattr(mu, "pick_image_to_base64"):
            b64, _ = mu.pick_image_to_base64(self)
        if not b64:
            return
        self.data["thumb_b64"] = b64
        if hasattr(self.preview, "set_image_b64"):
            self.preview.set_image_b64(b64)

    def get_data(self):
        return {
            "name": self.name_le.text().strip(),
            "thumb_b64": self.data.get("thumb_b64",""),
            "assets": list(self.data.get("assets",[]))
        }

# ---------------- Card ----------------
class MaterialCard(QtWidgets.QFrame):
    nameEditedLive = QtCore.Signal(object, str)   # ไลฟ์อัปเดตชื่อใน tree
    nameCommitted  = QtCore.Signal(object, str)   # ค่อย rename จริงเมื่อจบ
    requestEdit    = QtCore.Signal(object)
    requestSelect  = QtCore.Signal(object)
    requestLink    = QtCore.Signal(object)

    def __init__(self, mat_ref: dict, parent=None):
        super().__init__(parent)
        self.mat = mat_ref
        self.mat.setdefault("assets", [])

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setStyleSheet("QFrame{border:1px solid #505050; border-radius:8px;}")
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(12,12,12,12)
        main.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        if hasattr(mu, "ImagePreview"):
            self.preview = mu.ImagePreview(150,150,self)
            self.preview.set_image_b64(self.mat.get("thumb_b64",""))
        else:
            self.preview = QtWidgets.QLabel("No Preview")
            self.preview.setMinimumSize(360,260)
            self.preview.setAlignment(QtCore.Qt.AlignCenter)
            self.preview.setStyleSheet("background:#2b2b2b;border:1px solid #555;color:#aaa;")
        top.addWidget(self.preview,0)

        right = QtWidgets.QVBoxLayout()
        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(QtWidgets.QLabel("Name :"))
        self.name_le = QtWidgets.QLineEdit(self.mat.get("name",""))
        name_row.addWidget(self.name_le,1)
        right.addLayout(name_row)

        row1 = QtWidgets.QHBoxLayout()
        self.btn_edit = QtWidgets.QPushButton("Edit Material")
        self.btn_link = QtWidgets.QPushButton("Link Material")
        for b in (self.btn_edit, self.btn_link):
            b.setMinimumHeight(28)
        row1.addWidget(self.btn_edit); row1.addWidget(self.btn_link)
        right.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        self.btn_addimg = QtWidgets.QPushButton("Edit Image")
        self.btn_select = QtWidgets.QPushButton("Select All")
        for b in (self.btn_addimg, self.btn_select):
            b.setMinimumHeight(28)
        row2.addWidget(self.btn_addimg); row2.addWidget(self.btn_select)
        right.addLayout(row2)

        top.addLayout(right,1)
        main.addLayout(top)
        main.addWidget(self._hline())

        header = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Asset Used"); lbl.setStyleSheet("font-weight:600;")
        header.addWidget(lbl); header.addStretch(1)
        self.btn_asset_del = QtWidgets.QToolButton(); self.btn_asset_del.setText("Remove")
        header.addWidget(self.btn_asset_del)
        main.addLayout(header)

        self.asset_list = QtWidgets.QListWidget()
        self.asset_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.asset_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.asset_list.setMinimumHeight(120)
        main.addWidget(self.asset_list,1)

        main.addWidget(self._hline())

        # connects
        self.name_le.textEdited.connect(lambda t: self.nameEditedLive.emit(self.mat, t))
        self.name_le.editingFinished.connect(lambda: self.nameCommitted.emit(self.mat, self.name_le.text().strip()))
        self.btn_edit.clicked.connect(lambda: self.requestEdit.emit(self.mat))
        self.btn_link.clicked.connect(lambda: self.requestLink.emit(self.mat))
        self.btn_select.clicked.connect(lambda: self.requestSelect.emit(self.mat))
        self.btn_addimg.clicked.connect(self._pick_image)
        self.btn_asset_del.clicked.connect(self._asset_del)
        self.asset_list.itemSelectionChanged.connect(self._select_assets)

        self._populate_assets()

    def _hline(self):
        l = QtWidgets.QFrame()
        l.setFrameShape(QtWidgets.QFrame.HLine)
        l.setFrameShadow(QtWidgets.QFrame.Sunken)
        return l

    def _populate_assets(self):
        self.asset_list.blockSignals(True)
        self.asset_list.clear()
        for name in self.mat.get("assets", []):
            self.asset_list.addItem(QtWidgets.QListWidgetItem(name))
        self.asset_list.blockSignals(False)

    def _pick_image(self):
        b64 = ""
        if hasattr(mu, "pick_image_to_base64"):
            b64, _ = mu.pick_image_to_base64(self)
        if not b64:
            return
        self.mat["thumb_b64"] = b64
        if hasattr(self.preview, "set_image_b64"):
            self.preview.set_image_b64(b64)

    def _asset_del(self):
        sel = self.asset_list.selectedItems()
        if not sel:
            return
        names = [i.text() for i in sel]
        self._unassign_from_scene(names)
        self.mat["assets"] = [n for n in self.mat.get("assets", []) if n not in set(names)]
        self._populate_assets()

    def _unassign_from_scene(self, names):
        try:
            import maya.cmds as cmds
        except Exception:
            return
        mat_name = self.mat.get("name",""); 
        if not mat_name:
            return
        sg = mu.get_shading_engine(mat_name) if hasattr(mu, "get_shading_engine") else None
        if not sg:
            return
        shapes = []
        for n in names:
            if not cmds.objExists(n):
                continue
            if cmds.nodeType(n) == "transform":
                shapes += cmds.listRelatives(n, s=True, ni=True, pa=True) or []
            else:
                shapes.append(n)
        shapes = list(dict.fromkeys(shapes))
        if not shapes:
            return
        try:
            for s in shapes:
                try:
                    cmds.sets(s, rm=sg)
                except Exception:
                    pass
            try:
                cmds.sets(shapes, e=True, forceElement="initialShadingGroup")
            except Exception:
                try:
                    cur = cmds.ls(sl=True)
                    cmds.select(shapes, r=True); cmds.hyperShade(assign="lambert1")
                    if cur: cmds.select(cur, r=True)
                except Exception:
                    pass
        except Exception:
            pass

    def _select_assets(self):
        try:
            import maya.cmds as cmds
        except Exception:
            return
        names = [self.asset_list.item(i).text()
                 for i in range(self.asset_list.count())
                 if self.asset_list.item(i).isSelected()]
        try:
            cmds.select(names if names else [], r=True)
        except Exception:
            pass

    def set_name(self, new_name):
        self.name_le.blockSignals(True)
        self.name_le.setText(new_name)
        self.name_le.blockSignals(False)

    def refresh(self):
        if hasattr(self.preview, "set_image_b64"):
            self.preview.set_image_b64(self.mat.get("thumb_b64",""))
        self._populate_assets()

# ---------------- Main Dialog ----------------
class MaterialLibraryDialog(QtWidgets.QDialog):
    KIND_ROLE   = QtCore.Qt.UserRole
    KIND_ROOT   = "root"
    KIND_FOLDER = "folder"
    KIND_MAT    = "material"
    MAT_ID_ROLE = QtCore.Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 Material Library")
        self.setWindowModality(QtCore.Qt.NonModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.resize(DEFAULT_SIZE)
        self.setMinimumSize(680,680)

        self.lib_data = {}
        self.folder_counter = 1
        self.current_folder = None
        self._tree_index, self._card_index = {}, {}
        self._sized_once = False

        # left
        left = QtWidgets.QWidget()
        left_l = QtWidgets.QVBoxLayout(left); left_l.setContentsMargins(6,6,6,6)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True); self.tree.setIndentation(16)
        self.tree.setIconSize(TREE_ICON_SIZE)
        left_l.addWidget(self.tree)

        lb = QtWidgets.QHBoxLayout()
        self.btn_create_folder = QtWidgets.QPushButton("Create Folder")
        self.btn_add_material  = QtWidgets.QPushButton("Add Material")
        self.btn_delete        = QtWidgets.QPushButton("Delete")
        lb.addWidget(self.btn_create_folder); lb.addWidget(self.btn_add_material); lb.addWidget(self.btn_delete)
        left_l.addLayout(lb)

        # right
        right = QtWidgets.QWidget()
        right_l = QtWidgets.QVBoxLayout(right)
        title = QtWidgets.QLabel("Materials Detail"); title.setStyleSheet("font-weight:600;")
        right_l.addWidget(title)

        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True)
        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(16); self.cards_layout.setContentsMargins(8,8,8,8)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.cards_container)
        right_l.addWidget(self.scroll,1)

        right_l.addWidget(self._hline())
        hb = QtWidgets.QHBoxLayout(); hb.addStretch(1)
        self.btn_save = QtWidgets.QPushButton("Save"); hb.addWidget(self.btn_save)
        right_l.addLayout(hb)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(left); self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0,0); self.splitter.setStretchFactor(1,1)

        main = QtWidgets.QVBoxLayout(self); main.addWidget(self.splitter)

        # signals
        self.btn_create_folder.clicked.connect(self.on_create_folder)
        self.btn_add_material.clicked.connect(self.on_add_material)
        self.btn_delete.clicked.connect(self.on_delete)
        self.tree.itemClicked.connect(self.on_tree_clicked)
        self.tree.itemDoubleClicked.connect(self.on_tree_rename)
        self.btn_save.clicked.connect(self.on_save)

        # build & default select = All Material
        self._try_load()
        if not os.path.isfile(SAVE_JSON):
            self._refresh_tree()

        def _select_all_default():
            root = self.tree.topLevelItem(0)
            if root:
                self.tree.setCurrentItem(root)
                self._rebuild_cards_for_all()
            self._apply_initial_sizes()
        QtCore.QTimer.singleShot(0, _select_all_default)

    # --- helpers ---
    def _warn(self, title, msg):
        QtWidgets.QMessageBox.warning(self, title, msg)

    def _rename_strict(self, old_name: str, new_name: str) -> bool:
        """rename ใน Maya แบบ 'strict' – ชื่อซ้ำ/ไม่พบ = เตือนและไม่เปลี่ยน"""
        try:
            import maya.cmds as cmds
        except Exception:
            self._warn("Rename failed", "Cannot access maya.cmds")
            return False
        if not new_name or old_name == new_name:
            return True
        if not cmds.objExists(old_name):
            self._warn("Rename failed", "Material not found: %s" % old_name)
            return False
        if cmds.objExists(new_name):
            self._warn("Duplicate name", "A node named '%s' already exists." % new_name)
            return False
        try:
            cmds.rename(old_name, new_name)
            return True
        except Exception as e:
            self._warn("Rename failed", str(e))
            return False

    def _apply_initial_sizes(self):
        self.splitter.setSizes([LEFT_PANEL_W, max(300, self.width()-LEFT_PANEL_W)])

    def _hline(self):
        l = QtWidgets.QFrame()
        l.setFrameShape(QtWidgets.QFrame.HLine)
        l.setFrameShadow(QtWidgets.QFrame.Sunken)
        return l

    def _material_icon(self, m: dict):
        b64 = m.get("thumb_b64","")
        if b64:
            ic = _qicon_from_b64(b64)
            if not ic.isNull():
                return ic
        pm = QtGui.QPixmap(48,48); pm.fill(QtGui.QColor("#777"))
        return QtGui.QIcon(pm)

    def _merge_scene_assets(self, m: dict):
        if not hasattr(mu, "objects_using_material"):
            return
        try:
            scene_objs = mu.objects_using_material(m.get("name",""), True) or []
        except Exception:
            scene_objs = []
        if scene_objs:
            merged = set(m.get("assets", []) or []); merged.update(scene_objs)
            m["assets"] = sorted(merged)

    def _focus_card_by_id(self, mat_id: int):
        card = self._card_index.get(mat_id)
        if not card:
            return
        def _do():
            vp = self.scroll.viewport().height()
            y = card.mapTo(self.cards_container, QtCore.QPoint(0,0)).y()
            sb = self.scroll.verticalScrollBar(); sb.setValue(max(0, y - vp//2))
            card.setFocus(QtCore.Qt.OtherFocusReason)
        QtCore.QTimer.singleShot(0, _do)

    def _sync_all_assets_from_scene(self):
        """สแกนทั้งไลบรารีใหม่จาก scene: ใครถือวัสดุอะไรอยู่บ้าง"""
        if not hasattr(mu, "objects_using_material"):
            return
        for mats in self.lib_data.values():
            for m in mats:
                try:
                    scene_objs = mu.objects_using_material(m.get("name",""), True) or []
                except Exception:
                    scene_objs = []
                m["assets"] = sorted(set(scene_objs))

    # --- Qt events ---
    def showEvent(self, e):
        super().showEvent(e)
        if not self._sized_once:
            self.resize(DEFAULT_SIZE)
            self._sized_once = True

    # --- tree build ---
    def _refresh_tree(self):
        self._tree_index.clear()
        self.tree.clear()

        root = QtWidgets.QTreeWidgetItem(["All Material"])
        root.setData(0, self.KIND_ROLE, self.KIND_ROOT)
        # อนุญาตให้เลือก Root ได้
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

    def _clear_cards(self):
        while self.cards_layout.count():
            it = self.cards_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def _rebuild_cards_for_folder(self, folder_name):
        self.current_folder = folder_name
        self._clear_cards()
        self._card_index.clear()

        for m in self.lib_data.get(folder_name, []):
            self._merge_scene_assets(m)
            card = MaterialCard(m, self.cards_container)
            card.nameEditedLive.connect(self._card_name_live)
            card.nameCommitted.connect(self._card_name_commit)
            card.requestEdit.connect(self._card_edit_material)
            card.requestSelect.connect(self._card_select_objs)
            card.requestLink.connect(self._card_link_material)
            self.cards_layout.addWidget(card)
            self._card_index[id(m)] = card
        self.cards_layout.addStretch()

    def _rebuild_cards_for_all(self):
        """สร้างการ์ดสำหรับทุก material ใต้ All Material (เลือก Root/เปิดครั้งแรก)"""
        self._clear_cards()
        self._card_index.clear()

        for folder, mats in self.lib_data.items():
            for m in mats:
                self._merge_scene_assets(m)
                card = MaterialCard(m, self.cards_container)
                card.nameEditedLive.connect(self._card_name_live)
                card.nameCommitted.connect(self._card_name_commit)
                card.requestEdit.connect(self._card_edit_material)
                card.requestSelect.connect(self._card_select_objs)
                card.requestLink.connect(self._card_link_material)
                self.cards_layout.addWidget(card)
                self._card_index[id(m)] = card
        self.cards_layout.addStretch()

    # --- card callbacks ---
    def _card_name_live(self, mat_ref, text):
        item = self._tree_index.get(id(mat_ref))
        if item:
            item.setText(0, text)

    def _card_name_commit(self, mat_ref, text):
        old = mat_ref.get("name","")
        new = (text or "").strip()
        if not new or new == old:
            item = self._tree_index.get(id(mat_ref))
            if item:
                item.setText(0, old)
            return
        if self._rename_strict(old, new):
            mat_ref["name"] = new
            item = self._tree_index.get(id(mat_ref))
            if item:
                item.setText(0, new)
            card = self._card_index.get(id(mat_ref))
            if card:
                card.set_name(new)
            self._merge_scene_assets(mat_ref)
            if card:
                card.refresh()
        else:
            # revert
            item = self._tree_index.get(id(mat_ref))
            if item:
                item.setText(0, old)
            card = self._card_index.get(id(mat_ref))
            if card:
                card.set_name(old)

    def _card_edit_material(self, mat_ref):
        if hasattr(mu, "open_hypershade"):
            mu.open_hypershade((mat_ref or {}).get("name",""))

    def _card_select_objs(self, mat_ref):
        name = (mat_ref or {}).get("name","")
        if not hasattr(mu, "select_objects_from_material"):
            return
        try:
            selected = mu.select_objects_from_material(name)
            if not selected:
                QtWidgets.QMessageBox.information(self, "Select Objects", "No objects are using this material.")
        except Exception as e:
            self._warn("Select Objects", str(e))

    def _card_link_material(self, mat_ref):
        name = (mat_ref or {}).get("name","")
        if not hasattr(mu, "link_material_to_objects"):
            return
        try:
            affected = mu.link_material_to_objects(name)
        except Exception as e:
            self._warn("Link Material", str(e))
            return
        if not affected:
            QtWidgets.QMessageBox.information(self, "Link Material", "Please select object(s) in the scene first.")
            return

        # อัปเดตรายชื่อของทุก material ให้ตรงกับ scene (จัดการกรณีย้ายวัสดุ)
        self._sync_all_assets_from_scene()
        # รีเฟรช UI
        for card in self._card_index.values():
            card.refresh()

    # --- actions ---
    def on_create_folder(self):
        name = f"Folder {self.folder_counter}"
        while name in self.lib_data:
            self.folder_counter += 1
            name = f"Folder {self.folder_counter}"
        self.lib_data[name] = []
        self.folder_counter += 1
        self._refresh_tree()

    def on_add_material(self):
        # บังคับต้องเลือก material ใน Hypershade ก่อน
        sel_name = mu.get_selected_material_name() if hasattr(mu, "get_selected_material_name") else ""
        if not sel_name:
            self._warn("Add Material", "Please select a material in Hypershade first.")
            return

        item = self.tree.currentItem()
        if not item:
            self._warn("Add Material", "Select a folder first.")
            return

        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_ROOT:
            folders = list(self.lib_data.keys())
            if not folders:
                self._warn("Add Material", "Create a folder first.")
                return
            folder, ok = QtWidgets.QInputDialog.getItem(self, "Add Material", "Folder:", folders, 0, False)
            if not ok:
                return
        else:
            folder = item.text(0) if kind == self.KIND_FOLDER else (item.parent().text(0) if kind == self.KIND_MAT else None)
            if not folder:
                self._warn("Add Material", "Select a folder first.")
                return

        init = {"name": sel_name, "thumb_b64": "", "assets": []}
        dlg = MaterialPropDialog(self, initial=init, title="Add Material")
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        data = dlg.get_data()
        self._merge_scene_assets(data)
        self.lib_data.setdefault(folder, []).append(data)
        self._refresh_tree()

        cur = self.tree.currentItem()
        if cur and cur.data(0, self.KIND_ROLE) == self.KIND_ROOT:
            self._rebuild_cards_for_all()
        else:
            self._rebuild_cards_for_folder(folder)
        self._focus_card_by_id(id(data))

    def on_tree_clicked(self, item, _col):
        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_ROOT:
            self._rebuild_cards_for_all()
        elif kind == self.KIND_FOLDER:
            self._rebuild_cards_for_folder(item.text(0))
        elif kind == self.KIND_MAT:
            folder = item.parent().text(0)
            self._rebuild_cards_for_folder(folder)
            self._focus_card_by_id(item.data(0, self.MAT_ID_ROLE))

    def on_tree_rename(self, item, _col):
        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_ROOT:
            return
        old = item.text(0)
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename", "New name:", text=old)
        if not ok or not new or new == old:
            return

        if kind == self.KIND_FOLDER:
            if new in self.lib_data:
                self._warn("Rename", "Folder already exists.")
                return
            self.lib_data[new] = self.lib_data.pop(old)
            self._refresh_tree()
            cur = self.tree.currentItem()
            if cur and cur.data(0, self.KIND_ROLE) == self.KIND_ROOT:
                self._rebuild_cards_for_all()
            else:
                self._rebuild_cards_for_folder(new)
        else:
            folder = item.parent().text(0)
            mats = self.lib_data.get(folder, [])
            mat_id = item.data(0, self.MAT_ID_ROLE)
            ref = next((m for m in mats if id(m) == mat_id), None)
            if not ref:
                return

            real_old = ref.get("name","")
            if self._rename_strict(real_old, new):
                ref["name"] = new
                item.setText(0, new)
                card = self._card_index.get(mat_id)
                if card:
                    card.set_name(new)
                self._merge_scene_assets(ref)
                if card:
                    card.refresh()
                self._focus_card_by_id(mat_id)
            else:
                item.setText(0, real_old)

    def on_delete(self):
        item = self.tree.currentItem()
        if not item:
            return
        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_FOLDER:
            name = item.text(0)
            self.lib_data.pop(name, None)
            item.parent().removeChild(item)
            cur = self.tree.currentItem()
            if cur and cur.data(0, self.KIND_ROLE) == self.KIND_ROOT:
                self._rebuild_cards_for_all()
            else:
                self._rebuild_cards_for_folder("")
        elif kind == self.KIND_MAT:
            folder = item.parent().text(0)
            mat_id = item.data(0, self.MAT_ID_ROLE)
            mats = self.lib_data.get(folder, [])
            self.lib_data[folder] = [m for m in mats if id(m) != mat_id]
            item.parent().removeChild(item)
            cur = self.tree.currentItem()
            if cur and cur.data(0, self.KIND_ROLE) == self.KIND_ROOT:
                self._rebuild_cards_for_all()
            else:
                self._rebuild_cards_for_folder(folder)
        else:
            QtWidgets.QMessageBox.information(self, "Delete", "Root cannot be deleted.")

    def on_save(self):
        try:
            with open(SAVE_JSON, "w", encoding="utf-8") as f:
                json.dump(self.lib_data, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(self, "Save", "Material Library saved.")
        except Exception as e:
            self._warn("Save failed", str(e))

    def _try_load(self):
        if not os.path.isfile(SAVE_JSON):
            return
        try:
            with open(SAVE_JSON, "r", encoding="utf-8") as f:
                self.lib_data = json.load(f)
            for mats in self.lib_data.values():
                for m in mats:
                    m.setdefault("assets", [])
                    m.setdefault("thumb_b64","")
        except Exception as e:
            self._warn("Load failed", str(e))
        max_f = 0
        for name in self.lib_data.keys():
            mf = re.match(r'^Folder\s+(\d+)$', name)
            if mf:
                max_f = max(max_f, int(mf.group(1)))
        self.folder_counter = max(1, max_f+1)
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
