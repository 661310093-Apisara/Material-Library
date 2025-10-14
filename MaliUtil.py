# -*- coding: utf-8 -*-
# MaliUtil.py : Utilities for Material Library (Maya)

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except Exception:
    from PySide2 import QtCore, QtGui, QtWidgets

import os, base64, re

# maya
try:
    import maya.cmds as cmds
except Exception:
    cmds = None


# =============================================================================
# Basic material / selection helpers
# =============================================================================

def selected_materials():
    if not cmds: return []
    mats = cmds.ls(sl=True, materials=True) or []
    out, seen = [], set()
    for m in mats:
        if m not in seen:
            seen.add(m); out.append(m)
    return out

def get_selected_material_name():
    if not cmds: return ""
    mats = selected_materials()
    if mats: return mats[0]

    shader_types = {
        "lambert","blinn","phong","phongE","surfaceShader",
        "aiStandardSurface","aiStandardHair","aiStandardHair2",
        "aiToon","aiCarPaint","aiSkin"
    }
    for n in cmds.ls(sl=True) or []:
        try:
            if cmds.nodeType(n) in shader_types:
                return n
        except Exception:
            pass
    return ""

def get_shading_engine(material):
    if not cmds or not material or not cmds.objExists(material): return None
    ses = cmds.listConnections(material, type="shadingEngine") or []
    return ses[0] if ses else None

def objects_using_material(material, unique_parents=True):
    if not cmds: return []
    se = get_shading_engine(material)
    if not se: return []
    members = cmds.sets(se, q=True) or []
    if not unique_parents: return members
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
    if not cmds: return []
    objs = objects_using_material(material, unique_parents=True)
    cmds.select(objs or [], r=True)
    return objs

def link_material_to_objects(material, objects=None):
    if not cmds: return []
    if not material or not cmds.objExists(material):
        raise RuntimeError("Material not found: %s" % material)
    if objects is None:
        objects = cmds.ls(sl=True, dag=False, transforms=True) or []
    if not objects: return []
    cmds.select(objects, r=True)
    cmds.hyperShade(assign=material)
    cmds.select(clear=True)
    return list(objects)

def open_hypershade(material=None):
    if not cmds: return
    cmds.HypershadeWindow()
    if material and cmds.objExists(material):
        try: cmds.select(material, r=True)
        except Exception: pass

def create_material(name, shader="lambert"):
    if not cmds: return "", ""
    if not name: raise RuntimeError("Material name is empty")
    if cmds.objExists(name):
        mat = name
    else:
        mat = cmds.shadingNode(shader, asShader=True, name=name)
    se = get_shading_engine(mat)
    if not se:
        se = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name+"SG")
        try: cmds.connectAttr(mat+".outColor", se+".surfaceShader", f=True)
        except Exception: pass
    return mat, se

def rename_material(old_name, new_name):
    if not cmds: return new_name
    if not cmds.objExists(old_name):
        raise RuntimeError("Material not found: %s" % old_name)
    if old_name == new_name: return new_name
    return cmds.rename(old_name, new_name)

# =============================================================================
# Name normalization & viewport selection
# =============================================================================

def _to_transform(name):
    if not cmds or not name or not cmds.objExists(name): return None
    if cmds.nodeType(name) == "transform": return name
    parent = (cmds.listRelatives(name, p=True) or [None])[0]
    return parent or name

def normalize_objects(names):
    seen, out = set(), []
    for n in names or []:
        t = _to_transform(n)
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out

def select_objects_by_names(names):
    if not cmds: return []
    objs = normalize_objects(names)
    cmds.select(objs or [], r=True)
    return objs

# =============================================================================
# Image helpers
# =============================================================================

def qicon_from_b64(b64str):
    if not b64str: return QtGui.QIcon()
    try:
        ba = QtCore.QByteArray.fromBase64(QtCore.QByteArray(b64str.encode("utf-8")))
        pm = QtGui.QPixmap(); pm.loadFromData(ba)
        return QtGui.QIcon(pm) if not pm.isNull() else QtGui.QIcon()
    except Exception:
        return QtGui.QIcon()

