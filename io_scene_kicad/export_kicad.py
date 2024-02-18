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


# マテリアルのベースカラーを取得
# ================================================================================================================================
def get_material_base_color(mat=None):
    # 戻り値の初期化
    base_color = (1, 1, 1)
    alpha_value = 1
    # アルファブレンドの有無取得
    alpha_blend = False
    if mat.blend_method == 'BLEND':
        alpha_blend = True

    # マテリアルがノードを使用しているとき
    if mat.use_nodes:
        # BSDFを検索
        for node in mat.node_tree.nodes:
            if node.type[0:4] != 'BSDF':
                continue
            # アルファブレンド有効でプリンシパルBSDFのノードのとき
            if alpha_blend and (node.type == 'BSDF_PRINCIPLED'):
                # #4番目のα値を取得する
                alpha_value = float(node.inputs[4].default_value)
            # ノードの値探索
            for io in node.inputs:
                # default_value 属性が無効のとき
                if not hasattr(io, 'default_value'):
                    # スキップ
                    continue
                # クラスタイプが配列以外はスキップ
                if str(type(io.default_value))[8:-2] != 'bpy_prop_array':
                    continue
                # 3つの要素（ベースカラー）を取得
                base_color = io.default_value[0:3]
                # 処理終了
                break
    # ベースからとα値を返す
    return (base_color, alpha_value)

# 基本色に倍率をかけて返す
# base_color 元の色
# zoom_color 各色別の比率(0～1)
# color_mag ベースカラーの増幅率
# 戻り値の下限値
# ================================================================================================================================
def zoom_color(base_color, zoom_color, color_mag, under=0.01, caption=""):
    # 戻り値の初期化
    ret_color = [0, 0, 0]
    # ベースカラーの各要素にアクセス
    for inx in range(len(base_color)):
        # 要素の色値取得
        color = float(base_color[inx])
        # 下限値より小さいなら
        if color < under:
            # 下限を設定
            color = under
        # 色倍数で乗算
        color *= color_mag
        # 色別比で乗算
        color *= float(zoom_color[inx])
        # 戻り値に格納
        ret_color[inx] = color
    # デバッグ:
    print("%s: base[%s], zoom[%s] => ret[%s]" % \
        (caption, ' '.join(map(str, base_color)), ' '.join(map(str, zoom_color)), ' '.join(map(str, ret_color))))
    # 計算後のカラーを返す
    return tuple(ret_color)

# ファイルライター
# 出力内容の括弧類に合わせてインデントを自動生成します。
# ================================================================================================================================
class FW:
    def __init__(self, file):
        # インデント初期レベル
        self.indent = 0
        # ファイル設定
        self.file = file

    # ファイル出力
    # data: 出力文字列
    # ofs: 一時的に加算するインデントレベル
    def print(self, data="", ofs=0):
        # アンインデント判定
        if re.search(r"[\]})]+", data):
            self.indent -= 1
        # インデント文字列生成
        prefix = (self.indent + ofs) * "\t"
        # 出力
        self.file.write(prefix + data)
        # インデント判定
        if re.search(r"[\[{(]+", data):
            self.indent += 1

    # 改行付ファイル出力
    # data: 出力文字列
    # ofs: 一時的に加算するインデントレベル
    def println(self, data="", ofs=0):
        self.print(data + "\n", ofs=ofs)

# 反復子操作
# ================================================================================================================================
class ItOp:
    def __init__(self, items=None):
        self.count = 0
        # 第2引数が有効なとき
        if not items is None:
            # 第2引数がリストのとき
            if type(items) is list:
                # リスト長をカウンタに設定
                self.count = len(items)
            # 第2引数が整数のとき
            elif type(items) is int:
                # 整数値をカウンタに設定
                self.count = int(items)
        # リセット時のカウンタを設定
        self.maxcount = self.count

    # 反復呼び出しのエントリ(1反復毎にCALLしてカウンタを減算する)
    def entry(self):
        self.count -= 1

    # カウンタのリセット
    def reset(self):
        # 反復数が0に達しているとき
        if self.count == 0:
            # 初期値に戻す
            self.count = self.maxcount

    # 末尾判定
    def get_last(self, last=",", empty=""):
        if self.count > 0:
            return last
        return empty

# オブジェクトモードの切り替え
# ================================================================================================================================
class ObjectModeApply:

    def __init__(self, obj, apply=True):
        # 編集モード状態取得
        self.is_editmode = (obj.mode == 'EDIT')
        if apply:
            self.store()
    
    def store(self):
        # 編集モードならモードを戻す
        if self.is_editmode:
            bpy.ops.object.editmode_toggle()

    def restore(self):
        # 編集モードならモードを戻す
        if self.is_editmode:
            bpy.ops.object.editmode_toggle()

