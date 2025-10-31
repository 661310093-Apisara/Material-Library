

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


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)
try:
    from . import MaliUtil as mu   # type: ignore
except Exception:
    import MaliUtil as mu


THEME = {
    # ---- Global font ----
    "font_family": "SF Pro Display",
    "font_size":   9,

    # ---- Base / Panels ----
    "bg_top":      "#0b0f19",
    "bg_bottom":   "#11172a",
    "panel_bg":    "rgba(255,255,255,0.035)",
    "text":        "#F2F4F8",
    "muted":       "#B7C0D0",
    "border":      "rgba(255,255,255,0.08)",
    "round":        10,

    # ---- Buttons ----
    "btn_bg":         "rgba(255,255,255,0.06)",
    "btn_fg":         "#EAF0FF",
    "btn_hover_a":    "#7A5CFF",
    "btn_hover_b":    "#4CB3FF",
    "btn_hover_fg":   "#FFFFFF",
    "btn_disabledbg": "rgba(255,255,255,0.04)",
    "btn_disabledfg": "#8892A6",
    "btn_border":     "rgba(255,255,255,0.10)",
    "btn_round":      14,

    # ---- Pressed/Checked solid ----
    "solid_purple": "#7A5CFF",
    "solid_fg":     "#FFFFFF",
    "solid_bd":     "#7ea6ff",

    # ---- Inputs / Lists ----
    "field_bg":     "rgba(255,255,255,0.05)",
    "field_fg":     "#EAF0FF",
    "field_sel":    "#3D5AFE",
    "field_sel_fg": "#FFFFFF",
    "focus_ring":   "#86B7FF",

    # ---- Headings ----
    "title_fg":     "#FFFFFF",
    "header_fg":    "#E9ECF7",

    # ---- Preview fallback ----
    "preview_bg":   "rgba(255,255,255,0.04)",
    "preview_bd":   "rgba(255,255,255,0.08)",
}

def build_stylesheet(t=THEME) -> str:
    r  = int(t["round"])
    br = int(t["btn_round"])
    fs = int(t["font_size"])
    return f"""
    QDialog, QWidget {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {t['bg_top']}, stop:1 {t['bg_bottom']});
        color: {t['text']};
        font-family: "{t['font_family']}";
        font-size: {fs}pt;
    }}
    QLabel {{ background: transparent; }}

    QWidget#LeftPanel, QWidget#RightPanel, QFrame[objectName^="Card"] {{
        background-color: {t['panel_bg']};
        border: 1px solid {t['border']};
        border-radius: {r}px;
    }}

    QLabel#TitleLabel {{
        color: {t['title_fg']}; font-weight: 700; font-size: {fs+2}pt;
    }}
    QLabel#HeaderLabel {{
        color: {t['header_fg']}; font-weight: 600;
    }}

    QPushButton, QToolButton {{
        background: {t['btn_bg']};
        color: {t['btn_fg']};
        border: 1px solid {t['btn_border']};
        border-radius: {br}px;
        padding: 7px 14px;
    }}
    QPushButton:default {{
        background: {t['btn_bg']};
        color: {t['btn_fg']};
        border: 1px solid {t['btn_border']};
        border-radius: {br}px;
    }}
    QPushButton:hover, QToolButton:hover, QPushButton:default:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {t['btn_hover_a']}, stop:1 {t['btn_hover_b']});
        color: {t['btn_hover_fg']};
        border-color: rgba(255,255,255,0.25);
    }}
    QPushButton:pressed,
    QPushButton:checked,
    QToolButton:pressed,
    QToolButton:checked,
    QPushButton:default:pressed,
    QPushButton:default:checked {{
        background: {t['solid_purple']};
        color: {t['solid_fg']};
        border: 1px solid {t['solid_bd']};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        background: {t['btn_disabledbg']}; color: {t['btn_disabledfg']}; border-color: {t['border']};
    }}

    QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {t['field_bg']};
        color: {t['field_fg']};
        border: 1px solid {t['border']};
        border-radius: {r}px;
        padding: 6px 8px;
        selection-background-color: {t['field_sel']};
        selection-color: {t['field_sel_fg']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {t['focus_ring']};
    }}

    QTreeWidget, QListWidget, QTableView, QScrollArea {{
        background: {t['field_bg']};
        color: {t['field_fg']};
        border: 1px solid {t['border']};
        border-radius: {r}px;
    }}
    QTreeWidget::item:selected, QListWidget::item:selected {{
        background: {t['field_sel']};
        color: {t['field_sel_fg']};
    }}

    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        background: {t['border']}; max-height: 1px; border: none;
    }}

    QLabel#PreviewFallback {{
        background: {t['preview_bg']};
        color: {t['muted']};
        border: 1px solid {t['preview_bd']};
        border-radius: {r}px;
    }}

    QScrollBar:vertical, QScrollBar:horizontal {{
        background: transparent; border: none; margin: 0px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: rgba(255,255,255,0.12); border-radius: 7px;
        min-height: 28px; min-width: 28px;
    }}
    """