class ImagePreview(QtWidgets.QLabel):
    """พรีวิวภาพ 'มุมโค้ง' พร้อมกรอบ วาดเองทั้งหมด"""
    def __init__(self, w=200, h=160, parent=None, radius=90):
        super().__init__(parent)
        self.setMinimumSize(w, h)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("background: transparent;")  # เราจะวาด background เอง
        self._b64 = ""
        self._pm  = QtGui.QPixmap()
        self._radius = int(radius)
        self._bg_col = QtGui.QColor("#2b2b2b")
        self._border_col = QtGui.QColor("#555555")

    def set_image_b64(self, b64str):
        self._b64 = b64str or ""
        self._pm = QtGui.QPixmap()
        if self._b64:
            try:
                ba = QtCore.QByteArray.fromBase64(QtCore.QByteArray(self._b64.encode("utf-8")))
                self._pm.loadFromData(ba)
            except Exception:
                pass
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)

        # สร้าง path มุมโค้ง
        path = QtGui.QPainterPath()
        r = float(self._radius)
        path.addRoundedRect(QtCore.QRectF(rect), r, r)

        # พื้นหลัง
        p.fillPath(path, self._bg_col)

        # วาดรูป (clip ให้เป็นมุมโค้ง)
        if not self._pm.isNull():
            p.save()
            p.setClipPath(path)
            scaled = self._pm.scaled(rect.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            x = rect.x() + (rect.width()  - scaled.width())  * 0.5
            y = rect.y() + (rect.height() - scaled.height()) * 0.5
            p.drawPixmap(int(x), int(y), scaled)
            p.restore()
        else:
            p.setPen(QtGui.QPen(QtGui.QColor("#aaaaaa")))
            p.drawText(rect, QtCore.Qt.AlignCenter, "No Preview")

        # เส้นขอบ
        pen = QtGui.QPen(self._border_col)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(path)
        p.end()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.update()

def pick_image_to_base64(parent=None):
    filters = "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, "Choose Image", "", filters)
    if not path: return "", ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return b64, path

# =============================================================================
# Whole material graph snapshot (serialize/deserialize)
# =============================================================================

_SKIP_ATTR_PATTERNS = (
    r'^message$', r'^isHistoricallyInteresting$', r'^caching$', r'^blackBox$',
    r'^nodeState$', r'^binMembership$', r'^uuid$', r'^hasBrush$', r'^drawOverride\..*',
)
def _skip_attr(attr_name: str) -> bool:
    return any(re.match(p, attr_name) for p in _SKIP_ATTR_PATTERNS)

def _safe_list(value):
    if isinstance(value, (list, tuple)): return list(value)
    return value

def _all_upstream_nodes(mat):
    hist = cmds.listHistory(mat, pruneDagObjects=True, allConnections=True, future=False) or []
    out, seen = [], set()
    for n in hist + [mat]:
        if n in seen: continue
        seen.add(n)
        try:
            if cmds.objectType(n, isAType="dagNode"):
                continue
        except Exception:
            pass
        out.append(n)
    return out

def _node_attrs_dump(node):
    data = {}
    atts = cmds.listAttr(node, settable=True) or []
    for a in atts:
        if _skip_attr(a): continue
        plug = f"{node}.{a}"
        try:
            if cmds.connectionInfo(plug, isDestination=True):
                continue
            val = cmds.getAttr(plug)
        except Exception:
            continue
        payload = {"name": a, "value": _safe_list(val), "type": None}
        try:
            payload["type"] = cmds.getAttr(plug, type=True)
        except Exception:
            pass
        if payload["type"] in ("double3","float3") and isinstance(payload["value"], list):
            if len(payload["value"])==1 and isinstance(payload["value"][0], (list,tuple)):
                payload["value"] = list(payload["value"][0])
        data[a] = payload
    return data

def _node_connections_dump(nodes_set):
    conns = set()
    for n in nodes_set:
        try:
            plugs = cmds.listConnections(n, c=True, p=True, s=True, d=True) or []
        except Exception:
            continue
        for i in range(0, len(plugs), 2):
            dstPlug, srcPlug = plugs[i], plugs[i+1]
            dstNode = dstPlug.split('.')[0]
            srcNode = srcPlug.split('.')[0]
            if dstNode in nodes_set and srcNode in nodes_set:
                conns.add((srcPlug, dstPlug))
    return [{"src": s, "dst": d} for (s, d) in sorted(conns)]

def _collect_file_embeds(node):
    info = {}
    try:
        if cmds.nodeType(node) not in ("file",): return {}
        path = cmds.getAttr(node + ".fileTextureName") or ""
        info["path"] = path
        try:
            cs = cmds.getAttr(node + ".colorSpace"); info["colorSpace"] = cs
        except Exception:
            pass
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                info["b64"] = base64.b64encode(f.read()).decode("utf-8")
            info["name"] = os.path.basename(path)
    except Exception:
        pass
    return info

def capture_material_network(material):
    if not cmds or not cmds.objExists(material): return {}
    nodes = _all_upstream_nodes(material)
    nodes_set = set(nodes)
    out_nodes = {}
    for n in nodes:
        try: ntype = cmds.nodeType(n)
        except Exception: continue
        spec = {"type": ntype, "attrs": _node_attrs_dump(n)}
        if ntype == "file":
            spec["embed"] = _collect_file_embeds(n)
        out_nodes[n] = spec
    connections = _node_connections_dump(nodes_set)
    return {"material": material, "nodes": out_nodes, "connections": connections}

def _unique_name_like(base):
    i, name = 2, base
    while cmds.objExists(name):
        name = f"{base}_{i}"; i += 1
    return name

def _ensure_sourceimages():
    try:
        root = cmds.workspace(q=True, rd=True)
        if not root: raise RuntimeError()
    except Exception:
        root = os.path.expanduser("~/Documents/maya/")
    src = os.path.join(root, "sourceimages")
    os.makedirs(src, exist_ok=True)
    return src

def _write_embed_to_disk(embed):
    if not embed or not embed.get("b64"): return None
    dst_dir = _ensure_sourceimages()
    fname = embed.get("name") or "tex.png"
    base, ext = os.path.splitext(os.path.join(dst_dir, fname))
    fp, i = base+ext, 1
    while os.path.exists(fp):
        i += 1; fp = f"{base}_{i}{ext}"
    with open(fp, "wb") as f:
        f.write(base64.b64decode(embed["b64"]))
    return fp

def rebuild_material_network(snapshot: dict, new_material_name: str = None, namespace: str = "MLI"):
    if not cmds or not snapshot: return ""
    nodes = snapshot.get("nodes") or {}
    conns = snapshot.get("connections") or []
    mat_old = snapshot.get("material") or ""

    rename_map = {}
    for old, spec in nodes.items():
        ntype = spec.get("type")
        if old == mat_old and new_material_name:
            new = _unique_name_like(new_material_name)
        else:
            base = f"{namespace}_{old}" if cmds.objExists(old) else old
            new = _unique_name_like(base)
        try:
            created = cmds.shadingNode(ntype, asShader=True, name=new) if ntype.endswith("Surface") \
                      else cmds.createNode(ntype, name=new)
        except Exception:
            try: created = cmds.createNode(ntype, name=new)
            except Exception: continue
        rename_map[old] = created

    # set attrs
    for old, spec in nodes.items():
        new = rename_map.get(old)
        if not new: continue
        for a, payload in (spec.get("attrs") or {}).items():
            plug = f"{new}.{payload['name']}"
            val, atype = payload.get("value"), payload.get("type")
            if val is None: continue
            try:
                if atype in ("string","cstring"):
                    cmds.setAttr(plug, val, type="string")
                elif atype in ("double3","float3"):
                    if isinstance(val, (list,tuple)) and len(val)==3:
                        cmds.setAttr(plug, *val, type=atype)
                else:
                    cmds.setAttr(plug, val)
            except Exception:
                pass
        # restore file node texture
        if spec.get("type") == "file":
            emb = spec.get("embed") or {}
            path = None
            if emb.get("b64"):
                path = _write_embed_to_disk(emb)
            elif emb.get("path"):
                path = emb["path"]
            if path:
                try: cmds.setAttr(new + ".fileTextureName", path, type="string")
                except Exception: pass
            if emb.get("colorSpace"):
                try: cmds.setAttr(new + ".colorSpace", emb["colorSpace"], type="string")
                except Exception: pass

    # connect
    for c in conns:
        s_old, d_old = c.get("src"), c.get("dst")
        if not s_old or not d_old: continue
        s_node, s_attr = s_old.split('.',1)
        d_node, d_attr = d_old.split('.',1)
        s_new, d_new = rename_map.get(s_node), rename_map.get(d_node)
        if not s_new or not d_new: continue
        try: cmds.connectAttr(f"{s_new}.{s_attr}", f"{d_new}.{d_attr}", f=True)
        except Exception: pass

    # ensure SG
    mat_new = rename_map.get(mat_old)
    if mat_new:
        se = get_shading_engine(mat_new)
        if not se:
            se = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{mat_new}SG")
            try: cmds.connectAttr(mat_new + ".outColor", se + ".surfaceShader", f=True)
            except Exception: pass

    return mat_new or ""
