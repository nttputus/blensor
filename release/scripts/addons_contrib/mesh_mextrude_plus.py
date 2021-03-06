# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

################################################################################
# Repeats extrusion + rotation + scale for one or more faces                   #

################################################################################

bl_info = {
    "name": "MExtrude Plus",
    "author": "liero",
    "version": (1, 2, 8),
    "blender": (2, 6, 2),
    "location": "View3D > Tool Shelf",
    "description": "Repeat extrusions from faces to create organic shapes",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts",
    "tracker_url": "http://projects.blender.org/tracker/index.php?"\
        "func=detail&aid=28570",
    "category": "Mesh"}

import  bpy, bmesh, mathutils, random
from random import gauss
from math import radians
from mathutils import Euler, Vector
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty

def vloc(self, r):
    random.seed(self.ran + r)
    return self.off * (1 + random.gauss(0, self.var1 / 3))

def vrot(self,r):
    random.seed(self.ran+r)
    return Euler((radians(self.rotx) + random.gauss(0, self.var2 / 3), \
        radians(self.roty) + random.gauss(0, self.var2 / 3), \
        radians(self.rotz) + random.gauss(0,self.var2 / 3)), 'XYZ')

def vsca(self, r):
    random.seed(self.ran + r)
    return [self.sca * (1 + random.gauss(0, self.var3 / 3))] * 3
# funcion para calcular el centro de una seleccion de vertices
def centro(ver):
    vvv = [v for v in ver if v.select]
    if not vvv or len(vvv) == len(ver): return ('error')
    x = sum([round(v.co[0],4) for v in vvv]) / len(vvv)
    y = sum([round(v.co[1],4) for v in vvv]) / len(vvv)
    z = sum([round(v.co[2],4) for v in vvv]) / len(vvv)
    return (x,y,z)

def volver(obj, copia, om, msm, msv):
    for i in copia: obj.data.vertices[i].select = True
    #bpy.ops.object.mode_set(mode=om) #stay in object mode...
    bpy.context.tool_settings.mesh_select_mode = msm
    for i in range(len(msv)):
        obj.modifiers[i].show_viewport = msv[i]