def apply_theme(widget: QtWidgets.QWidget):
    f = widget.font()
    f.setPointSize(int(THEME["font_size"]))
    f.setFamily(THEME["font_family"])
    widget.setFont(f)
    widget.setStyleSheet(build_stylesheet(THEME))


# Constants / sizing

DEFAULT_SIZE    = QtCore.QSize(780, 500)
LEFT_PANEL_W    = 100
TREE_ICON_SIZE  = QtCore.QSize(28, 28)
PREVIEW_W       = 150
PREVIEW_H       = 150

# JSON path policy (per-scene)

def _scene_json_path():
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


# Dialog: Add Material

class MaterialPropDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial=None, title="Add Material"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(250, 250)

        base = {"name": "", "thumb_b64": "", "assets": []}
        if initial:
            base.update(initial)
        else:
            if hasattr(mu, "get_selected_material_name"):
                base["name"] = mu.get_selected_material_name() or ""
        self.data = base

        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(6)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0,0,0,0)
        self.name_le = QtWidgets.QLineEdit(self.data.get("name", ""))
        self.name_le.setReadOnly(True)
        self.name_le.setToolTip("Select a material in Hypershade. Name is not editable here.")
        form.addRow("Name:", self.name_le)
        main.addLayout(form)

        if hasattr(mu, "ImagePreview"):
            self.preview = mu.ImagePreview(200, 200, self)
            self.preview.set_image_b64(self.data.get("thumb_b64", ""))
        else:
            self.preview = QtWidgets.QLabel("No Preview")
            self.preview.setObjectName("PreviewFallback")
            self.preview.setMinimumSize(200, 200)
            self.preview.setAlignment(QtCore.Qt.AlignCenter)
        center_row = QtWidgets.QHBoxLayout()
        center_row.addStretch(1); center_row.addWidget(self.preview, 0); center_row.addStretch(1)
        main.addLayout(center_row)

        btns = QtWidgets.QHBoxLayout()
        self.btn_addimg = QtWidgets.QPushButton("Add Image")
        btns.addWidget(self.btn_addimg)
        btns.addStretch(1)
        ok_btn     = QtWidgets.QPushButton("OK");     ok_btn.setDefault(True)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        btns.addWidget(ok_btn); btns.addWidget(cancel_btn)
        main.addLayout(btns)

        self.btn_addimg.clicked.connect(self._pick_image)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        apply_theme(self)

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
            "thumb_b64": self.data.get("thumb_b64", ""),
            "assets": list(self.data.get("assets", [])),
        }


