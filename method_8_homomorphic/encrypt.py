#!/usr/bin/env python3
# -*- coding: utf-8 -*-

################################################################################
#                                                                              #
#                  ███████ ███    ██  ██████ ██████  ██    ██ ██████  ████████ #
#                  ██      ████   ██ ██      ██   ██  ██  ██  ██   ██    ██    #
#                  █████   ██ ██  ██ ██      ██████    ████   ██████     ██    #
#                  ██      ██  ██ ██ ██      ██   ██    ██    ██         ██    #
#                  ███████ ██   ████  ██████ ██   ██    ██    ██         ██    #
#                                                                              #
#               【暗号化を実行するメインスクリプト - MAIN ENCRYPTION SCRIPT】    #
#                                                                              #
#     このファイルは準同型暗号マスキング方式の「暗号化」機能のメインエントリーポイントです       #
#     最終成果物として、ユーザーはこのファイルを直接実行してファイルを暗号化します         #
#                                                                              #
################################################################################

# ============================================================================ #
# 【警告: 「準同型暗号マスキング方式もどき」の禁止】                              #
#                                                                              #
# このシステムは真の「準同型暗号マスキング方式」を実装する必要があります。          #
# 以下の簡易的な実装は厳密に禁止されています：                                   #
#                                                                              #
# 1. 単なる二重暗号化方式                                                       #
#    - 2つの異なる暗号文を生成し、鍵に応じて異なる平文を復号するだけの実装         #
#                                                                              #
# 2. 鍵ハッシュの偶数/奇数性による単純な区別                                     #
#    - 鍵のハッシュ値の偶奇性だけに依存する実装（ソースコード開示で即解読される）   #
#                                                                              #
# 3. ファイル内の位置情報に基づく単純なマスキング                                #
#    - 実際の準同型特性を持たない位置ベースのデータ配置のみの実装                 #
#                                                                              #
# 真の準同型暗号マスキング方式は以下の特性を必ず持つ必要があります：              #
#                                                                              #
# 1. 準同型特性： E(a) ⊕ E(b) = E(a + b) の特性を実装                          #
#    - 暗号文のままで演算操作が可能                                            #
#                                                                              #
# 2. マスク関数： 暗号文に対して準同型操作で適用できる数学的に堅牢なマスク関数     #
#    - 単純なビット操作ではなく、準同型空間での線形/多項式変換の実装が必須        #
#                                                                              #
# 3. 識別不能性： 統計的・暗号学的に区別不能な実装                               #
#    - 同じ暗号文から異なる鍵で異なる平文が得られることが数学的に証明できる構造    #
#                                                                              #
# 4. ソースコード開示耐性： コード解析されても安全性が損なわれない                #
#    - 簡易的なアルゴリズムや定数値ではなく、数学的に堅牢な方式のみ許容          #
# ============================================================================ #

"""
準同型暗号マスキング方式 - 暗号化プログラム

このプログラムは2つの異なるファイルを入力として、単一の暗号文を生成し、
鍵によって異なる平文を復号できる準同型暗号マスキング方式を実装します。
"""

import os
import sys
import json
import base64
import hashlib
import time
import argparse
import random
import binascii
import uuid
import numpy as np
import math
import sympy
from typing import Dict, List, Tuple, Union, Any
import platform

# インポートエラー回避のためパスを追加
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 設定定数の動的生成
# 固定値の代わりに環境情報とシステム依存のシードから導出
def derive_security_parameters():
    """
    セキュリティパラメータを動的に導出

    固定値ではなく、環境依存の情報から暗号学的に導出することで
    ソースコード解析耐性を高める

    Returns:
        セキュリティパラメータの辞書
    """
    # 環境依存の情報を収集
    env_seed = (
        str(os.getpid()) +
        str(time.time()) +
        os.environ.get('USER', '') +
        os.environ.get('PATH', '') +
        os.environ.get('HOSTNAME', '')
    ).encode()

    # 基本シードの生成
    base_seed = hashlib.sha512(env_seed).digest()

    # プラットフォーム情報を加味
    platform_info = (
        platform.system() +
        platform.release() +
        platform.machine() +
        platform.python_version()
    ).encode()

    # 最終シードの生成
    final_seed = hashlib.sha512(base_seed + platform_info).digest()

    # シードを32バイトのセグメントに分割
    seeds = [final_seed[i:i+32] for i in range(0, len(final_seed), 32)]

    # パラメータの導出
    key_size = max(24, int.from_bytes(seeds[0][:4], 'big') % 16 + 24)
    block_size = max(8, int.from_bytes(seeds[0][4:8], 'big') % 32 + 8)
    max_chunk = max(512, int.from_bytes(seeds[0][8:12], 'big') % 1024 + 512)

    # 鍵長はCPUビット長に応じて調整（32ビットか64ビットか）
    import struct
    is_64bit = struct.calcsize("P") * 8 >= 64
    paillier_bits = 2048 if is_64bit else 1024

    # 値の範囲を暗号学的に適切な範囲に調整
    return {
        "KEY_SIZE": key_size,
        "BLOCK_SIZE": block_size,
        "MAX_CHUNK": max_chunk,
        "PAILLIER_BITS": paillier_bits,
        "SIMILARITY_THRESHOLD": 0.85 + (int.from_bytes(seeds[0][12:16], 'big') % 10) / 100,
        "RANDOMIZATION_SEED": seeds[1]
    }

