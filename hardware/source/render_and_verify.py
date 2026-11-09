"""Independent exported-file checks, review pictures, and package manifest."""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh
import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
FONT = FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}


def read_3mf(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        root = ET.fromstring(archive.read('3D/3dmodel.model'))
    assert root.attrib['unit'] == 'millimeter'
    meshes = {}
    for obj in root.findall('m:resources/m:object', NS):
        vertices = [[float(v.attrib[axis]) for axis in ('x', 'y', 'z')]
                    for v in obj.findall('m:mesh/m:vertices/m:vertex', NS)]
        faces = [[int(f.attrib[axis]) for axis in ('v1', 'v2', 'v3')]
                 for f in obj.findall('m:mesh/m:triangles/m:triangle', NS)]
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, path
        meshes[obj.attrib['name']] = mesh
    assert len(root.findall('m:build/m:item', NS)) == len(meshes)
    return meshes


def verify_files():
    checks = []
    for path in sorted((ROOT / 'stl_print').glob('*.stl')):
        mesh = trimesh.load_mesh(path, process=True)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, path
        assert np.all(mesh.bounds[0] >= -1e-4), path
        assert max(mesh.extents[:2]) <= 240 and mesh.extents[2] <= 256, path
        checks.append(path.name)
    plates = [ROOT / '00_PRINT_FIRST_fit_coupons.3mf'] + sorted((ROOT / 'plates_3mf').glob('*.3mf'))
    for path in plates:
        meshes = read_3mf(path)
        for name, mesh in meshes.items():
            assert np.all(mesh.bounds[0] >= -1e-4), (path, name)
            assert np.all(mesh.bounds[1] <= np.array([256, 256, 256]) + 1e-4), (path, name)
        # Check the conservative projected bounding boxes for overlaps.
        items = list(meshes.items())
        for index, (first, a) in enumerate(items):
            for second, b in items[index + 1:]:
                if np.all(np.minimum(a.bounds[1][:2], b.bounds[1][:2]) -
                          np.maximum(a.bounds[0][:2], b.bounds[0][:2]) > 1e-4):
                    raise AssertionError((path, first, second, 'XY placement overlaps'))
        checks.append(path.name)
    glb = trimesh.load(ROOT / 'review' / 'assembly.glb', force='scene')
    assert .4 < glb.extents[0] < .5  # metre conversion must not be lost
    assembled = read_3mf(ROOT / 'review' / 'assembly_geometry_only.3mf')
    lo = np.min([mesh.bounds[0] for mesh in assembled.values()], axis=0)
    hi = np.max([mesh.bounds[1] for mesh in assembled.values()], axis=0)
    assert 440 < hi[0] - lo[0] < 460  # assembly coordinates must remain in mm
    step = cq.importers.importStep(str(ROOT / 'review' / 'assembly.step')).val()
    assert step.isValid() and len(step.Solids()) == 87
    report = dict(exported_files_checked=len(checks), plate_files=len(plates),
                  tests=['STL reread', '3MF XML reread', 'positive watertight meshes',
                         '256mm plate bounds', 'plate XY non-overlap', 'GLB metre scale',
                         'STEP reread: 87 valid solids'],
                  not_a_slicer_test=True)
    (ROOT / 'review' / 'export_verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def color(name):
    for prefix, value in [('B_', '#8093a5'), ('L_', '#a5b8d6'), ('R_', '#a5b8d6'),
                          ('K_', '#94accb'), ('T_', '#55b49e'), ('C_', '#d3ad6b'),
                          ('F_', '#8594a5'), ('J_', '#e88957')]:
        if name.startswith(prefix):
            return value
    return '#969fa6'


def draw(ax, meshes, hidden=(), exploded=False, lift_tray=False):
    for name, mesh in meshes.items():
        if any(name.startswith(prefix) for prefix in hidden):
            continue
        vertices = mesh.vertices.copy()
        if exploded and (name.startswith('C_') or '_C_lid' in name):
            vertices[:, 2] += 90
        if lift_tray and (name.startswith('T_') or '_T_tray' in name):
            vertices[:, 2] += 70
        collection = Poly3DCollection(vertices[mesh.faces], facecolors=color(name),
                                     linewidth=0, alpha=1, shade=True)
        ax.add_collection3d(collection)
    ax.set(xlim=(-255, 255), ylim=(-45, 395), zlim=(-10, 470 if exploded else 375))
    ax.set_box_aspect((510, 440, 480 if exploded else 385))
    ax.view_init(elev=22, azim=-58)
    ax.set_axis_off()


def render():
    meshes = read_3mf(ROOT / 'review' / 'assembly_geometry_only.3mf')
    # A depth-buffered renderer avoids painter-order artifacts between the two
    # faces of thin enclosure panels. Render off-screen, without opening a UI.
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk
    from matplotlib.colors import to_rgb
    from PIL import Image, ImageDraw, ImageFont

    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(2400, 1280)
    window.SetMultiSamples(8)
    for index, (title, hidden, exploded) in enumerate([
        ('整机与可取下箱盖', (), True),
        ('移去前板、右侧板并抬起托板：查看承托结构', ('R_', 'F_', 'C_'), False)], 1):
        renderer = vtk.vtkRenderer()
        renderer.SetViewport((index - 1) / 2, .11, index / 2, .91)
        renderer.SetBackground(*to_rgb('#f4f5f7'))
        window.AddRenderer(renderer)
        filtered = {k: v for k, v in meshes.items()
                    if not any(k.startswith(p) or ('_' + p.rstrip('_')) in k
                               for p in hidden)}
        for name, mesh in filtered.items():
            vertices = mesh.vertices.copy()
            if exploded and (name.startswith('C_') or '_C_lid' in name):
                vertices[:, 2] += 90
            if index == 2 and (name.startswith('T_') or '_T_tray' in name):
                vertices[:, 2] += 70
            points = vtk.vtkPoints()
            points.SetData(numpy_to_vtk(vertices, deep=True))
            triangles = vtk.vtkCellArray()
            for face in mesh.faces:
                triangles.InsertNextCell(3)
                for vertex in face:
                    triangles.InsertCellPoint(int(vertex))
            poly = vtk.vtkPolyData()
            poly.SetPoints(points)
            poly.SetPolys(triangles)
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputData(poly)
            normals.ComputePointNormalsOff()
            normals.ComputeCellNormalsOn()
            normals.ConsistencyOn()
            normals.AutoOrientNormalsOn()
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(normals.GetOutputPort())
            mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(*to_rgb(color(name)))
            actor.GetProperty().SetAmbient(.35)
            actor.GetProperty().SetDiffuse(.65)
            renderer.AddActor(actor)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(700, -900, 640)
        camera.SetFocalPoint(0, 175, 200)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(330)
        renderer.ResetCameraClippingRange()
    window.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(window)
    grab.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(ROOT / 'review' / '结构预览.png'))
    writer.SetInputConnection(grab.GetOutputPort())
    writer.Write()
    window.Finalize()
    picture = Image.open(ROOT / 'review' / '结构预览.png').convert('RGB')
    pen = ImageDraw.Draw(picture)
    heading = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 30)
    caption = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 24)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
    pen.rectangle((0, 0, 2400, 100), fill='#f4f5f7')
    pen.rectangle((0, 1150, 2400, 1280), fill='#f4f5f7')
    pen.text((330, 35), '整机与可取下箱盖', font=heading, fill='#26394b')
    pen.text((1280, 35), '移去前板、右侧板并抬起托板：查看承托结构', font=heading, fill='#26394b')
    pen.text((90, 1175), '15.6英寸 / 屏厚15mm · 托板6mm＋加强筋＋六处落地支撑 · 无螺钉定位桥接片＋热熔胶', font=caption, fill='#26394b')
    pen.text((90, 1220), '结构预览：未包含屏幕、透明板和黑卡；承重、热运行与打印配合需现场验证。', font=small, fill='#576674')
    picture.save(ROOT / 'review' / '结构预览.png')

    report = json.loads((ROOT / 'review' / 'build_report.json').read_text(encoding='utf-8'))
    fig, axes = plt.subplots(2, 3, figsize=(14, 10), facecolor='white')
    for ax, group in zip(axes.flat, report['groups']):
        umin, umax, vmin, vmax = group['ranges']
        usplit, vsplit = group['splits']
        for iu, (a, b) in enumerate(((umin, usplit), (usplit, umax)), 1):
            for iv, (c, d) in enumerate(((vmin, vsplit), (vsplit, vmax)), 1):
                ax.add_patch(plt.Rectangle((a, c), b - a, d - c,
                                          facecolor='#eaf0f7', edgecolor='#426585', linewidth=1.5))
                ax.text((a + b) / 2, (c + d) / 2, f"{group['name']}_{iu}{iv}",
                        ha='center', va='center', fontsize=10)
        ax.set(xlim=(umin - 12, umax + 12), ylim=(vmin - 12, vmax + 12), aspect='equal')
        ax.set_title(group['name'])
        ax.tick_params(labelsize=8)
    fig.suptitle('板块编号对照｜均从各板件外表面/托板底面观察；右侧板与左侧板方向相反',
                 fontproperties=FONT, fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(ROOT / 'review' / '分块编号图.png', dpi=150)
    plt.close(fig)


def manifest_and_zip():
    lines = []
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and path.suffix != '.zip' and '__pycache__' not in path.parts and path.name != 'SHA256SUMS.txt':
            lines.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(ROOT).as_posix())
    (ROOT / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    path = ROOT / '影有回声_无螺钉分块打印包_2026-11-04.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(ROOT.rglob('*')):
            if item.is_file() and item.suffix != '.zip' and '__pycache__' not in item.parts:
                archive.write(item, item.relative_to(ROOT))
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
    print(path)


if __name__ == '__main__':
    print(verify_files())
    render()
    manifest_and_zip()
