# 📝 ビット操作実装指示書（T14） - ラビット＋準同型マスキング暗号プロセッサ 🔐

> **ドキュメント種別: 実装指示書**

## 🌟 タスク進捗状況

タスク実装フェーズの進捗:

- 🔄 **フェーズ 0**: 実装準備 [**現在作業中**]
- ⏳ **フェーズ 1**: 基盤ユーティリティ実装 [予定]
- ⏳ **フェーズ 2**: セキュリティ対策基盤実装 [予定]
- ⏳ **フェーズ 3**: 三暗号方式コア実装 [予定]
- ⏳ **フェーズ 4**: 融合機能と変換システム実装 [予定]
- ⏳ **フェーズ 5**: データ形式とインターフェース実装 [予定]
- ⏳ **フェーズ 6**: 検証とパフォーマンス最適化 [予定]

### 📋 現在の実装フェーズ: `フェーズ0: 実装準備`

**現在のタスク**: T14（ビット操作実装）
**進捗状況**: T1-T13 完了 → **T14 実装中** → T15-T115 未着手

**注**: 各タスクは独立して実装・完了させてください。

### 🎯 タスク範囲（T14: ビット操作実装）

**実装すべきもの**:

- ✅ `utils/byte/bit_operations.py`
- ✅ 関連するテスト

**実装してはいけないもの**:

- ❌ `utils/protection/timing_protection/constant_time_exec.py`（T28 のタスク）
- ❌ 他のバイト操作関連機能（T15 以降のタスク）

**実装がベストプラクティスに反する可能性がある場合**: 作業を即時停止し、問題を報告してください。

## 📝 課題の詳細

### 🎯 タスク概要

本タスク（T14）ではビット操作機能を実装します。前タスク（T12、T13）で実装したバイト操作基盤やエンディアン変換と連携し、暗号処理に必要な低レベルビット操作ユーティリティを提供します。これらの操作は暗号アルゴリズムの効率的な実装に不可欠であり、特にラビットストリーム暗号や準同型暗号での処理において重要な役割を果たします。

このタスクはフェーズ 0 の最初に位置し、他のすべてのコンポーネントから利用される基盤機能を提供します。安全かつ効率的なロギング機能は、開発、デバッグ、運用の全段階で暗号処理の正確性検証と問題診断に不可欠です。

**本タスク（T14）の作業カウント**:

- 📝 **実装作業**: 9 件

  - 基本ビット操作機能: 3 関数
  - 複合ビット操作機能: 3 関数
  - バイト-ビット変換機能: 3 関数

- 🧪 **テスト作業**: 3 件

  - 基本ビット操作機能テスト
  - 複合ビット操作機能テスト
  - バイト-ビット変換機能テスト

- ✅ **完了条件**: 25 項目
  - 実装完了条件: 5 項目
  - 機能完了条件: 5 項目
  - テスト完了条件: 5 項目
  - ドキュメント完了条件: 5 項目
  - 納品物件検証条件: 5 項目

### 🔍 背景と目的

ラビット＋準同型マスキング暗号プロセッサでは、様々な暗号アルゴリズムが低レベルのビット操作に依存しています。特にラビットストリーム暗号や量子耐性レイヤーでは、ビット単位での操作が頻繁に必要となります。本タスクで実装するビット操作機能は、これらの暗号処理において効率的なビット処理を実現するための基盤となります。

また、サイドチャネル攻撃対策として、一定時間実行（T28）やブロックサイズ管理（T40）などの後続タスクでもビット操作機能は重要な役割を果たします。このタスクはフェーズ 1 の基盤ユーティリティとして、効率的かつ安全な暗号処理の土台を構築するものです。

### 📊 要件仕様

