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

# ================================================================================================================================

bl_info = {
    "name": "WRL (KiCad) エクスポート",
    "author": "Hideki Matsunobu",
    "version": (0, 1),
    "blender": (3, 6, 0),
    "location": "ファイル→エクスポート",
    "description": "メッシュ オブジェクトを KiCad 用の WRL ファイルにエクスポートします。",
    "warning": "",
    "doc_url": "https://github.com/maznobu/io-scene-kicad",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}

# ※このアドインの動作は、Blender 3.6, 4.0 で確認しています。
# The operation of this add-in has been confirmed with Blender 3.6 and 4.0.
# ================================================================================================================================

import os
import re
import webbrowser
from . import localeui

if "bpy" in locals():
    import importlib
    if "export_kicad" in locals():
        importlib.reload(export_kicad)

import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatProperty,
)
from bpy_extras.io_utils import (
    ExportHelper,
    orientation_helper,
    axis_conversion,
    path_reference_mode
)

# ================================================================================================================================
@orientation_helper(axis_forward='Y', axis_up='Z')
class ExportWRL(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.wrl"
    bl_label = "WRLをエクスポート"
    filename_ext = ".wrl"

    def checkChangeCallback(self, context):
        o = self.use_worigin_to_center

    filter_glob: StringProperty(
        default="*.wrl",
        options={'HIDDEN'},
    ) # type: ignore
    # オプション：選択のみ 初期値 False
    use_selection: BoolProperty(
        name=localeui.gtext("use_selection", "選択オブジェクトのみ"),
        description=localeui.gtext("desc_selection", "選択したオブジェクトのみをエクスポートします"),
        default=False,
    ) # type: ignore
 
    # オプション：子オブジェクトを対象とする。初期値 True
    fetch_children: BoolProperty(
        name=localeui.gtext("fetch_children", "子オブジェクトを対象"),
        description=localeui.gtext("desc_fetch_children", "未選択の子オブジェクトも対象とします"),
        default=True,
    ) # type: ignore
   
    # オプション：モディファイアを適用 初期値 True
    use_mesh_modifiers: BoolProperty(
        name=localeui.gtext("use_mesh_modifiers", "モディファイアを適用"),
        description=localeui.gtext("desc_mesh_modifiers", "エクスポートされたメッシュにモディファイアを適用します"),
        default=True,
    ) # type: ignore

    # オプション：ワールド原点を中心とする。初期値 False
    use_worigin_to_center: BoolProperty(
        name=localeui.gtext("use_worigin_to_center", "ワールド原点を中心とする"),
        description=localeui.gtext("desc_worigin_to_center", "ワールド原点をシンボルの原点（0,0,0）に変換し、1つのBlenderファイルが1シンボルに対応します"),
        default=False,
        update=checkChangeCallback,
    ) # type: ignore

    # オプション：カラーの増幅率。初期値 1.5
    color_mag: FloatProperty(
        name=localeui.gtext("color_mag", "カラーの増幅率"),
        description=localeui.gtext("desc_color_mag", "生成されるオブジェクトのカラーを増減させて調整します"),
        min=0.01, max=1000.0,
        default=1.5000,
    ) # type: ignore
    # オプション：グローバルスケール。初期値 0.3937
    global_scale: FloatProperty(
        name="Scale",
        description=localeui.gtext("desc_global_scale", """\
KiCadの3Dモデルを生成するためのスケールをBlenderでの1単位を1mmとして設定します。
初期値は、1/2.54（0.3937）です"""),
        min=0.01, max=1000.0,
        default=0.393700,
    ) # type: ignore
    # ------------------------------------------------------------------------------------------------
    def execute(self, context):
        from . import export_kicad
        from mathutils import Matrix

        keywords = {
            "filepath": self.filepath,
            "use_selection": self.use_selection,
            "fetch_children": self.fetch_children,
            "use_mesh_modifiers": self.use_mesh_modifiers,
            "use_worigin_to_center": self.use_worigin_to_center,
            "color_mag": self.color_mag,
        }
        keywords["global_matrix"] = axis_conversion(to_forward=self.axis_forward,
                                        to_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_scale"] =  Matrix.Scale(self.global_scale, 4)

        return export_kicad.save(self, context, **keywords)

    # ------------------------------------------------------------------------------------------------
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_selection")
        layout.prop(self, "fetch_children")
        layout.prop(self, "use_mesh_modifiers")
        layout.prop(self, "use_worigin_to_center")
        layout.prop(self, "color_mag")
        layout.prop(self, "axis_forward")
        layout.prop(self, "axis_up")
        layout.prop(self, "global_scale")

# 
# ================================================================================================================================
class HelpOperation(bpy.types.Operator):
    bl_idname = "object.help_operation"
    bl_label = localeui.gtext("Help", "ヘルプ")
    bl_description = "ヘルプを表示"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        url = "file:///" + os.path.dirname(__file__) + "/README_J.html"
        webbrowser.open_new_tab(url)
        return {'FINISHED'}

# ================================================================================================================================
# 左側[ツール]に表示
class IOSceneKiCadTools(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    # パネルのラベル
    bl_label = "KiCad"
    def draw(self, context):
        layout = self.layout
        # ※textは単語であれば英字のままで日本語化される
        layout.operator(HelpOperation.bl_idname, text = localeui.gtext("Help", "ヘルプ"))
        layout.operator(ExportWRL.bl_idname, text = localeui.gtext("Export", "エクスポート"))

# ================================================================================================================================
# 右側のツール（Nキー）のタブに表示
class IOSceneKiCadUi(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # タブ名称
    bl_category = "KiCad"
    # パネルのラベル
    bl_label = "WRL(KiCad) エクスポート"

    def draw(self, context):
        layout = self.layout
        # ※textは単語であれば英字のままで日本語化される
        layout.operator(HelpOperation.bl_idname, text = localeui.gtext("Help", "ヘルプ"))
        layout.operator(ExportWRL.bl_idname, text = localeui.gtext("Export", "エクスポート"))

# ================================================================================================================================
# [プロパティ]ウィンドウの[データ]タブに表示
class IOSceneKiCadPropertyWindow(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    # パネルの名称
    bl_category = "KiCad"
    # パネルのラベル
    bl_label = "WRL(KiCad)エクスポート"

    def draw(self, context):
        layout = self.layout
        layout.operator(HelpOperation.bl_idname, text = localeui.gtext("Help", "ヘルプ"))
        layout.operator(ExportWRL.bl_idname, text = localeui.gtext("Export", "エクスポート"))
# ================================================================================================================================
def menu_func(self, context):
    self.layout.operator(ExportWRL.bl_idname, text="KiCadエクスポート (.wrl)")

# ================================================================================================================================
classes = (
#   IOSceneKiCadTools,
    IOSceneKiCadUi,
    HelpOperation,
#   IOSceneKiCadPropertyWindow,
    ExportWRL,
)
# アドオンの登録メソッド
# ================================================================================================================================
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    # メニュー登録
    bpy.types.TOPBAR_MT_file_export.append(menu_func)
    # 翻訳辞書の登録
    ## bpy.app.translations.register(__name__, translation_dict)

# アドオンの登録解除メソッド
# ================================================================================================================================
def unregister():
    from bpy.utils import unregister_class
    # 翻訳辞書の登録解除
    ## bpy.app.translations.unregister(__name__)
    # メニュー削除
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    for cls in classes:
        unregister_class(cls)

# ================================================================================================================================
if __name__ == "__main__":
    register()
