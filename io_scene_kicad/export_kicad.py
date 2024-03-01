# GNU GENERAL PUBLIC LICENSE
# Version 3, 29 June 2007
#
# This file is part of io_scene_kicad.
# Copyright (C) 2024  Hideki Matsunobu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import bpy
import bpy_extras
import bmesh
import mathutils
import os
import re
from bpy_extras import object_utils
from . import localeui
from . import bautils

# DEBUG = False
DEBUG = True


# ================================================================================================================================
class MeshExporter:

    global_matrix: None
    global_scale: None
    local_matrix: None
    local_origin: None
    use_selection: False
    use_worigin_to_center: False
    use_mesh_modifiers: True
    fetch_children: False
    color_mag: 1.5000
    # 単独シンボル生成時のコレクション（ワールド原点が中心）
    target_objs: list
    # 原点別のコレクション
    origin_objs: dict
    fw: bautils.FW

    # ------------------------------------------------------------------------------------------------
    def __init__(self):
        pass

    # 変換対象のオブジェクトか否かを取得
    # ------------------------------------------------------------------------------------------------
    def avail_obj(self, obj, skipSelection=False):
        # メッシュでないとき
        if obj.type != 'MESH':
            return False
        # オブジェクトが非表示のとき
        if not obj.visible_get():
            return False
        # 選択をスキップしない指示で、[選択のみ]チェックでオブジェクトが未選択のとき
        if (not skipSelection) and self.use_selection and (not obj.select_get()):
            return False
        return True

    # ------------------------------------------------------------------------------------------------
    def avail_objs(self, objs, skipSelection=False):
        for obj in objs:
            if not self.avail_obj(obj, skipSelection=skipSelection):
                continue
            yield obj

    # 親オブジェクト取得
    # ------------------------------------------------------------------------------------------------
    def parent_get(self, obj):
        target = obj
        while not target.parent is None:
            target = target.parent
        loc, rot, scale = target.matrix_world.decompose()
        # 親オブジェクト, objが誰かの子かどうか, 位置情報
        return (target, True if target != obj else False, mathutils.Vector(loc))

    # オブジェクトの子オブジェクトを収集
    # ------------------------------------------------------------------------------------------------
    def children_get(self, obj):
        collect = []
        # 子オブジェクトを対象とするとき
        # ※子オブジェクトを選択時はcontext.selected_objectsに含まれるのでここではチェックしない
        if self.fetch_children:
            for child in obj.children:#_recursive:
                # 収集対象オブジェクトのとき
                if self.avail_obj(child):
                    # リストに追加
                    collect.append(child)
        # 収集したリストを返す
        return collect
    
