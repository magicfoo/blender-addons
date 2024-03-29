# Copyright 2018-2019 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bpy
from math import sqrt
from mathutils import Quaternion
from .gltf2_blender_node import BlenderNode
from .gltf2_blender_skin import BlenderSkin
from .gltf2_blender_animation import BlenderAnimation


class BlenderScene():
    """Blender Scene."""
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def create(gltf, scene_idx):
        """Scene creation."""
        gltf.blender_active_collection = None
        if scene_idx is not None:
            pyscene = gltf.data.scenes[scene_idx]
            list_nodes = pyscene.nodes

            # Create a new scene only if not already exists in .blend file
            # TODO : put in current scene instead ?
            if pyscene.name not in [scene.name for scene in bpy.data.scenes]:
                # TODO: There is a bug in 2.8 alpha that break CLEAR_KEEP_TRANSFORM
                # if we are creating a new scene
                scene = bpy.context.scene
                if bpy.context.collection.name in bpy.data.collections: # avoid master collection
                    gltf.blender_active_collection = bpy.context.collection.name
                if scene.render.engine not in ['CYCLES', 'BLENDER_EEVEE']:
                    scene.render.engine = "BLENDER_EEVEE"

                gltf.blender_scene = scene.name
            else:
                gltf.blender_scene = pyscene.name

            # Switch to newly created main scene
            bpy.context.window.scene = bpy.data.scenes[gltf.blender_scene]
            if bpy.context.collection.name in bpy.data.collections: # avoid master collection
                gltf.blender_active_collection = bpy.context.collection.name

        else:
            # No scene in glTF file, create all objects in current scene
            scene = bpy.context.scene
            if scene.render.engine not in ['CYCLES', 'BLENDER_EEVEE']:
                scene.render.engine = "BLENDER_EEVEE"
            if bpy.context.collection.name in bpy.data.collections: # avoid master collection
                gltf.blender_active_collection = bpy.context.collection.name
            gltf.blender_scene = scene.name
            list_nodes = BlenderScene.get_root_nodes(gltf)

        if bpy.app.debug_value != 100:
            # Create Yup2Zup empty
            obj_rotation = bpy.data.objects.new("Yup2Zup", None)
            obj_rotation.rotation_mode = 'QUATERNION'
            obj_rotation.rotation_quaternion = Quaternion((sqrt(2) / 2, sqrt(2) / 2, 0.0, 0.0))

            if gltf.blender_active_collection is not None:
                bpy.data.collections[gltf.blender_active_collection].objects.link(obj_rotation)
            else:
                bpy.data.scenes[gltf.blender_scene].collection.objects.link(obj_rotation)

        if list_nodes is not None:
            for node_idx in list_nodes:
                BlenderNode.create(gltf, node_idx, None)  # None => No parent

        # Now that all mesh / bones are created, create vertex groups on mesh
        if gltf.data.skins:
            for skin_id, skin in enumerate(gltf.data.skins):
                if hasattr(skin, "node_ids"):
                    BlenderSkin.create_vertex_groups(gltf, skin_id)

            for skin_id, skin in enumerate(gltf.data.skins):
                if hasattr(skin, "node_ids"):
                    BlenderSkin.assign_vertex_groups(gltf, skin_id)

            for skin_id, skin in enumerate(gltf.data.skins):
                if hasattr(skin, "node_ids"):
                    BlenderSkin.create_armature_modifiers(gltf, skin_id)

        if gltf.data.animations:
            gltf.animation_managed = []
            for anim_idx, anim in enumerate(gltf.data.animations):
                gltf.current_animation_names = {}
                gltf.actions_stashed= {}
                if list_nodes is not None:
                    for node_idx in list_nodes:
                        BlenderAnimation.anim(gltf, anim_idx, node_idx)
                for an in gltf.current_animation_names.values():
                    gltf.animation_managed.append(an)
                    for node_idx in list_nodes:
                        BlenderAnimation.stash_action(gltf, anim_idx, node_idx, an)
            for node_idx in list_nodes:
                BlenderAnimation.restore_last_action(gltf, node_idx)

        if bpy.app.debug_value != 100:
            # Parent root node to rotation object
            if list_nodes is not None:
                exclude_nodes = []
                for node_idx in list_nodes:
                    if gltf.data.nodes[node_idx].is_joint:
                        # Do not change parent if root node is already parented (can be the case for skinned mesh)
                        if not bpy.data.objects[gltf.data.nodes[node_idx].blender_armature_name].parent:
                            bpy.data.objects[gltf.data.nodes[node_idx].blender_armature_name].parent = obj_rotation
                        else:
                            exclude_nodes.append(node_idx)
                    else:
                        # Do not change parent if root node is already parented (can be the case for skinned mesh)
                        if not bpy.data.objects[gltf.data.nodes[node_idx].blender_object].parent:
                            bpy.data.objects[gltf.data.nodes[node_idx].blender_object].parent = obj_rotation
                        else:
                            exclude_nodes.append(node_idx)

                if gltf.animation_object is False:





                    # Avoid rotation bug if collection is hidden or disabled
                    if gltf.blender_active_collection is not None:
                        gltf.collection_hide_viewport = bpy.data.collections[gltf.blender_active_collection].hide_viewport
                        bpy.data.collections[gltf.blender_active_collection].hide_viewport = False
                        # TODO for visibility ... but seems not exposed on bpy for now

                    for node_idx in list_nodes:

                        if node_idx in exclude_nodes:
                            continue # for root node that are parented by the process
                            # for example skinned meshes

                        for obj_ in bpy.context.scene.objects:
                            obj_.select_set(False)
                        if gltf.data.nodes[node_idx].is_joint:
                            bpy.data.objects[gltf.data.nodes[node_idx].blender_armature_name].select_set(True)
                            bpy.context.view_layer.objects.active = bpy.data.objects[gltf.data.nodes[node_idx].blender_armature_name]

                        else:
                            bpy.data.objects[gltf.data.nodes[node_idx].blender_object].select_set(True)
                            bpy.context.view_layer.objects.active = bpy.data.objects[gltf.data.nodes[node_idx].blender_object]

                        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

                    # remove object
                    #bpy.context.scene.collection.objects.unlink(obj_rotation)
                    bpy.data.objects.remove(obj_rotation)

                    # Restore collection hiden / disabled values
                    if gltf.blender_active_collection is not None:
                        bpy.data.collections[gltf.blender_active_collection].hide_viewport = gltf.collection_hide_viewport
                        # TODO restore visibility when expose in bpy

        # Make first root object the new active one
        if list_nodes is not None:
            bpy.context.view_layer.objects.active = bpy.data.objects[gltf.data.nodes[list_nodes[0]].blender_object]

    @staticmethod
    def get_root_nodes(gltf):
        if gltf.data.nodes is None:
            return None

        parents = {}
        for idx, node  in enumerate(gltf.data.nodes):
            pynode = gltf.data.nodes[idx]
            if pynode.children:
                for child_idx in pynode.children:
                    parents[child_idx] = idx

        roots = []
        for idx, node in enumerate(gltf.data.nodes):
            if idx not in parents.keys():
                roots.append(idx)

        return roots

