# -*- coding: utf-8 -*-

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except Exception:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

import os, sys, json, re

import maya.OpenMayaUI as omui
try:
    import maya.cmds as cmds
except Exception:
    cmds = None

# -- import MaliUtil ทั้งแบบแพ็กเกจและแบบสคริปต์เดี่ยว --
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
if THIS_DIR not in sys.path: sys.path.insert(0, THIS_DIR)
try:
    from . import MaliUtil as mu   # type: ignore
except Exception:
    import MaliUtil as mu

# ================================
# Constants / sizing
# ================================
DEFAULT_SIZE    = QtCore.QSize(980, 740)
LEFT_PANEL_W    = 270
TREE_ICON_SIZE  = QtCore.QSize(28, 28)
PREVIEW_W       = 220
PREVIEW_H       = 220

# ================================
# JSON path policy (per-scene)
# ================================
def _scene_json_path():
    """ใช้ JSON ข้างๆ scene ปัจจุบันเท่านั้น (ไฟล์ใหม่/ยังไม่ save = ไม่โหลดอะไรเลย)"""
    try:
        sn = cmds.file(q=True, sn=True) if cmds else ""
    except Exception:
        sn = ""
    if not sn:
        return None
    folder = os.path.dirname(sn)
    return os.path.join(folder, "material_library.json")

# ---- fallback icon ----
def _qicon_from_b64(b64str: str) -> QtGui.QIcon:
    if hasattr(mu, "qicon_from_b64"):
        try: return mu.qicon_from_b64(b64str)
        except Exception: pass
    if not b64str: return QtGui.QIcon()
    try:
        ba = QtCore.QByteArray.fromBase64(QtCore.QByteArray(b64str.encode('utf-8')))
        pm = QtGui.QPixmap(); pm.loadFromData(ba)
        return QtGui.QIcon(pm) if not pm.isNull() else QtGui.QIcon()
    except Exception:
        return QtGui.QIcon()

