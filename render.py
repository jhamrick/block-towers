import bpy
import pandas as pd
import numpy as np
import hashlib
import colorsys
import os

from mathutils import Vector


def new_floor():
    scene = bpy.data.scenes["Scene"]

    # add a cylinder for the floor, and make it big
    bpy.ops.mesh.primitive_cylinder_add()
    floor = bpy.data.objects["Cylinder"]
    floor.scale = np.array([5, 5, 0.1])
    floor.location = np.array([0, 0, -0.1])

    # set the material properties to something wood-y
    material = bpy.data.materials.new(name="wood_floor_material")
    material.diffuse_intensity = 0.8
    material.specular_color = (0.8, 0.8, 0.8)
    material.specular_intensity = 0.5
    material.ambient = 0
    floor.data.materials.append(material)

    # create the texture
    image = bpy.data.images.load("resources/wood_tile_polar.png")
    tex = bpy.data.textures.new(name="wood_floor_texture", type="IMAGE")
    tex.image = image
    slot = material.texture_slots.add()
    slot.texture = tex
    slot.texture_coords = "ORCO"
    slot.mapping = "FLAT"

    # add a rigid physics body
    bpy.ops.object.select_all(action='DESELECT')
    floor.select = True
    bpy.context.scene.objects.active = floor
    bpy.ops.rigidbody.object_add()
    body = floor.rigid_body
    floor.select = False

    # set physical properties
    body.friction = 0.89442718029
    body.restitution = 0.0
    body.collision_shape = "BOX"
    body.type = "PASSIVE"

    # select the floor
    scene.objects.active = floor
    floor.select = True

    return floor


def new_stimulus(spec):
    scene = bpy.data.scenes["Scene"]

    # create the first cube
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.data.objects["Cube"]

    # add a bevel to the cube object
    cube.select = True
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.bevel(offset_type='PERCENT', offset=3, segments=15)
    bpy.ops.object.editmode_toggle()
    cube.select = False

    def get_pos(d):
        return np.array([d["pos_{}".format(x)] for x in ["x", "y", "z"]])
    def get_quat(d):
        return np.array([d["quat_{}".format(x)] for x in ["w", "x", "y", "z"]])
    def get_scale(d):
        return np.array([d["scale_{}".format(x)] for x in ["x", "y", "z"]]) / 2

    # parse the stim id into block locations
    objects = sorted(spec.keys())
    cube.rotation_mode = 'QUATERNION'
    cube.rotation_quaternion = get_quat(spec[objects[0]])
    cube.scale = get_scale(spec[objects[0]])
    cube.location = get_pos(spec[objects[0]])

    # create copies of the cube to form the full stimulus
    blocks = [cube]
    for i in range(1, len(objects)):
        name = objects[i]
        mesh = bpy.data.meshes.new(name)
        ob_new = bpy.data.objects.new(name, mesh)
        ob_new.data = cube.data.copy()
        ob_new.data.name = "{}_data".format(name)
        ob_new.rotation_mode = 'QUATERNION'
        ob_new.rotation_quaternion = get_quat(spec[name])
        ob_new.scale = get_scale(spec[name])
        ob_new.location = get_pos(spec[name])
        scene.objects.link(ob_new)
        blocks.append(ob_new)

    # add physics for all the blocks
    for block in blocks:
        bpy.ops.object.select_all(action='DESELECT')
        block.select = True
        bpy.context.scene.objects.active = block
        bpy.ops.rigidbody.object_add()
        body = block.rigid_body
        block.select = False

        body.mass = spec[name]["mass"]
        body.friction = spec[name]["friction"]
        body.restitution = spec[name]["restitution"]
        body.use_deactivation = False
        body.linear_damping = 0.1
        body.angular_damping = 0.9
        body.collision_shape = "BOX"

    return blocks