class MExtrude(bpy.types.Operator):
    bl_idname = 'object.mextrude'
    bl_label = 'MExtrude'
    bl_description = 'Multi Extrude'
    bl_options = {'REGISTER', 'UNDO'}

    off = FloatProperty(name='Offset', min=-2, soft_min=0.001, \
        soft_max=2, max=5, default=.5, description='Translation')
    rotx = FloatProperty(name='Rot X', min=-85, soft_min=-30, \
        soft_max=30, max=85, default=0, description='X rotation')
    roty = FloatProperty(name='Rot Y', min=-85, soft_min=-30, \
        soft_max=30, max=85, default=0, description='Y rotation')
    rotz = FloatProperty(name='Rot Z', min=-85, soft_min=-30, \
        soft_max=30, max=85, default=-0, description='Z rotation')
    sca = FloatProperty(name='Scale', min=0.1, soft_min=0.5, \
        soft_max=1.2, max =2, default=.9, description='Scaling')
    var1 = FloatProperty(name='Offset Var', min=-5, soft_min=-1, \
        soft_max=1, max=5, default=0, description='Offset variation')
    var2 = FloatProperty(name='Rotation Var', min=-5, soft_min=-1, \
        soft_max=1, max=5, default=0, description='Rotation variation')
    var3 = FloatProperty(name='Scale Noise', min=-5, soft_min=-1, \
        soft_max=1, max=5, default=0, description='Scaling noise')
    num = IntProperty(name='Repeat', min=1, max=50, soft_max=100, \
        default=5, description='Repetitions')
    ran = IntProperty(name='Seed', min=-9999, max=9999, default=0, \
        description='Seed to feed random values')

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'MESH')

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        column.label(text='Transformations:')
        column.prop(self, 'off', slider=True)
        column.prop(self, 'rotx', slider=True)
        column.prop(self, 'roty', slider=True)
        column.prop(self, 'rotz', slider=True)
        column.prop(self, 'sca', slider=True)
        column = layout.column(align=True)
        column.label(text='Variation settings:')
        column.prop(self, 'var1', slider=True)
        column.prop(self, 'var2', slider=True)
        column.prop(self, 'var3', slider=True)
        column.prop(self, 'ran')
        column = layout.column(align=False)
        column.prop(self, 'num')

    def execute(self, context):
        obj = bpy.context.object
        data, om, msv =  obj.data, obj.mode, []
        msm = bpy.context.tool_settings.mesh_select_mode
        bpy.context.tool_settings.mesh_select_mode = [False, False, True]

        # disable modifiers
        for i in range(len(obj.modifiers)):
            msv.append(obj.modifiers[i].show_viewport)
            obj.modifiers[i].show_viewport = False

        # isolate selection
        bpy.ops.object.mode_set()
        bpy.ops.object.mode_set(mode='EDIT')
        total = data.total_face_sel
        try: bpy.ops.mesh.select_inverse()
        except: bpy.ops.mesh.select_all(action='INVERT')
        bpy.ops.object.vertex_group_assign(new=True)
        bpy.ops.mesh.hide()

        # faces loop
        for i in range(total):
            bpy.ops.object.editmode_toggle()
            # is bmesh..?
            try:
                faces = data.polygons
            except:
                faces = data.faces
            for f in faces:
                if not f.hide:
                    f.select = True
                    break
            norm = f.normal.copy()
            rot, loc = vrot(self, i), vloc(self, i)
            norm.rotate(obj.matrix_world.to_quaternion())
            bpy.ops.object.editmode_toggle()

            # extrude loop
            for a in range(self.num):
                norm.rotate(rot)
                r2q = rot.to_quaternion()
                bpy.ops.mesh.extrude_faces_move()
                bpy.ops.transform.translate(value = norm * loc)
                bpy.ops.transform.rotate(value = [r2q.angle], axis = r2q.axis)
                bpy.ops.transform.resize(value = vsca(self, i + a))
            bpy.ops.object.vertex_group_remove_from()
            bpy.ops.mesh.hide()

        # keep just last faces selected
        bpy.ops.mesh.reveal()
        bpy.ops.object.vertex_group_deselect()
        bpy.ops.object.vertex_group_remove()
        bpy.ops.object.mode_set()


        # restore user settings
        for i in range(len(obj.modifiers)): 
            obj.modifiers[i].show_viewport = msv[i]
        bpy.context.tool_settings.mesh_select_mode = msm
        bpy.ops.object.mode_set(mode=om)
        if not total:
            self.report({'INFO'}, 'Select one or more faces...')
        return{'FINISHED'}