# BMesh の保存
# ================================================================================================================================
def save_bmesh(
    fw: FW,         # ファイルライター
    bm,             # 対象のBMesh
    materials,      # マテリアル群
    color_mag,      # 色倍率
    last            # 継続記号（',' or ''）
    ):

    # シェイプ定義開始
    fw.println('Shape {')
    # ※マテリアル定義が無くてもmaterial記述を生成しないとKiCadはモデルを表示しない。
    fw.println('appearance Appearance {')
    fw.println('material Material {')

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
        for m in materials:
            if m is None:
                continue
            base_color = (1, 1, 1)  # White
            alpha_value = 1
            # ノードを使用するとき
            if m.use_nodes:
                # ノードからα値を取得（プリンシパルBSDFのアルファ値取得）
                base_color,alpha_value = get_material_base_color(m)

            # マテリアル名(※日本語名は KiCad が認識しない)
            fw.println('# Material %r, %s' % (materialid(m.name), vrmlid(m.name)))
            # 拡散反射色
            fw.println("diffuseColor %.3g %.3g %.3g" % zoom_color(base_color, m.diffuse_color, color_mag, caption=" diffuse"))
            # 光源反射色
            fw.println("emissiveColor %.3g %.3g %.3g" % zoom_color(base_color, [0.3, 0.3, 0.3], color_mag, caption="emissive"))
            # 鏡面反射色
            fw.println("specularColor %.3g %.3g %.3g" % zoom_color(base_color, m.specular_color, color_mag, caption="specular"))
            # 環境光反射率
            fw.println("ambientIntensity %.3g" % ao_factor)
            # 透過率
            fw.println("transparency %.3g" % (1 - alpha_value))
            # 鏡面反射率
            fw.println("shininess %.3g" % m.specular_intensity)
            # 1つのマテリアル生成後終了
            break
    else:
        fw.println("# No material definition.")

    fw.println('}')  # end 'Material'
    fw.println('}')  # end 'Appearance'

    fw.println('geometry IndexedFaceSet {')
    fw.println('coord Coordinate {')
    fw.println('point [')

    # 座標列の生成
    v = None
    nl_ok = False

    # 反復操作オブジェクト生成
    itverts = ItOp(bm.verts)            # データ終端判定の指定

    for v in bm.verts:

        # 反復操作エントリ
        itverts.entry()

        # 丸め誤差をゼロにスナップする
        if abs (v.co[0]) < 0.00001:
            v.co[0] = 0
        if abs (v.co[1]) < 0.00001:
            v.co[1] = 0
        if abs (v.co[2]) < 0.00001:
            v.co[2] = 0

        # カンマと改行文字制御
        set_sep = itverts.get_last()

        fw.println("%.6g %.6g %.6g%s" % \
           (v.co[0], v.co[1], v.co[2], set_sep))

    del v
    fw.println(']')  # end point[]
    fw.println('}')  # end Coordinate

    # 座標インデックスの列生成
    fw.println('coordIndex [')
    f = fv = None
    itfaces = ItOp(bm.faces)
    for f in bm.faces:

        fv = f.verts[:]

        # カンマと改行文字制御
        set_sep = itfaces.get_last()

        fw.println("%d, %d, %d, -1%s" % \
            (fv[0].index, fv[1].index, fv[2].index, set_sep))

    del f, fv
    fw.println(']')  # end 'coordIndex[]'
    fw.println('}')  # end 'IndexedFaceSet'

    fw.println('}%s' % (last))  # end 'Shape'


# メッシュへのマトリクス適用
# ================================================================================================================================
def mesh_apply(bm, obj, global_matrix):
    # 回転
    mat_rot_x = mathutils.Matrix.Rotation(obj.rotation_euler[0], 4, 'X')
    mat_rot_y = mathutils.Matrix.Rotation(obj.rotation_euler[1], 4, 'Y')
    mat_rot_z = mathutils.Matrix.Rotation(obj.rotation_euler[2], 4, 'Z')
    mat_rot = mat_rot_x @ mat_rot_y @ mat_rot_z
    # スケール
    mat_sca_x = mathutils.Matrix.Scale(obj.scale[0], 4, (1, 0, 0))
    mat_sca_y = mathutils.Matrix.Scale(obj.scale[1], 4, (0, 1, 0))
    mat_sca_z = mathutils.Matrix.Scale(obj.scale[2], 4, (0, 0, 1))
    mat_sca = mat_sca_x @ mat_sca_y @ mat_sca_z
    # マトリクス展開
    mat_out = mat_rot @ mat_sca @ global_matrix @ obj.matrix_world
    # マトリクス適用
    bm.transform(mat_out)

