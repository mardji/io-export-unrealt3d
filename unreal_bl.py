import bpy_extras
import math
from mathutils import Vector

def format_vert(vec):
    v = vec.copy()
    #print("format_vert", v)
    return '{:+013.6f},{:+013.6f},{:+013.6f}'.format(v[0], v[1], v[2])

def format_float(float):
    return '{:+013.6f}'.format(float)

def format_location(x,y,z):
    return ("{:.6f}".format(x),
        "{:.6f}".format(y),
        "{:.6f}".format(z))

ROTATION_MAX = 2.0**16

def format_rotation(x,y,z):
    x = ((x % (2*math.pi))/(2*math.pi)) * 2**16
    y = ((y % (2*math.pi))/(2*math.pi)) * 2**16
    z = ((z % (2*math.pi))/(2*math.pi)) * 2**16
    return (str(int(x)),str(int(y)),str(int(z)))

class UActor:
    def __init__(self, o):
        self.group = ""
        self.name = None # is set elsewhere
        self.location = None
        self.rotation = None
        self.object = o
        self.post_scale = None

    def class_name(self):
        return self.object.class_name

    def export(self):
        if not self.name:
            self.name = UMap.unique_name(self)
        output = "Begin Actor Class={} Name={}\n".format(self.object.class_name, self.name)
        if self.location:
            x,y,z = self.location
            if (abs(x) + abs(y) + abs(z) != 0.0):
                strx,stry,strz = format_location(x,y,z)
                output += "\tLocation=(X={},Y={},Z={})\n".format(strx,stry,strz)
        if self.rotation:
            x,y,z = self.rotation
            if (abs(x) + abs(y) + abs(z) != 0.0):
                strx,stry,strz = format_rotation(x,y,z)
                output += "\tRotation=(Roll={},Yaw={},Pitch={})\n".format(strx,strz,stry)
        if self.post_scale:
            x,y,z = self.post_scale
            strx,stry,strz = format_location(x,y,z)
            output += "\tPostScale=(Scale=(X={},Y={},Z={}))\n".format(strx,stry,strz)
        # print(" -- Exporting object data")
        output += self.object.export()
        output += "End Actor\n"
        return output

class UBrush:
    class_name = 'Brush'

    def __init__(self):
        self.csg_oper = None
        self.polylist = []
        self.brush_name = None # should be set

    def add_polygon(self, polygon):
        self.polylist.append(polygon)

    def export(self):
        output = ""
        if self.csg_oper:
            output += "\tCsgOper=CSG_{}\n".format(self.csg_oper)
        if not self.brush_name:
            self.brush_name = UMap.unique_name(self)
        output += "\tBegin Brush Name={}\n".format(self.brush_name)
        if len(self.polylist) > 0:
            output += "\t\tBegin PolyList\n"
            for poly in self.polylist:
                # print(" --- Exporting a polygon")
                output += poly.export()
            output += "\t\tEnd PolyList\n"
        output += "\tEnd Brush\n"
        output += "\tBrush=Model'MyLevel.{}'\n".format(self.brush_name) # TODO:
        return output

class UPolygon:

    def __init__(self, origin, normal, verts):
        self.origin = origin
        self.normal = normal
        self.verts = verts
        self.flags = 0
        v = (origin - verts[1]).normalized()
        # u = v.cross(normal)
        u = (origin - verts[1]).cross(normal).normalized()
        self.tex_u = v
        self.tex_v = u

    def set(self, flag, val):
        if val:
            self.flags += flag
        elif not val:
            self.flags -= flag
        # self.flags -= (flag * (-1)**int(val))

    def export(self):
        output = "\t\t\tBegin Polygon\n"
        output += "\t\t\tOrigin {}\n".format(format_vert(self.origin))
        output += "\t\t\tNormal {}\n".format(format_vert(self.normal))
        # TODO: TextureU and TextureV should be calculated from normal
        # output += "\t\t\tTextureU +00001.000000,+00000.000000,+00000.000000\n"
        output += "\t\t\tTextureU {}\n".format(format_vert(self.tex_u))
        output += "\t\t\tTextureV {}\n".format(format_vert(self.tex_v))
        output += "\t\t\tPan      U=0 V=0\n"

        for vert in self.verts:
            output += "\t\t\tVertex {}\n".format(format_vert(vert))
        output += "\t\t\tEnd Polygon\n"

        return output

class UMap:
    names = dict()

    def __init__(self):
        self.actors = []
        # self.names = dict()

    def export(self):
        output = "Begin Map\n"
        # output += self.level_info()
        output += self.actors[0].export() # Maker brush
        for actor in self.actors:
            output += actor.export()
        output += "End Map\n"
        return output

    def add_actor(self, actor):
        self.actors.append(actor)

    def level_info(self):
        output = "Begin Actor Class=LevelInfo Name=LevelInfo0\n"
        output += "TimeSeconds=0.0\n"
        output += "Summary=LevelSummary'MyLevel.LevelSummary'\n"
        output += "VisibleGroups=\"\"\n"
        output += "AIProfile(0)=49808\n"
        output += "End Actor\n"
        return output

    import bpy_extras.io_utils
    @classmethod
    def unique_name(self, o):
        if type(o) == UActor:
            root = o.object.class_name
        elif type(o) == UBrush:
            root = "Model"
        return bpy_extras.io_utils.unique_name(o, root, self.names, sep="")