# Material Card
class MaterialCard(QtWidgets.QFrame):
    nameEditedLive = QtCore.Signal(object, str)
    nameCommitted  = QtCore.Signal(object, str)
    requestEdit    = QtCore.Signal(object)
    requestSelect  = QtCore.Signal(object)
    requestLink    = QtCore.Signal(object)
    thumbChanged   = QtCore.Signal(object)

    def __init__(self, mat_ref: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("Card_Material")
        self.mat = mat_ref
        self.mat.setdefault("assets", [])
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)

        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(12,12,12,12); main.setSpacing(10)

        top = QtWidgets.QHBoxLayout()

        if hasattr(mu, "ImagePreview"):
            self.preview = mu.ImagePreview(PREVIEW_W, PREVIEW_H, self)
            self.preview.set_image_b64(self.mat.get("thumb_b64",""))
        else:
            self.preview = QtWidgets.QLabel("No Preview")
            self.preview.setObjectName("PreviewFallback")
            self.preview.setMinimumSize(PREVIEW_W, PREVIEW_H)
            self.preview.setAlignment(QtCore.Qt.AlignCenter)
        top.addWidget(self.preview,0)

        right = QtWidgets.QVBoxLayout()

        name_row = QtWidgets.QHBoxLayout()
        name_lbl = QtWidgets.QLabel("Name :")
        name_lbl.setFocusPolicy(QtCore.Qt.NoFocus)
        self.name_le = QtWidgets.QLineEdit(self.mat.get("name",""))
        name_row.addWidget(name_lbl); name_row.addWidget(self.name_le, 1)
        right.addLayout(name_row)

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
        lbl = QtWidgets.QLabel("Asset Used"); lbl.setObjectName("HeaderLabel")
        lbl.setFocusPolicy(QtCore.Qt.NoFocus)
        header.addWidget(lbl); header.addStretch(1)
        self.btn_asset_del = QtWidgets.QToolButton(); self.btn_asset_del.setText("Remove")
        self.btn_asset_del.setFocusPolicy(QtCore.Qt.StrongFocus)
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
        self.thumbChanged.emit(self.mat)

    def _asset_del(self):
        sel = self.asset_list.selectedItems()
        if not sel: return
        names = [i.text() for i in sel]
        self._unassign_from_scene(names)
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
        self.name_le.blockSignals(True); self.name_le.setText(new_name); self.name_le.blockSignals(False)

    def refresh(self):
        if hasattr(self.preview, "set_image_b64"):
            self.preview.set_image_b64(self.mat.get("thumb_b64",""))
        self._populate_assets()


# MaterialTree (Drag & Drop controller)

class MaterialTree(QtWidgets.QTreeWidget):
    MIME = "application/x-mli-material"

    def __init__(self, owner_dialog, *a, **kw):
        super().__init__(*a, **kw)
        self._dlg = owner_dialog
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.viewport().setAcceptDrops(True)

    def mimeTypes(self):
        return [self.MIME]

    def mimeData(self, items):
        md = QtCore.QMimeData()
        if not items:
            return md
        it = items[0]
        kind = it.data(0, self._dlg.KIND_ROLE)
        if kind != self._dlg.KIND_MAT:
            return md
        mat_id = it.data(0, self._dlg.MAT_ID_ROLE)
        src_folder = it.parent().text(0) if it.parent() else ""
        payload = json.dumps({"mat_id": int(mat_id), "src_folder": src_folder})
        md.setData(self.MIME, payload.encode("utf-8"))
        return md

    def startDrag(self, supportedActions):
        it = self.currentItem()
        if not it:
            return
        md = self.mimeData([it])
        if not md or not md.hasFormat(self.MIME):
            return
        drag = QtGui.QDrag(self)
        drag.setMimeData(md)
        drag.exec_(QtCore.Qt.MoveAction)

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        if not e.mimeData().hasFormat(self.MIME):
            e.ignore(); return
        it = self.itemAt(e.pos())
        if not it:
            e.ignore(); return
        kind = it.data(0, self._dlg.KIND_ROLE)
        if kind in (self._dlg.KIND_FOLDER, self._dlg.KIND_MAT):
            e.setDropAction(QtCore.Qt.MoveAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e: QtGui.QDropEvent):
        if not e.mimeData().hasFormat(self.MIME):
            e.ignore(); return
        try:
            data = json.loads(bytes(e.mimeData().data(self.MIME)).decode("utf-8"))
            mat_id = int(data["mat_id"]); src_folder = data["src_folder"]
        except Exception:
            e.ignore(); return

        dest_item = self.itemAt(e.pos())
        if not dest_item:
            e.ignore(); return

        dest_kind = dest_item.data(0, self._dlg.KIND_ROLE)
        if dest_kind == self._dlg.KIND_FOLDER:
            dest_folder = dest_item.text(0)
            insert_index = None
        elif dest_kind == self._dlg.KIND_MAT:
            dest_folder = dest_item.parent().text(0)
            insert_index = dest_item.parent().indexOfChild(dest_item)
        else:
            e.ignore(); return

        moved = self._dlg._move_material_between_folders(
            mat_id=mat_id,
            src_folder=src_folder,
            dest_folder=dest_folder,
            insert_index=insert_index
        )
        if moved:
            e.setDropAction(QtCore.Qt.MoveAction)
            e.accept()
        else:
            e.ignore()