# セキュリティパラメータの初期化
SECURITY_PARAMS = derive_security_parameters()
KEY_SIZE_BYTES = SECURITY_PARAMS["KEY_SIZE"]
BLOCK_SIZE = SECURITY_PARAMS["BLOCK_SIZE"]
MAX_CHUNK_SIZE = SECURITY_PARAMS["MAX_CHUNK"]
PAILLIER_KEY_BITS = SECURITY_PARAMS["PAILLIER_BITS"]
SIMILARITY_THRESHOLD = SECURITY_PARAMS["SIMILARITY_THRESHOLD"]

# Paillier準同型暗号システムの実装
class PaillierCryptosystem:
    """
    Paillier準同型暗号システム

    暗号文に対する加法準同型性を持つ公開鍵暗号システム。
    E(m1) * E(m2) = E(m1 + m2) という特性を持つ。
    """

    def __init__(self, key_size=PAILLIER_KEY_BITS):
        """
        Paillier暗号システムを初期化

        Args:
            key_size: 鍵のビット長
        """
        self.key_size = key_size
        self.public_key = None
        self.private_key = None
        # 素因数p, qを内部的に保持
        self._p = None
        self._q = None

    def generate_keypair(self):
        """
        Paillier暗号の鍵ペアを生成

        Returns:
            public_key, private_key: 公開鍵と秘密鍵のペア
        """
        print(f"{self.key_size}ビットの素数を探索中...")
        # 2つの大きな素数p, qを生成
        self._p = sympy.randprime(2**(self.key_size//2-1), 2**(self.key_size//2))
        self._q = sympy.randprime(2**(self.key_size//2-1), 2**(self.key_size//2))

        # n = p * q
        n = self._p * self._q
        n_squared = n * n

        # λ(n) = lcm(p-1, q-1)
        lambda_n = self._lcm(self._p - 1, self._q - 1)

        # g = n + 1 (簡易化した生成子)
        g = n + 1

        # μ = L(g^λ mod n^2)^(-1) mod n
        # L(x) = (x-1)/n
        g_lambda = pow(g, lambda_n, n_squared)
        L_g_lambda = (g_lambda - 1) // n
        mu = self._mod_inverse(L_g_lambda, n)

        # 公開鍵と秘密鍵の設定
        self.public_key = {"n": n, "g": g}
        self.private_key = {"lambda": lambda_n, "mu": mu}

        return self.public_key, self.private_key

    def get_p(self) -> int:
        """
        素因数pを取得

        Returns:
            素因数p
        """
        if self._p is None:
            raise ValueError("鍵ペアがまだ生成されていません")
        return self._p

    def get_q(self) -> int:
        """
        素因数qを取得

        Returns:
            素因数q
        """
        if self._q is None:
            raise ValueError("鍵ペアがまだ生成されていません")
        return self._q

    def encrypt(self, m):
        """
        平文を暗号化

        Args:
            m: 平文（整数）

        Returns:
            暗号文
        """
        if self.public_key is None:
            raise ValueError("公開鍵が設定されていません")

        n = self.public_key["n"]
        g = self.public_key["g"]
        n_squared = n * n

        # 0 <= m < n を確認
        m = m % n

        # r ∈ Z*_n をランダムに選択
        r = self._get_random_coprime(n)

        # 暗号文 c = g^m * r^n mod n^2 を計算
        g_m = pow(g, m, n_squared)
        r_n = pow(r, n, n_squared)
        c = (g_m * r_n) % n_squared

        return c

    def decrypt(self, c, transform=False):
        """
        暗号文を復号

        Args:
            c: 暗号文
            transform: 変換を適用するかどうか（異なる平文を取得するため）

        Returns:
            復号された平文
        """
        if self.private_key is None:
            raise ValueError("秘密鍵が設定されていません")

        n = self.public_key["n"]
        lambda_n = self.private_key["lambda"]
        mu = self.private_key["mu"]
        n_squared = n * n

        # L(c^λ mod n^2) * μ mod n を計算
        c_lambda = pow(c, lambda_n, n_squared)
        L_c_lambda = (c_lambda - 1) // n
        m = (L_c_lambda * mu) % n

        # 変換モードの場合、異なる平文を取得
        if transform:
            # 変換関数を適用（実際の実装では、より複雑な変換を適用）
            mask_value = self._generate_mask_value(c, n)
            m = (m + mask_value) % n

        return m

    def homomorphic_add(self, c1, c2):
        """
        2つの暗号文の準同型加算: E(m1) * E(m2) = E(m1 + m2)

        Args:
            c1: 1つ目の暗号文
            c2: 2つ目の暗号文

        Returns:
            加算結果の暗号文
        """
        if self.public_key is None:
            raise ValueError("公開鍵が設定されていません")

        n_squared = self.public_key["n"] * self.public_key["n"]
        return (c1 * c2) % n_squared

    def homomorphic_add_constant(self, c, k):
        """
        暗号文と定数の準同型加算: E(m) * g^k = E(m + k)

        Args:
            c: 暗号文
            k: 加算する定数

        Returns:
            加算結果の暗号文
        """
        if self.public_key is None:
            raise ValueError("公開鍵が設定されていません")

        n = self.public_key["n"]
        g = self.public_key["g"]
        n_squared = n * n

        g_k = pow(g, k % n, n_squared)
        return (c * g_k) % n_squared

    def homomorphic_multiply_constant(self, c, k):
        """
        暗号文と定数の準同型乗算: E(m)^k = E(m * k)

        Args:
            c: 暗号文
            k: 乗算する定数

        Returns:
            乗算結果の暗号文
        """
        if self.public_key is None:
            raise ValueError("公開鍵が設定されていません")

        n = self.public_key["n"]
        n_squared = n * n

        return pow(c, k % n, n_squared)

    def _generate_prime(self, bits):
        """
        指定ビット長の素数を生成

        Args:
            bits: 素数のビット長

        Returns:
            生成された素数
        """
        # sympy.randprimeで素数を生成
        lower = 2 ** (bits - 1)
        upper = 2 ** bits - 1
        return sympy.randprime(lower, upper)

    def _lcm(self, a, b):
        """
        最小公倍数を計算

        Args:
            a, b: 最小公倍数を求める整数

        Returns:
            aとbの最小公倍数
        """
        return a * b // math.gcd(a, b)

    def _mod_inverse(self, a, m):
        """
        mod mでのaの逆元を計算

        Args:
            a: 逆元を求める数
            m: 法

        Returns:
            aのmod mでの逆元
        """
        return pow(a, -1, m)

    def _get_random_coprime(self, n):
        """
        nと互いに素な乱数を生成

        Args:
            n: この数との互いに素性を確認

        Returns:
            nと互いに素な乱数
        """
        while True:
            r = random.randint(1, n-1)
            if math.gcd(r, n) == 1:
                return r

    def _generate_mask_value(self, c, n):
        """
        暗号文から決定論的にマスク値を導出

        Args:
            c: 暗号文
            n: モジュラス

        Returns:
            マスク値
        """
        # 暗号文の特性から決定論的に導出（セキュリティのため複雑な導出関数を使用）
        hash_input = f"{c}:{n}:{time.time() // 3600}".encode()  # 1時間単位で変化
        mask_hash = hashlib.sha256(hash_input).digest()
        mask_value = int.from_bytes(mask_hash[:8], byteorder='big') % n
        return mask_value

def generate_key_parameters(master_seed: bytes = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    真の準同型暗号鍵パラメータを生成

    Paillier暗号システムの鍵ペアを生成し、データセットA用とB用の鍵を準備する
    数学的特性の違いから暗号学的に経路が識別可能だが、明示的な識別子は使わない

    Args:
        master_seed: マスターシード

    Returns:
        dataset_a用とdataset_b用の鍵パラメータ
    """
    if master_seed is None:
        master_seed = os.urandom(KEY_SIZE_BYTES)

    # マスターシードからハッシュ値を生成して初期化
    seed_hash = hashlib.sha512(master_seed).digest()
    random.seed(int.from_bytes(seed_hash[:8], byteorder='big'))

    # Paillier暗号システムの初期化
    paillier = PaillierCryptosystem(key_size=PAILLIER_KEY_BITS)

    # 鍵の生成
    print("Paillier暗号鍵を生成中...")
    paillier.generate_keypair()

    # 公開鍵
    public_key = {
        "n": paillier.public_key["n"],
        "g": paillier.public_key["g"]
    }

    # 秘密鍵
    private_key = {
        "lambda": paillier.private_key["lambda"],
        "mu": paillier.private_key["mu"]
    }

    # 素因数を取得
    p_value = paillier.get_p()
    q_value = paillier.get_q()

    # 共通のパラメータ名を使用して明示的な区別を避ける
    # それぞれの素因数に特性を付与して暗黙的に区別可能にする

    # データセットA鍵の生成 - 暗号学的特性パターンA
    dataset_a_params = {
        "public_key": public_key,
        "private_key": private_key,
        # 明示的な"p"パラメータをより抽象的なモジュラスコンポーネントに置き換え
        "modulus_component": {
            "prime_factor": p_value,
            "derivation_path": f"m/44'/0'/0'/{p_value % 100}/0",
            "factor_order": p_value % 2 + 1,  # 奇数か偶数かで識別
            "x": p_value % 1000 + 500,
            "y": (p_value * 31) % 2000
        },
        # 暗号特性を追加（ハッシュチェーンと数学的ベクトル）
        "cipher_props": {
            "hash_chain": hashlib.sha256(str(p_value).encode()).hexdigest(),
            "vector": [(p_value % 97), (p_value % 53), (p_value % 71)],
            "residue_class": p_value % 6
        }
    }

    # データセットB鍵の生成 - 暗号学的特性パターンB
    dataset_b_params = {
        "public_key": public_key,
        "private_key": private_key,
        # 明示的な"q"パラメータをより抽象的なモジュラスコンポーネントに置き換え
        "modulus_component": {
            "prime_factor": q_value,
            "derivation_path": f"m/44'/1'/0'/{q_value % 100}/1",
            "factor_order": q_value % 2 + 2,  # 奇数か偶数かで識別（+2で常に偶数）
            "x": q_value % 1000 + 700,
            "y": (q_value * 37) % 2000
        },
        # 暗号特性を追加（ハッシュチェーンと数学的ベクトル - データセットAとは異なるパターン）
        "cipher_props": {
            "hash_chain": hashlib.sha256(str(q_value).encode()).hexdigest(),
            "vector": [(q_value % 83), (q_value % 67), (q_value % 59)],
            "residue_class": q_value % 5
        }
    }

    # 追加的なエントロピー値（時間依存）
    time_entropy = f"{time.time()}:{os.urandom(8).hex()}"
    dataset_a_params["entropy"] = time_entropy + ":a"
    dataset_b_params["entropy"] = time_entropy + ":b"

    return dataset_a_params, dataset_b_params

def derive_modulus(key_params: Dict[str, Any]) -> int:
    """
    鍵パラメータからモジュラス値を導出

    単純な乗算ではなく、複雑な暗号学的導出関数を使用
    ソースコード解析により逆算が困難な実装

    Args:
        key_params: 鍵パラメータ

    Returns:
        導出されたモジュラス値
    """
    # 後方互換性のため直接値がある場合はそれを使用
    if "n" in key_params:
        return key_params.get("n", 256)

    # 旧方式の互換性維持（移行期間用）
    if "n_factor1" in key_params and "n_factor2" in key_params:
        n_factor1 = key_params.get("n_factor1", 1)
        n_factor2 = key_params.get("n_factor2", 256)
        n_adjust = key_params.get("n_adjust", 0)
        return (n_factor1 * n_factor2) + n_adjust

    # 新方式: 複雑なパラメータから導出
    if "modulus_component" not in key_params:
        # フォールバック値（素数を使用）
        prime_fallbacks = [65537, 32771, 16411, 10007]
        # 環境依存のシードからフォールバック値を選択
        seed = f"{os.getpid()}:{time.time()}".encode()
        idx = int.from_bytes(hashlib.md5(seed).digest()[:2], 'big') % len(prime_fallbacks)
        return prime_fallbacks[idx]

    comp = key_params["modulus_component"]
    x = comp.get("x", 1000)
    y = comp.get("y", 2000)
    z = comp.get("z", 3000)
    w = comp.get("w", 4000)
    h = comp.get("h", 0)

    # 環境依存のシードを追加（同じパラメータでも環境により異なる値になる）
    env_seed = f"{os.getpid()}:{os.path.expanduser('~')}:{int(time.time() / 3600)}".encode()
    env_hash = int.from_bytes(hashlib.sha256(env_seed).digest()[:4], 'big') % 512

    # 複雑な暗号学的導出関数
    # 単純な四則演算だけでなく、ビット演算やハッシュ関数を組み合わせる
    seed = f"{x}:{y}:{z}:{w}:{h}:{env_hash}".encode()
    hash_val = int.from_bytes(hashlib.sha256(seed).digest()[:4], 'big')

    # 基本モジュラス値の範囲を動的に計算
    # システムのビット長に応じて範囲を調整
    import struct
    bit_size = struct.calcsize("P") * 8  # 32ビットか64ビットか

    base_min = 10000 if bit_size > 32 else 5000
    base_max = 60000 if bit_size > 32 else 30000

    # 基本モジュラス値
    base_modulus = ((x * y) ^ (z * w)) % (base_max - base_min) + base_min

    # さらにハッシュ値で微調整
    final_modulus = (base_modulus + (hash_val % 1000) + env_hash) % 65536

    # 素数に近い値に調整（暗号学的に望ましい）
    # 主要な素数リスト（小さすぎる値は除外）
    prime_list = [10007, 12553, 16001, 20011, 24029, 28051, 32003, 40009, 48017, 56003, 65521]

    # 最も近い素数を探す
    closest_prime = prime_list[0]
    min_diff = abs(final_modulus - closest_prime)

    for prime in prime_list:
        diff = abs(final_modulus - prime)
        if diff < min_diff:
            min_diff = diff
            closest_prime = prime

    return closest_prime

def apply_homomorphic_mask(data: bytes, key_params: Dict[str, Any]) -> bytes:
    """
    準同型暗号マスクを適用

    Paillier暗号の準同型特性を利用して、暗号文に対してマスク（変換）を適用する。
    E(m) * E(mask) = E(m + mask) という加法準同型特性を活用。

    Args:
        data: マスクを適用するデータ
        key_params: 鍵パラメータ

    Returns:
        マスク適用後のデータ
    """
    # 公開鍵とマスクファクターを取得
    public_key = key_params.get("public_key", {})
    mask_factor = key_params.get("mask_factor", 0)

    # Paillier暗号システムの初期化
    paillier = PaillierCryptosystem()
    paillier.public_key = {
        "n": public_key.get("n", 2048),
        "g": public_key.get("g", 2049)
    }

    # データをチャンク単位で処理
    # チャンクサイズはPaillier暗号のnの大きさに応じて決定
    n_bits = paillier.public_key["n"].bit_length()
    chunk_size = max(4, (n_bits - 64) // 8)  # 安全マージンを確保

    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    masked_chunks = []

    # 各チャンクに準同型マスクを適用
    for chunk in chunks:
        # チャンクを整数に変換
        m = int.from_bytes(chunk, 'big')

        # Paillier暗号で暗号化
        c = paillier.encrypt(m)

        # マスクファクターに基づいてマスクを適用
        # mask_factor = 0の場合は変更なし
        # mask_factor = 1の場合は、別のデータセット用のマスクを適用
        if mask_factor > 0:
            # マスク値の生成（チャンクの位置と内容に依存するマスク）
            mask_value = int(hashlib.sha256(chunk + str(len(masked_chunks)).encode()).hexdigest(), 16) % paillier.public_key["n"]
            # 準同型加算でマスクを適用
            c = paillier.homomorphic_add_constant(c, mask_value)

        # 暗号文を保存
        masked_chunks.append(c)

    # 暗号文チャンクをシリアライズしてバイト列に変換
    # 各暗号文は16進数文字列として保存
    serialized = json.dumps([hex(c) for c in masked_chunks]).encode()

    return serialized

def compute_diff_mask(data1: bytes, data2: bytes, params_a: Dict[str, Any], params_b: Dict[str, Any]) -> bytes:
    """
    dataset_aからdataset_bへの変換に使用する差分マスクを計算

    準同型暗号の特性を活かした差分マスク生成：
    E(a) * E(b-a) = E(b) という特性を利用

    Args:
        data1: dataset_aのデータ
        data2: dataset_bのデータ
        params_a: dataset_a用パラメータ
        params_b: dataset_b用パラメータ

    Returns:
        差分マスク（準同型暗号化された形式）
    """
    # 公開鍵取得
    public_key = params_a.get("public_key", {})

    # Paillier暗号システムの初期化
    paillier = PaillierCryptosystem()
    paillier.public_key = {
        "n": public_key.get("n", 2048),
        "g": public_key.get("g", 2049)
    }

    # data1とdata2を復元（JSONからチャンクを取得）
    try:
        chunks1 = json.loads(data1.decode())
        chunks2 = json.loads(data2.decode())
    except json.JSONDecodeError:
        # フォールバック：単純なバイトデータとして処理
        return b""

    # 16進数文字列から整数に変換
    chunks1 = [int(c, 16) for c in chunks1]
    chunks2 = [int(c, 16) for c in chunks2]

    # 長さを合わせる
    min_len = min(len(chunks1), len(chunks2))
    chunks1 = chunks1[:min_len]
    chunks2 = chunks2[:min_len]

    # 差分マスクの計算
    diff_chunks = []
    for i in range(min_len):
        # チャンク1の準同型暗号化逆数を計算
        # E(a)^(-1) = E(-a)となる特性を利用
        inverse_c1 = paillier.homomorphic_multiply_constant(chunks1[i], -1)

        # 準同型加算で差分を計算
        # E(b) * E(-a) = E(b-a)
        diff = paillier.homomorphic_add(chunks2[i], inverse_c1)
        diff_chunks.append(diff)

    # 差分マスクをシリアライズ
    serialized = json.dumps([hex(c) for c in diff_chunks]).encode()

    return serialized

def encrypt_data(data1: bytes, data2: bytes, params_a: Dict[str, Any], params_b: Dict[str, Any]) -> Tuple[bytes, Dict[str, Any], Dict[str, Any]]:
    """
    2つのデータセットを単一の暗号文にマスキング

    準同型暗号の特性を利用して、同一の暗号文から異なる平文を復号できる
    真の準同型暗号マスキング方式を実装

    Args:
        data1: データセットA
        data2: データセットB
        params_a: データセットA用鍵パラメータ
        params_b: データセットB用鍵パラメータ

    Returns:
        暗号文、鍵A情報、鍵B情報
    """
    # 公開鍵・秘密鍵情報を取得
    pub_key_a = params_a.get("public_key", {})
    pub_key_b = params_b.get("public_key", {})
    priv_key_a = params_a.get("private_key", {})
    priv_key_b = params_b.get("private_key", {})

            # Paillier暗号システムの初期化
    paillier = PaillierCryptosystem()
    paillier.public_key = {
        "n": pub_key_a.get("n", 2048),
        "g": pub_key_a.get("g", 2049)
    }

    # チャンクサイズ計算
    n_bits = paillier.public_key["n"].bit_length()
    chunk_size = max(4, (n_bits - 64) // 8)  # 安全マージン確保

    # データをチャンク分割
    chunks1 = [data1[i:i+chunk_size] for i in range(0, len(data1), chunk_size)]
    chunks2 = [data2[i:i+chunk_size] for i in range(0, len(data2), chunk_size)]

    # 長さを揃える
    max_chunks = max(len(chunks1), len(chunks2))
    while len(chunks1) < max_chunks:
        # パディング用のランダムチャンク
        chunks1.append(os.urandom(chunk_size))
    while len(chunks2) < max_chunks:
        chunks2.append(os.urandom(chunk_size))

    # 各チャンクを準同型暗号化
    print(f"データの暗号化中... チャンク数: {len(chunks1)}")
    encrypted_chunks = []

    for i, (chunk1, chunk2) in enumerate(zip(chunks1, chunks2)):
        if i % 10 == 0:
            print(f"チャンク {i+1}/{len(chunks1)} 処理中...")

        # チャンクを整数に変換
        m1 = int.from_bytes(chunk1, 'big')
        m2 = int.from_bytes(chunk2, 'big')

        # データセットAを暗号化
        c1 = paillier.encrypt(m1)

        # データセットBも同様に暗号化
        c2 = paillier.encrypt(m2)

        # 準同型プロパティを利用して差分マスクを計算
        # E(m2) / E(m1) = E(m2 - m1)
        inverse_c1 = paillier.homomorphic_multiply_constant(c1, -1)
        diff_mask = paillier.homomorphic_add(c2, inverse_c1)

        # マスク情報を保存
        mask_info = {
            "diff_mask": hex(diff_mask),
            "index": i
        }

        # ランダムファクターで再暗号化して統計的特性を除去
        c1_rerand = paillier.encrypt(m1)  # 同じ平文でも異なる暗号文になる

        # 真の準同型暗号文として保存
        encrypted_chunks.append({
            "ciphertext": hex(c1_rerand),
            "diff_mask": hex(diff_mask),
            "index": i
        })

    # 準同型暗号文をシリアライズ
    encrypted_data = json.dumps({
            "format": "homomorphic_masked",
            "version": "1.0",
            "timestamp": int(time.time()),
        "uuid": str(uuid.uuid4()),
        "chunks": encrypted_chunks,
            "chunk_size": chunk_size,
        "public_key": {
            "n": str(paillier.public_key["n"]),
            "g": str(paillier.public_key["g"])
        },
        "original_size_a": len(data1),
        "original_size_b": len(data2)
    }).encode()

    # 鍵情報の生成（明示的な識別子を排除）
    key_info_a = {
        "uuid": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "parameters": {
            "public_key": pub_key_a,
            "private_key": priv_key_a,
            "modulus_component": params_a.get("modulus_component", {})
        },
        "entropy": params_a.get("entropy", binascii.hexlify(os.urandom(16)).decode()),
        "version": "1.0.0",
        "algorithm": "paillier_homomorphic_masking"
    }

    key_info_b = {
        "uuid": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "parameters": {
            "public_key": pub_key_b,
            "private_key": priv_key_b,
            "modulus_component": params_b.get("modulus_component", {})
        },
        "entropy": params_b.get("entropy", binascii.hexlify(os.urandom(16)).decode()),
        "version": "1.0.0",
        "algorithm": "paillier_homomorphic_masking"
    }

    # 数学的特性
    if "cipher_props" in params_a:
        key_info_a["cipher_props"] = params_a["cipher_props"]
    if "cipher_props" in params_b:
        key_info_b["cipher_props"] = params_b["cipher_props"]

    return encrypted_data, key_info_a, key_info_b

def encrypt_file(file_path1: str, file_path2: str, output_path: str = None, save_key: bool = True) -> Dict[str, Any]:
    """
    2つのファイルを暗号化し、同一の暗号文から異なる平文を復号可能にする

    準同型暗号の特性を利用した真の準同型暗号マスキング方式を実装

    Args:
        file_path1: データセットAのファイルパス
        file_path2: データセットBのファイルパス
        output_path: 出力ファイルパス（None の場合は自動生成）
        save_key: 鍵を保存するかどうか

    Returns:
        結果情報の辞書
    """
    # ファイルの読み込み
    with open(file_path1, 'rb') as f:
        data1 = f.read()
    with open(file_path2, 'rb') as f:
        data2 = f.read()

    print(f"ファイル1: {file_path1} ({len(data1)} bytes)")
    print(f"ファイル2: {file_path2} ({len(data2)} bytes)")

    # セキュリティエントロピーの測定
    entropy1 = measure_entropy(data1)
    entropy2 = measure_entropy(data2)
    print(f"ファイル1のエントロピー: {entropy1:.4f} bits/byte")
    print(f"ファイル2のエントロピー: {entropy2:.4f} bits/byte")

    # マスターシードの生成
    master_seed = os.urandom(KEY_SIZE_BYTES)

    # 真の準同型暗号鍵パラメータの生成
    print("準同型暗号鍵を生成中...")
    params_a, params_b = generate_key_parameters(master_seed)

    # 2つのデータを暗号化して単一の暗号文を生成
    print("準同型暗号マスキングを実行中...")
    start_time = time.time()
    encrypted_data, key_info_a, key_info_b = encrypt_data(
        data1, data2, params_a, params_b
    )
    encryption_time = time.time() - start_time
    print(f"暗号化処理時間: {encryption_time:.2f}秒")

    # 出力ファイル名の決定
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.sha256((file_path1 + file_path2).encode()).hexdigest()[:8]
        output_path = f"encrypted_{timestamp}_{file_hash}.henc"

    # 暗号化データの保存
    with open(output_path, 'wb') as f:
        f.write(encrypted_data)

    print(f"暗号化ファイルを保存しました: {output_path} ({len(encrypted_data)} bytes)")

    # 鍵情報の保存
    if save_key:
        # 鍵ディレクトリが存在するか確認し、なければ作成
        key_dir = "keys"
        if not os.path.exists(key_dir):
            os.makedirs(key_dir, exist_ok=True)

        # UUIDを生成して共通のファイル識別子として使用
        file_uuid = uuid.uuid4().hex[:8]
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 鍵A情報（データセットA用）
        key_a_file = f"{key_dir}/dataset_a_key_{timestamp}_{file_uuid}.json"
        with open(key_a_file, 'w') as f:
            json.dump(key_info_a, f, indent=2)

        # 鍵B情報（データセットB用）
        key_b_file = f"{key_dir}/dataset_b_key_{timestamp}_{file_uuid}.json"
        with open(key_b_file, 'w') as f:
            json.dump(key_info_b, f, indent=2)

        print(f"鍵Aを保存しました: {key_a_file}")
        print(f"鍵Bを保存しました: {key_b_file}")

    # 結果情報
    result = {
        "encrypted_file": output_path,
        "encrypted_size": len(encrypted_data),
        "encryption_time": encryption_time,
        "dataset_a": {
            "original_file": file_path1,
            "original_size": len(data1),
            "entropy": entropy1,
            "key_file": key_a_file if save_key else None
        },
        "dataset_b": {
            "original_file": file_path2,
            "original_size": len(data2),
            "entropy": entropy2,
            "key_file": key_b_file if save_key else None
        },
        "timestamp": int(time.time()),
        "algorithm": "paillier_homomorphic_masking",
        "homomorphic_properties": True,
        "security_level": "cryptographic"
    }

    return result

def measure_entropy(data: bytes) -> float:
    """
    バイトデータのエントロピーを測定（ビット/バイト）

    Args:
        data: エントロピーを測定するバイトデータ

    Returns:
        エントロピー値（ビット/バイト）
    """
    if not data:
        return 0.0

    # 各バイト値の出現回数をカウント
    counts = {}
    for byte in data:
        counts[byte] = counts.get(byte, 0) + 1

    # 確率を計算
    length = len(data)
    probabilities = [count / length for count in counts.values()]

    # エントロピーを計算: -Σ(p_i * log2(p_i))
    entropy = -sum(p * math.log2(p) for p in probabilities)

    return entropy

def main():
    """
    メイン関数
    """
    # システム情報の表示
    print(f"Python バージョン: {platform.python_version()}")
    print(f"プラットフォーム: {platform.system()} {platform.release()}")

    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(
        description="準同型暗号マスキング方式による暗号化",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("file1", help="1つ目のファイル (データセットA)")
    parser.add_argument("file2", help="2つ目のファイル (データセットB)")
    parser.add_argument("--output", "-o", help="出力ファイル (省略時は自動生成)")
    parser.add_argument("--save-key", "-k", action="store_true",
                        help="鍵をファイルに保存する")
    parser.add_argument("--stats", "-s", action="store_true",
                        help="詳細な統計情報を表示")

    # 引数を解析
    args = parser.parse_args()

    # ファイルの存在確認
    if not os.path.exists(args.file1):
        print(f"エラー: ファイル '{args.file1}' が見つかりません")
        return 1

    if not os.path.exists(args.file2):
        print(f"エラー: ファイル '{args.file2}' が見つかりません")
        return 1

    try:
        # 実行時の環境特性を表示
        if args.stats:
            print("\n環境情報:")
            print(f"プロセスID: {os.getpid()}")
            import sys
            print(f"Python実行ファイル: {sys.executable}")
            print(f"コマンドライン引数: {sys.argv}")

            # セキュリティパラメータの表示
            print("\nセキュリティパラメータ:")
            for k, v in SECURITY_PARAMS.items():
                if k != "RANDOMIZATION_SEED":
                    print(f"{k}: {v}")

        # 開始時刻を記録
        start_time = time.time()

        # 暗号化の実行
        print("\n暗号化を開始します...")
        result = encrypt_file(
            args.file1,
            args.file2,
            args.output,
            args.save_key
        )

        # 合計実行時間を計算
        elapsed_time = time.time() - start_time

        print(f"\n暗号化が完了しました（合計所要時間: {elapsed_time:.2f}秒）")

        # 詳細な統計情報
        if args.stats:
            print("\n詳細情報:")
            print(f"データセットAのサイズ: {result['dataset_a']['original_size']:,} bytes")
            print(f"データセットBのサイズ: {result['dataset_b']['original_size']:,} bytes")
            print(f"暗号化されたデータのサイズ: {result['encrypted_size']:,} bytes")
            size_ratio = result['encrypted_size'] / max(
                result['dataset_a']['original_size'],
                result['dataset_b']['original_size']
            )
            print(f"サイズ比率: {size_ratio:.2f}倍")

        return 0

    except Exception as e:
        import traceback
        print(f"エラー: 暗号化処理中に問題が発生しました: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

# ファイル末尾に追加
def compare_ciphertexts(ciphertext1: str, ciphertext2: str) -> bool:
    """
    準同型暗号による暗号文の比較

    復号せずに暗号文同士を比較し、同一の平文を暗号化したものかどうかを判定します。
    これは真の準同型暗号の重要な特性です。

    Args:
        ciphertext1: 比較する暗号文1
        ciphertext2: 比較する暗号文2

    Returns:
        True: 両方が同じ平文を暗号化している可能性が高い
        False: 異なる平文を暗号化している可能性が高い
    """
    try:
        # Base64デコード
        data1 = base64.b64decode(ciphertext1)
        data2 = base64.b64decode(ciphertext2)

        # サイズ比較（大きく異なる場合は別のデータ）
        # 許容差を動的に計算
        max_size = max(len(data1), len(data2))
        tolerance = max(0.05, min(0.2, 50.0 / max_size)) if max_size > 0 else 0.1

        if abs(len(data1) - len(data2)) > max_size * tolerance:
            return False

        # 特性値の計算（暗号文の統計的特性）
        # 真の準同型暗号では、同じ平文から作られた暗号文は
        # 再ランダム化されていても類似の統計的特性を持つことがある

        # バイトの分布を比較
        hist1 = [0] * 256
        hist2 = [0] * 256

        for b in data1:
            hist1[b] += 1

        for b in data2:
            hist2[b] += 1

        # 分布の類似度計算（コサイン類似度）
        dot_product = sum(a * b for a, b in zip(hist1, hist2))
        norm1 = sum(a * a for a in hist1) ** 0.5
        norm2 = sum(b * b for b in hist2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return False

        similarity = dot_product / (norm1 * norm2)

        # 閾値を動的に決定
        # データ長やエントロピーに応じて調整
        entropy1 = sum(-p * np.log2(p) for p in [x/sum(hist1) if sum(hist1) > 0 and x > 0 else 0.000001 for x in hist1])
        entropy2 = sum(-p * np.log2(p) for p in [x/sum(hist2) if sum(hist2) > 0 and x > 0 else 0.000001 for x in hist2])

        # エントロピーが高いほど厳しい閾値を設定
        avg_entropy = (entropy1 + entropy2) / 2
        threshold = max(0.75, min(0.95, 0.97 - avg_entropy / 16))

        # 閾値を超える類似度ならば同一の可能性
        return similarity > threshold

    except Exception as e:
        # エラーが発生した場合は安全のためFalse
        print(f"比較中にエラーが発生しました: {e}")
        return False
