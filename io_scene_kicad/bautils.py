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
import bpy
import mathutils
import os
import re
from typing import TypeVar, Sequence
T = TypeVar('T')

DEBUG = False
# DEBUG = True

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
    if DEBUG:
        print("%s: base[%s], zoom[%s] => ret[%s]" % \
            (caption, ' '.join(map(str, base_color)), ' '.join(map(str, zoom_color)), ' '.join(map(str, ret_color))))
    # 計算後のカラーを返す
    return tuple(ret_color)

# ファイルライター
# 出力内容の括弧類に合わせてインデントを自動生成します。
# ================================================================================================================================
class FW:

    lastch = ""

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
        output = (prefix if self.lastch == '\n' else '') + data
        # 出力
        self.file.write(output)
        self.lastch = output[-1:]
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
# 主に、反復を伴うリストの終端を判定するために使う
# 末端以外なら、次要素への','、そうでないならブランク出力する等。
#
class ItOp:
    count: 0
    Iterator: Sequence[T]
    # コンストラクタ
    # ----------------------------------------------------------------
    def __init__(self, items: Sequence[T]):
        self.Iterator = items

    # 反復呼び出し（条件指定関数付）
    # ----------------------------------------------------------------
    def loop(self, condit=None):
        self.count = len(self.Iterator)
        for item in self.Iterator:
            self.count -= 1
            if (not condit is None) and callable(condit):
                if not condit(item):
                    continue
            yield item
 
    # 末尾取得
    # ----------------------------------------------------------------
    def last_get(self, last=",", empty=""):
        return last if self.count > 0 else empty

# オブジェクトモードの切り替え
# ================================================================================================================================
class ObjectModeApply:
    # コンストラクタ
    # ----------------------------------------------------------------
    def __init__(self, obj, apply=True):
        # 編集モード状態取得
        self.is_editmode = (obj.mode == 'EDIT')
        if apply:
            self.store()
    
    # ----------------------------------------------------------------
    def store(self):
        # 編集モードならモードを戻す
        if self.is_editmode:
            bpy.ops.object.editmode_toggle()

    # ----------------------------------------------------------------
    def restore(self):
        # 編集モードならモードを戻す
        if self.is_editmode:
            bpy.ops.object.editmode_toggle()

# オブジェクトの選択切り替え
# ================================================================================================================================
class Selector:
    def __init__(self):
        self.deselect_all()

    def __del__(self):
        if self.dsa:
            self.restore_select_all()

    # 全選択解除
    # ----------------------------------------------------------------
    def deselect_all(self):
        self.dsa = True
        self.selected_objects = bpy.context.selected_objects
        self.active_object = bpy.context.active_object
        for obj in self.selected_objects:
            obj.select_set(False)

    # 全選択復元
    # ----------------------------------------------------------------
    def restore_select_all(self):
        self.dsa = False
        bpy.context.view_layer.objects.active = self.active_object
        for obj in self.selected_objects:
            obj.select_set(True)
    
    # 指定オブジェクト選択
    # ----------------------------------------------------------------
    def set_select(self, obj):
        bpy.context.view_layer.objects.active = obj
        state = obj.select_get()
        obj.select_set(True)
        return state

    # 指定オブジェクト選択復元
    # ----------------------------------------------------------------
    def restore_select(self, obj, state):
        obj.select_set(state)

# 元のファイルパスからファイル名にサブ名を追加しファイルパスを返す        
# ================================================================================================================================
def get_subpath(filepath, subname):
    # ディレクトリ名の取得
    dirname = os.path.dirname(filepath)
    # ベース名の取得
    basename = os.path.basename(filepath)
    # 拡張子の抽出
    mcx = re.search(r"([.][^.]+)$", basename)
    fext = mcx.group(1) if mcx else ""
    # ファイルタイトルの抽出
    ftitle = basename[0:len(basename) - len(fext)].strip('_')
    # 新しいファイル名の作成
    fname = ftitle + '_' + vrmlid(subname).strip('_') + fext
    # パスを組み立てて返す
    return os.path.join(dirname, fname)