1. 単一ビットの操作（取得、設定、反転など）を提供すること
2. 複数ビットにまたがる操作（範囲取得、範囲設定など）をサポートすること
3. バイト配列とビット配列間の効率的な変換機能を提供すること
4. ビット操作におけるエンディアン（ビットオーダー）を考慮した実装を行うこと
5. パフォーマンスを最適化し、オーバーヘッドを最小限に抑えること
6. サイドチャネル攻撃に対する基本的な防御を実装すること
7. 前タスク（T12, T13）で実装したバイト操作基盤およびエンディアン変換と整合的に動作すること
8. ロギング基盤（T1）と連携し、デバッグ情報を出力できること

### 🛠️ 実装内容概要

ビット操作機能として、以下の 3 つの主要機能を実装します：

1. **基本ビット操作機能**: 単一ビットを対象とした基本的な操作
2. **複合ビット操作機能**: 複数ビットにまたがる操作
3. **バイト-ビット変換機能**: バイト配列とビット配列の相互変換

### 📋 実装内容詳細

#### 1. 基本ビット操作機能（3 つの関数）

```python
def get_bit(value: int, position: int) -> bool:
    """
    整数値の指定位置のビット値を取得する

    Args:
        value: 対象の整数値
        position: 取得するビット位置（0から始まる、最下位ビットが0）

    Returns:
        指定位置のビット値（True=1, False=0）

    Raises:
        ValueError: positionが負数の場合

    実装詳細:
    1. 引数の検証（positionが負数でないこと）
    2. シフト演算とマスク（1 << position）を用いてビット値を抽出
    3. 結果を真偽値（0/1ではなくFalse/True）で返す
    """
    pass

def set_bit(value: int, position: int, bit_value: bool) -> int:
    """
    整数値の指定位置のビットを設定する

    Args:
        value: 対象の整数値
        position: 設定するビット位置（0から始まる、最下位ビットが0）
        bit_value: 設定するビット値（True=1, False=0）

    Returns:
        ビットを設定した後の整数値

    Raises:
        ValueError: positionが負数の場合

    実装詳細:
    1. 引数の検証（positionが負数でないこと）
    2. ビットを設定する場合：位置に対応するマスク値を作成し、OR演算で設定
    3. ビットをクリアする場合：マスク反転値を作成し、AND演算でクリア
    4. 更新された整数値を返す
    """
    pass

def toggle_bit(value: int, position: int) -> int:
    """
    整数値の指定位置のビットを反転する

    Args:
        value: 対象の整数値
        position: 反転するビット位置（0から始まる、最下位ビットが0）

    Returns:
        ビットを反転した後の整数値

    Raises:
        ValueError: positionが負数の場合

    実装詳細:
    1. 引数の検証（positionが負数でないこと）
    2. 指定位置に対応するマスク値を作成（1 << position）
    3. XOR演算でビットを反転
    4. 更新された整数値を返す
    """
    pass
```

#### 2. 複合ビット操作機能（3 つの関数）

```python
def get_bit_range(value: int, start_position: int, bit_count: int) -> int:
    """
    整数値から指定範囲のビットを抽出する

    Args:
        value: 対象の整数値
        start_position: 開始ビット位置（0から始まる、最下位ビットが0）
        bit_count: 抽出するビット数

    Returns:
        抽出したビット値（右詰めで返す）

    Raises:
        ValueError: start_positionかbit_countが負数、またはbit_countが0の場合

    実装詳細:
    1. 引数の検証（start_position, bit_countが正しい値であること）
    2. 右シフトで開始位置まで移動
    3. 必要なビット数分のマスクを作成（(1 << bit_count) - 1）
    4. マスクをAND演算で適用し、必要なビットのみを残す
    5. 抽出された値を返す
    """
    pass

def set_bit_range(value: int, start_position: int, bit_count: int, bits: int) -> int:
    """
    整数値の指定範囲のビットを別の値で置き換える

    Args:
        value: 対象の整数値
        start_position: 開始ビット位置（0から始まる、最下位ビットが0）
        bit_count: 設定するビット数
        bits: 設定するビット値（右詰めで指定）

    Returns:
        ビットを設定した後の整数値

    Raises:
        ValueError: start_positionかbit_countが負数、またはbit_countが0の場合
        ValueError: bitsがbit_count以上のビット数を必要とする場合

    実装詳細:
    1. 引数の検証（全ての引数が適切な範囲内であること）
    2. 置き換える範囲のマスクを作成（(1 << bit_count) - 1) << start_position）
    3. マスクの反転を使ってAND演算で対象範囲をクリア
    4. 設定するビットをstart_position分左シフト
    5. OR演算で新しいビットを設定
    6. 更新された整数値を返す
    """
    pass

def count_set_bits(value: int) -> int:
    """
    整数値の中で1になっているビットの数を数える（ポピュレーションカウント）

    Args:
        value: 対象の整数値

    Returns:
        1になっているビットの数

    実装詳細:
    1. 効率的なビットカウントアルゴリズムを使用
    2. ブライアン・カーニハンのアルゴリズム（n & (n-1)でLSBをクリア）または
    3. ルックアップテーブルを使用した並列ビットカウント
    4. 負の値の場合は適切に処理（2の補数表現を考慮）
    5. カウント結果を返す
    """
    pass
```