# メッシュへのマトリクス適用
    # ------------------------------------------------------------------------------------------------
    def bmesh_locRotScale(self, bm, obj):
        # glb_mat = obj.matrix_world  # 表示はOK.位置とスケールがNG
        mtx = self.local_origin @ obj.matrix_world @ self.local_matrix
        # マトリクスから位置・回転・スケールを取得
        loc, rot, sca = mtx.decompose()
        assert(type(loc) is mathutils.Vector)
        assert(type(rot) is mathutils.Quaternion)
        assert(type(sca) is mathutils.Vector)
        # VRMLでは移動量にスケールする必要あり
        loc *= sca
        # tupleに変換(rotationはQuaternionからEulerに置換)
        locs = bautils.from_tuples(loc)
        rots = bautils.from_tuples(rot)
        scas = bautils.from_tuples(sca)
        for loc in locs:
            self.fw.println("translation %g %g %g" % loc)
        for rot in rots:
            self.fw.println("rotation %g %g %g %g" % rot)
        for sca in scas:
            self.fw.println("scale %g %g %g" % sca)
        # self.fw.println("bboxCenter %g %g %g" % from_tuple(self.local_origin))
        # VRML上でトランスフォームするのでBMeshのトランスフォームは不要。
        ## bm.transform(glb_mat)

    # Materialの保存
    # ------------------------------------------------------------------------------------------------
    def save_materials(self, obj, materials):

        # ※マテリアル定義が無くてもmaterial記述を生成しないとKiCadはモデルを表示しない。
        self.fw.println('appearance Appearance {')
        self.fw.println('material Material {')
        # マテリアル定義があるとき
        if len(materials) > 0:
            # ライト設定があるとき
            if not bpy.data.worlds[0].light_settings is None:
                # ライト設定のao_factorを取得
                ao_factor = bpy.data.worlds[0].light_settings.ao_factor
            # ライト設定がないとき
            else:
                # α値は1固定
                ao_factor = 1.0

            # 最初のマテリアルのみエクスポート（サブメッシュ毎に1つのマテリアルに制限）
            maters = bautils.ItOp(materials)
            for m in maters.loop(lambda o: not o is None):
                base_color = (1, 1, 1)  # White
                alpha_value = 1
                # ノードを使用するとき
                if m.use_nodes:
                    # ノードからα値を取得（プリンシパルBSDFのアルファ値取得）
                    base_color, alpha_value = bautils.get_material_base_color(m)

                # マテリアル名(※日本語名は KiCad が認識しない)
                self.fw.println('# Material %r, %s' % (bautils.materialid(m.name), bautils.vrmlid(m.name)))
                # 拡散反射色
                self.fw.println("diffuseColor %.3g %.3g %.3g" % bautils.zoom_color(base_color, m.diffuse_color, self.color_mag, caption=" diffuse"))
                # 光源反射色
                self.fw.println("emissiveColor %.3g %.3g %.3g" % bautils.zoom_color(base_color, [0.3, 0.3, 0.3], self.color_mag, caption="emissive"))
                # 鏡面反射色
                self.fw.println("specularColor %.3g %.3g %.3g" % bautils.zoom_color(base_color, m.specular_color, self.color_mag, caption="specular"))
                # 環境光反射率
                self.fw.println("ambientIntensity %.3g" % ao_factor)
                # 透過率
                self.fw.println("transparency %.3g" % (1 - alpha_value))
                # 鏡面反射率
                self.fw.println("shininess %.3g" % m.specular_intensity)
                # 1つのマテリアル生成後終了
                break
        else:
            self.fw.println("# No material definition.")

        self.fw.println('}')  # end 'Material'
        self.fw.println('}')  # end 'Appearance'

    # BMesh の保存
    # ------------------------------------------------------------------------------------------------
    def save_bmesh(self,
            bm,             # 対象のBMesh
            obj,            # オブジェクト
            materials       # マテリアル群
            ):

        self.fw.println("# %r (%s)" % (obj.name, bautils.vrmlid(obj.name)), ofs=1)
        self.fw.println('Transform {')

        self.bmesh_locRotScale(bm, obj)

        self.fw.println('children [')
        self.fw.println('Shape {')

        self.save_materials(obj, materials)

        self.fw.println('geometry IndexedFaceSet {')
        self.fw.println('coord Coordinate {')
        self.fw.println('point [')

        # 座標列の生成
        v = None
        # 反復操作オブジェクト生成
        itverts = bautils.ItOp(bm.verts)    # データ終端判定の指定
        for v in itverts.loop():

            # 丸め誤差をゼロにスナップする
            v.co[0] = 0 if abs(v.co[0]) < 0.00001 else v.co[0]
            v.co[1] = 0 if abs(v.co[1]) < 0.00001 else v.co[1]
            v.co[2] = 0 if abs(v.co[2]) < 0.00001 else v.co[2]

            self.fw.println("%.6g %.6g %.6g%s" % \
                (v.co[0], v.co[1], v.co[2], itverts.last_get()))

            del v

        self.fw.println(']')  # end 'point'
        self.fw.println('}')  # end 'Coordinate'

        # 座標インデックスの列生成
        self.fw.println('coordIndex [')
        f = fv = None
        itfaces = bautils.ItOp(bm.faces)
        for f in itfaces.loop():

            fv = f.verts[:]

            self.fw.println("%d, %d, %d, -1%s" % \
                (fv[0].index, fv[1].index, fv[2].index, itfaces.last_get()))

            del f, fv

        self.fw.println(']')     # end 'coordIndex'
        self.fw.println('}')     # end 'IndexedFaceSet'

        self.fw.println('}')     # end 'Shape'
        self.fw.println(']')     # end 'children'
        self.fw.print('}')       # end 'Transform'
   

    # オブジェクトの保存
    # ------------------------------------------------------------------------------------------------
    def save_object(self, obj):

        # ※オブジェクトはメッシュ必須
        assert(obj.type == 'MESH')

        # 選択済みオブジェクトの選択解除
        sel = bautils.Selector()
        # 複製オブジェクトのインスタンス兼リリースフラグ
        rel_obj = None

        # モディファイアを適用するとき
        if self.use_mesh_modifiers:
            # オブジェクトモードへ移行
            mode_state = bautils.ObjectModeApply(obj, True)
            # 対象オブジェクトの選択設定
            state = sel.set_select(obj)
            # 変換->メッシュでモディファイヤを適用したオブジェクトを生成する
            bpy.ops.object.convert(target='MESH', keep_original=True)
            # モディファイヤ適用後の複製されたメッシュを取得
            rel_obj = bpy.context.active_object
            # メッシュ参照
            me = rel_obj.data
            # 選択状態復元
            sel.restore_select(obj, state)
            # 編集モードの復元
            mode_state.restore()
        else:
            # メッシュ参照
            me = obj.data

        # 編集モードのとき
        if obj.mode == 'EDIT':
            # 編集状態のメッシュからBMeshを取得
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()
        else:
            # BMesh を作成
            bm = bmesh.new()
            bm.from_mesh(me)

        # 変換前に三角形分割を行う（変換後に行うと失敗する。2.7以前）
        bmesh.ops.triangulate(bm, faces=bm.faces)
        # BMeshの保存
        self.save_bmesh(bm, obj, me.materials)
        # BMesh インスタンス解放
        bm.free()

        # 複製されたオブジェクトがあるとき
        if not rel_obj is None:
            # 複製オブジェクトを選択して削除
            sel.set_select(rel_obj)
            bpy.ops.object.delete(use_global=True, confirm=False)
            rel_obj = None

        # 選択済みオブジェクトの選択復元
        sel.restore_select_all()

    # ------------------------------------------------------------------------------------------------
    def save_objects(self, objects):

            # プリミティブ定義開始
            self.fw.println()
            self.fw.println("Group {")
            self.fw.println("children [")

            obj = None
            itobj = bautils.ItOp(objects)
            # メッシュで表示以外はスキップ
            for obj in itobj.loop(lambda o: o.type == 'MESH' and o.visible_get()):

                # オブジェクトの保存
                self.save_object(obj)

                # end 'Shape'
                self.fw.println('%s' % (itobj.last_get()))

                del obj

            # プリミティブ定義終了
            self.fw.println("]")
            self.fw.println("}")

    # ファイルに出力
    # ------------------------------------------------------------------------------------------------
    def save_to_file(self, filepath, objects):
        file = None
        try:
            # ファイルを開く
            file = open(filepath, 'w', encoding='utf-8')

            # ファイルライター作成
            self.fw = bautils.FW(file)

            # VRML2 エントリ書込み
            self.fw.println('#VRML V2.0 utf8')
            self.fw.println('#modeled using blender3d http://blender.org')

            # オブジェクトの保存
            self.save_objects(objects)

        except FileNotFoundError as e:
            pass
        finally:
            if not file is None:
                file.close()

    # コレクション収集
    # ------------------------------------------------------------------------------------------------
    def target_collect(self, *args):
        for target in args:
            if type(target) is tuple or type(target) is list:
                for child in target:
                    if not child in self.target_objs:
                        self.target_objs.append(child)
            else:
                if not target in self.target_objs:
                    self.target_objs.append(target)

    # 位置情報別のコレクション収集
    # ------------------------------------------------------------------------------------------------
    def location_map_collect(self, location, *args, subkey=None):
        # 位置情報(恐らくVector)をタプルに置換
        loc = tuple(location)
        # サブキー指定ありのとき
        if not subkey is None:
            # 位置情報が未登録のとき
            if not loc in self.origin_objs:
                # 位置情報要素の空辞書を登録
                self.origin_objs[loc] = {}
            # サブキー要素が未登録のとき
            if not subkey in self.origin_objs[loc]:
                # サブキー要素の空リストを登録
                self.origin_objs[loc][subkey] = []
            for target in args:
                # ターゲットがtuple/listのいずれかのとき
                if type(target) is tuple or type(target) is list:
                    for child in target:
                        # オブジェクトが未登録のとき
                        if not child in self.origin_objs[loc][subkey]:
                            self.origin_objs[loc][subkey].append(child)
                # ターゲットがtuple/listの何れもなく、オブジェクトが未登録のとき
                elif not target in self.origin_objs[loc][subkey]:
                    self.origin_objs[loc][subkey].append(target)
        # サブキー指定なしのとき
        else:
            # 位置情報が未登録のとき
            if not loc in self.origin_objs:
                # 位置情報要素の空リストを登録
                self.origin_objs[loc] = []

            for target in args:
                # ターゲットがtuple/listのいずれかのとき
                if type(target) is tuple or type(target) is list:
                    for child in target:
                        # サブキー指定なしでオブジェクトが未登録のとき
                        if not child in self.origin_objs[loc]:
                            self.origin_objs[loc].append(child)
                # ターゲットがtuple/listの何れもなく、オブジェクトが未登録のとき
                elif not target in self.origin_objs[loc]:
                    self.origin_objs[loc].append(target)

    # ------------------------------------------------------------------------------------------------
    def collector(self, context):
          
        # 収集コレクションの初期化
        self.target_objs = []
        self.origin_objs = {}

        # 全オブジェクトを登録リストに追加
        it_objs = bautils.ItOp(context.scene.objects)
        for obj in it_objs.loop(lambda o: self.avail_obj(o)):
            # 対象外はスキップ(メッシュ and 表示 and ([選択のみ]なしor[選択のみ]で選択済))
            # if not self.avail_obj(obj):
            #     continue
            # 親オブジェクトを取得
            parent_obj, is_child, parent_loc = self.parent_get(obj)
            # 子オブジェクトを取得
            children = self.children_get(obj)
            # objは子オブジェクトであるとき
            if is_child:
                # ワールド原点を中心とするとき
                if  self.use_worigin_to_center:
                    # 親が収集対象に該当するとき
                    if self.avail_obj(parent_obj):
                        # 親オブジェクトを収集
                        self.target_collect(parent_obj)
                    self.target_collect(obj, children)
                else:
                    # 親が収集対象に該当するとき
                    if self.avail_obj(parent_obj):
                        # 親オブジェクトを収集
                        self.location_map_collect(parent_loc, parent_obj)
                    self.location_map_collect(parent_loc, obj, children)
            # オブジェクトが最上位オブジェクトであるとき
            else:
                # ワールド原点を中心とするとき
                if  self.use_worigin_to_center:
                    # 子オブジェクト対象以外、かつ、選択のみでobjが未選択のとき
                    if (not self.fetch_children) and self.use_selection and (not obj.select_get()):
                        # スキップ
                        continue
                    self.target_collect(obj, children)
                else:
                    self.location_map_collect(parent_loc, obj, children)

    # エクスポート実行
    # ------------------------------------------------------------------------------------------------
    def execute(self, operator, filepath):
        # マトリクス設定
        self.local_matrix = self.global_matrix * self.global_scale
        # 平行移動量初期値（移動なし）
        self.local_origin = mathutils.Matrix.Translation((0, 0, 0))
        # ワールド原点を中心とするオブジェクト収集があるとき
        if len(self.target_objs) > 0:
            self.save_to_file(filepath, self.target_objs)
            # 完了メッセージ差k製
            completed_msg = localeui.gtext("CompletedOutput", "%s の出力を完了しました。")
            # レポート出力
            operator.report({'INFO'}, completed_msg % (filepath))
        else:
            # 原点別オブジェクトの出力
            cfiles = 0
            msgs = []
            for origin in self.origin_objs:
                # 平行移動量
                self.local_origin = mathutils.Matrix.Translation(-mathutils.Vector(origin))
                # モデルのオブジェクトリストを取得
                collect = self.origin_objs[origin]
                # オブジェクト名でソート
                sublist = sorted(collect, key=lambda o: o.name)
                # 生成ファイルパスの取得
                subpath = bautils.get_subpath(filepath, sublist[0].name)
                # ファイルへ保存
                self.save_to_file(subpath, collect)
                cfiles = cfiles + 1
                proceeded_msg = localeui.gtext("ProceededOutput", "%s を出力しました。")
                msgs.append(proceeded_msg % (os.path.basename(subpath)))
            # 完了メッセージ差k製
            count_msg = localeui.gtext("CompletedCountOutput", "件のファイル出力を完了しました。")
            msgs.append(count_msg % (cfiles))
            # レポート出力
            operator.report({'INFO'}, '\n'.join(msgs))

# エクスポートメインエントリ
# ================================================================================================================================
def save(operator,
         context,
         filepath="",
         global_matrix=None,
         global_scale=None,
         use_selection=False,
         use_worigin_to_center=False,
         use_mesh_modifiers=True,
         fetch_children=False,
         color_mag=1.5000):

    mexp = MeshExporter()
    mexp.global_matrix = global_matrix
    mexp.global_scale = global_scale
    mexp.use_selection = use_selection
    mexp.use_worigin_to_center = use_worigin_to_center
    mexp.use_mesh_modifiers = use_mesh_modifiers
    mexp.fetch_children = fetch_children
    mexp.color_mag = color_mag

    mexp.collector(context)
    mexp.execute(operator, filepath)

    return {'FINISHED'}

# ================================================================================================================================