class BB(bpy.types.Operator):
    bl_idname = 'object.mesh2bones'
    bl_label = 'Create Armature'
    bl_description = 'Create an armature rig based on mesh selection'
    bl_options = {'REGISTER', 'UNDO'}

    numb = IntProperty(name='Max Bones', min=1, max=1000, soft_max=100, default=5, description='Max number of bones')
    skip = IntProperty(name='Skip Loops', min=0, max=5, default=0, description='Skip some edges to get longer bones')
    long = FloatProperty(name='Min Length', min=0.01, max=5, default=0.15, description='Discard bones shorter than this value')
    ika = BoolProperty(name='IK constraints', default=True, description='Add an Empty and a IK constraint')
    rotk = BoolProperty(name='Use rotation', default=False, description='Activate constraint rotation')
    auto = BoolProperty(name='Auto weight', default=True, description='Auto weight and assign vertices')
    env = BoolProperty(name='Use Envelopes', default=False, description='Use envelopes instead of weights')
    rad = FloatProperty(name='Radius', min=0.01, max=5, default=0.25, description='Envelope deform radius')
    nam = StringProperty(name='', default='hueso', description='Default name for bones / groups')

    @classmethod
    def poll(cls, context):
        obj = bpy.context.object
        return (obj and obj.type == 'MESH')

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        column.prop(self,'numb')
        column.prop(self,'skip')
        column.prop(self,'long')
        column = layout.column(align=True)
        column.prop(self,'auto')
        if self.auto:
            column.prop(self,'env')
            if self.env: column.prop(self,'rad')
        column.prop(self,'ika')
        if self.ika: column.prop(self,'rotk')
        layout.prop(self,'nam')

    def execute(self, context):
        scn = bpy.context.scene
        obj = bpy.context.object
        fac, ver, om = obj.data.polygons, obj.data.vertices, obj.mode
        msm, msv = list(bpy.context.tool_settings.mesh_select_mode), []
        for i in range(len(obj.modifiers)):
            msv.append(obj.modifiers[i].show_viewport)
            obj.modifiers[i].show_viewport = False
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        txt = 'Select a face or a vertex where the chain should end...'

        # una cadena de huesos por cara...
        bpy.ops.object.mode_set(mode='OBJECT')
        copia = [v.index for v in ver if v.select]
        sel = [f.index for f in fac if f.select]
        if sel == []: sel = ['simple']

        # reciclar el rig en cada refresco...
        try: scn.objects.unlink(rig)
        except: pass

        for i in sel:
            if sel[0] != 'simple':
                for v in ver: v.select = False
                for v in fac[i].vertices: ver[v].select = True
            lista = [centro(ver)]
            if lista[0] == 'error':
                self.report({'INFO'}, txt)
                volver(obj, copia, om, msm, msv)
                return{'FINISHED'}

            # crear lista de coordenadas para los huesos
            scn.objects.active = obj
            for t in range(self.numb):
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.vertex_group_assign(new=True)
                for m in range(self.skip+1):
                    bpy.ops.mesh.select_more()
                bpy.ops.object.vertex_group_deselect()
                bpy.ops.object.mode_set(mode='OBJECT')
                lista.append(centro(ver))
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.vertex_group_select()
                bpy.ops.object.vertex_group_remove()
                if lista[-1] == 'error':
                    self.numb = t
                    lista.pop()
                    break
                if len(lista) > 1:
                    delta = Vector(lista[-2]) - Vector(lista[-1])
                    if delta.length < self.long:
                        lista.pop()

            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            # crear armature y copiar transformaciones del objeto
            lista.reverse()
            if len(lista) < 2:
                self.report({'INFO'}, txt)
                volver(obj, copia, om, msm, msv)
                return{'FINISHED'}
            try: arm
            except:
                arm = bpy.data.armatures.new('arm')
                if self.env: arm.draw_type = 'ENVELOPE'
                else: arm.draw_type = 'STICK'
                rig = bpy.data.objects.new(obj.name+'_rig', arm)
                rig.matrix_world = obj.matrix_world
                if self.env: rig.draw_type = 'WIRE'
                rig.show_x_ray = True
                scn.objects.link(rig)
            scn.objects.active = rig
            bpy.ops.object.mode_set(mode='EDIT')

            # crear la cadena de huesos desde la lista
            for i in range(len(lista)-1):
                bon = arm.edit_bones.new(self.nam+'.000')
                bon.use_connect = True
                bon.tail = lista[i+1]
                bon.head = lista[i]
                if self.auto and self.env:
                    bon.tail_radius = self.rad
                    bon.head_radius = self.rad
                if i: bon.parent = padre
                padre = bon
            bpy.ops.object.mode_set(mode='OBJECT')

            # crear IK constraint y un Empty como target
            if self.ika:
                ik = rig.data.bones[-1].name
                loc = rig.matrix_world * Vector(lista[-1])
                rot = rig.matrix_world * rig.data.bones[-1].matrix_local
                bpy.ops.object.add(type='EMPTY', location=loc, rotation=rot.to_euler())
                tgt = bpy.context.object
                tgt.name = obj.name+'_target.000'
                if len(sel) > 1:
                    try: mega
                    except:
                        bpy.ops.object.add(type='EMPTY', location = obj.location)
                        mega = bpy.context.object
                        mega.name = obj.name+'_Controls'
                        tgt.select = True
                    scn.objects.active = mega
                    bpy.ops.object.parent_set(type='OBJECT')

                scn.objects.active = rig
                bpy.ops.object.mode_set(mode='POSE')
                con = rig.pose.bones[ik].constraints.new('IK')
                con.target = tgt
                if self.rotk: con.use_rotation = True
                tgt.select = False
                bpy.ops.object.mode_set(mode='OBJECT')

        obj.select = True
        if self.auto:
            if self.env: bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
            else: bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        scn.objects.active = obj
        volver(obj, copia, om, msm, msv)
        return{'FINISHED'}


class BotonME(bpy.types.Panel):
    bl_label = 'Multi Extrude Plus'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    def draw(self, context):
        layout = self.layout
        layout.operator('object.mextrude')
        layout.operator('object.mesh2bones')

def register():
    bpy.utils.register_class(MExtrude)
    bpy.utils.register_class(BotonME)
    bpy.utils.register_class(BB)

def unregister():
    bpy.utils.unregister_class(MExtrude)
    bpy.utils.unregister_class(BotonME)
    bpy.utils.unregister_class(BB)


if __name__ == '__main__':
    register()
