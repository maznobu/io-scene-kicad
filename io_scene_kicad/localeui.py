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
import os
import re
import locale

#
# i18n非対応ビルド Blender の多言語化をサポートするモジュールです。
# 理由：英語圏のコーダーではないので、ベースが英語圏であるBlenderのためのアドインに於いて、
# 日本語で出力メッセージを直接書くのには抵抗があります。
# そして、アドインはi18n対応または非対応のどちらに読み込まれるかは確定していないため、これを実装しました。
#
# A module for supporting multilingualization of i18n non-compatible build blender.
# Reason: Since I am not an English-speaking coder, I am reluctant to directly write output messages in Japanese in
# an add-in for Blender, which is based on an English-speaking country.
# And since it is not certain whether the add-in will be loaded on i18n compatible or non-i18n compatible systems,
# I implemented this.
# ================================================================================================================================
# 辞書データ
trans_dict = {}
# ================================================================================================================================
# 仕様:
# ・ファイルは lang/ロケール名.txt を翻訳テキストとする
# ・キー無効時は#開始行をコメント、及び、空行有効。
# ・キー: 訳文（2行目以降複数行可能） でキー有効。
# ・次行の キー: ～でキーが代わる。
# ・複数行時に2行目以降に"#!END!"でキー解除。
def getdict(loc):
    # スクリプトがあるフォルダのlangサブフォルダ下からロケール名.txtのパスを作成
    fpath = os.path.join(os.path.dirname(__file__), "lang", loc + ".txt")
    # そのファイルが存在するとき
    if os.path.exists(fpath):
        # ファイルを読み込みモードで開く(UTF8)
        file = open(fpath, 'r', encoding="utf8")
        # 全行読み込み
        lines = file.readlines()
        file.close()

        # 最後のキー初期化
        last_key = ""
        # 行ごとに処理
        for line in lines:
            # 前後空白のトリム
            line = line.strip()
            # キー無効であるとき
            if len(last_key) == 0:
                # 空行またはコメント行はスキップ
                if (len(line) == 0) or (line[0] == "#"):
                    continue
            # キー有効で行頭 #!END! のとき
            elif line == "#!END!":
                # キー無効化
                last_key = ""
                continue
            # キー: 文字列のとき
            m = re.match(r"^([^:]+):\s*(.*)$", line)
            if not m is None:
                # キー取得
                last_key = m.group(1)
                # 翻訳内容格納
                trans_dict[last_key] = m.group(2)
            # キー書式以外のとき
            else:
                # 翻訳内容の追加格納
                trans_dict[last_key] += line

# i18n未対応のblenderではtranslationsは役立たず。独自のコード
# ================================================================================================================================
def gtext(msgid, defmsg=None):
    # メッセージ初期化
    msg = defmsg if not defmsg is None else msgid
    # ロケール名取得
    loc = locale.getdefaultlocale()[0]
    # 翻訳マップが空のとき
    if len(trans_dict) == 0:
        # 辞書ファイル読み込み
        getdict(loc)
    # ロケーションが辞書に存在するとき
    if msgid in trans_dict:
        # メッセージIDに該当する翻訳内容を取得
        msg = trans_dict[msgid]
    # メッセージを返す
    return msg

# ================================================================================================================================