def apply_colors(blocks, seed=None):
    if seed:
        rso = np.random.RandomState(seed)
    else:
        rso = np.random

    def get_color():
        return np.array(colorsys.hsv_to_rgb(rso.rand(), 1, 1))

    for block in blocks:
        # set the material properties to something plastic-y
        material = bpy.data.materials.new(name="{}_material".format(block.name))
        material.diffuse_color = get_color()
        material.diffuse_intensity = 0.8
        material.specular_color = (0.5, 0.5, 0.5)
        material.specular_intensity = 0.1
        material.specular_shader = 'WARDISO'
        material.ambient = 0
        block.data.materials.append(material)


def apply_redblue(blocks, blocktypes, seed=None):
    if seed:
        rso = np.random.RandomState(seed)
    else:
        rso = np.random

    def get_rgb(color, rso):
        """Add a little bit of variation to the saturation and
        value channels"""
        r = int(color[1:3], base=16) / 255.
        g = int(color[3:5], base=16) / 255.
        b = int(color[5:7], base=16) / 255.
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s > 0:
            s = max(0, min(1, s + rso.randn() / 8.))
        v = max(0, min(1, v + rso.randn() / 8.))
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (r, g, b)

    for block, blocktype in zip(blocks, blocktypes):
        # set the material properties to something plastic-y
        material = bpy.data.materials.new(name="{}_material".format(block.name))
        material.diffuse_intensity = 0.8
        material.specular_color = (0.5, 0.5, 0.5)
        material.specular_intensity = 0.1
        material.specular_shader = 'WARDISO'
        material.ambient = 0

        if blocktype == 0:
            material.diffuse_color = get_rgb("#CA0020", rso)
        else:
            material.diffuse_color = get_rgb("#0571B0", rso)

        block.data.materials.append(material)


def apply_stoneplastic(blocks, blocktypes, seed=None):
    if seed:
        rso = np.random.RandomState(seed)
    else:
        rso = np.random

    lcscale = 0.1
    hcscale = 0.1
    clip = lambda x: np.clip(x, 0, 1)

    plastic_image = bpy.data.images.load("resources/stripes.png")
    plastic_tex = bpy.data.textures.new(name="plastic_texture", type="IMAGE")
    plastic_tex.image = plastic_image

    stone_image = bpy.data.images.load("resources/granite-grayscale.jpg")
    stone_tex = bpy.data.textures.new(name="stone_texture", type="IMAGE")
    stone_tex.image = stone_image

    for block, blocktype in zip(blocks, blocktypes):
        material = bpy.data.materials.new(name="{}_material".format(block.name))
        material.diffuse_intensity = 0.8

        slot = material.texture_slots.add()
        slot.texture_coords = "ORCO"
        slot.mapping = "CUBE"
        slot.blend_type = "MULTIPLY"

        r = rso.randn() * lcscale / 2.0
        if blocktype == 0:
            slot.texture = plastic_tex
            slot.scale = (0.5, 0.5, 0.5)
            material.diffuse_color = np.array([
                clip(.3 + r),
                clip(1. + rso.randn() * lcscale / 2. + r),
                clip(.65 + rso.randn() * lcscale / 2. + r),
            ])
            material.specular_color = (0.5, 0.5, 0.5)
            material.specular_intensity = 0.1

        elif blocktype == 1:
            slot.texture = stone_tex
            slot.scale = (0.575, 0.575, 0.575)
            material.diffuse_color = np.array([
                clip(.65 + rso.randn() * hcscale / 2. + r),
                clip(.65 + r),
                clip(.65 + rso.randn() * hcscale / 2. + r)
            ])
            material.specular_color = (0, 0, 0)
            material.specular_intensity = 0

        block.data.materials.append(material)


def look_at(obj, point):
    direction = Vector(point) - obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj.rotation_euler = rot_quat.to_euler()


def new_camera(name, location, rotation):
    # create the camera
    data = bpy.data.cameras.new(name=name)
    camera = bpy.data.objects.new(name=name, object_data=data)

    # position the camera
    camera.location = location
    #camera.rotation_mode = 'XYZ'
    look_at(camera, rotation)

    # add it to the scene
    scene = bpy.data.scenes["Scene"]
    scene.objects.link(camera)
    scene.objects.active = camera
    camera.select = True
    bpy.context.scene.camera = camera

    return camera