# オブジェクトの保存
# ================================================================================================================================
def save_object(fw, global_matrix,
                scene, obj,
                use_mesh_modifiers,
                color_mag,
                last
                ):

    # ※オブジェクトはメッシュ必須
    assert(obj.type == 'MESH')

    # モディファイアを適用するとき
    if use_mesh_modifiers:

        # オブジェクトモードへ移行
        mode_state = ObjectModeApply(obj, True)

        # 仮にプレビューでモディファイヤを適用する
        dg = bpy.context.evaluated_depsgraph_get()
        me = obj.to_mesh(preserve_all_data_layers=True, depsgraph=dg)

        # モディファイヤを適用したオブジェクトのコピーを作成
        bm = bmesh.new()
        bm.from_mesh(me)
        #obj.to_mesh_clear() #<-これやらないよ

        # 編集モードの復元
        mode_state.restore()
    else:
        me = obj.data
        # 編集モードのとき
        if obj.mode == 'EDIT':
            # 編集状態のメッシュからBMeshを取得
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()
        else:
            bm = bmesh.new()
            bm.from_mesh(me)

    # 変換前に三角形分割を行う（変換後に行うと失敗する。2.7以前）
    bmesh.ops.triangulate(bm, faces=bm.faces)

    # ワールド座標系でのマトリックス成分取得
    loc, rot, scale = obj.matrix_world.decompose()

    # マトリックス適用
    mesh_apply(bm, obj, global_matrix)

    # BMeshの保存
    save_bmesh(fw, bm, me.materials, color_mag, last)

    # BMesh インスタンス解放
    bm.free()

# オブジェクトIDを VRML用に変換
# ================================================================================================================================
def vrmlid(n):
    return '_' + n.replace ('.', '_').replace (' ','_')

# マテリアル名をVRML用に変換
# ================================================================================================================================
# VRML との互換性を保つためにマテリアル名を変換しますが、先頭の '_' がない場合は、
# wrl を再インポートしてマテリアル名を保持する可能性がある
def materialid(n):
    return n.replace ('.', '_').replace (' ','-')

# エクスポートメインエントリ
# ================================================================================================================================
def save(operator,
         context,
         filepath="",
         global_matrix=None,
         use_selection=False,
         use_mesh_modifiers=True,
         use_origin_to_center=True,
         global_mag=1.5000):

    # シーンの取得
    scene = context.scene

    # 選択のみが有効なとき
    if use_selection:
        # 選択済みオブジェクトを取得
        objects = context.selected_objects
    else:
        # シーン全てのオブジェクトを取得
        objects = scene.objects

    # [原点を中心にする]オプション指定のとき
    if use_origin_to_center:
        # 選択したオブジェクトの最上位の親を検索します
        top = None
        toploc = None
        for obj in objects:
            # メッシュ以外はスキップ
            if obj.type != 'MESH':
                continue
            # 非表示オブジェクトはスキップ
            if not obj.visible_get():
                continue

            # 最上位のオブジェクトを取得
            cur = obj
            while not (cur.parent is None):
                cur = cur.parent
            loc, rot, scale = cur.matrix_world.decompose()

            if top == None:
                top = cur
                toploc = loc
            elif (top != cur) and (toploc != loc):
                toploc = toploc[:]
                loc = loc[:]
                msg = localeui.gtext("ObjectsWithDifferentOriginsWereFound")
                operator.report ({'ERROR'}, msg % (top.name, cur.name, toploc [0], toploc [1], toploc [2], loc [0], loc [1], loc [2]))
                # 処理を中止する
                return {'CANCELLED'}

        # 最上位オブジェクトがあるとき
        if not (top is None):
            # 最上位オブジェクトの位置を原点移動
            global_matrix = global_matrix @ mathutils.Matrix.Translation (-toploc)

    file = None
    try:
        # ファイルを開く
        file = open(filepath, 'w', encoding='utf-8')

        # ファイルライター作成
        fw = FW(file)

        # VRML2 エントリ書込み
        fw.println('#VRML V2.0 utf8')
        fw.println('#modeled using blender3d http://blender.org')

        # プリミティブ定義開始
        fw.println()
        fw.println("Group {")
        fw.println("children [")

        obj = None
        itobj = ItOp(objects)
        for obj in objects:
            # 反復操作エントリ
            itobj.entry()

            # 末尾文字取得
            last = itobj.get_last(",")

            # メッシュ以外はスキップ
            if (obj.type != 'MESH'):
                continue

            # 非表示オブジェクトはスキップ
            if not obj.visible_get():
                continue

            # オブジェクトの名称出力
            fw.println()
            fw.println("# %r (%s)" % (obj.name, vrmlid (obj.name)), ofs=1)

            # オブジェクトの保存
            save_object(fw, global_matrix, scene, obj, use_mesh_modifiers, global_mag, last)

        # プリミティブ定義終了
        fw.println("]")
        fw.println("}")

    except FileNotFoundError as e:
        pass
    finally:
        if not file is None:
            file.close()

    msg = localeui.gtext("CompletedOutput", "%s の出力を完了しました。")
    operator.report({'INFO'}, msg % (filepath))

    return {'FINISHED'}


# ================================================================================================================================
