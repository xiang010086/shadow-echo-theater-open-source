"""Build the screw-free, segmented stage. Units: mm. No printer is contacted.

Run with Python 3.13 and cadquery/trimesh/numpy/matplotlib installed.
The archived model is read as a reference; its export/delete code is never run.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

import cadquery as cq
import numpy as np
import trimesh
from OCP.gp import gp_Trsf

ROOT = Path(__file__).resolve().parents[1]
HARDWARE = ROOT.parent
ARCHIVE = HARDWARE / '03_原始压缩包' / 'Kimi_Agent_全息盒子设计.zip'
GAP = 0.24
TRAY_TOP, TRAY_T = 55.0, 6.0
TRAY_BASE = TRAY_TOP - TRAY_T
RIB_BOTTOM = TRAY_BASE - 10.0
SUPPORTS = [(x, y) for x in (-150.0, 55.0, 150.0) for y in (125.0, 300.0)]
LIGHT = dict(length=50.0, width=18.0, web=3.0, pin=8.0, height=2.0, depth=2.3)
HEAVY = dict(length=60.0, width=24.0, web=4.0, pin=12.0, height=3.0, depth=3.3)
PIN_CLEARANCE = 0.30  # per side; verify on coupons before production
PIN_OFFSET = 15.0


def box(dx, dy, dz, center):
    return cq.Workplane('XY').box(dx, dy, dz).translate(center).val()


def union(shapes):
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.clean()


def matrix(origin=(0, 0, 0), u=(1, 0, 0), v=(0, 1, 0), n=(0, 0, 1)):
    transform = np.eye(4)
    transform[:3, :3] = np.array([u, v, n]).T
    transform[:3, 3] = origin
    assert np.isclose(np.linalg.det(transform[:3, :3]), 1)
    return transform


def transform(shape, mat):
    rigid = gp_Trsf()
    rigid.SetValues(*np.asarray(mat, dtype=float)[:3, :4].ravel().tolist())
    return shape.transformShape(cq.Matrix(rigid))


def reference_namespace():
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    assert digest == '1b4d1dd801f16d180147bf28dacc0e40d9b598fa4754a54f9a5fee7c0d1c2a27'
    with zipfile.ZipFile(ARCHIVE) as archive:
        source = archive.read('model/build_holographic_box.py').decode('utf-8-sig')
    # Only known geometry definitions and constants, stopping before any exports.
    prefix = source.split('\nbottom = make_bottom()')[0]
    parsed = ast.parse(prefix)
    definitions = []
    for node in parsed.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assert)):
            definitions.append(node)
        elif isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if 'OUT' not in names:
                definitions.append(node)
    namespace = {}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(ARCHIVE), 'exec'), namespace)
    return namespace, digest


def bridge_geometry(config):
    pieces = [box(config['length'], config['width'], config['web'],
                  (0, 0, -config['web'] / 2))]
    for x in (-PIN_OFFSET, PIN_OFFSET):
        # Rounded upper edges are not required for geometry; generous clearance
        # and the supplied fit coupons determine the practical assembly fit.
        pieces.append(box(config['pin'], config['pin'], config['height'],
                          (x, 0, config['height'] / 2)))
    return union(pieces)


def sockets(config):
    return [box(config['pin'] + 2 * PIN_CLEARANCE,
                config['pin'] + 2 * PIN_CLEARANCE, config['depth'] + .02,
                (x, 0, config['depth'] / 2 - .01))
            for x in (-PIN_OFFSET, PIN_OFFSET)]


def seam_positions(umin, umax, vmin, vmax, usplit, vsplit):
    positions = []
    for low, high in ((vmin, vsplit), (vsplit, vmax)):
        for value in (low + 46, high - 46):
            positions.append((usplit, value, 0))
    for low, high in ((umin, usplit), (usplit, umax)):
        for value in (low + 46, high - 46):
            positions.append((value, vsplit, 90))
    return positions


def local_placement(u, v, angle):
    theta = math.radians(angle)
    return matrix((u, v, 0), (math.cos(theta), math.sin(theta), 0),
                  (-math.sin(theta), math.cos(theta), 0), (0, 0, 1))


def mesh_from_shape(shape):
    vertices, faces = shape.tessellate(.10, .12)
    return trimesh.Trimesh(vertices=np.array([v.toTuple() for v in vertices]),
                           faces=np.asarray(faces), process=True)


def write_3mf(path, meshes):
    ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    ET.register_namespace('', ns)
    model = ET.Element(f'{{{ns}}}model', unit='millimeter',
                       attrib={'{http://www.w3.org/XML/1998/namespace}lang': 'en-US'})
    metadata = ET.SubElement(model, f'{{{ns}}}metadata', name='Title')
    metadata.text = path.stem + ' | geometry only, not sliced'
    resources = ET.SubElement(model, f'{{{ns}}}resources')
    build = ET.SubElement(model, f'{{{ns}}}build')
    for index, (name, mesh) in enumerate(meshes, 1):
        obj = ET.SubElement(resources, f'{{{ns}}}object', id=str(index), type='model', name=name)
        data = ET.SubElement(obj, f'{{{ns}}}mesh')
        verts = ET.SubElement(data, f'{{{ns}}}vertices')
        for vertex in mesh.vertices:
            ET.SubElement(verts, f'{{{ns}}}vertex', **dict(zip(('x', 'y', 'z'),
                          (f'{value:.6f}' for value in vertex))))
        triangles = ET.SubElement(data, f'{{{ns}}}triangles')
        for face in mesh.faces:
            ET.SubElement(triangles, f'{{{ns}}}triangle', **dict(zip(('v1', 'v2', 'v3'),
                          (str(int(value)) for value in face))))
        ET.SubElement(build, f'{{{ns}}}item', objectid=str(index))
    relationships = ('<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    types = ('<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        '</Types>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', types)
        archive.writestr('_rels/.rels', relationships)
        archive.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))


def build():
    for folder in ('stl_print', 'plates_3mf', 'review'):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    ns, digest = reference_namespace()
    parts, bridge_instances, groups = {}, [], []

    def group(name, world_shape, frame, ranges, splits, heavy=False, print_flip=False,
              custom_positions=None):
        config = HEAVY if heavy else LIGHT
        local = transform(world_shape, np.linalg.inv(frame))
        umin, umax, vmin, vmax = ranges
        usplit, vsplit = splits
        placements = (custom_positions if custom_positions is not None
                      else seam_positions(*ranges, *splits))
        for u, v, angle in placements:
            placement = local_placement(u, v, angle)
            for socket in sockets(config):
                local = local.cut(transform(socket, placement))
            bridge_instances.append((name, 'heavy' if heavy else 'light',
                                     frame @ placement))
        local = local.clean()
        groups.append(dict(name=name, ranges=ranges, splits=splits, bridges=len(placements)))
        for iu, (a, b) in enumerate(((umin, usplit - GAP / 2), (usplit + GAP / 2, umax)), 1):
            for iv, (c, d) in enumerate(((vmin, vsplit - GAP / 2), (vsplit + GAP / 2, vmax)), 1):
                piece = local.intersect(box(b - a, d - c, 1000, ((a + b) / 2, (c + d) / 2, 250))).clean()
                key = f'{name}_{iu}{iv}'
                parts[key] = dict(shape=transform(piece, frame), local=piece,
                                  flip=print_flip, kind=name)

    # Six integral pedestals land directly on the existing 8 mm base.
    bottom = ns['make_bottom']()
    bottom = union([bottom] + [box(24, 24, RIB_BOTTOM - 8,
                    (x, y, (RIB_BOTTOM + 8) / 2)) for x, y in SUPPORTS])
    group('B_base', bottom, matrix(), (-220, 220, 0, 350), (0, 175), heavy=True)

    # Side rails and tray guides remain integral with each side tile.
    for sign, name in ((-1, 'L_side'), (1, 'R_side')):
        side = ns['make_side'](sign)
        side = side.cut(box(1000, 1000, 100, (0, 175, 406)))  # remove old top tabs
        # Replace the 3.4 mm tray groove with a 6.6 mm groove below Z=55.
        # Extending the cut to the inner wall opens it even beside the port window.
        side = side.cut(box(2.4, 342.4, TRAY_T + .6,
                            (sign * 217.0, 170.8, TRAY_BASE + TRAY_T / 2))).clean()
        frame = (matrix((-220, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)) if sign < 0
                 else matrix((220, 350, 0), (0, -1, 0), (0, 0, 1), (-1, 0, 0)))
        group(name, side, frame, (0, 350, 4, 356), (175, 180))

    back = ns['make_back']().cut(box(1000, 1000, 100, (0, 175, 406))).clean()
    group('K_back', back, matrix((0, 350, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)),
          (-220, 220, 4, 356), (0, 180))

    # Build connector landing pads before cutting ventilation slots in the tray.
    tray_frame = matrix((0, 0, TRAY_BASE))
    tray_seams = seam_positions(-217.8, 217.8, 8, 342, 0, 175)
    # Move the positive inner bridge away from the longitudinal rib at X=55.
    tray_seams = [(85 if angle == 90 and abs(u - 46) < .01 else u, v, angle)
                  for u, v, angle in tray_seams]
    keepouts = []
    for u, v, angle in tray_seams:
        placement = tray_frame @ local_placement(u, v, angle)
        for x in (-PIN_OFFSET, PIN_OFFSET):
            keepouts.append(transform(box(20, 20, 20, (x, 0, 3)), placement))
    tray = box(435.6, 334, TRAY_T, (0, 175, TRAY_BASE + TRAY_T / 2))
    for y in ns['VENT_CENTERS_Y']:
        slot = box(320, 4, 20, (0, y, 52))
        for pad in keepouts:
            slot = slot.cut(pad)
        tray = tray.cut(slot)
    ribs = [box(6, 334, 10, (x, 175, TRAY_BASE - 5)) for x in (-150, 55, 150)]
    pads = [box(24, 24, 10, (x, y, TRAY_BASE - 5)) for x, y in SUPPORTS]
    tray = union([tray] + ribs + pads)
    group('T_tray', tray, tray_frame, (-217.8, 217.8, 8, 342), (0, 175),
          heavy=True, print_flip=True, custom_positions=tray_seams)

    # Lid: flat roof with a 0.4 mm radial clearance and 12 mm downward skirt.
    lid_z = 356.4
    lid = box(447.2, 357.2, 4, (0, 175, lid_z + 2))
    lid = union([lid,
        box(3.2, 357.2, 12, (-222, 175, lid_z - 6)),
        box(3.2, 357.2, 12, (222, 175, lid_z - 6)),
        box(440.8, 3.2, 12, (0, -2, lid_z - 6)),
        box(440.8, 3.2, 12, (0, 352, lid_z - 6))])
    group('C_lid', lid, matrix((0, 0, lid_z)), (-223.6, 223.6, -3.6, 353.6),
          (0, 175), print_flip=True)

    # A planar front preserves the original baffle height and tongue locations,
    # while avoiding the old 4 mm step that would require broad print supports.
    front = union([box(431.6, 4, 152, (0, 2, 84))] +
                  [box(6, 13.6, 8, (x, 10.8, z))
                   for x in (-204, 204) for z in (35, 100)])
    front_frame = matrix((0, 0, 0), (1, 0, 0), (0, 0, -1), (0, 1, 0))
    front_local = transform(front, np.linalg.inv(front_frame))
    for z in (25, 90, 140):
        placement = local_placement(0, -z, 0)
        for socket in sockets(LIGHT):
            front_local = front_local.cut(transform(socket, placement))
        bridge_instances.append(('F_front', 'light', front_frame @ placement))
    for index, (a, b) in enumerate(((-215.8, -GAP / 2), (GAP / 2, 215.8)), 1):
        piece = front_local.intersect(box(b - a, 200, 100,
                                             ((a + b) / 2, -84, 40))).clean()
        parts[f'F_front_{index}'] = dict(shape=transform(piece, front_frame), local=piece,
                                       flip=False, kind='F_front')

    for sign, name in ((-1, 'S_stop_L'), (1, 'S_stop_R')):
        shape = ns['make_acrylic_stop'](sign)
        # Undo the reference obox's X rotation; this makes the 2 mm face flat.
        orient = np.eye(4)
        angle = math.radians(-135)
        orient[1:3, 1:3] = [[math.cos(angle), -math.sin(angle)],
                            [math.sin(angle), math.cos(angle)]]
        parts[name] = dict(shape=shape, local=transform(shape, orient), flip=False, kind='S_stop')

    # Loose 4 mm feet keep the base level with the heavy underside bridge webs.
    foot = box(24, 24, 4, (0, 0, -2))
    for index, (x, y) in enumerate(SUPPORTS, 1):
        parts[f'P_foot_{index}'] = dict(shape=foot.translate((x, y, 0)),
                                       local=foot, flip=False, kind='P_foot')

    return export(parts, bridge_instances, groups, ns, digest)


def export(parts, bridges, groups, ns, digest):
    scene = trimesh.Scene()
    assembly = cq.Assembly(name='shadow_stage_screw_free_revision')
    world_meshes, print_meshes, records, solids = [], {}, [], {}
    colors = {'B_base': (85, 100, 115), 'L_side': (90, 110, 145),
              'R_side': (90, 110, 145), 'K_back': (100, 125, 155),
              'T_tray': (80, 160, 140), 'C_lid': (190, 155, 90),
              'F_front': (90, 100, 120), 'S_stop': (220, 135, 60), 'P_foot': (110, 110, 110)}
    def add_world(name, shape, color):
        mesh = mesh_from_shape(shape)
        assert shape.isValid() and len(shape.Solids()) == 1, name
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
        mesh.visual.face_colors = list(color) + [255]
        solids[name] = shape
        scene.add_geometry(mesh, node_name=name, geom_name=name)
        world_meshes.append((name, mesh))
        assembly.add(shape, name=name, color=cq.Color(*(v / 255 for v in color)))
        return mesh

    for name, data in parts.items():
        shape, local = data['shape'], data['local']
        mesh = add_world(name, shape, colors[data['kind']])
        local_mesh = mesh_from_shape(local)
        if data['flip']:
            local_mesh.apply_transform(np.diag([1, -1, -1, 1]))
        local_mesh.apply_translation(-local_mesh.bounds[0])
        local_mesh.export(ROOT / 'stl_print' / f'{name}.stl')
        size = local_mesh.extents
        assert max(size[:2]) <= 240 and size[2] <= 256, (name, size)
        assert local_mesh.is_watertight
        print_meshes[name] = local_mesh
        records.append(dict(name=name, kind=data['kind'], quantity=1,
                            size_mm=[round(float(v), 3) for v in size],
                            volume_cm3=round(float(mesh.volume) / 1000, 3),
                            watertight=bool(mesh.is_watertight), cad_valid=bool(shape.isValid())))
        print('export', name, [round(float(v), 2) for v in size], flush=True)

    counts = {kind: sum(1 for _, k, _ in bridges if k == kind) for kind in ('light', 'heavy')}
    for kind, config in (('light', LIGHT), ('heavy', HEAVY)):
        local = bridge_geometry(config)
        mesh = mesh_from_shape(local)
        mesh.apply_translation(-mesh.bounds[0])
        mesh.export(ROOT / 'stl_print' / f'J_{kind}_print_{counts[kind]}.stl')
        print_meshes[f'J_{kind}'] = mesh
        records.append(dict(name=f'J_{kind}', kind='connector', quantity=counts[kind],
                            size_mm=mesh.extents.tolist(), volume_cm3=round(mesh.volume / 1000, 3),
                            watertight=bool(mesh.is_watertight), cad_valid=bool(local.isValid())))
    for index, (parent, kind, placement) in enumerate(bridges, 1):
        add_world(f'J_{index:02}_{parent}', transform(bridge_geometry(HEAVY if kind == 'heavy' else LIGHT),
                                                  placement), (210, 110, 65))

    _, acrylic, screen, _ = ns['make_reference_parts']()
    for name, shape, color in (('REF_acrylic', acrylic, (100, 210, 235, 70)),
                                ('REF_screen_15mm', screen, (50, 50, 55, 255))):
        mesh = mesh_from_shape(shape)
        mesh.visual.face_colors = color
        scene.add_geometry(mesh, geom_name=name, node_name=name)
        assembly.add(shape, name=name, color=cq.Color(*(v / 255 for v in color)))
        solids[name] = shape

    # Broad-phase AABBs followed by independent exact solid intersections.
    intersections = []
    bounds = {}
    for name, shape in solids.items():
        bb = shape.BoundingBox()
        bounds[name] = (np.array([bb.xmin, bb.ymin, bb.zmin]),
                        np.array([bb.xmax, bb.ymax, bb.zmax]))
    names = list(solids)
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            lo = np.maximum(bounds[first][0], bounds[second][0])
            hi = np.minimum(bounds[first][1], bounds[second][1])
            if np.any(hi - lo <= 1e-5):
                continue
            volume = float(solids[first].intersect(solids[second]).Volume())
            if volume > .01:
                intersections.append(dict(first=first, second=second, volume_mm3=round(volume, 5)))
    (ROOT / 'review' / 'interference_report.json').write_text(
        json.dumps(intersections, ensure_ascii=False, indent=2), encoding='utf-8')
    assert not intersections, intersections

    # Sample the intended sequential insertion paths, excluding parts installed
    # later. These are discrete collision samples, not a continuous motion proof.
    motion_checks = []
    fixed_names = [name for name in solids if name.startswith(('B_', 'L_', 'R_', 'K_', 'P_'))
                   or any('_' + prefix in name for prefix in ('B_base', 'L_side', 'R_side', 'K_back'))]
    tray_names = [name for name in solids if name.startswith('T_') or '_T_tray' in name]
    for phase, moving, fixed, offsets in (
        ('tray_front_slide', tray_names, fixed_names,
         [(0, y, 0) for y in (-350, -250, -150, -50, 0)]),
        ('screen_front_slide', ['REF_screen_15mm'], fixed_names + tray_names,
         [(0, y, 0) for y in (-350, -200, -75, 0)]),
        ('acrylic_45deg_slide', ['REF_acrylic'], fixed_names + tray_names + ['REF_screen_15mm'],
         [(0, -distance / math.sqrt(2), distance / math.sqrt(2)) for distance in (400, 200, 75, 0)]),
    ):
        for offset in offsets:
            for moving_name in moving:
                moved = solids[moving_name].translate(offset)
                bb = moved.BoundingBox()
                moved_bounds = (np.array([bb.xmin, bb.ymin, bb.zmin]),
                                np.array([bb.xmax, bb.ymax, bb.zmax]))
                for fixed_name in fixed:
                    lo = np.maximum(moved_bounds[0], bounds[fixed_name][0])
                    hi = np.minimum(moved_bounds[1], bounds[fixed_name][1])
                    if np.any(hi - lo <= 1e-5):
                        continue
                    volume = float(moved.intersect(solids[fixed_name]).Volume())
                    assert volume <= .01, (phase, moving_name, fixed_name, offset, volume)
        motion_checks.append(dict(phase=phase, sampled_offsets=offsets, collisions=0))
    (ROOT / 'review' / 'insertion_samples.json').write_text(
        json.dumps(motion_checks, indent=2), encoding='utf-8')
    glb_scene = scene.copy()
    glb_scene.apply_scale(.001)  # glTF uses metres; STEP/STL/3MF stay in millimetres.
    glb_scene.export(ROOT / 'review' / 'assembly.glb')
    assembly.export(str(ROOT / 'review' / 'assembly.step'))
    write_3mf(ROOT / 'review' / 'assembly_geometry_only.3mf', world_meshes)

    # One already-oriented geometry file per large part. No printer profile or G-code.
    plate_number = 0
    for name, mesh in print_meshes.items():
        if name.startswith(('J_', 'P_foot', 'S_stop')):
            continue
        plate_number += 1
        centered = mesh.copy()
        centered.apply_translation([(256 - mesh.extents[0]) / 2,
                                    (256 - mesh.extents[1]) / 2, 0])
        write_3mf(ROOT / 'plates_3mf' / f'{plate_number:02}_{name}.3mf', [(name, centered)])
    for kind, columns, rows in (('light', 4, 10), ('heavy', 3, 8)):
        mesh = print_meshes[f'J_{kind}']
        batch = []
        for index in range(counts[kind]):
            assert index < columns * rows
            piece = mesh.copy()
            piece.apply_translation([8 + (index % columns) * (mesh.extents[0] + 6),
                                     8 + (index // columns) * (mesh.extents[1] + 5), 0])
            assert np.all(piece.bounds[1][:2] <= 248)
            batch.append((f'J_{kind}_{index + 1}', piece))
        plate_number += 1
        write_3mf(ROOT / 'plates_3mf' / f'{plate_number:02}_J_{kind}_{counts[kind]}.3mf', batch)
    batch = []
    for index, name in enumerate(name for name in print_meshes if name.startswith(('P_foot', 'S_stop'))):
        piece = print_meshes[name].copy()
        piece.apply_translation([10 + (index % 4) * 40, 10 + (index // 4) * 40, 0])
        batch.append((name, piece))
    plate_number += 1
    write_3mf(ROOT / 'plates_3mf' / f'{plate_number:02}_feet_and_stops.3mf', batch)

    # Coupons use the very same connector geometry and socket clearances.
    coupons = []
    for index, (kind, config, thick) in enumerate((('light', LIGHT, 4), ('heavy', HEAVY, 6))):
        sample = box(config['length'] + 8, config['width'] + 8, thick,
                     (0, 0, thick / 2))
        for socket in sockets(config):
            sample = sample.cut(socket)
        for side, a, b in (('A', -40, -GAP / 2), ('B', GAP / 2, 40)):
            half = sample.intersect(box(b - a, 60, 30, ((a + b) / 2, 0, 10))).clean()
            m = mesh_from_shape(half)
            # Pocket opening up, so the coupon does not need bridging supports.
            m.apply_transform(np.diag([1, -1, -1, 1]))
            m.apply_translation(-m.bounds[0] + np.array([8 + (side == 'B') * 45, 8 + index * 60, 0]))
            coupons.append((f'{kind}_{side}', m))
        m = print_meshes[f'J_{kind}'].copy()
        m.apply_translation([110, 8 + index * 60, 0])
        coupons.append((f'{kind}_bridge', m))
    # A small 2.4 mm acrylic channel test reproduces the production channel width.
    channel = union([box(30, 22, 3, (0, 0, 1.5)),
                     box(30, 8, 5, (0, -5.2, 5.5)),
                     box(30, 8, 5, (0, 5.2, 5.5))])
    m = mesh_from_shape(channel)
    m.apply_translation(-m.bounds[0] + np.array([8, 145, 0]))
    coupons.append(('acrylic_2p4_slot', m))
    tray_channel = union([box(30, 30, 3, (0, 0, 1.5)),
                          box(30, 8, 8, (0, -7.3, 7)),
                          box(30, 8, 8, (0, 7.3, 7))])
    m = mesh_from_shape(tray_channel)
    m.apply_translation(-m.bounds[0] + np.array([55, 145, 0]))
    coupons.append(('tray_6p6_slot', m))
    lid_sample = union([box(27.2, 27.2, 4, (0, 0, 2)),
                        box(3.2, 27.2, 12, (-12, 0, 10)),
                        box(3.2, 27.2, 12, (12, 0, 10)),
                        box(20.8, 3.2, 12, (0, -12, 10)),
                        box(20.8, 3.2, 12, (0, 12, 10))])
    for label, sample, x in (('lid_0p4_clearance', lid_sample, 105),
                              ('lid_male_20mm', box(20, 20, 10, (0, 0, 5)), 150)):
        m = mesh_from_shape(sample)
        m.apply_translation(-m.bounds[0] + np.array([x, 145, 0]))
        coupons.append((label, m))
    write_3mf(ROOT / '00_PRINT_FIRST_fit_coupons.3mf', coupons)

    report = dict(version='2026-11-04-screw-free', original_sha256=digest,
                  screen_mm=[360, 225, 15], acrylic_mm=[400, 350, 2],
                  tray_top_z=TRAY_TOP, tray_thickness=TRAY_T, supports=SUPPORTS,
                  wall_joint_gap=GAP, connector_clearance_per_side=PIN_CLEARANCE,
                  connectors=counts, part_records=records, groups=groups,
                  geometry_plate_count=plate_number,
                  material_solid_volume_cm3=round(sum(r['quantity'] * r['volume_cm3'] for r in records), 2),
                  exact_interference_pairs=len(intersections),
                  insertion_samples=motion_checks,
                  checked=['CAD solid validity', 'positive volume', 'watertight tessellation',
                           'consistent winding', 'oriented part XY <= 240 mm', '3MF XML millimeter units'],
                  not_checked=['slicer toolpath', 'support generation', 'print time/material consumption',
                               'physical fit', 'load rating', 'thermal run', 'actual board/cable occupancy'])
    (ROOT / 'review' / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with (ROOT / '零件清单.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['编号', '数量', '打印包络X毫米', 'Y毫米', 'Z毫米', '实体体积cm3'])
        for record in records:
            writer.writerow([record['name'], record['quantity'], *record['size_mm'], record['volume_cm3']])
    print(json.dumps({k: report[k] for k in ('connectors', 'geometry_plate_count', 'material_solid_volume_cm3')}, ensure_ascii=False), flush=True)
    return report


if __name__ == '__main__':
    build()