def new_point_lamp(name, energy, location):
    data = bpy.data.lamps.new(name=name, type='POINT')
    lamp = bpy.data.objects.new(name=name, object_data=data)
    data.energy = energy
    lamp.location = location

    # add it to the scene
    scene = bpy.data.scenes["Scene"]
    scene.objects.link(lamp)
    scene.objects.active = lamp
    lamp.select = True

    return lamp


def new_spotlight(name, energy, location, rotation):
    data = bpy.data.lamps.new(name=name, type='SPOT')
    lamp = bpy.data.objects.new(name=name, object_data=data)
    data.energy = energy
    lamp.location = location
    look_at(lamp, rotation)

    # add it to the scene
    scene = bpy.data.scenes["Scene"]
    scene.objects.link(lamp)
    scene.objects.active = lamp
    lamp.select = True

    return lamp


def setup_world():
    # delete everything
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # create and position the camera
    camera = new_camera("Camera", (2, -8, 2.75), (0, 0, 1.5))

    # create and position the lights
    new_point_lamp('Lamp1', 2, camera.location)
    new_point_lamp('Lamp2', 4, (1.75, -4, 11.5))
    new_spotlight('Lamp3', 2, (8, -8, 10), (0, 0, 1.5))

    # add environment lighting
    world = bpy.data.worlds["World"]
    world.light_settings.use_environment_light = True
    world.use_sky_blend = True
    world.use_sky_real = False
    world.horizon_color = (0.061, 0.08, 0.1)
    world.zenith_color = (0.01, 0.004, 0.023)
    world.ambient_color = (0, 0, 0)

    # add a floor
    new_floor()

    # setup render properties
    scene = bpy.data.scenes["Scene"]
    scene.frame_end = 120
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.compression = 15

    # physics settings
    scene = bpy.data.scenes["Scene"]
    scene.gravity = (0, 0, -98.1)
    physics = scene.rigidbody_world
    physics.steps_per_second = 1000
    physics.solver_iterations = 100
    physics.time_scale = 1


def render(filepath):
    scene = bpy.data.scenes["Scene"]
    scene.render.filepath = filepath
    bpy.ops.ptcache.free_bake_all()
    bpy.ops.ptcache.bake_all(bake=True)
    bpy.ops.render.render(animation=True)


datasets = {
    "whichdirection-sameheight": "colors",
    "whichdirection": "colors",
    "whichdirection-mass": "stoneplastic",
    "willitfall": "colors",
    "willitfall-sameheight": "colors",
    "willitfall-mass": "stoneplastic",
    "whichisheavier-experimental": "redblue",
    "whichisheavier-training": "redblue"
}

for dataset in sorted(datasets.keys()):
    stims = pd.read_csv("stimuli/{}.csv".format(dataset))
    names = stims["name"].unique()

    for stim_id in names:
        ratios = stims.query("name == '{}'".format(stim_id))["ratio"].unique()

        for ratio in ratios:
            print((stim_id, ratio))
            filepath = "render/frames/{}/{}_ratio{}/".format(dataset, stim_id, ratio)
            if os.path.exists(filepath):
                continue

            spec = stims\
                .query("name == '{}' and ratio == {}".format(stim_id, ratio))\
                .set_index("object")\
                .sort_index(level="object")
            seed = int(str(int(hashlib.md5(stim_id.encode()).hexdigest(), base=16))[:9])

            setup_world()
            blocks = new_stimulus(spec.T.to_dict())
            if datasets[dataset] == "colors":
                apply_colors(blocks, seed=seed)
            elif datasets[dataset] == "stoneplastic":
                apply_stoneplastic(blocks, list(spec["blocktype"]), seed=seed)
            elif datasets[dataset] == "redblue":
                apply_redblue(blocks, list(spec["blocktype"]), seed=seed)
            else:
                raise ValueError("unhandled dataset type: {}".format(dataset[dataset]))

            render(filepath)