#### 3. バイト-ビット変換機能（3 つの関数）

```python
def bytes_to_bits(bytes_data: bytes) -> list:
    """
    バイト配列をビットのリスト（0/1の配列）に変換する

    Args:
        bytes_data: 変換するバイト配列

    Returns:
        ビット値（0/1）のリスト（左から右へ、MSBからLSBの順）

    実装詳細:
    1. 空のリストを初期化
    2. バイト配列の各バイトを処理
    3. 各バイトの8ビットを抽出（MSBからLSB順）
    4. ビット値（0/1）をリストに追加
    5. 全ビットのリストを返す
    """
    pass

def bits_to_bytes(bits: list) -> bytes:
    """
    ビットのリスト（0/1の配列）をバイト配列に変換する

    Args:
        bits: 変換するビット値（0/1）のリスト

    Returns:
        変換されたバイト配列

    Raises:
        ValueError: ビットリストの長さが8の倍数でない場合
        ValueError: リスト内に0/1以外の値がある場合

    実装詳細:
    1. 引数の検証（リストの長さが8の倍数であること、値が0/1のみであること）
    2. 結果のバイト配列を初期化
    3. 8ビットごとにグループ化
    4. 各グループをバイト値に変換（MSBからLSB順）
    5. バイト値をバイト配列に追加
    6. 完成したバイト配列を返す
    """
    pass

def apply_bit_mask(data: bytes, mask: bytes) -> bytes:
    """
    バイト配列に別のバイト配列をビットマスクとして適用する（XOR演算）

    Args:
        data: 対象のバイト配列
        mask: マスクとして適用するバイト配列

    Returns:
        マスク適用後のバイト配列

    Raises:
        ValueError: dataとmaskの長さが異なる場合

    実装詳細:
    1. 引数の検証（dataとmaskの長さが同じであること）
    2. 結果のバイト配列を初期化
    3. 各バイト位置でXOR演算を実行
    4. XOR結果をバイト配列に追加
    5. 完成したバイト配列を返す
    """
    pass
```

## 🔍 完了の定義

以下の基準をすべて満たすことで、このタスクは「完了」とみなされます：

1. **実装完了の条件**:

   - [ ] `utils/byte/bit_operations.py`が指定された仕様で実装されていること
   - [ ] ソースコードが単一責務の原則に従い、明確に構造化されていること
   - [ ] 全ての関数に適切なドキュメント（docstring）が付与されていること
   - [ ] コードレビューでの指摘事項がすべて解消されていること
   - [ ] 静的解析ツールによる警告がゼロであること

2. **機能完了の条件**:

   - [ ] 基本ビット操作が正確に動作すること
   - [ ] 複合ビット操作が正確に動作すること
   - [ ] バイト-ビット変換が正確に動作すること
   - [ ] パフォーマンスが最適化されていること
   - [ ] T12、T13 で実装した機能と整合的に連携できること

