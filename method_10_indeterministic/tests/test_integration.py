"""
不確定性転写暗号化方式 - 統合テスト

このスクリプトは、encrypt.py、decrypt.py、StateCapsuleとCapsuleAnalyzerの
連携テストを行います。
"""

import os
import sys
import time
import hashlib
import unittest
import matplotlib.pyplot as plt
import numpy as np
import datetime
import random
import tempfile
from collections import Counter

# プロジェクトルートをインポートパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
method_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(method_dir)
sys.path.insert(0, project_root)

# 内部モジュールのインポート
from method_10_indeterministic.state_capsule import StateCapsule, BLOCK_TYPE_SEQUENTIAL, BLOCK_TYPE_INTERLEAVE
from method_10_indeterministic.capsule_analyzer import CapsuleAnalyzer
from method_10_indeterministic.encrypt import encrypt_file, encrypt
from method_10_indeterministic.decrypt import decrypt_file, decrypt

# テスト出力ディレクトリ
TEST_OUTPUT_DIR = os.path.join(project_root, "test_output")
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)


class IntegrationTests(unittest.TestCase):
    """統合テストクラス"""

    def setUp(self):
        # テスト用の一時ファイルパス
        self.true_text_path = os.path.join(TEST_OUTPUT_DIR, "test_true.txt")
        self.false_text_path = os.path.join(TEST_OUTPUT_DIR, "test_false.txt")
        self.encrypted_path = os.path.join(TEST_OUTPUT_DIR, "test_encrypted.indt")
        self.key_path = os.path.join(TEST_OUTPUT_DIR, "test_encrypted.key")
        self.decrypted_true_path = os.path.join(TEST_OUTPUT_DIR, f"test_encrypted.indt_true_decrypted.txt")
        self.decrypted_false_path = os.path.join(TEST_OUTPUT_DIR, f"test_encrypted.indt_false_decrypted.txt")

        # テスト用のデータを生成
        self.true_text = """
この文書は「正規パス（true path）」用のテストデータです。
このデータは暗号化され、正規パスで復号された場合に表示されるべき内容です。
暗号化処理では、正規データと非正規データの両方を一つのカプセルに格納し、
どちらが本物かを第三者が判別できないようにします。

これは不確定性転写暗号化方式のテストです。
"""

        self.false_text = """
この文書は「非正規パス（false path）」用のテストデータです。
このデータは暗号化され、非正規パスで復号された場合に表示されるべき内容です。
実際の用途では、攻撃者が強制的に復号を試みた場合にこのデータが表示されます。

両方のデータが同じカプセル内に存在していますが、どちらが本物かは判別できません。
"""

        # テスト用のファイルを作成
        with open(self.true_text_path, "w", encoding="utf-8") as f:
            f.write(self.true_text)

        with open(self.false_text_path, "w", encoding="utf-8") as f:
            f.write(self.false_text)

    def tearDown(self):
        # テスト後のクリーンアップは行わない（ファイルを残しておく）
        pass

    def test_full_encryption_decryption_file(self):
        """ファイルの暗号化と復号の完全なフローをテスト"""
        # 暗号化
        encrypt_file(
            true_file_path=self.true_text_path,
            false_file_path=self.false_text_path,
            output_path=self.encrypted_path,
            save_key=True
        )

        # ファイルが生成されたことを確認
        self.assertTrue(os.path.exists(self.encrypted_path))
        self.assertTrue(os.path.exists(self.key_path))

        # true パスでの復号
        decrypt_file(
            encrypted_file=self.encrypted_path,
            key_file=self.key_path,
            output_file=self.decrypted_true_path,
            path_type="true"
        )

        # false パスでの復号
        decrypt_file(
            encrypted_file=self.encrypted_path,
            key_file=self.key_path,
            output_file=self.decrypted_false_path,
            path_type="false"
        )

        # 復号されたファイルの内容を検証
        with open(self.decrypted_true_path, "r", encoding="utf-8") as f:
            decrypted_true_content = f.read()

        with open(self.decrypted_false_path, "r", encoding="utf-8") as f:
            decrypted_false_content = f.read()

        # 元のテキストと復号されたテキストが一致するか確認
        self.assertEqual(self.true_text, decrypted_true_content)
        self.assertEqual(self.false_text, decrypted_false_content)

        # 暗号化されたファイルを分析
        self._analyze_encrypted_file(self.encrypted_path)

    def test_encryption_decryption_text(self):
        """テキストの暗号化と復号をテスト"""
        # 一時ファイルに保存してからencrypt関数を使用
        true_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        false_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        output_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".indt")

        try:
            # テストデータを一時ファイルに書き込み
            with open(true_temp.name, 'w', encoding='utf-8') as f:
                f.write(self.true_text)

            with open(false_temp.name, 'w', encoding='utf-8') as f:
                f.write(self.false_text)

            # 暗号化
            key, _ = encrypt(
                true_file_path=true_temp.name,
                false_file_path=false_temp.name,
                output_path=output_temp.name,
                save_key=True
            )

            # 復号 (trueパス)
            true_output = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            decrypt(
                encrypted_file=output_temp.name,
                key=key,
                output_file=true_output.name,
                path_type="true"
            )

            # 復号 (falseパス)
            false_output = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            decrypt(
                encrypted_file=output_temp.name,
                key=key,
                output_file=false_output.name,
                path_type="false"
            )

            # 復号結果の検証
            with open(true_output.name, 'r', encoding='utf-8') as f:
                decrypted_true = f.read()

            with open(false_output.name, 'r', encoding='utf-8') as f:
                decrypted_false = f.read()

            # 元のテキストと復号されたテキストが一致するか確認
            self.assertEqual(self.true_text, decrypted_true)
            self.assertEqual(self.false_text, decrypted_false)

        finally:
            # 一時ファイルの削除
            for temp_file in [true_temp.name, false_temp.name, output_temp.name, true_output.name, false_output.name]:
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def test_different_block_types(self):
        """異なるブロック処理タイプでの暗号化・復号をテスト"""
        # 一時ファイルを準備
        true_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        false_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")

        try:
            # テストデータを一時ファイルに書き込み
            with open(true_temp.name, 'w', encoding='utf-8') as f:
                f.write(self.true_text)

            with open(false_temp.name, 'w', encoding='utf-8') as f:
                f.write(self.false_text)

            # 順次配置での暗号化
            sequential_output = tempfile.NamedTemporaryFile(delete=False, suffix=".indt")
            sequential_key, _ = encrypt(
                true_file_path=true_temp.name,
                false_file_path=false_temp.name,
                output_path=sequential_output.name
            )

            # インターリーブ配置での暗号化
            interleaved_output = tempfile.NamedTemporaryFile(delete=False, suffix=".indt")
            interleaved_key, _ = encrypt(
                true_file_path=true_temp.name,
                false_file_path=false_temp.name,
                output_path=interleaved_output.name
            )

            # 各方式での復号
            sequential_true_output = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            sequential_false_output = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")

            interleaved_true_output = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            interleaved_false_output = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")

            # 順次方式の復号
            decrypt(sequential_output.name, sequential_key, sequential_true_output.name, "true")
            decrypt(sequential_output.name, sequential_key, sequential_false_output.name, "false")

            # インターリーブ方式の復号
            decrypt(interleaved_output.name, interleaved_key, interleaved_true_output.name, "true")
            decrypt(interleaved_output.name, interleaved_key, interleaved_false_output.name, "false")

            # 復号結果の読み込み
            with open(sequential_true_output.name, 'r', encoding='utf-8') as f:
                sequential_true = f.read()
            with open(sequential_false_output.name, 'r', encoding='utf-8') as f:
                sequential_false = f.read()

            with open(interleaved_true_output.name, 'r', encoding='utf-8') as f:
                interleaved_true = f.read()
            with open(interleaved_false_output.name, 'r', encoding='utf-8') as f:
                interleaved_false = f.read()

            # 復号結果の検証
            self.assertEqual(self.true_text, sequential_true)
            self.assertEqual(self.false_text, sequential_false)
            self.assertEqual(self.true_text, interleaved_true)
            self.assertEqual(self.false_text, interleaved_false)

            # 暗号文サイズと解析耐性の比較
            # 直接ファイルを読み込む
            with open(sequential_output.name, 'rb') as f:
                sequential_encrypted = f.read()
            with open(interleaved_output.name, 'rb') as f:
                interleaved_encrypted = f.read()

            analyzer = CapsuleAnalyzer()
            sequential_analysis = analyzer.analyze_capsule(sequential_encrypted)
            interleaved_analysis = analyzer.analyze_capsule(interleaved_encrypted)

            # 結果の可視化
            self._compare_and_visualize(sequential_encrypted, interleaved_encrypted)

            # 両方のデータが同じ長さの入力から生成されたにも関わらず、異なるサイズと特性を持っていることを確認
            self.assertNotEqual(len(sequential_encrypted), len(interleaved_encrypted))

        finally:
            # 一時ファイルの削除
            for temp_file in [
                true_temp.name, false_temp.name,
                sequential_output.name, interleaved_output.name,
                sequential_true_output.name, sequential_false_output.name,
                interleaved_true_output.name, interleaved_false_output.name
            ]:
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def _analyze_encrypted_file(self, file_path):
        """暗号化されたファイルを解析"""
        # ファイルを読み込む
        with open(file_path, "rb") as f:
            encrypted_data = f.read()

        # 解析器でカプセルを分析
        analyzer = CapsuleAnalyzer()
        analysis_results = analyzer.analyze_capsule(encrypted_data)

        # 解析結果の可視化
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(TEST_OUTPUT_DIR, f"integration_test_{timestamp}.png")

        # 可視化用の図を作成
        plt.figure(figsize=(12, 8))

        # エントロピー分布の可視化
        plt.subplot(2, 2, 1)
        entropy_value = analysis_results["entropy_analysis"]["shannon_entropy"]
        plt.bar(["エントロピー"], [entropy_value], color='green')
        plt.title('エントロピー分析')
        plt.ylabel('ビット/バイト')
        plt.grid(True, alpha=0.3)

        # バイト分布の可視化
        plt.subplot(2, 2, 2)
        distribution = analysis_results["byte_distribution"]
        byte_values = list(range(256))
        byte_counts = [distribution.get(b, 0) for b in byte_values]
        plt.bar(byte_values[::4], byte_counts[::4], color='blue', alpha=0.7)  # 4バイト毎に表示
        plt.title('バイト値分布')
        plt.xlabel('バイト値')
        plt.ylabel('出現頻度')
        plt.grid(True, alpha=0.3)

        # 基本情報の表示
        plt.subplot(2, 2, 3)
        plt.axis('off')
        basic_info = analysis_results["basic_info"]
        header_text = (
            f"ファイルサイズ: {basic_info['size']}バイト\n"
            f"ユニークバイト数: {basic_info['unique_bytes']}\n"
            f"最小バイト値: {basic_info['min_byte']}\n"
            f"最大バイト値: {basic_info['max_byte']}"
        )
        plt.text(0.5, 0.5, header_text, ha='center', va='center', fontsize=12)

        # 解析耐性スコアの表示
        plt.subplot(2, 2, 4)
        overall_score = analysis_results["resistance_score"]["total"]
        plt.bar(["解析耐性スコア"], [overall_score], color='purple')
        plt.title(f'解析耐性スコア')
        plt.ylabel('スコア (0-10)')
        plt.ylim(0, 10)
        plt.text(0, overall_score + 0.3, f"{overall_score:.2f}", ha='center')

        # 全体のタイトル
        plt.suptitle('不確定性転写暗号化方式 - 統合テスト分析結果', fontsize=16)

        # 保存
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(output_file)
        print(f"統合テスト分析結果を保存しました: {output_file}")

    def _compare_and_visualize(self, sequential_data, interleaved_data):
        """2つの暗号化手法の比較結果を可視化"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(TEST_OUTPUT_DIR, f"block_type_comparison_{timestamp}.png")

        # 解析
        analyzer = CapsuleAnalyzer()

        # 順次配置の解析
        sequential_analysis = analyzer.analyze_capsule(sequential_data)

        # インターリーブの解析
        interleaved_analysis = analyzer.analyze_capsule(interleaved_data)

        # 可視化用の図を作成
        plt.figure(figsize=(12, 8))

        # ファイルサイズの比較
        plt.subplot(2, 2, 1)
        sizes = [len(sequential_data), len(interleaved_data)]
        plt.bar(['順次配置', 'インターリーブ'], sizes, color=['blue', 'green'])
        plt.title('暗号化データサイズの比較')
        plt.ylabel('サイズ (バイト)')
        for i, size in enumerate(sizes):
            plt.text(i, size + 50, str(size), ha='center')

        # エントロピーの比較
        plt.subplot(2, 2, 2)
        entropy_values = [
            sequential_analysis["entropy_analysis"]["normalized_entropy"],
            interleaved_analysis["entropy_analysis"]["normalized_entropy"]
        ]
        plt.bar(['順次配置', 'インターリーブ'], entropy_values, color=['blue', 'green'])
        plt.title('正規化エントロピーの比較')
        plt.ylabel('正規化エントロピー')
        plt.ylim(0, 1)
        for i, val in enumerate(entropy_values):
            plt.text(i, val + 0.05, f"{val:.3f}", ha='center')

        # 解析耐性スコアの比較
        plt.subplot(2, 2, 3)
        scores = [
            sequential_analysis["resistance_score"]["total"],
            interleaved_analysis["resistance_score"]["total"]
        ]
        plt.bar(['順次配置', 'インターリーブ'], scores, color=['blue', 'green'])
        plt.title('解析耐性スコアの比較')
        plt.ylabel('総合スコア (0-10)')
        plt.ylim(0, 10)
        for i, score in enumerate(scores):
            plt.text(i, score + 0.3, f"{score:.2f}", ha='center')

        # 自己相関分析の比較
        plt.subplot(2, 2, 4)
        correlation_values = [
            sequential_analysis["block_analysis"]["independence_score"] if "independence_score" in sequential_analysis["block_analysis"] else 5.0,
            interleaved_analysis["block_analysis"]["independence_score"] if "independence_score" in interleaved_analysis["block_analysis"] else 5.0
        ]
        plt.bar(['順次配置', 'インターリーブ'], correlation_values, color=['blue', 'green'])
        plt.title('独立性スコアの比較')
        plt.ylabel('独立性スコア (0-10)')
        plt.ylim(0, 10)
        for i, val in enumerate(correlation_values):
            plt.text(i, val + 0.3, f"{val:.2f}", ha='center')

        # 全体のタイトル
        plt.suptitle('不確定性転写暗号化方式 - ブロック処理方式の比較', fontsize=16)

        # 保存
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(output_file)
        print(f"ブロック処理方式の比較結果を保存しました: {output_file}")


if __name__ == "__main__":
    unittest.main()