# 日本語を含む文字列を半角英数字に置換
# ================================================================================================================================
def zen2hex(str):
    sv = []
    for x in range(len(str)):
        ch = str[x]
        cd = ord(ch)
        if (cd >= 0) and (cd <= 255):
            sv.append(ch)
        else:
            sv.append(hex(cd)[2:].upper())
    return "".join(sv)

# VRML用のオブジェクトID取得
# ================================================================================================================================
def vrmlid(n, zen=False):
    if zen:
        return '_' + zen2hex(n).replace ('.', '_').replace (' ','_')
    return '_' + str(n).replace ('.', '_').replace (' ','_')

# VRML用のマテリアル名取得
# ================================================================================================================================
def materialid(n, zen=False):
    if zen:
        return zen2hex(n).replace ('.', '_').replace (' ','-')
    return str(n).replace ('.', '_').replace (' ','-')

# 正規表現のfor文対応（search版）
# ================================================================================================================================
def re_search(pattern, value):
    sval = str(value)
    rx = re.compile(pattern)
    sta, end = (0, len(sval))
    while True:
        mx = rx.search(sval, sta, end)
        if mx is None:
            break
        prefix = sval[sta:mx.start()] if sta < mx.start() else ""
        yield prefix, mx
        sta = mx.end()

# 正規表現のfor文対応（match版）
# ================================================================================================================================
def re_match(pattern, value):
    sval = str(value)
    rx = re.compile(pattern)
    sta, end = (0, len(sval))
    while True:
        mx = rx.match(sval, sta, end)
        if mx is None:
            break
        prefix = sval[sta:mx.start()] if sta < mx.start() else ""
        yield prefix, mx
        sta = mx.end()

# 数値の符号のみを返す
# ================================================================================================================================
def sign(val):
    return -1 if val < 0 else (1 if val > 0 else 0) 

# 配列の要素（ビットアドレス=要素インデクス）が一致するかを返す
# ================================================================================================================================
def isAbsSame(ary, bits, cbitmax=3):
    val = None
    cok = 0
    cbit = 0
    for ba in range(0, cbitmax):
        bm = 1 << ba
        if (bits & bm) != 0:
            cbit += 1
            if val is None:
                val = abs(ary[ba])
                cok += 1
            elif val == abs(ary[ba]):
                cok += 1
    return cbit == cok

# -a,-b,c を値毎に方向と値の列に分割
# ================================================================================================================================
def from_rotation(value, zeroIsSkip=True):
    map = {}
    count = len(value)
    # 絶対値と符号のマップを作成
    for i, v in enumerate(value):
        av = abs(v)
        if not av in map:
            map[av] = []
        map[av].append({ 'index': i, 'sign': -1 if v < 0 else (1 if v > 0 else 0) })
        del i, v, av
    # 絶対値のサム計算
    def asum(items):
        ans = 0
        for item in items:
            ans += abs(item)
        return ans
    # 値毎にリストを作成
    mkall = []
    for av, vms in map.items():
        if DEBUG:
            print("%r: %r" % (av, vms))
        # 軸方向の値の展開
        mk = []
        for ix in range(0, count):
            success = False
            for vm in vms:
                if vm['index'] != ix:
                    continue
                mk.append(vm['sign'])
                success = True
                break
            if not success:
                mk.append(0)
            del ix
        # 角度値の展開
        mk.append(av)
        if DEBUG:
            print("mk: %r" % (mk))
        # ゼロスキップしない or 絶対値合計が有効なとき
        if not zeroIsSkip or asum(mk) != 0:
            # リストの複製を戻り値に追加
            mkall.append(tuple(mk[:]))
        del av, vm, mk
    del map
    # 一切リストが作られなかったとき
    if len(mkall) == 0:
        # 空結果を作成
        mkall = [tuple([0 for x in range(0, count)]+[0])]
    return mkall

