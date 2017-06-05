# FIXME: use_blender_axis subtracted geometry does not work. (Normals incorrect?)
# FIXME: when exporting, add an extra brush for maker brush (i.e. red brush).
# FIXME: Make sure Rotation= is written to in the correct order.

bl_info = {
    "name": "Export: UnrealEd 2.1 T3D (.t3d)",
    "author": "mara",
    "version": (2, 2),
    "blender": (2, 64, 0),
    "location": "File > Export > Unreal 227 UnrealEd 2.1 .t3d",
    "description": "Export brush geometry",
    "warning": "",
    "wiki_url": "http://",
    "category": "Import-Export",
}

import bpy
from bpy.types import Panel, Menu
from rna_prop_ui import PropertyPanel

from .unreal_bl import UMap, UActor, UBrush, UPolygon
# from .unreal_bl import * 

import bpy_extras

def unrealed_inner_view(context):
    # set backface culling on
    # flip normals
    # show_backface_culling = bpy.context.space_data.show_backface_culling
    for area in bpy.context.screen.areas:
        if area.type == 'SPACEVIEW_3D':
            show_backface_culling = bpy.context.screen.areas[0].spaces[0].show_backface_culling
            bpy.context.screen.areas[0].spaces[0].show_backface_culling = not show_backface_culling
    # mode = bpy.context.mode
    mode = bpy.context.active_object.mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode=mode)
    #show_backface_culling = not show_backface_culling
    #bpy.context.space_data.show_backface_culling = show_backface_culling

def unrealed_csg_update(self, context):
    print("TODO", self, context)

class ToggleInnerView(bpy.types.Operator):
    """Todo."""
    bl_idname = "mesh.toggle_inner_view"
    bl_label = "Toggle backface culling and flip normals"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        #self.unrealed_inner_view(context)
        unrealed_inner_view(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

class ObjectButtonsPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

SUPPORTED_TYPES = ('MESH')

from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty
import bmesh
import mathutils

class UnrealT3DExport(bpy.types.Operator, ExportHelper):
    """Todo."""
    bl_idname = "export.t3d"
    bl_label = "UnrealEd 2.1 t3d export"
    filepath = StringProperty(subtype='FILE_PATH')
    filename_ext = ".t3d"
    filter_glob = StringProperty(default="*.t3d", options={'HIDDEN'})
    export_scene = BoolProperty(name="Export scene", default=False,
        description="Export all mesh objects (instead of selected objects) in active scene.")
    use_blender_axis = BoolProperty(name="Use Blender axis", default=False,
        description="Export so that top-view in UnrealEd matches this view.")
    scale = bpy.props.FloatProperty(name="Scale", default=128.0, description="All vectors are scaled by this factor.")

    def mesh_to_uactor(self, context, matrices, o):
        # o.update_from_editmode()
        use_mesh_modifiers = True
        mesh = o.to_mesh(context.scene, use_mesh_modifiers, 'PREVIEW')

        return mesh

    def object_to_uactor(self, context, matrices, o):
        brush = UBrush()
        actor = UActor(brush)
        actor.name = o.name
        # actor.location = (o.matrix_world * o.location).to_tuple()
        # actor.location = (o.location * self.scale).to_tuple()
        # actor.location = (o.matrix_world * o.location * matrices['axis'] * matrices['scale']).to_tuple()
        matrix_world = matrices['axis'] * o.matrix_world
        actor.location = (matrices['axis'] * matrices['scale'] * o.location).to_tuple()
        actor.rotation = o.rotation_euler.copy()
        if self.use_blender_axis:
            actor.post_scale = mathutils.Vector((1,-1,1))
        # actor.rotation.rotate_axis('Z', matrices['rotation_offset'])
        if o.custom_CSG:
            brush.csg_oper = o.custom_CSG
        # o2 = o.copy()
        # o2.matrix_world = matrices['axis'] * o2.matrix_world
        mesh = self.mesh_to_uactor(context, matrices, o)
        # mesh.transform(o2.matrix_world)
        bm = bmesh.new()
        bm.from_mesh(mesh)

        bm.transform(matrices['scale'])
        # bm.normal_update()
        for f in bm.faces:
            # if self.use_blender_axis:
            #    f.normal = matrices['axis'] * f.normal 
            f.normal_update()
            
            verts = [v.co.copy() for v in f.verts] #v.co.copy()?
            poly = UPolygon(verts[0].copy(), f.normal.copy(), verts)
            brush.add_polygon(poly)
        bm.free()
        bpy.data.meshes.remove(mesh)
        return actor

    def export(self, context, filePath, options):
        print("----------\nExporting to {}".format(filePath))
        scene = context.scene
        objects = (ob for ob in scene.objects if ob.is_visible(scene) and ob.select and ob.type in SUPPORTED_TYPES)
        umap = UMap()
        
        axis_matrix = bpy_extras.io_utils.axis_conversion().to_4x4()
        if self.use_blender_axis:
            axis_matrix = mathutils.Matrix.Scale(-1, 4, mathutils.Vector((0, 1, 0))) 
            # axis_matrix = bpy_extras.io_utils.axis_conversion(to_forward='-Y').to_4x4()
        matrices = {'scale': mathutils.Matrix.Scale(self.scale, 4), 'axis': axis_matrix}

        objects = list(objects)
        for o in objects:
            actor = self.object_to_uactor(context, matrices, o)
            if actor:
                umap.add_actor(actor)
        with open(filePath, "w", encoding="utf8", newline="\n") as f:
            output = umap.export()
            f.write(output)
        print("Finished")

    def execute(self, context):
        filePath = bpy.path.ensure_ext(self.filepath, ".t3d")
        config = {
            'export_scene' : self.export_scene
        }
        self.export(context, filePath, config)
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".t3d")
        WindowManager = context.window_manager
        WindowManager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class UnrealEdPanel(ObjectButtonsPanel, Panel):
    bl_label = "UnrealEd"

    obj = bpy.types.Object

    csg_items = [('Add', 'Add', 'Add'), ('Subtract', 'Subtract', 'Subtract')]
    obj.custom_CSG = bpy.props.EnumProperty(name="CSG Operation", items=csg_items, update=unrealed_csg_update)
    csg_polyflags_items = [('Solid', 'Solid', 'Solid'), ('Semisolid', 'Semisolid', 'Semisolid'), ('Nonsolid', 'Nonsolid', 'Nonsolid')]
    obj.custom_CSG_solidity = bpy.props.EnumProperty(name="CSG flags", items=csg_polyflags_items, update=unrealed_csg_update)
    obj.custom_texture = bpy.props.StringProperty(name="Unreal Texture")

    def draw(self, context):
        layout = self.layout

        ob = context.object
        
        split = layout.split()
        
        col = split.column()
        col.label(text="CSG operation:")
        col.prop(ob, "custom_CSG", expand=True)

        col = split.column()
        col.label(text="Solidity:")
        col.prop(ob, "custom_CSG_solidity", expand=True)
        col.enabled = (ob.custom_CSG == 'Add')

        layout.prop(ob, "custom_texture")

        layout.operator("mesh.toggle_inner_view", text="Toggle inner view")
        # tex = context.texture
        tex = context.active_object.active_material.active_texture
        if tex:
            layout.template_preview(tex)

def menu_func(self, context):
    self.layout.operator(UnrealT3DExport.bl_idname, text="UnrealEd 2.1 (.t3d) popanus")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":  # only for live edit.
    register()