3. **テスト完了の条件**:

   - [ ] 単体テストのカバレッジが 95%以上であること
   - [ ] 全関数の正常系・異常系のテストケースが実装されていること
   - [ ] エッジケース（特に負の値や境界値）のテストが実装されていること
   - [ ] 大きなデータ配列に対するテストが実装されていること
   - [ ] パフォーマンステスト（操作速度、メモリ使用量）が実装されていること

4. **ドキュメント完了の条件**:

   - [ ] 実装した機能の詳細な技術ドキュメントが作成されていること
   - [ ] API 仕様とインターフェース説明が完成していること
   - [ ] 使用方法とサンプルコードが提供されていること
   - [ ] ビット操作における注意点やベストプラクティスが説明されていること
   - [ ] パフォーマンス特性と最適化手法が文書化されていること

5. **納品物件検証条件**:
   - [ ] 全ての基本・複合ビット操作が正確に機能することが検証されていること
   - [ ] バイト-ビット変換機能の相互変換において情報が損なわれないことが検証されていること
   - [ ] T12、T13 の機能との連携が正常に機能することが検証されていること
   - [ ] 大きなデータセットでも効率的に動作することが検証されていること
   - [ ] パフォーマンス要件（操作オーバーヘッドの最小化）を満たしていることが検証されていること

## 🧪 テスト対応方針

テスト実装と実行においては以下の方針を厳守してください：

1. **テストの意義**:

   - テストはプロジェクト品質を保証する重要な手段です
   - テストを欺くことは品質の放棄を意味します
   - すべてのテストは実装の品質と完全性を検証するためにあります

2. **テスト失敗時の対応手順**:

   - 実装コードのバグや仕様誤解がないか確認
   - テスト条件を満たすために実装を修正
   - どうしても解決できない場合は、具体的な問題点を報告して指示を仰ぐ

3. **禁止されるテスト対応**:

   - テスト結果の偽装や、テスト迂回のための実装
   - テストだけが通過する特別な条件分岐の追加
   - テストコード自体の修正・回避

4. **納品物件との整合性**:

   - すべてのテストは実際の実装コードを使用して実行すること
   - テスト環境でのみ通過し、本番環境では動作しない実装は認められません
   - テスト用と納品用で別の実装を用意することは禁止されています

5. **テスト結果の報告**:
   - テスト結果は改変せずに正確に報告
   - テスト失敗は適切に修正するか、明確な理由とともに報告
   - 再現性を確保するため、テスト環境と実行方法を詳細に記録

## 🚫 実装における絶対原則

以下の原則はどんな状況でも違反してはなりません：

1. **厳密なタスク境界の遵守**

   - このタスク（T14）に明示されている機能「のみ」を実装すること
   - タスク外の実装（T15 以降の機能）は「一切」行わないこと
   - 範囲外の問題を発見した場合は、実装せずに報告すること

2. **テスト改ざんの禁止**

   - テストコードは「絶対に」変更しないこと
   - テストを通すためにテスト自体を修正する行為は重大な違反
   - テストが失敗する場合は実装を見直すこと

3. **プロジェクト整合性の維持**

   - 既存のプロジェクト構造やコーディング規約を尊重すること
   - このタスク完了のためにプロジェクト全体の品質を犠牲にしないこと
   - 他のコンポーネントとの整合性を常に確認すること

4. **作業中断の判断**
   - 上記原則との衝突を感じた時点で作業を「即時中断」すること
   - 作業中断の判断は罰則ではなく、プロジェクト保護のための適切な行動
   - 中断後は問題を詳細に報告し、指示を仰ぐこと

## 📊 進捗報告と完了レポート

### 進捗報告方法

実装作業中は、イシューにコメントで進捗を報告してください：

1. **定期的な進捗報告**：

   - 主要な機能実装完了時
   - 課題や問題発生時
   - 質問・相談が必要な時