# mathutils.Vector or mathutils.Quaternion をVRML向けタプルのリストで返す
# ================================================================================================================================
def from_tuples(value, defval=(0, 0, 0)):
    axis = list(defval if not defval is None else (0, 0, 0))
    # クオータニオン↓ここに解説が...。
    # https://qiita.com/drken/items/0639cf34cce14e8d58a5
    # 90°=√2/2, 180°=√2, 360°=2√2
    # クオータニオンの3次元角表記:
    # qua.x=λx・sin(Θ/2)
    # qua.y=λy・sin(Θ/2)
    # qua.z=λZ・sin(Θ/2)
    # qua.w=cos(Θ/2)
    if type(value) is mathutils.Quaternion:
        va = value.to_euler()
        axis = from_rotation(va)
        if False:
            if sum(va[:]) == 0.0:
                axis.append((0.0, 0.0, 0.0, 0.0))
            else:
                bits = 0
                bits |= 0b001 if va[0] != 0.0 else 0
                bits |= 0b010 if va[1] != 0.0 else 0
                bits |= 0b100 if va[2] != 0.0 else 0
                # 何れか1つしか値が無いとき
                if bits in (1, 2, 4):
                    if bits == 1:
                        axis.append((sign(va[0]), 0, 0, abs(va[0])))
                    elif bits == 2:
                        axis.append((0, sign(va[1]), 0, abs(va[1])))
                    elif bits == 4:
                        axis.append((0, 0, sign(va[2]), abs(va[2])))
                    pass
                # 値が2つ存在するとき
                elif bits in (3,5,6):
                    # 要素[0]と[1]に値が存在するとき
                    if bits == 0b011:
                        # 絶対値が同じとき
                        if isAbsSame(va, 0b011):
                            axis.append((sign(va[0]), sign(va[1]), 0, abs(va[0])))
                        # 絶対値が異なるとき
                        else:
                            axis.append((sign(va[0]), 0, 0, abs(va[0])))
                            axis.append((0, sign(va[1]), 0, abs(va[1])))
                    # 要素[0]と[2]に値が存在するとき
                    elif bits == 0b101:
                        # 絶対値が同じとき
                        if isAbsSame(va, 0b101):
                            axis.append((sign(va[0]), 0, sign(va[2]), abs(va[0])))
                        # 絶対値が異なるとき
                        else:
                            axis.append((sign(va[0]), 0, 0, abs(va[0])))
                            axis.append((0, 0, sign(va[2]), abs(va[2])))
                    # 要素[0]と[1]に値が存在するとき
                    elif bits == 0b110:
                        # 絶対値が同じとき
                        if isAbsSame(va, 0b110):
                            axis.append((sign(va[1]), 0, sign(va[2]), abs(va[1])))
                        # 絶対値が異なるとき
                        else:
                            axis.append((0, sign(va[1]), 0, abs(va[1])))
                            axis.append((0, 0, sign(va[2]), abs(va[2])))
                # 値が3つ存在するとき
                elif bits in (7):
                    # 3要素共に絶対値が同じとき
                    if isAbsSame(va, 0b111):
                        axis.append((sign(va[0]), sign(va[1]), sign(va[2]), abs(va[0])))
                    # 要素[0]と[1]に値が存在するとき
                    elif isAbsSame(va, 0b011):
                        axis.append((sign(va[0]), sign(va[1]), 0, abs(va[0])))
                        axis.append((0, 0, sign(va[2]), abs(va[2])))
                    # 要素[1]と[2]に値が存在するとき
                    elif isAbsSame(va, 0b110):
                        axis.append((0, sign(va[1]), sign(va[2]), abs(va[1])))
                        axis.append((sign(va[0]), 0, 0, abs(va[0])))
                    # 要素[0]と[2]に値が存在するとき
                    elif isAbsSame(va, 0b101):
                        axis.append((sign(va[0]), 0, sign(va[2]), abs(va[0])))
                        axis.append((0, sign(va[1]), 0, abs(va[1])))
                    # 何れの要素も絶対値が異なるとき
                    else:
                        axis.append((sign(va[0]), 0, 0, abs(va[0])))
                        axis.append((0, sign(va[1]), 0, abs(va[1])))
                        axis.append((0, 0, sign(va[2]), abs(va[2])))
    if type(value) is mathutils.Vector:
        axis = [tuple(value)]
    return axis
