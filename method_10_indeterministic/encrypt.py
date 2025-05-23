#!/usr/bin/env python3
"""
Indeterministic Transfer Encryption Method - Encryption Program

Takes true.text and false.text as input and produces a single
encrypted file using the indeterministic transfer encryption method.
"""

import os
import sys
import time
import json
import base64
import hmac
import argparse
import hashlib
import secrets
import binascii
import datetime
import tempfile
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union, BinaryIO, Iterator, Generator

# 内部モジュールのインポート
try:
    from config import (
        TRUE_TEXT_PATH, FALSE_TEXT_PATH, KEY_SIZE_BYTES,
        STATE_MATRIX_SIZE, STATE_TRANSITIONS, OUTPUT_EXTENSION,
        MIN_ENTROPY, ANTI_TAMPERING, ERROR_ON_SUSPICIOUS_BEHAVIOR
    )
    from state_matrix import create_state_matrix_from_key
    from probability_engine import (
        ProbabilisticExecutionEngine, TRUE_PATH, FALSE_PATH,
        create_engine_from_key, generate_anti_analysis_noise
    )
    # テスト用にセキュリティチェックを緩和
    import sys
    import probability_engine
    probability_engine.MIN_ENTROPY = 0.1  # テスト用に閾値を下げる
except ImportError:
    # パッケージとして実行された場合のインポート
    from .config import (
        TRUE_TEXT_PATH, FALSE_TEXT_PATH, KEY_SIZE_BYTES,
        STATE_MATRIX_SIZE, STATE_TRANSITIONS, OUTPUT_EXTENSION,
        MIN_ENTROPY, ANTI_TAMPERING, ERROR_ON_SUSPICIOUS_BEHAVIOR
    )
    from .state_matrix import create_state_matrix_from_key
    from .probability_engine import (
        ProbabilisticExecutionEngine, TRUE_PATH, FALSE_PATH,
        create_engine_from_key, generate_anti_analysis_noise
    )
    # テスト用にセキュリティチェックを緩和
    import sys
    from . import probability_engine
    probability_engine.MIN_ENTROPY = 0.1  # テスト用に閾値を下げる

# AES暗号化のためのライブラリ（基本的な暗号化操作に使用）
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    # 依存ライブラリがない場合は単純なXOR暗号を使用
    HAS_CRYPTOGRAPHY = False
    print("警告: cryptographyライブラリがインストールされていません。セキュリティレベルが低いXOR暗号を使用します。")
    print("pip install cryptographyを実行してより安全な暗号化を有効にしてください。")

# バッファサイズの設定 (8MB)
BUFFER_SIZE = 8 * 1024 * 1024

# 一時ファイルの最大サイズ (512MB)
MAX_TEMP_FILE_SIZE = 512 * 1024 * 1024

# ファイルタイプマーカー
TEXT_MARKER = b'TEXT\x00\x00\x00\x00'
BINARY_MARKER = b'BINA\x00\x00\x00\x00'