# =========================
# Dialog: Add Material
# =========================
class MaterialPropDialog(QtWidgets.QDialog):
    """ชื่อเป็น read-only (ดึงจาก selection ใน Hypershade เท่านั้น)"""
    def __init__(self, parent=None, initial=None, title="Add Material"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(420, 300)

        base = {"name": "", "thumb_b64": "", "assets": []}
        if initial: base.update(initial)
        else:
            if hasattr(mu, "get_selected_material_name"):
                guess = mu.get_selected_material_name() or ""
                base["name"] = guess
        self.data = base

        main = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_le = QtWidgets.QLineEdit(self.data.get("name",""))
        self.name_le.setReadOnly(True)
        self.name_le.setToolTip("Select a material in Hypershade. Name is not editable here.")
        form.addRow("Name:", self.name_le); main.addLayout(form)

        img_row = QtWidgets.QHBoxLayout()
        if hasattr(mu, "ImagePreview"):
            self.preview = mu.ImagePreview(200, 180, self)
            self.preview.set_image_b64(self.data.get("thumb_b64",""))
        else:
            self.preview = QtWidgets.QLabel("No Preview")
            self.preview.setMinimumSize(200,180)
            self.preview.setAlignment(QtCore.Qt.AlignCenter)
            self.preview.setStyleSheet("background:#2b2b2b;border:1px solid #555;color:#aaa;")
        img_row.addWidget(self.preview, 0)
        pick_btn = QtWidgets.QPushButton("Add Image"); img_row.addWidget(pick_btn, 1)
        main.addLayout(img_row)

        btns = QtWidgets.QHBoxLayout(); btns.addStretch(1)
        ok_btn, cancel_btn = QtWidgets.QPushButton("OK"), QtWidgets.QPushButton("Cancel")
        btns.addWidget(ok_btn); btns.addWidget(cancel_btn); main.addLayout(btns)

        pick_btn.clicked.connect(self._pick_image)
        ok_btn.clicked.connect(self.accept); cancel_btn.clicked.connect(self.reject)

    def _pick_image(self):
        b64 = ""
        if hasattr(mu, "pick_image_to_base64"):
            b64, _ = mu.pick_image_to_base64(self)
        if not b64: return
        self.data["thumb_b64"] = b64
        if hasattr(self.preview, "set_image_b64"): self.preview.set_image_b64(b64)

    def get_data(self):
        return {"name": self.name_le.text().strip(),
                "thumb_b64": self.data.get("thumb_b64",""),
                "assets": []}  # ไม่พก assets จาก dialog


# =================
# Material Card
# =================
class MaterialCard(QtWidgets.QFrame):
    nameEditedLive = QtCore.Signal(object, str)
    nameCommitted  = QtCore.Signal(object, str)
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
        main.setContentsMargins(12,12,12,12); main.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        if hasattr(mu, "ImagePreview"):
            self.preview = mu.ImagePreview(PREVIEW_W, PREVIEW_H, self)
            self.preview.set_image_b64(self.mat.get("thumb_b64",""))
        else:
            self.preview = QtWidgets.QLabel("No Preview")
            self.preview.setMinimumSize(PREVIEW_W, PREVIEW_H)
            self.preview.setAlignment(QtCore.Qt.AlignCenter)
            self.preview.setStyleSheet("background:#2b2b2b;border:1px solid #555;color:#aaa;")
        top.addWidget(self.preview,0)

        right = QtWidgets.QVBoxLayout()
        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(QtWidgets.QLabel("Name :"))
        self.name_le = QtWidgets.QLineEdit(self.mat.get("name",""))
        name_row.addWidget(self.name_le, 1); right.addLayout(name_row)

        row1 = QtWidgets.QHBoxLayout()
        self.btn_edit = QtWidgets.QPushButton("Edit Material")
        self.btn_link = QtWidgets.QPushButton("Link Material")
        for b in (self.btn_edit, self.btn_link): b.setMinimumHeight(28)
        row1.addWidget(self.btn_edit); row1.addWidget(self.btn_link)
        right.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        self.btn_addimg = QtWidgets.QPushButton("Edit Image")
        self.btn_select = QtWidgets.QPushButton("Select All")
        for b in (self.btn_addimg, self.btn_select): b.setMinimumHeight(28)
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
        self.asset_list.setMinimumHeight(140)
        main.addWidget(self.asset_list,1)
        main.addWidget(self._hline())

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
        l = QtWidgets.QFrame(); l.setFrameShape(QtWidgets.QFrame.HLine); l.setFrameShadow(QtWidgets.QFrame.Sunken); return l

    def _populate_assets(self):
        self.asset_list.blockSignals(True); self.asset_list.clear()
        for name in self.mat.get("assets", []):
            self.asset_list.addItem(QtWidgets.QListWidgetItem(name))
        self.asset_list.blockSignals(False)

    def _pick_image(self):
        b64 = ""
        if hasattr(mu, "pick_image_to_base64"): b64, _ = mu.pick_image_to_base64(self)
        if not b64: return
        self.mat["thumb_b64"] = b64
        if hasattr(self.preview, "set_image_b64"): self.preview.set_image_b64(b64)

    def _asset_del(self):
        sel = self.asset_list.selectedItems()
        if not sel: return
        names = [i.text() for i in sel]
        self._unassign_from_scene(names)
        # อัปเดตการ์ดชั่วคราว (ตัวจริงจะถูก rescan จากด้านนอก)
        self.mat["assets"] = [n for n in self.mat.get("assets", []) if n not in set(names)]
        self._populate_assets()

    def _unassign_from_scene(self, names):
        if not cmds: return
        mat_name = self.mat.get("name","")
        if not mat_name: return
        sg = mu.get_shading_engine(mat_name)
        if not sg: return
        shapes = []
        for n in names:
            if not cmds.objExists(n): continue
            if cmds.nodeType(n) == "transform":
                shapes += cmds.listRelatives(n, s=True, ni=True, pa=True) or []
            else:
                shapes.append(n)
        shapes = list(dict.fromkeys(shapes))
        if not shapes: return
        try:
            for s in shapes:
                try: cmds.sets(s, rm=sg)
                except Exception: pass
            try: cmds.sets(shapes, e=True, forceElement="initialShadingGroup")
            except Exception:
                try:
                    cur = cmds.ls(sl=True)
                    cmds.select(shapes, r=True); cmds.hyperShade(assign="lambert1")
                    if cur: cmds.select(cur, r=True)
                except Exception: pass
        except Exception: pass

    def _select_assets(self):
        if not cmds: return
        names = [self.asset_list.item(i).text()
                 for i in range(self.asset_list.count())
                 if self.asset_list.item(i).isSelected()]
        try: cmds.select(names if names else [], r=True)
        except Exception: pass

    def set_name(self, new_name):
        self.name_le.blockSignals(True)
        self.name_le.setText(new_name)
        self.name_le.blockSignals(False)

    def refresh(self):
        if hasattr(self.preview, "set_image_b64"):
            self.preview.set_image_b64(self.mat.get("thumb_b64",""))
        self._populate_assets()


# ==============
# Main Dialog
# ==============
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
        self.resize(DEFAULT_SIZE); self.setMinimumSize(860, 700)

        self.lib_data = {}               # { folder: [ {name, thumb_b64, assets, graph?}, ... ] }
        self.folder_counter = 1
        self.current_folder = None
        self._tree_index, self._card_index = {}, {}
        self._sized_once = False
        self._json_path = _scene_json_path()  # None เมื่อยังไม่ได้ save scene

        # cache ไว้เช็คเปลี่ยนแปลงทรัพยากรจากซีน
        self._assets_cache = {}  # {material_name: tuple(objects)}

        # left
        left = QtWidgets.QWidget()
        left_l = QtWidgets.QVBoxLayout(left); left_l.setContentsMargins(6,6,6,6)
        self.tree = QtWidgets.QTreeWidget(); self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16); self.tree.setIconSize(TREE_ICON_SIZE)
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

        # bottom buttons
        hb = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_import  = QtWidgets.QPushButton("Import…")
        self.btn_saveas  = QtWidgets.QPushButton("Save As…")
        self.btn_save    = QtWidgets.QPushButton("Save")
        hb.addStretch(1)
        hb.addWidget(self.btn_refresh)
        hb.addWidget(self.btn_import)
        hb.addWidget(self.btn_saveas)
        hb.addWidget(self.btn_save)
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
        self.btn_saveas.clicked.connect(self.on_save_as)
        self.btn_import.clicked.connect(self.on_import)
        self.btn_refresh.clicked.connect(self._rescan_all_assets)

        # build tree & load json (ถ้ามี)
        self._refresh_tree()
        self._try_load()

        # สแกนซีนครั้งแรกให้ครบทุก material
        self._rescan_all_assets()

        # โฟกัสที่ All Material + ตั้งขนาด splitter
        QtCore.QTimer.singleShot(0, self._apply_initial_sizes)

        # ---- Auto-rescan timer (แก้ปัญหา duplicate แล้วไม่ขึ้นชื่อ) ----
        self._scan_timer = QtCore.QTimer(self)
        self._scan_timer.setInterval(800)  # ms
        self._scan_timer.timeout.connect(self._rescan_tick)
        self._scan_timer.start()

    # ---------------- helpers (scan) ----------------
    def _assets_from_scene(self, mat_name: str):
        if not mat_name or not hasattr(mu, "objects_using_material"):
            return []
        try:
            objs = mu.objects_using_material(mat_name, True) or []
            if hasattr(mu, "normalize_objects"):
                objs = mu.normalize_objects(objs)
            return objs
        except Exception:
            return []

    def _rescan_tick(self):
        """เรียกบ่อย ๆ แต่จะอัปเดต UI ต่อเมื่อมีความต่างจาก cache"""
        changed = False
        for _folder, mats in self.lib_data.items():
            for m in mats:
                name = m.get("name","")
                new_assets = tuple(self._assets_from_scene(name))
                if self._assets_cache.get(name) != new_assets:
                    self._assets_cache[name] = new_assets
                    m["assets"] = list(new_assets)
                    # อัปเดตการ์ดหากมี
                    card = self._card_index.get(id(m))
                    if card: card.refresh()
                    changed = True
        # ไม่ต้อง rebuild ทั้ง pane ทุกครั้ง ลดกระพือหน้าจอ

    def _rescan_all_assets(self):
        """แทนที่ assets ของทุก material ด้วยรายการจากซีนจริง (ไม่ merge)"""
        for _folder, mats in self.lib_data.items():
            for m in mats:
                name = m.get("name","")
                new_assets = tuple(self._assets_from_scene(name))
                self._assets_cache[name] = new_assets
                m["assets"] = list(new_assets)
        # รีเฟรชการ์ดเฉพาะกลุ่มที่เปิดอยู่
        cur = self.tree.currentItem()
        if not cur:
            self._rebuild_cards_for_all(); return
        kind = cur.data(0, self.KIND_ROLE)
        if kind == self.KIND_FOLDER:
            self._rebuild_cards_for_folder(cur.text(0))
        elif kind == self.KIND_MAT:
            self._rebuild_cards_for_folder(cur.parent().text(0))
        else:
            self._rebuild_cards_for_all()

    # helpers (misc)
    def _warn(self, title, msg):
        QtWidgets.QMessageBox.warning(self, title, msg)

    def _apply_initial_sizes(self):
        self.splitter.setSizes([LEFT_PANEL_W, max(300, self.width()-LEFT_PANEL_W)])
        # focus 'All Material'
        root = self.tree.topLevelItem(0)
        if root: 
            self.tree.setCurrentItem(root)
            self._rebuild_cards_for_all()

    def _hline(self):
        l = QtWidgets.QFrame(); l.setFrameShape(QtWidgets.QFrame.HLine); l.setFrameShadow(QtWidgets.QFrame.Sunken); return l

    def _material_icon(self, m: dict):
        b64 = m.get("thumb_b64","")
        if b64:
            ic = _qicon_from_b64(b64)
            if not ic.isNull(): return ic
        pm = QtGui.QPixmap(48,48); pm.fill(QtGui.QColor("#777"))
        return QtGui.QIcon(pm)

    def showEvent(self, e):
        super().showEvent(e)
        if not self._sized_once:
            self.resize(DEFAULT_SIZE); self._sized_once = True
            self._rescan_all_assets()

    def closeEvent(self, e):
        try:
            self._scan_timer.stop()
        except Exception:
            pass
        return super().closeEvent(e)

    # ---------------- tree build ----------------
    def _refresh_tree(self):
        self._tree_index.clear(); self.tree.clear()
        root = QtWidgets.QTreeWidgetItem(["All Material"])
        root.setData(0, self.KIND_ROLE, self.KIND_ROOT)
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

    def _rebuild_cards_for_all(self):
        mats_all = []
        for mats in self.lib_data.values():
            mats_all.extend(mats)
        self._rebuild_cards(mats_all)

    def _rebuild_cards_for_folder(self, folder_name):
        mats = self.lib_data.get(folder_name, [])
        self._rebuild_cards(mats)

    def _rebuild_cards(self, mats_list):
        while self.cards_layout.count():
            it = self.cards_layout.takeAt(0)
            w = it.widget()
            if w: w.deleteLater()
        self._card_index.clear()

        for m in mats_list:
            # บังคับดึงจากซีนทุกครั้ง
            m["assets"] = self._assets_from_scene(m.get("name",""))
            self._assets_cache[m.get("name","")] = tuple(m["assets"])
            card = MaterialCard(m, self.cards_container)
            card.nameEditedLive.connect(self._card_name_live)
            card.nameCommitted.connect(self._card_name_commit)
            card.requestEdit.connect(self._card_edit_material)
            card.requestSelect.connect(self._card_select_objs)
            card.requestLink.connect(self._card_link_material)
            self.cards_layout.addWidget(card)
            self._card_index[id(m)] = card

        self.cards_layout.addStretch()

    # ---------------- card callbacks ----------------
    def _card_name_live(self, mat_ref, text):
        item = self._tree_index.get(id(mat_ref))
        if item: item.setText(0, text)

    def _rename_strict(self, old_name: str, new_name: str) -> bool:
        if not cmds:
            self._warn("Rename failed", "Cannot access maya.cmds"); return False
        if not new_name or old_name == new_name: return True
        if not cmds.objExists(old_name):
            self._warn("Rename failed", f"Material not found: {old_name}"); return False
        if cmds.objExists(new_name):
            self._warn("Duplicate name", f"A node named '{new_name}' already exists."); return False
        try:
            cmds.rename(old_name, new_name); return True
        except Exception as e:
            self._warn("Rename failed", str(e)); return False

    def _card_name_commit(self, mat_ref, text):
        old = mat_ref.get("name",""); new = (text or "").strip()
        if not new or new == old:
            item = self._tree_index.get(id(mat_ref))
            if item: item.setText(0, old)
            return
        if self._rename_strict(old, new):
            mat_ref["name"] = new
            item = self._tree_index.get(id(mat_ref))
            if item: item.setText(0, new)
            card = self._card_index.get(id(mat_ref))
            if card: card.set_name(new)
            self._rescan_all_assets()
        else:
            item = self._tree_index.get(id(mat_ref))
            if item: item.setText(0, old)
            card = self._card_index.get(id(mat_ref))
            if card: card.set_name(old)

    def _card_edit_material(self, mat_ref):
        if hasattr(mu, "open_hypershade"):
            mu.open_hypershade((mat_ref or {}).get("name",""))

    def _card_select_objs(self, mat_ref):
        name = (mat_ref or {}).get("name","")
        if not hasattr(mu, "select_objects_from_material"): return
        try:
            selected = mu.select_objects_from_material(name)
            if not selected:
                QtWidgets.QMessageBox.information(self, "Select Objects", "No objects are using this material.")
        except Exception as e:
            self._warn("Select Objects", str(e))

    def _card_link_material(self, mat_ref):
        name = (mat_ref or {}).get("name","")
        if not hasattr(mu, "link_material_to_objects"): return
        try:
            affected = mu.link_material_to_objects(name)
        except Exception as e:
            self._warn("Link Material", str(e)); return
        if not affected:
            QtWidgets.QMessageBox.information(self, "Link Material", "Please select object(s) in the scene first.")
            return
        self._rescan_all_assets()

    # ---------------- actions ----------------
    def on_create_folder(self):
        name = f"Folder {self.folder_counter}"
        while name in self.lib_data:
            self.folder_counter += 1; name = f"Folder {self.folder_counter}"
        self.lib_data[name] = []; self.folder_counter += 1
        self._refresh_tree()

    def on_add_material(self):
        sel_name = mu.get_selected_material_name() if hasattr(mu, "get_selected_material_name") else ""
        if not sel_name:
            self._warn("Add Material", "Please select a material in Hypershade first.")
            return

        item = self.tree.currentItem()
        if not item:
            self._warn("Add Material", "Select a folder first."); return
        kind = item.data(0, self.KIND_ROLE)
        folder = item.text(0) if kind == self.KIND_FOLDER else (item.parent().text(0) if kind == self.KIND_MAT else None)
        if kind == self.KIND_ROOT: folder = None
        if not folder:
            self._warn("Add Material", "Select a folder first."); return

        init = {"name": sel_name, "thumb_b64": "", "assets": []}
        dlg = MaterialPropDialog(self, initial=init, title="Add Material")
        if dlg.exec_() != QtWidgets.QDialog.Accepted: return
        data = dlg.get_data()
        try:
            if hasattr(mu, "capture_material_network"):
                data["graph"] = mu.capture_material_network(data.get("name",""))
        except Exception:
            data["graph"] = {}

        mats = self.lib_data.setdefault(folder, [])
        mats.append(data)
        self._refresh_tree()
        self._rescan_all_assets()
        self._rebuild_cards_for_folder(folder)

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

    def _focus_card_by_id(self, mat_id: int):
        card = self._card_index.get(mat_id)
        if not card: return
        def _do():
            vp = self.scroll.viewport().height()
            y = card.mapTo(self.cards_container, QtCore.QPoint(0,0)).y()
            sb = self.scroll.verticalScrollBar(); sb.setValue(max(0, y - vp//3))
            card.setFocus(QtCore.Qt.OtherFocusReason)
        QtCore.QTimer.singleShot(0, _do)

    def on_tree_rename(self, item, _col):
        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_ROOT: return
        old = item.text(0)
        new, ok = QtWidgets.QInputDialog.getText(self, "Rename", "New name:", text=old)
        if not ok or not new or new == old: return

        if kind == self.KIND_FOLDER:
            if new in self.lib_data:
                self._warn("Rename", "Folder already exists."); return
            self.lib_data[new] = self.lib_data.pop(old)
            self._refresh_tree(); self._rebuild_cards_for_folder(new)
        else:
            folder = item.parent().text(0)
            mats = self.lib_data.get(folder, [])
            mat_id = item.data(0, self.MAT_ID_ROLE)
            ref = next((m for m in mats if id(m) == mat_id), None)
            if not ref: return
            real_old = ref.get("name","")
            if self._rename_strict(real_old, new):
                ref["name"] = new
                item.setText(0, new)
                card = self._card_index.get(mat_id)
                if card: card.set_name(new)
                self._rescan_all_assets()
                self._focus_card_by_id(mat_id)
            else:
                item.setText(0, real_old)

    def on_delete(self):
        item = self.tree.currentItem()
        if not item: return
        kind = item.data(0, self.KIND_ROLE)
        if kind == self.KIND_FOLDER:
            name = item.text(0)
            self.lib_data.pop(name, None)
            item.parent().removeChild(item)
            self._rebuild_cards([])
        elif kind == self.KIND_MAT:
            folder = item.parent().text(0)
            mat_id = item.data(0, self.MAT_ID_ROLE)
            mats = self.lib_data.get(folder, [])
            self.lib_data[folder] = [m for m in mats if id(m) != mat_id]
            item.parent().removeChild(item)
            self._rebuild_cards_for_folder(folder)
        else:
            QtWidgets.QMessageBox.information(self, "Delete", "Root cannot be deleted.")

    # -------- Save / Save As / Import ----------
    def _gather_graphs(self):
        for folder, mats in self.lib_data.items():
            for m in mats:
                name = m.get("name","")
                try:
                    if hasattr(mu, "capture_material_network") and cmds and cmds.objExists(name):
                        m["graph"] = mu.capture_material_network(name)
                except Exception:
                    pass
                m["assets"] = []  # เคลียร์ก่อนบันทึก กัน carry-over

    def _write_json(self, path):
        self._gather_graphs()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.lib_data, f, ensure_ascii=False, indent=2)

    def on_save(self):
        if not self._json_path:
            self.on_save_as(); return
        try:
            self._write_json(self._json_path)
            QtWidgets.QMessageBox.information(self, "Save", f"Saved: {self._json_path}")
        except Exception as e:
            self._warn("Save failed", str(e))

    def on_save_as(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Library As",
                                                        _scene_json_path() or os.path.expanduser("~"),
                                                        "Material Library (*.json)")
        if not path: return
        try:
            self._write_json(path)
            self._json_path = path
            QtWidgets.QMessageBox.information(self, "Save As", f"Saved: {path}")
        except Exception as e:
            self._warn("Save As failed", str(e))

    def on_import(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Library",
                                                        _scene_json_path() or os.path.expanduser("~"),
                                                        "Material Library (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                incoming = json.load(f)
        except Exception as e:
            self._warn("Import failed", str(e)); return

        # เลือกโฟลเดอร์ปลายทาง
        folders = list(self.lib_data.keys())
        if not folders:
            dest_folder, ok = QtWidgets.QInputDialog.getText(self, "Destination Folder",
                                                             "Folder name:", text="Imported")
            if not ok or not dest_folder: return
            self.lib_data[dest_folder] = []
        else:
            dest_folder, ok = QtWidgets.QInputDialog.getItem(self, "Destination Folder",
                                                             "Choose a folder:", folders, 0, False)
            if not ok: return

        mats_in = []
        for k, v in (incoming or {}).items():
            if isinstance(v, list): mats_in.extend(v)

        for m in mats_in:
            snap = (m.get("graph") or {})
            if snap and hasattr(mu, "rebuild_material_network"):
                try:
                    real_name = mu.rebuild_material_network(snap, new_material_name=m.get("name",""))
                    if real_name:
                        m["name"] = real_name
                except Exception:
                    pass
            m["assets"] = []
            self.lib_data.setdefault(dest_folder, []).append(m)

        self._refresh_tree()
        self._rescan_all_assets()

    # persistence (auto-load only when JSON file exists next to this scene)
    def _try_load(self):
        if not self._json_path or not os.path.isfile(self._json_path):
            return
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                self.lib_data = json.load(f)
            for mats in self.lib_data.values():
                for m in mats:
                    m.setdefault("thumb_b64","")
                    m["assets"] = []
        except Exception as e:
            self._warn("Load failed", str(e))
        max_f = 0
        for name in self.lib_data.keys():
            mf = re.match(r'^Folder\s+(\d+)$', name)
            if mf: max_f = max(max_f, int(mf.group(1)))
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