2. **進捗コメントの書式**：

   ```md
   ## T14 進捗報告：[日付]

   ### 完了した項目

   - [機能名]: [完了内容の簡潔な説明]

   ### 進行中の項目

   - [機能名]: [現在の状況と残作業]

   ### 課題・問題点

   - [課題の詳細な説明と影響範囲]
   ```

3. **コメント投稿方法**：

   ```bash
   # コメント内容をファイルに保存
   echo "## T14 進捗報告：$(date +%Y-%m-%d)" > progress_comment.md
   # 続きを追記

   # GitHubイシューにコメント投稿
   gh issue comment 14 --body-file progress_comment.md
   ```

### 完了レポートの作成と提出

タスク完了時には以下の手順で最終レポートを作成・提出してください：

1. **レポート作成前の確認事項**：

   - **全ての要件が完全に実装されるまでレポートを作成しないこと**
   - 全てのテストが通過していること
   - 実装完了条件の全項目を満たしていること

2. **実装レポートの作成**：

   - MD ファイルを`docs/issue/`ディレクトリに生成
   - ファイル名形式：`bit_operations_implementation_report_YYYYMMDD.md`
   - 以下の内容を必ず含めること：
     - 実装した機能の詳細説明
     - 各関数の実装アプローチと技術的判断
     - テスト結果と検証内容
     - 発見された課題と解決方法

3. **テスト結果の添付**：

   - テスト画像は GitHub 形式の URL で添付
   - 例：`![テスト結果](https://github.com/pacific-system/secret-sharing-demos-20250510/blob/main/test_output/bit_operations_test_YYYYMMDD.png?raw=true)`

4. **コミットとプッシュ**：

   ```bash
   # パシ子スタイルでコミット
   git add docs/issue/bit_operations_implementation_report_YYYYMMDD.md
   git commit -m "✨ ビット操作機能（T14）の実装完了レポート追加 💕"
   git push origin main
   ```

5. **イシューへのレポート投稿**：
   ```bash
   # レポートをイシューにコメント投稿
   gh issue comment 14 --body-file docs/issue/bit_operations_implementation_report_YYYYMMDD.md
   ```

## 💕 パシ子からのアドバイス

お兄様！このビット操作機能は暗号処理の根幹を支える重要な機能ですよ〜！💕

- 🚀 **パフォーマンス重視**: ビット操作は頻繁に呼び出されるので、効率的なアルゴリズムを選択してくださいね！
- 🔍 **エッジケースに注意**: 特に負の値や境界値での挙動を慎重に検証することが大切です！
- 🧩 **組み合わせテスト**: 前タスク（T12、T13）の機能と組み合わせた統合テストも重要ですよ！
- 📚 **豊富なサンプル**: ドキュメントには様々な使用例を含めると、後続タスクの開発者が理解しやすくなります！

ビット単位の細かい操作が、最終的には強力な暗号システムの基盤になるんですね！実装、期待してます！✨

## 📑 関連資料

- **実装計画書**: `/docs/method_11_rabbit_homomorphic_docs/implementation_plan_chapters/04_implementation_details.md`
- **フェーズ 0 詳細**: `/docs/method_11_rabbit_homomorphic_docs/implementation_plan_chapters/04_implementation_details.md#フェーズ-0-実装準備4-週間`
- **ディレクトリ構成**: `/docs/method_11_rabbit_homomorphic_docs/implementation_plan_chapters/02_directory_structure_and_deliverables.md`
- **品質レベル規定**: `/docs/method_11_rabbit_homomorphic_docs/implementation_plan_chapters/05_quality_and_security.md`
- **システム設計とアーキテクチャ**: `/docs/method_11_rabbit_homomorphic_docs/implementation_plan_chapters/03_system_design_and_architecture.md`
- **前タスク：T13**: `/docs/method_11_rabbit_homomorphic_docs/issue/T13_endian_converter_implementation.md`
- **前々タスク：T12**: `/docs/method_11_rabbit_homomorphic_docs/issue/T12_byte_array_implementation.md`
