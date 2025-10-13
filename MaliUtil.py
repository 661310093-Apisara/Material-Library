# -*- coding: utf-8 -*-
# MaliUtil.py : Utilities for Material Library (Maya)

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except Exception:
    from PySide2 import QtCore, QtGui, QtWidgets

import base64
import maya.cmds as cmds
import maya.mel as mel


# ---------------------------
# Material / Selection helpers
# ---------------------------

def selected_materials():
    """Return currently selected material nodes (unique, keep order)."""
    mats = cmds.ls(sl=True, materials=True) or []
    out, seen = [], set()
    for m in mats:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def get_selected_material_name():
    """Return one selected material name (also works when selection is a shader node)."""
    mats = selected_materials()
    if mats:
        return mats[0]

    shader_types = {
        "lambert", "blinn", "phong", "phongE", "surfaceShader",
        "aiStandardSurface", "aiStandardHair", "aiStandardHair2",
        "aiToon", "aiCarPaint", "aiSkin"
    }
    for n in cmds.ls(sl=True) or []:
        try:
            if cmds.nodeType(n) in shader_types:
                return n
        except Exception:
            pass
    return ""


def get_shading_engine(material):
    if not material or not cmds.objExists(material):
        return None
    ses = cmds.listConnections(material, type="shadingEngine") or []
    return ses[0] if ses else None


def objects_using_material(material, unique_parents=True):
    se = get_shading_engine(material)
    if not se:
        return []
    members = cmds.sets(se, q=True) or []
    if not unique_parents:
        return members
    result = []
    for m in members:
        if cmds.nodeType(m) == "transform":
            t = m
        else:
            t = (cmds.listRelatives(m, p=True) or [None])[0]
        if t and t not in result:
            result.append(t)
    return result


def select_objects_from_material(material):
    objs = objects_using_material(material, unique_parents=True)
    if objs:
        cmds.select(objs, r=True)
    else:
        cmds.select(clear=True)
    return objs


def link_material_to_objects(material, objects=None):
    """Assign material to objects (or current selection). Return affected object names."""
    if not material or not cmds.objExists(material):
        raise RuntimeError("Material not found: %s" % material)

    if objects is None:
        # transforms only
        objects = cmds.ls(sl=True, dag=False, transforms=True) or []

    if not objects:
        return []

    cmds.select(objects, r=True)
    cmds.hyperShade(assign=material)
    cmds.select(clear=True)
    return list(objects)


def open_hypershade(material=None):
    """
    เปิด Hypershade และกราฟ material แบบที่รองรับ Maya ใหม่ ๆ
    ใช้คำสั่ง 'hyperShade' โดยตรง (ไม่พึ่ง hyperShadePanelGraphCommand/hyperShadePanel -e)
    """
    try:
        cmds.HypershadeWindow()
    except Exception:
        pass

    if material and cmds.objExists(material):
        try:
            cmds.select(material, r=True)
        except Exception:
            pass
        # เคลียร์ work area และกราฟแสดง material
        try:
            mel.eval('hyperShade -clearWorkArea;')
        except Exception:
            pass
        try:
            mel.eval('hyperShade -graphMaterials "{0}";'.format(material))
        except Exception:
            pass
        try:
            mel.eval('hyperShade -rearrangeGraph;')
        except Exception:
            pass
        try:
            mel.eval('hyperShade -frameAll;')
        except Exception:
            pass
    return True


def create_material(name, shader="lambert"):
    if not name:
        raise RuntimeError("Material name is empty")
    if cmds.objExists(name):
        mat = name
    else:
        mat = cmds.shadingNode(shader, asShader=True, name=name)
    se = get_shading_engine(mat)
    if not se:
        se = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
        try:
            cmds.connectAttr(mat + ".outColor", se + ".surfaceShader", f=True)
        except Exception:
            pass
    return mat, se


def rename_material(old_name, new_name):
    if not cmds.objExists(old_name):
        raise RuntimeError("Material not found: %s" % old_name)
    if old_name == new_name:
        return new_name
    return cmds.rename(old_name, new_name)


# ---------------------------
# Name normalization & select
# ---------------------------

def _to_transform(name):
    """Return transform name (if shape is given, return its parent)."""
    if not name or not cmds.objExists(name):
        return None
    if cmds.nodeType(name) == "transform":
        return name
    parent = (cmds.listRelatives(name, p=True) or [None])[0]
    return parent or name


def normalize_objects(names):
    """Convert names (shapes/transforms) into unique transform names, keep order."""
    seen = set()
    out = []
    for n in names or []:
        t = _to_transform(n)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def select_objects_by_names(names):
    """Select objects in viewport by names (normalized to transforms)."""
    objs = normalize_objects(names)
    if objs:
        cmds.select(objs, r=True)
    else:
        cmds.select(clear=True)
    return objs


# ---------------------------
# Image preview helpers (optional)
# ---------------------------

def qicon_from_b64(b64str):
    """Create QIcon from base64 png/jpg string."""
    if not b64str:
        return QtGui.QIcon()
    try:
        ba = QtCore.QByteArray.fromBase64(QtCore.QByteArray(b64str.encode("utf-8")))
        pm = QtGui.QPixmap()
        pm.loadFromData(ba)
        return QtGui.QIcon(pm) if not pm.isNull() else QtGui.QIcon()
    except Exception:
        return QtGui.QIcon()


class ImagePreview(QtWidgets.QLabel):
    """Simple QLabel based image preview with base64 setter."""
    def __init__(self, w=200, h=160, parent=None):
        super().__init__(parent)
        self.setMinimumSize(w, h)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("background:#2b2b2b;border:1px solid #555;color:#aaa;")
        self._b64 = ""

    def set_image_b64(self, b64str):
        self._b64 = b64str or ""
        if not self._b64:
            self.setText("No Preview")
            self.setPixmap(QtGui.QPixmap())
            return
        try:
            ba = QtCore.QByteArray.fromBase64(QtCore.QByteArray(self._b64.encode("utf-8")))
            pm = QtGui.QPixmap()
            pm.loadFromData(ba)
            if not pm.isNull():
                self.setPixmap(pm.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            else:
                self.setText("No Preview")
        except Exception:
            self.setText("No Preview")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        pm = self.pixmap()
        if pm and not pm.isNull():
            self.setPixmap(pm.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))


def pick_image_to_base64(parent=None):
    """Open file dialog to pick an image and return (b64, path)."""
    filters = "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, "Choose Image", "", filters)
    if not path:
        return "", ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return b64, path