# Main Dialog

class MaterialLibraryDialog(QtWidgets.QDialog):
    KIND_ROLE   = QtCore.Qt.UserRole
    KIND_ROOT   = "root"
    KIND_FOLDER = "folder"
    KIND_MAT    = "material"
    MAT_ID_ROLE = QtCore.Qt.UserRole + 1
    _FILEINFO_KEY = "MLI_JSON"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 Material Library")
        self.setWindowModality(QtCore.Qt.NonModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.resize(DEFAULT_SIZE)
        self.setMinimumSize(780, 500)

        self.lib_data = {}          
        self.folder_counter = 1
        self.current_folder = None
        self._tree_index, self._card_index = {}, {}
        self._sized_once = False
        self._json_path = _scene_json_path()

        # left panel
        left = QtWidgets.QWidget(); left.setObjectName("LeftPanel")
        left_l = QtWidgets.QVBoxLayout(left); left_l.setContentsMargins(6,6,6,6)
        self.tree = MaterialTree(self)   
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16); self.tree.setIconSize(TREE_ICON_SIZE)
        left_l.addWidget(self.tree)
        lb = QtWidgets.QHBoxLayout()
        self.btn_create_folder = QtWidgets.QPushButton("Create Folder")
        self.btn_add_material  = QtWidgets.QPushButton("Add Material")
        self.btn_delete        = QtWidgets.QPushButton("Delete")
        lb.addWidget(self.btn_create_folder); lb.addWidget(self.btn_add_material); lb.addWidget(self.btn_delete)
        left_l.addLayout(lb)

        # right panel
        right = QtWidgets.QWidget(); right.setObjectName("RightPanel")
        right_l = QtWidgets.QVBoxLayout(right)
        title = QtWidgets.QLabel("Materials Detail"); title.setObjectName("TitleLabel"); title.setFocusPolicy(QtCore.Qt.NoFocus)
        right_l.addWidget(title)
        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True)
        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(16); self.cards_layout.setContentsMargins(8,8,8,8)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.cards_container)
        right_l.addWidget(self.scroll,1)
        right_l.addWidget(self._hline())

        hb = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_import  = QtWidgets.QPushButton("Import")
        self.btn_saveas  = QtWidgets.QPushButton("Save As")
        self.btn_save    = QtWidgets.QPushButton("Save"); self.btn_save.setDefault(True)
        hb.addStretch(1); hb.addWidget(self.btn_refresh); hb.addWidget(self.btn_import); hb.addWidget(self.btn_saveas); hb.addWidget(self.btn_save)
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
        self.btn_refresh.clicked.connect(self.refresh_from_scene)

        self._refresh_tree()

        # scriptJobs & auto-load binding
        self.setObjectName("MLI_Dialog")
        self._scriptjobs = []
        try:
            self._auto_load_for_current_scene()
            self._scriptjobs.append(cmds.scriptJob(e=["SceneOpened",     self._auto_on_scene_event], p=self.objectName()))
            self._scriptjobs.append(cmds.scriptJob(e=["NewSceneOpened",  self._auto_on_scene_event], p=self.objectName()))
            self._scriptjobs.append(cmds.scriptJob(e=["SceneSaved",      self._autosave_current],     p=self.objectName()))
        except Exception:
            pass

        QtCore.QTimer.singleShot(0, self._apply_initial_sizes)

        apply_theme(self)

   
    def _get_bound_json_path(self):
        try:
            vals = cmds.fileInfo(self._FILEINFO_KEY, q=True) or []
            if vals:
                p = vals[0]
                return p if os.path.isfile(p) else None
        except Exception:
            pass
        return None

    def _bind_json(self, path):
        try:
            if path:
                cmds.fileInfo(self._FILEINFO_KEY, path)
                self._json_path = path
        except Exception:
            pass

    def _default_scene_side_json(self):
        return _scene_json_path()

    def _load_from_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.lib_data = json.load(f)
            for mats in self.lib_data.values():
                for m in mats:
                    m.setdefault("assets", []); m.setdefault("thumb_b64","")
            self._refresh_tree()
            root = self.tree.topLevelItem(0)
            if root:
                self.tree.setCurrentItem(root)
                self._rebuild_cards_for_all()
        except Exception as e:
            self._warn("Load failed", str(e))

    def _auto_load_for_current_scene(self):
        bound = self._get_bound_json_path()
        if bound and os.path.isfile(bound):
            self._json_path = bound
            self._load_from_path(bound)
            return
        side = self._default_scene_side_json()
        if side and os.path.isfile(side):
            self._json_path = side
            self._load_from_path(side)
            self._bind_json(side)
            return
        self.lib_data = {}
        self._refresh_tree()
        self._rebuild_cards([])

    def _auto_on_scene_event(self, *args):
        self._auto_load_for_current_scene()
        self.refresh_from_scene()

    def _autosave_current(self, *args):
        self._gather_graphs()
        dst = self._get_bound_json_path() or self._default_scene_side_json()
        if not dst:
            return
        try:
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(self.lib_data, f, ensure_ascii=False, indent=2)
            self._bind_json(dst)
        except Exception:
            pass

 
    def _warn(self, title, msg):
        QtWidgets.QMessageBox.warning(self, title, msg)

    def _apply_initial_sizes(self):
        self.splitter.setSizes([LEFT_PANEL_W, max(300, self.width()-LEFT_PANEL_W)])
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

    def _merge_scene_assets(self, m: dict):
        name = m.get("name","")
        if not name or not hasattr(mu, "objects_using_material"): return
        try: scene_objs = mu.objects_using_material(name, True) or []
        except Exception: scene_objs = []
        if scene_objs:
            merged = set(m.get("assets", []) or []); merged.update(scene_objs)
            m["assets"] = sorted(merged)

    def _focus_card_by_id(self, mat_id: int):
        card = self._card_index.get(mat_id)
        if not card: return
        def _do():
            y_top = card.mapTo(self.cards_container, QtCore.QPoint(0, 0)).y()
            sb = self.scroll.verticalScrollBar()
            TOP_PAD = 6
            sb.setValue(max(0, y_top - TOP_PAD))
            card.setFocus(QtCore.Qt.OtherFocusReason)
        QtCore.QTimer.singleShot(0, _do)

    def showEvent(self, e):
        super().showEvent(e)
        if not self._sized_once:
            self.resize(DEFAULT_SIZE); self._sized_once = True

    def _on_card_thumb_changed(self, mat_ref: dict):
        
        try:
            item = self._tree_index.get(id(mat_ref))
            if not item:
                return
            item.setIcon(0, self._material_icon(mat_ref))
            
            self.tree.viewport().update()
        except Exception:
            pass

    # tree build
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
            self._merge_scene_assets(m)
            card = MaterialCard(m, self.cards_container)
            card.nameEditedLive.connect(self._card_name_live)
            card.nameCommitted.connect(self._card_name_commit)
            card.requestEdit.connect(self._card_edit_material)
            card.requestSelect.connect(self._card_select_objs)
            card.requestLink.connect(self._card_link_material)
            card.thumbChanged.connect(lambda mm, self=self: self._on_card_thumb_changed(mm))

            self.cards_layout.addWidget(card)
            self._card_index[id(m)] = card

        self.cards_layout.addStretch()

    # -------- Drag/Drop backend --------
    def _move_material_between_folders(self, mat_id: int, src_folder: str, dest_folder: str, insert_index=None) -> bool:
        
        if not src_folder or not dest_folder: return False
        src_list = self.lib_data.get(src_folder, [])
        if not src_list: return False

        ref, src_idx = None, -1
        for i, m in enumerate(src_list):
            if id(m) == mat_id:
                ref, src_idx = m, i; break
        if ref is None: return False

        
        src_list.pop(src_idx)

        
        dest_list = self.lib_data.setdefault(dest_folder, [])
        if insert_index is None or insert_index < 0 or insert_index > len(dest_list):
            dest_list.append(ref)
        else:
            dest_list.insert(insert_index, ref)

        
        self._refresh_tree()
        
        self._rebuild_cards_for_folder(dest_folder)
        it = self._tree_index.get(id(ref))
        if it:
            self.tree.setCurrentItem(it)
            self._focus_card_by_id(id(ref))
        return True

    # card callbacks
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
            self._merge_scene_assets(mat_ref)
            if card: card.refresh()
        else:
            item = self._tree_index.get(id(mat_ref));  card = self._card_index.get(id(mat_ref))
            if item: item.setText(0, old)
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

    def _remove_from_other_assets(self, objects, keep_material):
        if not objects: return
        objs = set(objects)
        for folder, mats in self.lib_data.items():
            for m in mats:
                if m.get("name") == keep_material: continue
                if not m.get("assets"): continue
                new_list = [x for x in m["assets"] if x not in objs]
                if len(new_list) != len(m["assets"]):
                    m["assets"] = new_list
                    card = self._card_index.get(id(m))
                    if card: card.refresh()

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
        self._remove_from_other_assets(affected, keep_material=name)
        assets = set(mat_ref.setdefault("assets", [])); assets.update(affected)
        mat_ref["assets"] = sorted(assets)
        card = self._card_index.get(id(mat_ref))
        if card: card.refresh()

    # actions
    def on_create_folder(self):
        name = f"Folder {self.folder_counter}"
        while name in self.lib_data:
            self.folder_counter += 1; name = f"Folder {self.folder_counter}"
        self.lib_data[name] = []; self.folder_counter += 1
        self._refresh_tree()

    def on_add_material(self):
        sel_name = mu.get_selected_material_name() if hasattr(mu, "get_selected_material_name") else ""
        if not sel_name:
            self._warn("Add Material", "Please select a material in Hypershade first."); return

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
            mats = self.lib_data.get(folder, []); mat_id = item.data(0, self.MAT_ID_ROLE)
            ref = next((m for m in mats if id(m) == mat_id), None)
            if not ref: return
            real_old = ref.get("name","")
            if self._rename_strict(real_old, new):
                ref["name"] = new
                item.setText(0, new)
                card = self._card_index.get(mat_id)
                if card: card.set_name(new)
                self._merge_scene_assets(ref)
                if card: card.refresh()
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

    def _write_json(self, path):
        self._gather_graphs()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.lib_data, f, ensure_ascii=False, indent=2)

    def on_save(self):
        if not self._json_path:
            side = self._default_scene_side_json()
            if side:
                try:
                    self._write_json(side)
                    self._bind_json(side)
                    QtWidgets.QMessageBox.information(self, "Save", f"Saved: {side}")
                    return
                except Exception as e:
                    self._warn("Save failed", str(e))
            self.on_save_as(); return
        try:
            self._write_json(self._json_path)
            self._bind_json(self._json_path)
            QtWidgets.QMessageBox.information(self, "Save", f"Saved: {self._json_path}")
        except Exception as e:
            self._warn("Save failed", str(e))

    def on_save_as(self):
        default_dir = os.path.dirname(cmds.file(q=True, sn=True)) if cmds and cmds.file(q=True, sn=True) else os.path.expanduser("~")
        default_path = os.path.join(default_dir, "material_library.json")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Library As", default_path, "Material Library (*.json)")
        if not path: return
        try:
            self._write_json(path)
            self._bind_json(path)
            QtWidgets.QMessageBox.information(self, "Save As", f"Saved: {path}")
        except Exception as e:
            self._warn("Save As failed", str(e))

    def on_import(self):
        start_dir = self._default_scene_side_json() or os.path.expanduser("~")
        if isinstance(start_dir, str) and start_dir.endswith(".json"):
            start_dir = os.path.dirname(start_dir)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Library", start_dir or os.path.expanduser("~"), "Material Library (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                incoming = json.load(f)
        except Exception as e:
            self._warn("Import failed", str(e)); return

        folders = list(self.lib_data.keys())
        if not folders:
            dest_folder, ok = QtWidgets.QInputDialog.getText(self, "Destination Folder", "Folder name:", text="Imported")
            if not ok or not dest_folder: return
            self.lib_data[dest_folder] = []
        else:
            dest_folder, ok = QtWidgets.QInputDialog.getItem(self, "Destination Folder", "Choose a folder:", folders, 0, False)
            if not ok: return

        mats_in = []
        for k, v in (incoming or {}).items():
            if isinstance(v, list): mats_in.extend(v)

        for m in mats_in:
            snap = (m.get("graph") or {})
            if snap and hasattr(mu, "rebuild_material_network"):
                try:
                    real_name = mu.rebuild_material_network(snap, new_material_name=m.get("name",""))
                    if real_name: m["name"] = real_name
                except Exception:
                    pass
            self._merge_scene_assets(m)
            self.lib_data.setdefault(dest_folder, []).append(m)

        self._refresh_tree()
        root = self.tree.topLevelItem(0)
        for i in range(root.childCount()):
            ch = root.child(i)
            if ch.text(0) == dest_folder:
                self.tree.setCurrentItem(ch); break
        self._rebuild_cards_for_folder(dest_folder)

   
    def refresh_from_scene(self):
        changed = False
        for mats in self.lib_data.values():
            for m in mats:
                before = list(m.get("assets", []))
                self._merge_scene_assets(m)
                after = m.get("assets", [])
                if before != after:
                    changed = True
                    card = self._card_index.get(id(m))
                    if card: card.refresh()
        if changed:
            self._refresh_tree()

    def _try_load(self):
        if not self._json_path or not os.path.isfile(self._json_path): return
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                self.lib_data = json.load(f)
            for mats in self.lib_data.values():
                for m in mats:
                    m.setdefault("assets", []); m.setdefault("thumb_b64","")
        except Exception as e:
            self._warn("Load failed", str(e))
        max_f = 0
        for name in self.lib_data.keys():
            mf = re.match(r'^Folder\s+(\d+)$', name)
            if mf: max_f = max(max_f, int(mf.group(1)))
        self.folder_counter = max(1, max_f+1)
        self._refresh_tree()

    def closeEvent(self, e):
        try:
            for j in getattr(self, "_scriptjobs", []):
                try: cmds.scriptJob(kill=j, force=True)
                except Exception: pass
        except Exception:
            pass
        super().closeEvent(e)


def run():
    global ui
    try:
        ui.close()
    except Exception:
        pass
    ptr = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    ui = MaterialLibraryDialog(parent=ptr)
    ui.show()