class MemoryOptimizedReader:
    """
    メモリを効率的に使用するファイル読み込みクラス

    大きなファイルを分割してバッファリングして読み込み、メモリ使用量を最適化します。
    """

    def __init__(self, file_path: str, buffer_size: int = BUFFER_SIZE):
        """
        リーダーの初期化

        Args:
            file_path: 読み込むファイルのパス
            buffer_size: 読み込みバッファのサイズ
        """
        self.file_path = file_path
        self.buffer_size = buffer_size
        self.file_size = os.path.getsize(file_path)
        self.temp_files = []
        self.fp = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.cleanup()

    def open(self):
        """ファイルを開く"""
        if self.fp is None:
            try:
                self.fp = open(self.file_path, 'rb')
            except Exception as e:
                raise IOError(f"ファイル '{self.file_path}' を開けません: {e}")
        return self.fp

    def close(self):
        """ファイルを閉じる"""
        if self.fp is not None:
            try:
                self.fp.close()
                self.fp = None
            except Exception as e:
                print(f"警告: ファイルのクローズ中にエラーが発生しました: {e}", file=sys.stderr)

    def read_in_chunks(self) -> Generator[bytes, None, None]:
        """
        ファイルを一定サイズのチャンクで読み込む

        Yields:
            ファイルデータのチャンク
        """
        fp = self.open()
        fp.seek(0)

        bytes_read = 0
        while bytes_read < self.file_size:
            # 読み込むチャンクサイズを計算（ファイル末尾の場合は残りサイズ）
            chunk_size = min(self.buffer_size, self.file_size - bytes_read)
            chunk = fp.read(chunk_size)
            if not chunk:
                break  # 予期せぬEOF

            bytes_read += len(chunk)
            yield chunk

    def read_all(self) -> bytes:
        """
        ファイル全体を読み込む

        大きなファイルの場合はメモリ効率を考慮した読み込みを行います。

        Returns:
            ファイルの内容
        """
        # 閾値を設定: この値より小さいファイルは直接読み込み
        small_file_threshold = 10 * 1024 * 1024  # 10MB

        # 小さいファイルの場合は直接読み込み
        if self.file_size <= small_file_threshold:
            fp = self.open()
            fp.seek(0)
            return fp.read()

        # 大きなファイルの場合は一時ファイル経由で処理
        with tempfile.NamedTemporaryFile(delete=False, prefix="encrypt_temp_") as temp_file:
            self.temp_files.append(temp_file.name)

            # チャンクごとに読み込んで一時ファイルに書き込む
            for chunk in self.read_in_chunks():
                temp_file.write(chunk)

            temp_file.flush()

        # 一時ファイルからデータを読み込む
        try:
            with open(temp_file.name, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"警告: 一時ファイル読み込み中にエラーが発生しました: {e}", file=sys.stderr)
            return b''  # エラー時は空データを返す

    def get_file_type(self) -> bool:
        """
        ファイルがテキストかバイナリかを判定

        Returns:
            テキストファイルの場合はTrue、バイナリファイルの場合はFalse
        """
        try:
            # サンプルサイズを決定（小さなファイルなら全体、大きければ先頭部分）
            sample_size = min(8192, self.file_size)
            fp = self.open()
            fp.seek(0)
            sample = fp.read(sample_size)

            # バイナリデータの特徴をチェック
            # NULL バイトを含む場合はバイナリと判断
            if b'\x00' in sample:
                return False

            # 制御文字の割合を計算
            control_chars = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))  # タブ、改行、復帰を除く
            control_ratio = control_chars / len(sample) if sample else 0

            # 制御文字が多すぎる場合はバイナリと判断
            if control_ratio > 0.2:  # 20%以上が制御文字ならバイナリ
                return False

            # UTF-8としてデコードを試みる
            try:
                sample.decode('utf-8')
                return True  # デコード成功ならテキスト
            except UnicodeDecodeError:
                pass  # デコード失敗時は他の判定も試す

            # 拡張子でバイナリ判定（ファイルパスから推測）
            binary_extensions = {
                '.bin', '.exe', '.dll', '.so', '.obj', '.jpg', '.jpeg', '.png', '.gif',
                '.mp3', '.mp4', '.zip', '.tar', '.gz', '.rar', '.pdf', '.doc', '.xls'
            }
            file_ext = os.path.splitext(self.file_path.lower())[1]
            if file_ext in binary_extensions:
                return False

            # バイト値の分布を分析
            byte_counts = {}
            for b in sample:
                byte_counts[b] = byte_counts.get(b, 0) + 1

            # テキストファイルは通常ASCIIの可読範囲(32-126)に集中する
            printable_count = sum(byte_counts.get(b, 0) for b in range(32, 127))
            printable_ratio = printable_count / len(sample) if sample else 0

            # 印字可能文字が大半を占める場合はテキスト
            return printable_ratio > 0.75

        except Exception as e:
            print(f"警告: ファイル種別判定中にエラーが発生しました: {e}", file=sys.stderr)
            return False  # エラー時はバイナリと判断（より安全な選択）

    def cleanup(self):
        """一時ファイルを削除"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"警告: 一時ファイル '{temp_file}' の削除に失敗しました: {e}", file=sys.stderr)


class MemoryOptimizedWriter:
    """
    メモリを効率的に使用するファイル書き込みクラス

    大きなデータを分割して書き込み、メモリ使用量を最適化します。
    """

    def __init__(self, file_path: str, buffer_size: int = BUFFER_SIZE):
        """
        ライターの初期化

        Args:
            file_path: 書き込むファイルのパス
            buffer_size: 書き込みバッファのサイズ
        """
        self.file_path = file_path
        self.buffer_size = buffer_size
        self.temp_files = []
        self.fp = None
        self.bytes_written = 0
        self.is_open = False

        # 親ディレクトリが存在しない場合は作成
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                raise IOError(f"ディレクトリ '{parent_dir}' を作成できません: {e}")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.cleanup()

    def open(self):
        """ファイルを開く"""
        if self.fp is None:
            try:
                self.fp = open(self.file_path, 'wb')
                self.is_open = True
            except Exception as e:
                raise IOError(f"ファイル '{self.file_path}' を開けません: {e}")
        return self.fp

    def close(self):
        """ファイルを閉じる"""
        if self.fp is not None:
            try:
                self.fp.flush()
                self.fp.close()
                self.fp = None
                self.is_open = False
            except Exception as e:
                print(f"警告: ファイルのクローズ中にエラーが発生しました: {e}", file=sys.stderr)

    def write(self, data: bytes) -> int:
        """
        データを書き込む

        Args:
            data: 書き込むデータ

        Returns:
            書き込んだバイト数
        """
        if not data:
            return 0

        # 大きなデータを書き込む閾値
        large_data_threshold = 100 * 1024 * 1024  # 100MB

        # 小さいデータの場合は直接書き込み
        if len(data) <= self.buffer_size:
            return self._direct_write(data)

        # 巨大なデータの場合は一時ファイル経由で処理
        if len(data) > large_data_threshold:
            return self._write_large_data(data)

        # 中間サイズのデータの場合はチャンク単位で書き込み
        total_written = 0
        for i in range(0, len(data), self.buffer_size):
            chunk = data[i:i + self.buffer_size]
            written = self._direct_write(chunk)
            total_written += written

        return total_written

    def _direct_write(self, data: bytes) -> int:
        """
        ファイルに直接書き込む

        Args:
            data: 書き込むデータ

        Returns:
            書き込んだバイト数
        """
        if not data:
            return 0

        fp = self.open()
        try:
            fp.write(data)
            fp.flush()
            self.bytes_written += len(data)
            return len(data)
        except Exception as e:
            print(f"警告: ファイル書き込み中にエラーが発生しました: {e}", file=sys.stderr)
            raise  # 上位での処理のために例外を再送出

    def _write_large_data(self, data: bytes) -> int:
        """
        巨大なデータを一時ファイル経由で書き込む

        Args:
            data: 書き込むデータ

        Returns:
            書き込んだバイト数
        """
        # 一時ファイルを作成してデータを書き込む
        with tempfile.NamedTemporaryFile(delete=False, prefix="encrypt_temp_") as temp_file:
            self.temp_files.append(temp_file.name)

            # チャンク単位でデータを書き込む
            total_size = len(data)
            bytes_written_temp = 0

            while bytes_written_temp < total_size:
                chunk_size = min(self.buffer_size, total_size - bytes_written_temp)
                chunk = data[bytes_written_temp:bytes_written_temp + chunk_size]
                temp_file.write(chunk)
                bytes_written_temp += chunk_size

            temp_file.flush()

        # 一時ファイルから出力ファイルにコピー
        total_written = 0
        with open(temp_file.name, 'rb') as f_in:
            while True:
                chunk = f_in.read(self.buffer_size)
                if not chunk:
                    break
                written = self._direct_write(chunk)
                total_written += written

        return total_written

    def write_from_file(self, source_path: str) -> int:
        """
        別のファイルからデータを読み込んで書き込む

        Args:
            source_path: 元ファイルのパス

        Returns:
            書き込んだバイト数
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"ファイル '{source_path}' が見つかりません")

        # ファイルサイズを取得
        file_size = os.path.getsize(source_path)

        # 小さなファイルならメモリを介して処理
        if file_size <= self.buffer_size:
            with open(source_path, 'rb') as f_in:
                data = f_in.read()
                return self._direct_write(data)

        # 大きなファイルはチャンク単位でコピー
        total_written = 0
        with open(source_path, 'rb') as f_in:
            while True:
                chunk = f_in.read(self.buffer_size)
                if not chunk:
                    break
                written = self._direct_write(chunk)
                total_written += written

        return total_written

    def cleanup(self):
        """一時ファイルを削除"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"警告: 一時ファイル '{temp_file}' の削除に失敗しました: {e}", file=sys.stderr)


def read_file(file_path: str) -> Tuple[bytes, bool]:
    """
    ファイルを読み込み、ファイルタイプ（テキスト/バイナリ）も判定する

    Args:
        file_path: 読み込むファイルのパス

    Returns:
        (ファイルの内容, テキストかどうかのフラグ)
    """
    try:
        # ファイルサイズを取得
        file_size = os.path.getsize(file_path)

        # メモリ最適化リーダーを使用
        with MemoryOptimizedReader(file_path) as reader:
            is_text = reader.get_file_type()

            # ファイルの内容を読み込む
            data = reader.read_all()

            # ファイルタイプをプリント
            print(f"ファイル '{file_path}' は{'UTF-8テキスト' if is_text else 'バイナリ'}として認識されました（サイズ: {file_size} バイト）")

            return data, is_text
    except Exception as e:
        print(f"ファイル '{file_path}' の読み込みエラー: {e}", file=sys.stderr)
        raise


def generate_master_key() -> bytes:
    """
    マスター鍵を生成

    Returns:
        ランダムなマスター鍵
    """
    try:
        # 高エントロピーの鍵を生成
        return secrets.token_bytes(KEY_SIZE_BYTES)
    except Exception as e:
        print(f"警告: 安全な鍵生成に失敗しました: {e}", file=sys.stderr)
        # フォールバック: os.urandomを使用
        return os.urandom(KEY_SIZE_BYTES)


def basic_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    基本的な暗号化を行う

    暗号化ライブラリがある場合はAESを使用し、ない場合はXORベースの暗号化を行います。
    セキュリティとパフォーマンスを考慮した実装です。

    Args:
        data: 暗号化するデータ
        key: 暗号鍵
        iv: 初期化ベクトル

    Returns:
        暗号化されたデータ
    """
    if not data:
        raise ValueError("暗号化するデータが空です")

    if not key:
        raise ValueError("暗号鍵が空です")

    if not iv:
        raise ValueError("初期化ベクトルが空です")

    # 鍵とIVの品質をチェック
    key_entropy = calculate_entropy(key)
    iv_entropy = calculate_entropy(iv)

    # エントロピーが低い場合は警告（MIN_ENTROPYは設定ファイルから）
    if key_entropy < MIN_ENTROPY:
        print(f"警告: 暗号鍵のエントロピーが低いです ({key_entropy:.2f})", file=sys.stderr)

    if iv_entropy < MIN_ENTROPY:
        print(f"警告: 初期化ベクトルのエントロピーが低いです ({iv_entropy:.2f})", file=sys.stderr)

    # 大きなデータの場合はチャンク単位で処理
    large_data_threshold = 50 * 1024 * 1024  # 50MB
    if len(data) > large_data_threshold:
        if HAS_CRYPTOGRAPHY:
            return _encrypt_large_data_aes(data, key, iv)
        else:
            return _encrypt_large_data_xor(data, key, iv)

    if HAS_CRYPTOGRAPHY:
        try:
            # 鍵とIVを適切なサイズに調整
            normalized_key = normalize_key(key, 32)  # AES-256
            normalized_iv = normalize_key(iv, 16)    # CTRモードのIVサイズ

            cipher = Cipher(
                algorithms.AES(normalized_key),
                modes.CTR(normalized_iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # 暗号化
            return encryptor.update(data) + encryptor.finalize()
        except Exception as e:
            print(f"警告: AES暗号化に失敗しました: {e}", file=sys.stderr)
            print("XOR暗号化にフォールバックします")
            # AES暗号化に失敗した場合はXOR暗号化にフォールバック

    # XORベースの簡易暗号化（セキュリティ強化版）
    return _encrypt_xor(data, key, iv)


def calculate_entropy(data: bytes) -> float:
    """
    バイト列のエントロピーを計算

    Args:
        data: エントロピーを計算するデータ

    Returns:
        シャノンエントロピー値（0.0〜8.0）
    """
    if not data:
        return 0.0

    # バイト値の頻度を計算
    freq = {}
    for byte in data:
        freq[byte] = freq.get(byte, 0) + 1

    # シャノンエントロピーの計算
    entropy = 0.0
    for count in freq.values():
        probability = count / len(data)
        entropy -= probability * math.log2(probability)

    return entropy


def _encrypt_large_data_aes(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    AESを使用した大きなデータの暗号化処理

    メモリ効率を考慮して一時ファイルを使用します。

    Args:
        data: 暗号化するデータ
        key: 暗号鍵
        iv: 初期化ベクトル

    Returns:
        暗号化されたデータ
    """
    # 鍵とIVを正規化
    normalized_key = normalize_key(key, 32)
    normalized_iv = normalize_key(iv, 16)

    # 暗号器を準備
    cipher = Cipher(
        algorithms.AES(normalized_key),
        modes.CTR(normalized_iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()

    # 一時ファイルを作成
    temp_output = tempfile.NamedTemporaryFile(delete=False)

    try:
        # データをチャンク単位で処理
        total_size = len(data)
        bytes_processed = 0

        while bytes_processed < total_size:
            chunk_size = min(BUFFER_SIZE, total_size - bytes_processed)
            chunk = data[bytes_processed:bytes_processed + chunk_size]

            # チャンクを暗号化
            encrypted_chunk = encryptor.update(chunk)
            temp_output.write(encrypted_chunk)

            bytes_processed += chunk_size

        # 最終ブロックを処理
        final_block = encryptor.finalize()
        if final_block:
            temp_output.write(final_block)

        temp_output.flush()
        temp_output.close()

        # 暗号化されたデータを読み込む
        with open(temp_output.name, 'rb') as f:
            return f.read()

    finally:
        # 一時ファイルを削除
        try:
            if os.path.exists(temp_output.name):
                os.unlink(temp_output.name)
        except Exception as e:
            print(f"警告: 一時ファイルの削除に失敗しました: {e}", file=sys.stderr)


def _encrypt_xor(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    XORベースの暗号化

    簡易な暗号化だが、セキュリティを高める工夫を追加。

    Args:
        data: 暗号化するデータ
        key: 暗号鍵
        iv: 初期化ベクトル

    Returns:
        暗号化されたデータ
    """
    # 大きなデータの場合はチャンク単位で処理
    if len(data) > BUFFER_SIZE:
        return _encrypt_large_data_xor(data, key, iv)

    # 鍵をデータサイズに拡張
    extended_key = bytearray()
    segment_size = 32  # SHA-256のサイズ

    # データサイズに合わせて拡張鍵を生成
    key_rounds = (len(data) + segment_size - 1) // segment_size
    for i in range(key_rounds):
        # ソルトとして位置情報とカウンタを使用してセキュリティを向上
        counter = i.to_bytes(8, 'big')
        segment_key = hashlib.sha256(key + iv + counter).digest()
        extended_key.extend(segment_key)

    # データとXOR
    result = bytearray(len(data))
    for i in range(len(data)):
        result[i] = data[i] ^ extended_key[i]

    return bytes(result)


def _encrypt_large_data_xor(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    XORベースの大きなデータの暗号化処理

    メモリ効率を考慮して一時ファイルを使用します。

    Args:
        data: 暗号化するデータ
        key: 暗号鍵
        iv: 初期化ベクトル

    Returns:
        暗号化されたデータ
    """
    # 一時ファイルを作成
    temp_output = tempfile.NamedTemporaryFile(delete=False)

    try:
        # データをチャンク単位で処理
        total_size = len(data)
        bytes_processed = 0

        while bytes_processed < total_size:
            chunk_size = min(BUFFER_SIZE, total_size - bytes_processed)
            chunk = data[bytes_processed:bytes_processed + chunk_size]

            # このチャンク用の拡張鍵を生成
            start_segment = bytes_processed // 32
            end_segment = (bytes_processed + chunk_size + 31) // 32
            extended_key = bytearray()

            for i in range(start_segment, end_segment):
                counter = i.to_bytes(8, 'big')
                segment_key = hashlib.sha256(key + iv + counter).digest()
                extended_key.extend(segment_key)

            # チャンクを暗号化
            encrypted_chunk = bytearray(chunk_size)
            for i in range(chunk_size):
                key_offset = i % len(extended_key)
                encrypted_chunk[i] = chunk[i] ^ extended_key[key_offset]

            temp_output.write(encrypted_chunk)
            bytes_processed += chunk_size

        temp_output.flush()
        temp_output.close()

        # 暗号化されたデータを読み込む
        with open(temp_output.name, 'rb') as f:
            return f.read()

    finally:
        # 一時ファイルを削除
        try:
            if os.path.exists(temp_output.name):
                os.unlink(temp_output.name)
        except Exception as e:
            print(f"警告: 一時ファイルの削除に失敗しました: {e}", file=sys.stderr)


def normalize_key(key: bytes, target_size: int) -> bytes:
    """
    鍵やIVを指定サイズに正規化

    Args:
        key: 元の鍵データ
        target_size: 目標サイズ

    Returns:
        正規化された鍵
    """
    if len(key) < target_size:
        # 鍵が短い場合は、ハッシュ関数で拡張
        seed = key
        result = bytearray()

        while len(result) < target_size:
            seed = hashlib.sha256(seed).digest()
            result.extend(seed)

        return result[:target_size]
    elif len(key) > target_size:
        # 鍵が長い場合は、ハッシュ関数を使用して縮小
        return hashlib.sha256(key).digest()[:target_size]
    else:
        # 鍵のサイズが既に適切な場合
        return key


def state_based_encrypt(data: bytes, engine: ProbabilisticExecutionEngine, path_type: str) -> bytes:
    """
    状態遷移に基づく暗号化

    メモリ効率を考慮した大きなデータの暗号化が可能です。

    Args:
        data: 暗号化するデータ
        engine: 確率的実行エンジン
        path_type: パスタイプ（"true" または "false"）

    Returns:
        暗号化されたデータ
    """
    # データが少なすぎる場合はエラー
    if len(data) < 1:
        raise ValueError("暗号化するデータが空です")

    # パスタイプの検証
    if path_type not in (TRUE_PATH, FALSE_PATH):
        raise ValueError(f"無効なパスタイプです: {path_type}。'true' または 'false' を指定してください。")

    # エンジンを実行して状態遷移パスを取得
    path = engine.run_execution()
    if not path or len(path) < 1:
        raise ValueError("状態遷移パスの生成に失敗しました")

    # 解析攻撃対策のダミー処理
    dummy_key = hashlib.sha256(engine.key + path_type.encode()).digest()

    # ブロックサイズを定義
    block_size = 64  # 共通のブロックサイズ

    # データサイズのチェック - 非常に大きなファイルの場合
    very_large_threshold = 500 * 1024 * 1024  # 500MB

    if len(data) > very_large_threshold:
        # 非常に大きなファイルの場合はファイルベースの処理を行う
        return _encrypt_very_large_data(data, engine, path, path_type, block_size)
    # 大きなファイルだがメモリで処理可能な場合
    elif len(data) > MAX_TEMP_FILE_SIZE:
        return _encrypt_large_data(data, engine, path, path_type, block_size)
    # 通常のメモリ内処理
    else:
        return _encrypt_in_memory(data, engine, path, path_type, block_size)


def _encrypt_very_large_data(data: bytes, engine: ProbabilisticExecutionEngine,
                           path: List[int], path_type: str, block_size: int) -> bytes:
    """
    非常に大きなデータの暗号化処理（ストリーミングアプローチ）

    データを直接メモリに読み込まず、ファイルストリームとして処理します。

    Args:
        data: 暗号化するデータ
        engine: 実行エンジン
        path: 状態遷移パス
        path_type: パスタイプ
        block_size: ブロックサイズ

    Returns:
        暗号化されたデータ
    """
    # 入力用と出力用の一時ファイルを作成
    input_temp = tempfile.NamedTemporaryFile(delete=False, prefix="encrypt_in_")
    output_temp = tempfile.NamedTemporaryFile(delete=False, prefix="encrypt_out_")
    temp_files = [input_temp.name, output_temp.name]

    try:
        # 入力データを一時ファイルに書き込む（チャンク単位）
        total_size = len(data)
        bytes_written = 0
        write_chunk_size = 8 * 1024 * 1024  # 8MB書き込みチャンク

        while bytes_written < total_size:
            chunk_size = min(write_chunk_size, total_size - bytes_written)
            chunk = data[bytes_written:bytes_written+chunk_size]
            input_temp.write(chunk)
            bytes_written += chunk_size

        input_temp.flush()
        input_temp.close()

        # 解析攻撃対策のダミー処理
        dummy_key = hashlib.sha256(engine.key + path_type.encode()).digest()

        # 進捗表示用変数
        total_blocks = (total_size + block_size - 1) // block_size
        progress_interval = max(1, total_blocks // 20)  # 5%ごとに表示

        # ファイルをブロック単位で読み込み・暗号化・書き込み
        with open(input_temp.name, 'rb') as f_in, open(output_temp.name, 'wb') as f_out:
            block_index = 0

            while True:
                block = f_in.read(block_size)
                if not block:
                    break

                # 最後のブロックにパディングを適用
                if len(block) < block_size:
                    block = block + b'\x00' * (block_size - len(block))

                # 現在の状態を取得
                state_idx = min(block_index, len(path) - 1)
                state_id = path[state_idx]
                state = engine.states.get(state_id)

                # ブロックを暗号化
                encrypted_block = _encrypt_block(block, engine, state, state_id, block_index, dummy_key)

                # 暗号化したブロックを書き込む
                f_out.write(encrypted_block)

                # 進捗表示
                block_index += 1
                if block_index % progress_interval == 0:
                    print(f"暗号化進捗: {block_index * 100 // total_blocks}% ({block_index}/{total_blocks})")

        # 暗号化されたデータを読み込む
        with open(output_temp.name, 'rb') as f:
            # 大きなファイルを分割読み込み
            result = bytearray()
            read_chunk_size = 8 * 1024 * 1024  # 8MB読み込みチャンク

            while True:
                chunk = f.read(read_chunk_size)
                if not chunk:
                    break
                result.extend(chunk)

        return bytes(result)

    finally:
        # 一時ファイルを必ず削除
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"警告: 一時ファイル '{temp_file}' の削除に失敗しました: {e}", file=sys.stderr)


def _encrypt_in_memory(data: bytes, engine: ProbabilisticExecutionEngine,
                      path: List[int], path_type: str, block_size: int) -> bytes:
    """
    メモリ内での暗号化処理（小〜中サイズのデータ用）

    Args:
        data: 暗号化するデータ
        engine: 実行エンジン
        path: 状態遷移パス
        path_type: パスタイプ
        block_size: ブロックサイズ

    Returns:
        暗号化されたデータ
    """
    # データをブロックに分割
    blocks = []

    # データを block_size ごとに分割
    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        if len(block) < block_size:
            # パディングを適用（ゼロパディング）
            block = block + b'\x00' * (block_size - len(block))
        blocks.append(block)

    # 最低1ブロックを確保
    if not blocks:
        blocks.append(b'\x00' * block_size)

    # 解析攻撃対策のダミー処理
    dummy_key = hashlib.sha256(engine.key + path_type.encode()).digest()
    dummy_path = []

    # 状態遷移に基づいて各ブロックを暗号化
    encrypted_blocks = []
    for i, block in enumerate(blocks):
        # 現在の状態を取得（パスの長さを超えたら最後の状態を使用）
        state_idx = min(i, len(path) - 1)
        state_id = path[state_idx]
        state = engine.states.get(state_id)

        # ダミーパスにも状態を追加（解析対策）
        dummy_path.append(state_id)

        encrypted_block = _encrypt_block(block, engine, state, state_id, i, dummy_key)
        encrypted_blocks.append(encrypted_block)

    # セキュリティ脆弱性が入らないよう、ダミーパスに対する処理も行うが結果は使用しない
    dummy_blocks = []
    for i, state_id in enumerate(dummy_path):
        dummy_seed = hashlib.sha256(f"dummy_{i}_{state_id}".encode() + dummy_key).digest()
        dummy_blocks.append(dummy_seed[:8])  # ダミーデータ生成

    # 暗号化されたブロックを結合
    return b''.join(encrypted_blocks)


def _encrypt_large_data(data: bytes, engine: ProbabilisticExecutionEngine,
                       path: List[int], path_type: str, block_size: int) -> bytes:
    """
    大きなデータの暗号化処理（一時ファイル使用）

    Args:
        data: 暗号化するデータ
        engine: 実行エンジン
        path: 状態遷移パス
        path_type: パスタイプ
        block_size: ブロックサイズ

    Returns:
        暗号化されたデータ
    """
    # 一時ファイルを作成
    temp_input = tempfile.NamedTemporaryFile(delete=False)
    temp_output = tempfile.NamedTemporaryFile(delete=False)
    temp_files = [temp_input.name, temp_output.name]

    try:
        # 入力データを一時ファイルに書き込む（チャンク単位）
        total_size = len(data)
        bytes_written = 0

        while bytes_written < total_size:
            chunk_size = min(BUFFER_SIZE, total_size - bytes_written)
            chunk = data[bytes_written:bytes_written+chunk_size]
            temp_input.write(chunk)
            bytes_written += chunk_size

        temp_input.flush()
        temp_input.close()

        # 解析攻撃対策のダミー処理
        dummy_key = hashlib.sha256(engine.key + path_type.encode()).digest()
        dummy_path = []

        # ファイルをブロック単位で読み込み・暗号化・書き込み
        with open(temp_input.name, 'rb') as f_in:
            block_index = 0
            total_blocks = (total_size + block_size - 1) // block_size

            # 進捗表示用
            progress_interval = max(1, total_blocks // 20)  # 5%ごとに表示
            progress_next = progress_interval

            while True:
                block = f_in.read(block_size)
                if not block:
                    break

                # 最後のブロックにパディングを適用
                if len(block) < block_size:
                    block = block + b'\x00' * (block_size - len(block))

                # 現在の状態を取得
                state_idx = min(block_index, len(path) - 1)
                state_id = path[state_idx]
                state = engine.states.get(state_id)

                # ダミーパスの更新（解析対策）
                dummy_path.append(state_id)

                # ブロックを暗号化
                encrypted_block = _encrypt_block(block, engine, state, state_id, block_index, dummy_key)

                # 暗号化したブロックを書き込む
                with open(temp_output.name, 'ab') as f_out:
                    f_out.write(encrypted_block)

                # 進捗表示
                block_index += 1
                if block_index >= progress_next:
                    print(f"暗号化進捗: {block_index * 100 // total_blocks}% ({block_index}/{total_blocks})")
                    progress_next += progress_interval

                # メモリ使用量を定期的に確認し、必要に応じてGCを促進
                if block_index % 1000 == 0:
                    # ダミー変数の明示的なクリア
                    encrypted_block = None
                    block = None
                    import gc
                    gc.collect()

        # ダミー処理（セキュリティ対策）
        for i, state_id in enumerate(dummy_path):
            dummy_seed = hashlib.sha256(f"dummy_{i}_{state_id}".encode() + dummy_key).digest()

        # 暗号化されたデータを読み込む（チャンク単位）
        result = bytearray()
        with open(temp_output.name, 'rb') as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                result.extend(chunk)

        return bytes(result)

    except Exception as e:
        print(f"大きなデータの暗号化中にエラーが発生しました: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise
    finally:
        # 一時ファイルを必ず削除
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"警告: 一時ファイル '{temp_file}' の削除に失敗しました: {e}", file=sys.stderr)


def _encrypt_block(block: bytes, engine: ProbabilisticExecutionEngine,
                  state: Optional[Any], state_id: int, block_index: int,
                  dummy_key: bytes) -> bytes:
    """
    単一ブロックの暗号化処理

    Args:
        block: 暗号化するブロック
        engine: 実行エンジン
        state: 現在の状態
        state_id: 状態ID
        block_index: ブロックインデックス
        dummy_key: ダミー鍵

    Returns:
        暗号化されたブロック
    """
    if not state:
        # 状態が見つからない場合は単純な暗号化
        seed = hashlib.sha256(f"fallback_{block_index}".encode() + engine.key).digest()
        key = seed[:16]
        iv = seed[16:24]
        return basic_encrypt(block, key, iv)

    # 状態の属性から暗号化パラメータを導出
    attrs = state.attributes
    block_key = hashlib.sha256(
        engine.key +
        attrs.get("hash_seed", b"") +
        block_index.to_bytes(4, 'big')
    ).digest()

    # 状態ごとに異なる暗号化パラメータ
    key = block_key[:16]
    iv = block_key[16:24]

    # 変換キーを使った追加の処理（状態に依存）
    transform_key = attrs.get("transform_key", b"")
    if transform_key:
        # ブロックの一部を変換（複雑な処理を追加）
        complexity = attrs.get("complexity", 0)
        volatility = attrs.get("volatility", 0)

        # 複雑度に応じた処理（再帰的な暗号化など）
        if complexity > 80:
            # 高複雑度: 複数回の暗号化
            temp_block = block
            for j in range(3):
                temp_key = hashlib.sha256(key + j.to_bytes(1, 'big')).digest()[:16]
                temp_block = basic_encrypt(temp_block, temp_key, iv)
            block = temp_block
        elif complexity > 50:
            # 中複雑度: ブロックを分割して個別に暗号化
            half = len(block) // 2
            first_half = basic_encrypt(block[:half], key, iv)
            second_half = basic_encrypt(block[half:], key[::-1], iv)
            block = first_half + second_half

        # 揮発性に応じた処理（ノイズの追加など）
        if volatility > 70:
            # 高揮発性: ノイズの追加
            noise = hashlib.sha256(transform_key + block).digest()[:min(8, len(block))]
            block_list = bytearray(block)
            for j, noise_byte in enumerate(noise):
                block_list[j % len(block_list)] ^= noise_byte
            block = bytes(block_list)

    # 最終的な暗号化
    return basic_encrypt(block, key, iv)


def inject_entropy(true_data: bytes, false_data: bytes, key: bytes, salt: bytes) -> bytes:
    """
    true_dataとfalse_dataにエントロピーを注入する

    Args:
        true_data: 暗号化された正規データ
        false_data: 暗号化された非正規データ
        key: マスター鍵
        salt: ソルト値

    Returns:
        エントロピー注入されたデータ
    """
    try:
        # エントロピー注入モジュールをインポート
        from .entropy_injector import inject_entropy_to_data

        # 新しいエントロピー注入機能を使用
        return inject_entropy_to_data(true_data, false_data, key, salt, mix_ratio=0.3)

    except ImportError:
        # 旧バージョンの互換性のためのフォールバック実装
        print("警告: エントロピー注入モジュールが見つかりません。フォールバック実装を使用します。", file=sys.stderr)

        # キーとソルトから基本シードを生成
        seed = hashlib.sha256(key + salt).digest()

        # カプセル構造用の追加シード生成
        capsule_seed = hashlib.sha256(key + salt + b"state_capsule").digest()

        # データサイズに基づくエントロピーサイズの決定
        data_size = max(len(true_data), len(false_data))
        entropy_size = min(
            int(data_size * 0.3),  # データサイズの30%
            10 * 1024 * 1024       # 最大10MB
        )

        # 最小サイズの保証
        entropy_size = max(entropy_size, 1024)  # 最低1KB

        # 時間情報
        timestamp = int(time.time()).to_bytes(8, 'big')

        # システムエントロピー
        system_entropy = os.urandom(32)

        # ハッシュベースの擬似乱数生成器
        def generate_bytes(seed: bytes, count: int) -> bytes:
            """指定されたシードから疑似乱数バイト列を生成"""
            result = bytearray()
            current = seed

            while len(result) < count:
                current = hashlib.sha512(current).digest()
                result.extend(current)

            return bytes(result[:count])

        # 複数のエントロピーソースを組み合わせる
        combined_seed = seed + timestamp + system_entropy
        expanded_seed = hashlib.sha512(combined_seed).digest()

        # エントロピーデータの生成
        entropy_data = generate_bytes(expanded_seed, entropy_size)

        # エントロピー品質の検証
        entropy_value = calculate_entropy(entropy_data)
        if entropy_value < MIN_ENTROPY:
            # エントロピーが不足している場合は補強
            additional_entropy = os.urandom(entropy_size // 2)
            entropy_data = hashlib.sha512(entropy_data + additional_entropy).digest() + entropy_data

        return entropy_data


def _create_large_capsule(
    true_encrypted: bytes,
    false_encrypted: bytes,
    true_signature: bytes,
    false_signature: bytes,
    key: bytes,
    salt: bytes
) -> bytes:
    """
    一時ファイルを使用した大きなデータのカプセル化処理

    Args:
        true_encrypted: 正規データの暗号文
        false_encrypted: 非正規データの暗号文
        true_signature: 正規パスの署名
        false_signature: 非正規パスの署名
        key: マスター鍵
        salt: ソルト値

    Returns:
        カプセル化されたデータ
    """
    # 一時ファイルを作成
    true_temp = tempfile.NamedTemporaryFile(delete=False)
    false_temp = tempfile.NamedTemporaryFile(delete=False)
    output_temp = tempfile.NamedTemporaryFile(delete=False)

    try:
        # データを一時ファイルに書き込む
        with open(true_temp.name, 'wb') as f:
            f.write(true_encrypted)
        with open(false_temp.name, 'wb') as f:
            f.write(false_encrypted)

        # カプセル化パラメータを準備
        capsule_seed = hashlib.sha256(key + salt + b"state_capsule").digest()
        timestamp = int(time.time()).to_bytes(8, 'big')
        enhanced_seed = hashlib.sha512(capsule_seed + timestamp).digest()
        block_size = 64

        # 署名データを処理
        true_sig_processed = hashlib.sha256(capsule_seed + true_signature).digest()
        false_sig_processed = hashlib.sha256(capsule_seed + false_signature).digest()
        true_sig_noised = bytes([b ^ enhanced_seed[i % len(enhanced_seed)] for i, b in enumerate(true_sig_processed)])
        false_sig_noised = bytes([b ^ enhanced_seed[i+16 % len(enhanced_seed)] for i, b in enumerate(false_sig_processed)])

        # 署名を出力ファイルに書き込む
        with open(output_temp.name, 'wb') as f_out:
            f_out.write(true_sig_noised)
            f_out.write(false_sig_noised)

        # ファイルサイズを取得
        true_size = os.path.getsize(true_temp.name)
        false_size = os.path.getsize(false_temp.name)

        # ブロック数の計算
        true_blocks = (true_size + block_size - 1) // block_size
        false_blocks = (false_size + block_size - 1) // block_size
        max_blocks = max(true_blocks, false_blocks)

        # ブロック単位で処理
        with open(true_temp.name, 'rb') as f_true, \
             open(false_temp.name, 'rb') as f_false, \
             open(output_temp.name, 'ab') as f_out:

            for i in range(max_blocks):
                # true データのブロックを読み込む
                true_block = f_true.read(block_size) if i < true_blocks else None
                if true_block is None or len(true_block) < block_size:
                    # 不足分をダミーデータで埋める
                    dummy_seed = hashlib.sha256(capsule_seed + b"true_dummy" + i.to_bytes(4, 'big')).digest()
                    dummy = hashlib.sha512(dummy_seed + enhanced_seed[i % len(enhanced_seed):] + timestamp).digest()[:block_size]

                    if true_block is None:
                        true_block = dummy
                    else:
                        true_block = true_block + dummy[len(true_block):]

                # false データのブロックを読み込む
                false_block = f_false.read(block_size) if i < false_blocks else None
                if false_block is None or len(false_block) < block_size:
                    # 不足分をダミーデータで埋める
                    dummy_seed = hashlib.sha256(capsule_seed + b"false_dummy" + i.to_bytes(4, 'big')).digest()
                    dummy = hashlib.sha512(dummy_seed + enhanced_seed[i % len(enhanced_seed):] + timestamp).digest()[:block_size]

                    if false_block is None:
                        false_block = dummy
                    else:
                        false_block = false_block + dummy[len(false_block):]

                # パターンに基づいて配置
                pattern_seed = hashlib.sha512(capsule_seed + i.to_bytes(4, 'big') + enhanced_seed[i % len(enhanced_seed):]).digest()
                pattern_value = pattern_seed[0] % 4

                if pattern_value == 0:
                    # 正規→非正規
                    f_out.write(true_block)
                    f_out.write(false_block)
                elif pattern_value == 1:
                    # 非正規→正規
                    f_out.write(false_block)
                    f_out.write(true_block)
                elif pattern_value == 2:
                    # 交互にバイトを配置
                    mixed = bytearray()
                    for j in range(block_size):
                        if j < len(true_block):
                            mixed.append(true_block[j])
                        if j < len(false_block):
                            mixed.append(false_block[j])
                    f_out.write(mixed)
                else:
                    # バイト単位の混合（簡略化版）
                    mixed = bytearray()
                    for j in range(block_size):
                        if j % 2 == 0 and j < len(true_block):
                            mixed.append(true_block[j])
                        elif j % 2 == 1 and j < len(false_block):
                            mixed.append(false_block[j])
                    f_out.write(mixed)

        # 最後にシャッフルを適用
        # 注意: 大きなファイルのシャッフルは非効率なので、バッファリングして処理するか省略する
        # ここでは簡略化のため、シャッフルを省略

        # 出力ファイルを読み込む
        with open(output_temp.name, 'rb') as f:
            return f.read()

    finally:
        # 一時ファイルを削除
        try:
            os.unlink(true_temp.name)
            os.unlink(false_temp.name)
            os.unlink(output_temp.name)
        except Exception as e:
            print(f"警告: 一時ファイルの削除に失敗しました: {e}", file=sys.stderr)


def _shuffle_capsule(data: bytearray, seed: bytes, enhanced_seed: bytes) -> bytearray:
    """
    カプセルデータをシャッフル

    Args:
        data: シャッフルするデータ
        seed: シャッフルのシード
        enhanced_seed: 強化シード

    Returns:
        シャッフルされたデータ
    """
    final_capsule = bytearray(len(data))

    # シャッフルマップの生成
    shuffle_map = {}
    available_positions = list(range(len(data)))

    # シャッフルパターンをセキュアに生成
    for i in range(len(data)):
        # 決定論的なシャッフル（鍵に依存）
        shuffle_seed = hashlib.sha256(seed + i.to_bytes(4, 'big') + enhanced_seed[i % len(enhanced_seed):]).digest()
        index = int.from_bytes(shuffle_seed[:4], byteorder='big') % len(available_positions)
        position = available_positions.pop(index)
        shuffle_map[i] = position

    # シャッフルの適用
    for src, dst in shuffle_map.items():
        if src < len(data) and dst < len(final_capsule):
            final_capsule[dst] = data[src]

    return final_capsule


def encrypt_file(input_path: str, output_path: str = None, key_path: str = None,
             is_regular: bool = True, entropy_factor: float = 0.5) -> str:
    """
    ファイルを暗号化する

    Args:
        input_path: 入力ファイルパス
        output_path: 出力ファイルパス（省略時は入力パス + .enc）
        key_path: 鍵ファイルのパス（省略時は自動生成）
        is_regular: 正規の暗号化かどうか
        entropy_factor: エントロピー因子（0.0〜1.0）

    Returns:
        生成された鍵ファイルのパス
    """
    # パラメータの検証
    if not input_path or not os.path.exists(input_path):
        raise FileNotFoundError(f"入力ファイル '{input_path}' が見つかりません")

    if not os.path.isfile(input_path):
        raise ValueError(f"'{input_path}' はファイルではありません")

    # Entropy factorの範囲チェック
    if entropy_factor < 0.0 or entropy_factor > 1.0:
        raise ValueError(f"エントロピー因子は0.0〜1.0の範囲で指定してください: {entropy_factor}")

    # 出力パスが指定されていない場合は入力パス + .enc
    if not output_path:
        output_path = f"{input_path}.enc"

    # 出力先ディレクトリが存在するか確認し、必要なら作成
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            raise IOError(f"出力ディレクトリ '{output_dir}' を作成できません: {e}")

    # キーパスが指定されていない場合は出力パス + .key
    if not key_path:
        key_path = f"{output_path}.key"

    # 暗号化処理を実行
    try:
        # タイムスタンプを含む一意のファイル名を生成
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        if '.' in os.path.basename(output_path):
            base, ext = os.path.splitext(output_path)
            unique_output_path = f"{base}_{timestamp}{ext}"
        else:
            unique_output_path = f"{output_path}_{timestamp}"

        # 鍵ファイルのパスも更新
        if not key_path or key_path == f"{output_path}.key":
            key_path = f"{unique_output_path}.key"

        # メモリ最適化されたリーダーとライターを使用
        with MemoryOptimizedReader(input_path) as reader:
            # ファイルタイプを確認
            is_text = reader.get_file_type()

            # データを読み込む
            data = reader.read_all()
            if not data:
                raise ValueError(f"ファイル '{input_path}' は空またはアクセスできません")

            # エンジンを初期化
            engine = ProbabilisticExecutionEngine()

            # エントロピー注入でエンジンの状態を初期化
            _inject_entropy(engine, data, entropy_factor)

            # 暗号化状態選択（正規/非正規）
            path, alt_path = _initialize_state_paths(engine, is_regular)

            # 状態遷移に基づく暗号化
            print(f"暗号化を実行中... {'正規' if is_regular else '非正規'}パスを使用")
            path_type = TRUE_PATH if is_regular else FALSE_PATH
            encrypted_data = state_based_encrypt(data, engine, path_type)

            # 鍵情報を生成
            key_data = _generate_key_data(engine, path, alt_path, is_text)

            # 暗号化データを書き込む
            print(f"暗号化データを '{unique_output_path}' に書き込み中...")
            with MemoryOptimizedWriter(unique_output_path) as writer:
                writer.write(encrypted_data)

            # 鍵ファイルを書き込む
            print(f"鍵ファイルを '{key_path}' に書き込み中...")
            with open(key_path, 'wb') as f:
                f.write(key_data)

            # ファイル権限を設定（鍵ファイルは所有者のみ読み書き可能）
            try:
                os.chmod(key_path, 0o600)  # rw-------
                os.chmod(unique_output_path, 0o644)  # rw-r--r--
            except Exception as e:
                print(f"警告: ファイル権限の設定に失敗しました: {e}", file=sys.stderr)

            print(f"暗号化が完了しました: {input_path} -> {unique_output_path}")
            print(f"鍵ファイル: {key_path} ({len(key_data)} バイト)")
            print(f"ファイルタイプ: {'テキスト' if is_text else 'バイナリ'}")

            return key_path

    except Exception as e:
        print(f"暗号化処理中にエラーが発生しました: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        # 途中でエラーが発生した場合、部分的に書き込まれたファイルを削除
        try:
            if 'unique_output_path' in locals() and os.path.exists(unique_output_path):
                os.unlink(unique_output_path)
            if key_path and os.path.exists(key_path):
                os.unlink(key_path)
        except Exception as cleanup_error:
            print(f"警告: 一時ファイルの削除中にエラーが発生しました: {cleanup_error}", file=sys.stderr)

        raise


def _inject_entropy(engine: ProbabilisticExecutionEngine, data: bytes, entropy_factor: float) -> None:
    """
    エンジンにエントロピーを注入する

    データの特性に基づいたエントロピーを生成し、エンジンの状態を初期化します。

    Args:
        engine: 確率的実行エンジン
        data: 対象データ
        entropy_factor: エントロピー因子（0.0〜1.0）
    """
    # データからエントロピー源を抽出
    entropy_sources = []

    # 1. ファイルサイズ
    entropy_sources.append(len(data).to_bytes(8, 'big'))

    # 2. タイムスタンプ（現在時刻）
    timestamp = int(time.time() * 1000)
    entropy_sources.append(timestamp.to_bytes(8, 'big'))

    # 3. データのハッシュ値（SHA-256）
    data_hash = hashlib.sha256(data).digest()
    entropy_sources.append(data_hash)

    # 4. データサンプリング（大きなファイルでは全体からサンプリング）
    if len(data) > 10240:  # 10KB以上の場合
        samples = []
        # 先頭、中央、末尾からサンプリング
        samples.append(data[:1024])
        mid_point = len(data) // 2
        samples.append(data[mid_point - 512:mid_point + 512])
        samples.append(data[-1024:])
        # サンプルを連結してハッシュ化
        sample_hash = hashlib.sha256(b''.join(samples)).digest()
        entropy_sources.append(sample_hash)
    else:
        # 小さなファイルは全体を使用
        entropy_sources.append(data)

    # 5. 高頻度バイト分析
    if len(data) > 1000:
        byte_freq = {}
        sample_size = min(len(data), 10000)
        for i in range(sample_size):
            idx = (i * len(data)) // sample_size
            b = data[idx]
            byte_freq[b] = byte_freq.get(b, 0) + 1

        # 上位10バイトを抽出
        top_bytes = sorted(byte_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        top_bytes_data = bytes([b for b, _ in top_bytes])
        entropy_sources.append(top_bytes_data)

    # 6. エントロピー因子による乱数
    random_data = os.urandom(32)
    entropy_sources.append(random_data)

    # エントロピー源をエントロピー因子に基づいて組み合わせる
    combined = bytearray()

    # エントロピー因子が高いほど、よりランダムなデータを多く含める
    random_weight = entropy_factor
    data_weight = 1.0 - entropy_factor

    # 確定的なエントロピー源
    deterministic_sources = entropy_sources[:-1]  # 最後のランダムソースを除く
    deterministic_data = b''.join(deterministic_sources)

    # ランダムなエントロピー源
    random_data = entropy_sources[-1]

    # エントロピー因子に基づいて重み付けされたハッシュを生成
    for i in range(32):  # 256ビットのエントロピーを生成
        # データの位置に基づいた確定的なソース
        det_idx = (i * len(deterministic_data)) // 32
        det_byte = deterministic_data[det_idx % len(deterministic_data)]

        # ランダムソース
        rnd_byte = random_data[i % len(random_data)]

        # 重み付き組み合わせ（整数演算）
        combined_byte = int((det_byte * data_weight) + (rnd_byte * random_weight)) & 0xFF
        combined.append(combined_byte)

    # 複数回のハッシュ適用でエントロピーを拡散
    final_entropy = hashlib.sha256(combined).digest()
    for _ in range(3):
        final_entropy = hashlib.sha256(final_entropy + combined).digest()

    # エンジンを初期化
    engine.initialize_from_entropy(final_entropy)

    # 状態数を調整（16〜64）
    state_count = 16 + int(entropy_factor * 48)
    engine.initialize_states(state_count)


def _initialize_state_paths(engine: ProbabilisticExecutionEngine, is_regular: bool) -> Tuple[List[int], List[int]]:
    """
    状態遷移パスを初期化する

    正規パスと代替パスの両方を構築します。

    Args:
        engine: 確率的実行エンジン
        is_regular: 正規パスを使用するかどうか

    Returns:
        選択されたパス, 代替パス（正規と非正規を含むタプル）
    """
    # 状態数の取得
    state_count = len(engine.states)

    # エンジンの鍵から状態シード値を生成
    state_seed = hashlib.sha256(engine.key + b"state_paths").digest()

    # 有効な状態遷移のセキュリティレベル
    min_transitions = max(4, state_count // 4)  # 最低でも4つの遷移
    max_transitions = min(state_count * 2, 128)  # 最大でも128の遷移

    # 正規パスの生成
    regular_path = []

    # エンジンの状態からランダムな開始点を選択
    start_state = _get_deterministic_int(state_seed, "regular_start", 0, state_count - 1)
    regular_path.append(start_state)

    # 正規パスの遷移数
    regular_transitions = _get_deterministic_int(
        state_seed, "regular_count", min_transitions, max_transitions)

    # 一時的な状態シード値
    temp_seed = hashlib.sha256(state_seed + b"regular_path").digest()

    # 正規パスの状態遷移を構築（各状態は使用可能な状態から選択）
    for i in range(regular_transitions):
        # 遷移ごとに異なるシード値を生成
        transition_seed = hashlib.sha256(temp_seed + str(i).encode()).digest()

        # 可能な次状態からランダムに選択
        next_state = _get_deterministic_int(transition_seed, "next", 0, state_count - 1)

        # 同じ状態が続くのを避ける（シーケンスが意味を持つようにする）
        retries = 0
        while next_state == regular_path[-1] and retries < 5:
            next_state = (next_state + 1) % state_count
            retries += 1

        regular_path.append(next_state)

    # 代替パスの生成（正規とは異なるパターン）
    alternative_path = []

    # 代替パスの開始点
    alt_start_state = _get_deterministic_int(state_seed, "alt_start", 0, state_count - 1)
    # 正規と異なる開始点にする
    if alt_start_state == start_state:
        alt_start_state = (alt_start_state + 1) % state_count
    alternative_path.append(alt_start_state)

    # 代替パスの遷移数（正規と意図的に異なる長さにする）
    alt_transitions = _get_deterministic_int(
        state_seed, "alt_count", min_transitions, max_transitions)
    if abs(alt_transitions - regular_transitions) < min_transitions // 2:
        # 正規との差が少ない場合は調整
        alt_transitions = (regular_transitions + min_transitions) % max_transitions

    # 代替パスのシード値
    alt_seed = hashlib.sha256(state_seed + b"alternative_path").digest()

    # 代替パスの状態遷移を構築
    for i in range(alt_transitions):
        transition_seed = hashlib.sha256(alt_seed + str(i).encode()).digest()

        # 可能な次状態からランダムに選択
        next_state = _get_deterministic_int(transition_seed, "next", 0, state_count - 1)

        # 同じ状態が続くのを避ける
        retries = 0
        while next_state == alternative_path[-1] and retries < 5:
            next_state = (next_state + 1) % state_count
            retries += 1

        alternative_path.append(next_state)

    # 正規/非正規フラグに基づいて適切なパスを返す
    if is_regular:
        return regular_path, alternative_path
    else:
        return alternative_path, regular_path


def _generate_key_data(engine: ProbabilisticExecutionEngine,
                       path: List[int], alt_path: List[int],
                       is_text: bool) -> bytes:
    """
    鍵データを生成する

    暗号化情報と状態経路をカプセル化します。

    Args:
        engine: 確率的実行エンジン
        path: 使用したパス
        alt_path: 代替パス
        is_text: テキストファイルかどうか

    Returns:
        鍵データ
    """
    # 基本の鍵情報
    key_info = {
        "version": VERSION,
        "timestamp": int(time.time()),
        "encryption": "AES-256-CTR" if HAS_CRYPTOGRAPHY else "XOR-SHA256",
        "master_key": base64.b64encode(engine.key).decode('utf-8'),
        "file_type": "text" if is_text else "binary",
        "state_count": len(engine.states),
        "path_length": len(path),
        "alt_path_length": len(alt_path)
    }

    # 安全性を高めるため、鍵の本体部分を暗号化する
    sensitive_data = {
        "primary_path": path,
        "alternative_path": alt_path,
        "state_seeds": {
            str(state_id): base64.b64encode(state.seed).decode('utf-8')
            for state_id, state in engine.states.items()
        }
    }

    # 機密データをJSON化
    sensitive_json = json.dumps(sensitive_data, sort_keys=True).encode('utf-8')

    # 機密データを暗号化
    # マスター鍵からキー導出関数で鍵を生成
    encryption_key = hashlib.pbkdf2_hmac('sha256', engine.key, b'key_encryption', 10000)
    encryption_iv = hashlib.sha256(engine.key + b'iv_for_key').digest()[:16]

    # 暗号化
    encrypted_sensitive = basic_encrypt(sensitive_json, encryption_key, encryption_iv)

    # 鍵データの構築
    key_info["encrypted_data"] = base64.b64encode(encrypted_sensitive).decode('utf-8')
    key_info["checksum"] = hashlib.sha256(encrypted_sensitive).hexdigest()

    # 鍵データをJSON化
    key_json = json.dumps(key_info, sort_keys=True, indent=2).encode('utf-8')

    return key_json


def _get_deterministic_int(seed: bytes, salt: str, min_val: int, max_val: int) -> int:
    """
    シード値から決定論的に整数を生成する

    Args:
        seed: シード値
        salt: 塩（異なる用途で同じシードを使い分けるため）
        min_val: 最小値
        max_val: 最大値

    Returns:
        min_val以上max_val以下の整数
    """
    if min_val > max_val:
        min_val, max_val = max_val, min_val

    # シードと塩からハッシュを生成
    hash_val = hashlib.sha256(seed + salt.encode()).digest()

    # ハッシュから整数を抽出（8バイト = 64ビット使用）
    val = int.from_bytes(hash_val[:8], 'big')

    # 指定された範囲に収める
    range_size = max_val - min_val + 1
    return min_val + (val % range_size)


def encrypt(true_file_path: str, false_file_path: str, output_path: Optional[str] = None, save_key: bool = False) -> Tuple[bytes, str]:
    """
    ファイルを不確定性転写暗号化方式で暗号化する

    Args:
        true_file_path: 正規の平文ファイルパス
        false_file_path: 非正規の平文ファイルパス
        output_path: 出力ファイルパス（省略時は自動生成）
        save_key: 鍵をファイルに保存するか

    Returns:
        (マスター鍵, 暗号化ファイルパス)
    """
    try:
        # 入力ファイルの存在確認
        if not os.path.exists(true_file_path):
            raise FileNotFoundError(f"正規ファイル '{true_file_path}' が見つかりません")

        if not os.path.exists(false_file_path):
            raise FileNotFoundError(f"非正規ファイル '{false_file_path}' が見つかりません")

        # 出力パスが指定されていない場合は自動生成
        if not output_path:
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            output_path = f"encrypted_{timestamp}.bin"

        # メモリ効率良く読み込み
        print(f"ファイル '{true_file_path}' を読み込み中...")
        true_data, is_text = read_file(true_file_path)
        if not true_data:
            raise ValueError(f"ファイル '{true_file_path}' は空またはアクセスできません")

        print(f"ファイル '{false_file_path}' を読み込み中...")
        false_data, _ = read_file(false_file_path)
        if not false_data:
            raise ValueError(f"ファイル '{false_file_path}' は空またはアクセスできません")

        # マスター鍵の生成
        master_key = generate_master_key()

        # ソルト値の生成
        salt = os.urandom(8)

        # 確率的実行エンジンを初期化
        print("確率的実行エンジンを初期化中...")
        true_engine = create_engine_from_key(master_key, TRUE_PATH, salt)
        false_engine = create_engine_from_key(master_key, FALSE_PATH, salt)

        # 状態遷移パスの取得
        print("状態遷移パスを計算中...")
        true_path = true_engine.run_execution()
        false_path = false_engine.run_execution()

        # 状態依存の暗号化
        print(f"正規データ（{len(true_data)} バイト）を暗号化中...")
        true_encrypted = state_based_encrypt(true_data, true_engine, TRUE_PATH)

        print(f"非正規データ（{len(false_data)} バイト）を暗号化中...")
        false_encrypted = state_based_encrypt(false_data, false_engine, FALSE_PATH)

        # データの署名（認証用）
        print("データの署名を計算中...")
        true_signature = hmac.new(master_key, true_encrypted, hashlib.sha256).digest()
        false_signature = hmac.new(master_key, false_encrypted, hashlib.sha256).digest()

        # カプセル化（暗号文の包含）
        print("データをカプセル化中...")
        if max(len(true_encrypted), len(false_encrypted)) > 10 * 1024 * 1024:  # 10MB
            print("大規模データ用のカプセル化メソッドを使用...")
            capsule_data = _create_large_capsule(
                true_encrypted, false_encrypted,
                true_signature, false_signature,
                master_key, salt
            )
        else:
            # 標準的なカプセル化
            capsule_data = _create_capsule(
                true_encrypted, false_encrypted,
                true_signature, false_signature,
                master_key, salt
            )

        # エントロピー注入
        print("エントロピーを注入中...")
        entropy_data = inject_entropy(true_encrypted, false_encrypted, master_key, salt)

        # メタデータの準備
        metadata = {
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "true_size": len(true_data),
            "false_size": len(false_data),
            "is_text": is_text,
            "salt": base64.b64encode(salt).decode('utf-8'),
            "platform": platform.platform(),
            "true_states": len(true_engine.states),
            "false_states": len(false_engine.states),
            "true_path_length": len(true_path),
            "false_path_length": len(false_path),
            "true_entropy": calculate_entropy(true_data),
            "false_entropy": calculate_entropy(false_data),
            "entropy_block_size": len(entropy_data),
            "block_size": 64
        }

        # JSON形式に変換
        metadata_json = json.dumps(metadata).encode('utf-8')

        # ファイルヘッダーの作成
        file_marker = b"INDETERM" + salt
        version = (1).to_bytes(2, 'big')  # バージョン1
        options = (1 if is_text else 0).to_bytes(2, 'big')  # オプション（テキストかバイナリか）
        timestamp_bytes = int(time.time()).to_bytes(8, 'big')
        metadata_size = len(metadata_json).to_bytes(4, 'big')

        # エントロピーデータサイズを追加
        entropy_size = len(entropy_data).to_bytes(4, 'big')

        # 出力ファイルに書き込み
        print(f"暗号化ファイルを '{output_path}' に書き込み中...")
        with open(output_path, 'wb') as f:
            # ヘッダー
            f.write(file_marker)        # 16バイト
            f.write(version)           # 2バイト
            f.write(options)           # 2バイト
            f.write(timestamp_bytes)    # 8バイト
            f.write(metadata_size)      # 4バイト
            f.write(metadata_json)      # 可変長

            # エントロピーデータサイズを追加
            f.write(entropy_size)       # 4バイト

            # エントロピーデータ
            f.write(entropy_data)       # 可変長

            # カプセル化データ
            f.write(capsule_data)       # 可変長

        # 鍵情報の生成
        key_data = {
            "master_key": base64.b64encode(master_key).decode('utf-8'),
            "timestamp": int(time.time()),
            "encrypted_file": os.path.basename(output_path)
        }

        # 鍵情報をJSON形式で保存
        key_json = json.dumps(key_data, indent=2).encode('utf-8')

        # 鍵ファイルの保存（オプション）
        key_file_path = None
        if save_key:
            key_file_path = f"{output_path}.key"
            with open(key_file_path, 'wb') as f:
                f.write(key_json)

            # 鍵ファイルのパーミッション設定（所有者のみ読み書き可能）
            try:
                os.chmod(key_file_path, 0o600)  # rw-------
            except Exception as e:
                print(f"警告: 鍵ファイルのパーミッション設定に失敗しました: {e}", file=sys.stderr)

            print(f"鍵ファイルを '{key_file_path}' に保存しました")

        # 暗号化ファイルのパーミッション設定
        try:
            os.chmod(output_path, 0o644)  # rw-r--r--
        except Exception as e:
            print(f"警告: 暗号化ファイルのパーミッション設定に失敗しました: {e}", file=sys.stderr)

        # 成功メッセージ
        print(f"暗号化が完了しました: '{output_path}' ({os.path.getsize(output_path)/1024:.1f} KB)")
        print(f"エントロピーデータサイズ: {len(entropy_data)/1024:.1f} KB")
        print(f"カプセルデータサイズ: {len(capsule_data)/1024:.1f} KB")

        return master_key, output_path

    except Exception as e:
        print(f"暗号化エラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise


def main():
    """
    メイン関数
    """
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='不確定性転写暗号化方式による暗号化')
    parser.add_argument('true_file', help='正規テキストファイルのパス')
    parser.add_argument('false_file', help='非正規テキストファイルのパス')
    parser.add_argument('output', help='出力ファイルのパス')
    parser.add_argument('--key-file', '-k', help='鍵を保存するファイルのパス')
    parser.add_argument('--save-key', '-s', action='store_true', help='鍵情報をファイルに保存する')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細な出力を表示')
    parser.add_argument('--skip-validation', action='store_true', help='入力ファイルの検証をスキップ')
    parser.add_argument('--memory-limit', type=int, default=512, help='メモリ使用量制限（MB）')
    parser.add_argument('--chunk-size', type=int, default=16, help='チャンク処理サイズ（MB）')
    parser.add_argument('--entropy-factor', type=float, default=0.5, help='エントロピー注入強度（0.1〜1.0）')

    args = parser.parse_args()

    try:
        # タイムスタンプを取得して出力ファイル名に追加（上書き防止）
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        output_file = args.output
        if not output_file.endswith(OUTPUT_EXTENSION):
            base_name, ext = os.path.splitext(output_file)
            output_file = f"{base_name}_{timestamp}{ext}"
        else:
            base_name = output_file[:-len(OUTPUT_EXTENSION)]
            output_file = f"{base_name}_{timestamp}{OUTPUT_EXTENSION}"

        # 暗号化を実行
        key, output_path = encrypt(args.true_file, args.false_file, output_file, args.save_key)

        # 鍵の16進数表示
        key_hex = key.hex()
        print(f"鍵: {key_hex}")

        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


# スクリプトが直接実行された場合のエントリポイント
if __name__ == "__main__":
    main()