# シャミア秘密分散法による複数平文復号システム - 実装プロンプト

## 実装者のペルソナ

あなたは暗号学とセキュアコーディングに精通した優秀なPython開発者です。
シャミア秘密分散法に関する深い知識を持ち、セキュリティシステムの実装経験が豊富です。
「統計的区別不可能性」「定数時間処理」「サイドチャネル攻撃への対策」などの概念を熟知しています。
また、Pythonにおけるベストプラクティスを遵守し、効率的で保守性の高いコードを作成します。

以下の設計に基づいて、シャミア秘密分散法による複数平文復号システムをPythonで実装してください。
システムの核心は「複数の平文を単一の暗号ファイルに格納し、別々のパスワードでそれぞれ復号可能にする」ことです。

---

# シャミア秘密分散法による複数平文復号システム - 実装プロンプト

## システム概要と目的

あなたは暗号学とセキュアコーディングに精通した開発者です。シャミア秘密分散法を応用した「複数平文復号システム」を実装してください。このシステムは単一の暗号化ファイルから異なるパスワードを使用して異なる平文（JSON 文書）を復号可能にするものです。

**核心技術**: 「シェア ID による可能性の限定とパスワードによるマップ生成」という多段 MAP 方式

**重要な原則**: このシステムはケルクホフの原理に厳格に従います。アルゴリズムが完全に公開されてもパスワード（鍵）が秘匿されている限りセキュリティが保たれるよう設計してください。

## システムアーキテクチャ

### 基本原理

1. **シャミア秘密分散法**: 閾値暗号の一種。秘密情報を複数のシェアに分散し、一定数以上のシェアで元の情報を復元
2. **多段 MAP 方式**: シェア ID による第 1 段階の絞り込みとパスワードによる第 2 段階のマッピング
3. **統計的区別不可能性**: 異なる文書のシェアや未割当領域のシェアが統計的に区別できない
4. **直線的処理**: 復号処理中に評価や条件分岐を一切含まない

### 多段 MAP 方式の詳細

1. **第 1 段階（シェア ID による限定）**:

   - ユーザーが保持するシェア ID セットにより、全シェア空間から復号候補となるシェアの範囲を限定
   - この段階で不要なシェアの大部分を除外

2. **第 2 段階（パスワードによるマッピング）**:
   - パスワードから鍵導出関数を用いてマップデータを生成
   - 第 1 段階で限定された範囲内のシェアだけを対象にマッピングを適用
   - マッピング結果に基づき、実際に復号に使用するシェアを特定

## 実装上の絶対条件

### 1. セキュリティモデルの厳守

- **条件分岐の禁止**: 復号処理中に条件分岐を含めないこと（タイミング攻撃対策）
- **定数時間処理**: 全ての操作が入力値に関係なく一定時間で処理されること
- **統計的区別不可能性**: シェアの種類（A/B/未割当）が統計的に区別できないこと

### 2. シェア ID 空間設計

- **分割比率**: A 用 30-40%、B 用 30-40%、未割当 20-40%
- **分散配置**: 連続範囲や単純パターンを避け、バラバラに配置
- **実装方法**: 擬似乱数生成器で初期化、割り当て判別には 4 要素（パスワード A、B、シェア ID セット A、B）が全て必要

### 3. データ構造設計原則

- **最小情報の原則**: 復号に必須の情報のみを保存
- **識別情報の排除**: 文書種別の識別子（A/B 等）を含めない
- **構造的匿名性**: データ構造自体から情報が漏洩しないよう設計
- **冗長性の最小化**: 同じ情報を複数箇所に保存しない

### 4. 禁止事項

- ベストプラクティスに反する実装
- バックドアの設置や復号偽装
- 大原則（統計的区別不可能性、直線的処理等）を回避する設計

## 全体構成と依存関係

実装は次の 3 つの主要コンポーネントに分割されます:

1. **暗号化モジュール**: 複数の JSON 文書を単一の暗号化ファイルにエンコード
2. **復号化モジュール**: シェア ID とパスワードを用いて暗号化ファイルから特定の JSON 文書を復元
3. **更新モジュール**: 既存の暗号化ファイルの特定文書部分のみを安全に更新

これらのモジュールは CLI インターフェースから呼び出されます。
それぞれのモジュールの詳細実装は各ファイルを参照してください。

## 実装言語とライブラリ

- 実装言語: **Python**
- 推奨暗号ライブラリ:
  - KDF: `hashlib.pbkdf2_hmac` または `argon2-cffi`
  - 乱数生成: `secrets`モジュール
  - 有限体演算: `gmpy2`（必要な場合）
# 初期化モジュール実装ガイド

## 初期化モジュールの目的

このモジュールはシステムの初期設定を行い、シェア ID 空間を構築します。シェア ID を A 文書用、B 文書用、未割当に分割し、それぞれをセキュアに管理するための基盤を提供します。

## 主要な機能と要件

### 1. シェア ID 空間の設計と分割

- **分割比率**: A 用 30-40%、B 用 30-40%、未割当 20-40%
- **分散配置**: 連続範囲や偶数/奇数などの単純パターンを避け、ランダムに分散
- **安全性**: どの部分を切り取っても、A、B、未割当の識別が統計的に不可能

### 2. 出力データの独立性と安全性

- **セキュリティ分離**: A 文書と B 文書の両方を俯瞰できるマスターデータは出力しない
- **独立出力**: A 用シェア ID と B 用シェア ID は別々のファイルとして出力
- **高度暗号化**: シェアデータは高度に暗号化されたバイナリファイル形式で保存
- **パスワード保護**: 各シェアファイルはそれぞれ独立したパスワードで保護
- **情報分離**: 暗号化ファイル内に A 文書と B 文書の紐付け情報は一切残さない

### 3. シェア生成とランダム性の確保

- **暗号学的乱数**: 安全な乱数生成器を使用してシェア ID 空間を構築
- **反復検証**: 生成された分布の統計的特性を検証し、偏りがないことを確認
- **不可逆性**: 生成プロセスは一方向であり、シェアから元の割り当てを推測不可能

## 主要関数の実装ガイド

### 1. シェア ID 空間の生成

```python
def generate_share_id_space(total_shares, ratio_a, ratio_b, ratio_unassigned):
    """
    シェアID空間を生成して分割

    Args:
        total_shares (int): 生成するシェアID総数
        ratio_a (int): A用シェアの比率
        ratio_b (int): B用シェアの比率
        ratio_unassigned (int): 未割当シェアの比率

    Returns:
        tuple: (a_ids, b_ids, unassigned_ids) - 各カテゴリのシェアIDリスト
    """
    # 1. 全IDの生成（1からtotal_sharesまでの整数）
    # 2. シャッフルして順序をランダム化
    # 3. 比率に基づいて分割
    # 4. 各セットを返却
```

### 2. シェアファイルの暗号化出力

```python
def encrypt_share_file(share_ids, password, output_path):
    """
    シェアIDリストを暗号化してファイルに保存

    Args:
        share_ids (list): 暗号化するシェアIDのリスト
        password (str): 暗号化に使用するパスワード
        output_path (str): 出力ファイルパス

    Returns:
        bool: 成功した場合はTrue
    """
    # 1. シェアIDリストをバイナリ形式にシリアライズ
    # 2. パスワードから強力な鍵を導出
    # 3. 乱数IV(初期化ベクトル)を生成
    # 4. AES-GCMなど認証付き暗号化を適用
    # 5. メタデータ（バージョン、アルゴリズム情報）を追加
    # 6. バイナリファイルとして保存
```

### 3. シェアファイルの検証

```python
def verify_share_file(file_path, password):
    """
    暗号化されたシェアファイルを検証

    Args:
        file_path (str): 検証するファイルのパス
        password (str): 復号用パスワード

    Returns:
        bool: ファイルが有効な場合はTrue
    """
    # 1. ファイルからメタデータを読み取り
    # 2. パスワードから鍵を再導出
    # 3. 認証を検証
    # 4. 内容を復号
    # 5. フォーマット確認
```

## 実装上の制約とガイドライン

### 1. セキュリティ要件

- **識別不能性**: A 用、B 用、未割当のシェア ID が統計的に区別できないこと
- **マスターデータの排除**: A、B 両方のシェア ID 情報を含むマスターファイルを出力しない
- **暗号強度**: 最低でも AES-256 レベルの暗号強度を確保
- **キーストレッチング**: パスワードからの鍵導出には強力な KDF（Argon2 など）を使用

### 2. ファイル出力形式

- **独立ファイル**: A 用、B 用のシェアは別々のファイルに保存
- **バイナリ形式**: JSON ではなく、バイナリ形式で保存
- **認証タグ**: データの完全性と認証を確保するためのタグを含める
- **ファイル構造**: ヘッダ（メタデータ）、IV、暗号文、認証タグの構成

### 3. バックアップと冗長性

- **バックアップ推奨**: 初期化後のシェアファイルは安全にバックアップすることを強く推奨
- **エクスポート機能**: 必要に応じてプレーンテキスト形式でエクスポート可能（開発者オプション）
- **リカバリーメカニズム**: シェアファイル損失時のリカバリー手段を提供しない（セキュリティ上の理由）

## 出力ファイル形式の詳細

初期化モジュールが出力するシェアファイルは、以下の構造を持つバイナリファイルです：

```
[ファイルマジック (8バイト)] - 固定識別子
[バージョン (2バイト)] - ファイル形式バージョン
[アルゴリズム識別子 (2バイト)] - 使用暗号化アルゴリズム
[KDFパラメータ (可変長)] - 鍵導出関数のパラメータ
[IV (16バイト)] - 初期化ベクトル
[暗号化データ (可変長)] - 暗号化されたシェアIDリスト
[認証タグ (16バイト)] - GCMモード認証タグ
```

**重要**: このバイナリファイル形式は JSON 形式よりも解析が困難で、内容が暗号化されているため、不正アクセスから保護されます。
# 暗号化モジュール実装ガイド

## 暗号化モジュールの目的

このモジュールは一度に一つの JSON 文書（A 文書または B 文書）を暗号化ファイルに変換します。核心となる多段 MAP 方式とシャミア秘密分散法を用いて、異なるパスワードで異なる文書を復号できるようにします。

**重要**: 両方の文書を一度に暗号化する処理は一切実装禁止です。必ず一文書ずつ個別に暗号化してください。

## 主要な機能と要件

### 1. 多段エンコードプロセス

JSON 文書は以下の多段エンコードプロセスを適用します：

1. UTF-8 テキスト（元の JSON）
2. Latin-1 へのエンコード変換
3. Base64 エンコード
4. 常に圧縮（条件判断なし）

### 2. シャミア秘密分散法の実装

- 多項式の次数と閾値：実用的な値として閾値`t=3`～`5`
- 有限体の選択：大きな素数`p`を用いた有限体 GF(p)上での計算
- 推奨： 文書サイズに応じて十分大きい素数を選択（例：2^256-189）

### 3. シェア ID 空間の設計と管理

- A 用と B 用のシェア ID は予め分割し、暗号化時にはそれらを使用するだけ
- 未割当領域には統計的に区別不能なランダムデータを生成
- シェア ID の分布は特定のパターンを形成しないよう設計（交互配置など）

### 4. 暗号化プロセスの全体フロー

```
データの前処理（多段エンコード）
↓
データをチャンクに分割
↓
各チャンクをシャミア秘密分散でシェア化
↓
未割当領域にゴミデータを生成
↓
シェアをシャッフル
↓
メタデータを追加して高度に暗号化されたファイル生成
```

## 実装時の制約とガイドライン

### 絶対条件

1. **識別情報の排除**:

   - どのシェアがどの文書（A または B）に属するかを示す情報を格納しない
   - すべてのメタデータは A/B 区別なく同一形式

2. **シェア値の統計的区別不可能性**:

   - A 文書のシェア、B 文書のシェア、未割当領域のゴミデータが統計的に区別できないこと
   - これは情報理論的安全性のために必須

3. **保存データの最小化と高度暗号化**:

   - シャミア秘密分散法で生成されたシェア値
   - 塩値（再計算不可能な乱数）
   - 復号に必要な最小限のメタデータ（閾値など）
   - シェア ID はユーザー入力として提供されるため保存不要
   - マッピング情報はパスワードとシェア ID から計算で再生成可能なため保存不要
   - 全データはバイナリ形式で高度に暗号化して保存

4. **UUID の使用**:
   - 暗号化ファイル、復号化ファイル、シェアなどには UUID を付与する
   - ファイル名に UUID を含めて重複による上書きを防止（例: `encrypted_{timestamp}_{uuid}.henc`）
   - 一時ファイルやバックアップファイルにも一意の識別子を使用

### 主要関数の実装ガイド

#### 1. シャミア秘密分散法の実装

```python
def generate_polynomial(secret, degree, p):
    """degree次の多項式を生成"""
    # 係数配列を生成（最初の要素は秘密値）
    # 乱数を用いて残りの係数を生成

def evaluate_polynomial(coef, x, p):
    """多項式の評価"""
    # 係数配列と評価点xから多項式の値を計算

def generate_shares(secret, t, n, p):
    """n個のシェアを生成、閾値はt"""
    # 多項式を生成し、各シェアIDに対する値を計算
```

#### 2. 暗号化関数

```python
def encrypt(json_doc, password, share_ids, unassigned_ids, threshold=3):
    """
    単一のJSON文書を暗号化

    Args:
        json_doc: 暗号化するJSON文書（A文書またはB文書の一方のみ）
        password: 文書に対応するパスワード
        share_ids: 文書に対応するシェアIDセット
        unassigned_ids: 未割当のシェアIDリスト
        threshold: シェア復元に必要な閾値

    Returns:
        bytes: 高度に暗号化されたバイナリデータ（UUIDを含む識別子付き）
    """
    # 1. 単一JSON文書のエンコード処理
    # 2. チャンクに分割
    # 3. 各チャンクをシェア化（識別不能に）
    # 4. 未割当領域にゴミデータ生成
    # 5. シェアをシャッフル
    # 6. UUIDを生成しメタデータに含める
    # 7. 全体を二次暗号化して高度なセキュリティを確保
```

#### 3. 補助関数

```python
def preprocess_data(json_doc):
    """JSON文書の前処理（多段エンコード）"""
    # UTF-8 → Latin-1 → Base64の多段エンコード

def split_into_chunks(data, chunk_size=64):
    """データを固定長チャンクに分割"""
    # データをチャンクに分割

def generate_chunk_shares(secret, threshold, share_ids, p):
    """チャンクのシェア生成"""
    # シャミアの多項式を使ってシェアを生成

def generate_garbage_shares(unassigned_ids, num_real_shares, p):
    """未割当領域のゴミデータ生成"""
    # 統計的に区別できないランダムデータ生成

def encrypt_file_data(data, master_key):
    """データを高度に暗号化"""
    # AES-GCMなどの認証付き暗号化を適用
    # ファイルフォーマットを構築

def generate_file_uuid():
    """ファイル用のUUIDを生成"""
    # UUID v4を生成
    # タイムスタンプを組み合わせてファイル識別に使用
    # 書式: {timestamp}_{uuid}の形式
```

### 出力形式

暗号化の結果は高度に暗号化されたバイナリファイル形式で、以下の構造を持ちます：

```
[ファイルマジック (8バイト)] - 固定識別子
[UUID (16バイト)] - ファイル固有識別子
[バージョン (2バイト)] - ファイル形式バージョン
[アルゴリズム識別子 (2バイト)] - 使用暗号化アルゴリズム
[KDFパラメータ (可変長)] - 鍵導出関数のパラメータ
[IV (16バイト)] - 初期化ベクトル
[暗号化メタデータ (可変長)] - 暗号化された復号必須情報
[暗号化シェアデータ (可変長)] - 暗号化されたシェア情報
[認証タグ (16バイト)] - GCMモード認証タグ
```

この暗号化されたメタデータには次の情報が含まれます（暗号化されている）:

```
- 塩値（Salt）
- チャンク総数
- 閾値
- 使用素数
- その他必要な情報（A/B識別情報は含まない）
```

## 実装上の注意点

1. **セキュアな乱数生成**:

   - `secrets`モジュールを使用して暗号学的に安全な乱数を生成

2. **素数の選択**:

   - 有限体演算に使用する素数は十分に大きく選ぶ
   - 素数サイズは扱うデータサイズに合わせて調整

3. **効率性とメモリ使用量**:

   - 大きなファイルでもメモリ効率よく処理できるよう設計
   - 入力サイズの 3-4 倍程度のメモリ使用に抑える

4. **二重暗号化**:

   - データ本体の暗号化に加え、ファイル全体を二次暗号化することで安全性を強化
   - パスワードと乱数ソルトから導出した鍵を使用

5. **カナリア値**:

   - 復号検証用のカナリア値を埋め込み、正しい復号を確認できるようにする
   - カナリア値自体も暗号化して格納

6. **ファイル命名と衝突回避**:
   - 出力ファイル名に UUID とタイムスタンプを含める（例: `encrypted_{timestamp}_{uuid}.henc`）
   - 一時ファイルとバックアップファイルにも異なる UUID を付与
   - UUID 生成には Python の`uuid`モジュールを使用
   - ファイル上書きによる情報漏洩を防止
# 復号化モジュール実装ガイド

## 復号化モジュールの目的

このモジュールは暗号化ファイルとパスワードを入力として、対応する JSON 文書を復号します。シャミア秘密分散法を用いた多段 MAP 方式により、異なるパスワードによって異なる文書を復号することができます。

## 主要な機能と要件

### 1. 多段デコードプロセス

暗号ファイルを以下の多段デコードプロセスで処理します：

1. AES-GCM による二次暗号の解除
2. シェアマップの構築
3. 閾値以上のシェアを使って秘密値を復元
4. Base64 デコード
5. Latin-1 から UTF-8 へのデコード

### 2. シャミア秘密分散法によるシェア復元

- 閾値 `t` 以上のシェアから元の秘密値を復元
- ラグランジュ補間法による多項式の復元
- 有限体 GF(p) 上での計算

### 3. シェア ID と復号プロセスのマッピング

- パスワードとシェア ID リストを入力として受け取る
- シェア ID からシェア値へのマッピングを構築
- 閾値を満たすシェアを選択して復号を試行
- マッピングテーブルは一時的にのみ保持し、処理後に安全に削除

## 実装時の制約とガイドライン

### 絶対条件

1. **安全な一時ファイル処理**:

   - 一時ファイルもシャミア秘密分散法で保護
   - 一時ファイルには A 文書と B 文書が混在するデータを含まない
   - ファイル削除前に内容を上書き（0 バイトデータや乱数）して痕跡を残さない
   - メモリ上でも必要最小限のデータのみを保持

2. **処理の公平性**:

   - パスワードが間違っている場合も、処理時間が変わらないように実装
   - 早期リターンを避け、暗号学的にセキュアな比較を使用

3. **エラー処理の工夫**:

   - 正しくないパスワードに対しても同じ量の計算を行い、タイミング攻撃を防止
   - 適切なカナリア値の検証による安全な復号確認
   - エラーメッセージは情報漏洩のリスクを最小限に抑えるよう設計

4. **メモリ管理**:
   - 機密データを含む変数は使用後にゼロで上書き
   - 大きなファイルでもメモリ効率良く処理できるようストリーミング対応
   - ガベージコレクションを考慮した変数スコープの管理

### 主要関数の実装ガイド

#### 1. シャミア秘密分散法のシェア復元

```python
def lagrange_interpolation(shares, x_target, p):
    """
    ラグランジュ補間法を使用して多項式の値を計算

    Args:
        shares: シェアのリスト [(x1, y1), (x2, y2), ...]
        x_target: 計算対象のx座標（通常は0）
        p: 有限体の素数

    Returns:
        int: 補間された多項式の値 f(x_target)
    """
    # ラグランジュ補間法を実装
    # 有限体GF(p)上での計算に注意

def reconstruct_secret(shares, p):
    """
    閾値以上のシェアから秘密値を再構築

    Args:
        shares: 使用するシェアのリスト [(x1, y1), (x2, y2), ...]
        p: 有限体の素数

    Returns:
        int: 再構築された秘密値
    """
    # ラグランジュ補間法で多項式のf(0)を計算
```

#### 2. 復号関数

```python
def decrypt(encrypted_file, password, share_ids):
    """
    暗号化ファイルを復号

    Args:
        encrypted_file: 暗号化されたファイルパス
        password: 復号に使用するパスワード
        share_ids: 文書に対応するシェアIDのリスト

    Returns:
        str: 復号されたJSON文書、または失敗時はNone
    """
    # 1. 暗号化ファイルを読み込み
    # 2. 二次暗号化を解除
    # 3. マッピングテーブルを構築
    # 4. 適切なシェアを選択して秘密値を復元
    # 5. チャンクを元のデータに再構築
    # 6. 多段デコードを実行
    # 7. タイミング攻撃防止のため、全処理を同一時間で実行
```

#### 3. 補助関数

```python
def decrypt_file_data(encrypted_data, master_key):
    """
    暗号化されたファイルデータを復号（二次暗号の解除）

    Args:
        encrypted_data: 暗号化されたデータ
        master_key: 主暗号鍵（パスワードから導出）

    Returns:
        dict: 復号されたメタデータとシェアデータ
    """
    # AES-GCMなどによる認証付き復号を実行
    # 認証タグを検証して改ざんを検出

def build_share_map(shares_data, share_ids):
    """
    シェアIDからシェア値へのマッピングを構築

    Args:
        shares_data: すべてのシェアデータ
        share_ids: 使用するシェアIDのリスト

    Returns:
        dict: シェアIDをキー、シェア値を値とするマッピング
    """
    # シェアIDとシェア値のマッピングを構築

def reconstruct_chunks(chunk_secrets, chunk_count):
    """
    復元された秘密値からチャンクを再構築

    Args:
        chunk_secrets: 各チャンクの復元された秘密値のリスト
        chunk_count: チャンク総数

    Returns:
        bytes: 再構築されたデータ
    """
    # 復元された秘密値からチャンクを再構築
    # チャンクを連結して元のデータを形成

def post_process_data(data):
    """
    データの後処理（多段デコード）

    Args:
        data: 処理対象のデータ

    Returns:
        str: デコード後のJSON文書
    """
    # Base64デコード
    # Latin-1からUTF-8へのデコード
    # JSON文書の検証

def secure_delete_temp_files(temp_file_path):
    """
    一時ファイルを安全に削除

    Args:
        temp_file_path: 削除する一時ファイルのパス

    Returns:
        bool: 削除が成功した場合はTrue
    """
    # 1. ファイルをゼロで上書き
    # 2. 続いてランダムデータで上書き
    # 3. ファイルサイズを0に切り詰め
    # 4. ファイルを削除
    # 各ステップでエラー処理
```

## 復号化プロセスの詳細

### 1. 暗号ファイルの読み込みと検証

```
暗号化ファイル読み込み
↓
ファイルフォーマットの検証（マジック、バージョン）
↓
パスワードから主暗号鍵を導出（KDFパラメータ使用）
↓
二次暗号の解除とデータの整合性検証
```

### 2. シェアマッピングと秘密値の復元

```
シェアIDからシェア値へのマッピング構築
↓
各チャンクに対して:
  閾値以上のシェアを選択
  ↓
  ラグランジュ補間法による秘密値の復元
  ↓
  チャンク秘密値を保存
↓
チャンクを連結して元のデータを再構築
```

### 3. 多段デコードと文書復元

```
再構築されたデータをBase64デコード
↓
Latin-1からUTF-8へのデコード
↓
JSON文書の検証
```

## 実装上の注意点

### 1. セキュリティ考慮事項

- **タイミング攻撃対策**: パスワードが間違っている場合も同じ処理パスを通るよう実装
- **サイドチャネル攻撃対策**: 分岐処理を最小限に抑え、条件付き代入の使用を避ける
- **メモリ保護**: 使用後のメモリをゼロデータで上書き

### 2. 一時ファイル処理

- **シャミア保護**: 一時ファイルもシャミア秘密分散法で保護
- **固有識別子**: 一時ファイルは固有の UUID を使用して名前付け
- **安全な削除**: 使用後はゼロデータや乱数で上書きしてから削除
- **例外処理**: 処理中に例外が発生した場合も確実に一時ファイルを削除

### 3. エラー処理のガイドライン

- **最小情報の原則**: エラーメッセージは最小限の情報のみを提供
- **処理の継続**: 間違ったパスワードでも途中で処理を中断せず、同様の計算を続行
- **安全な比較**: 文字列比較には一定時間比較関数を使用

### 4. メモリ効率と大規模ファイル処理

- **チャンク処理**: 大きなファイルはチャンク単位で処理
- **メモリマッピング**: 必要に応じてメモリマッピングを使用
- **バッファリング**: ファイル操作にはバッファリングを適用

### 5. アップデート用パスワードの活用

- **アップデートマップ**: セキュリティ更新時にアップデート用パスワードと新しいシェア ID で復号マップを形成
- **パスワードフラグ**: アップデート用パスワードを識別するフラグを設け、別処理を定義

### 6. 一時ファイルの安全な処理のための追加関数

```python
def secure_temporary_file(prefix="temp", suffix=".bin"):
    """
    安全な一時ファイルを作成

    Args:
        prefix: ファイル名の接頭辞
        suffix: ファイル名の接尾辞

    Returns:
        tuple: (file_obj, file_path) - ファイルオブジェクトとパス
    """
    # UUIDを生成
    # 安全なディレクトリパスを構築
    # 一時ファイルを作成
    # カスタムクリーンアップをセット

def secure_overwrite(file_path, passes=3):
    """
    ファイルを安全に上書きして削除

    Args:
        file_path: 削除するファイルのパス
        passes: 上書き回数

    Returns:
        bool: 成功した場合はTrue
    """
    # ファイルサイズを取得
    # 複数回の上書き処理
    # ファイルを切り詰めて削除

def clean_memory_variable(variable):
    """
    メモリ変数を安全にクリア

    Args:
        variable: クリアする変数（バイト列やリスト）
    """
    # 変数タイプに応じてゼロデータで上書き
    # 可能であれば明示的に解放
```

これらの関数を活用して、一時ファイルと機密メモリデータを安全に管理してください。一時ファイルの処理は情報漏洩防止の重要な要素です。
# 更新モジュール実装ガイド

## 更新モジュールの目的

このモジュールは既存の暗号化ファイルに対して、A 文書または B 文書のいずれかを更新するためのものです。元の暗号化ファイルから必要な情報を取り出し、指定された文書のみを更新して新しい暗号化ファイルを生成します。

## 主要な機能と要件

### 1. 安全な一時ファイル処理

- **一時ファイルの保護**: 一時ファイルもシャミア秘密分散法で保護
- **アップデート用マップ**: パスワードから生成したマップを用いて一時ファイルアクセスを制御
- **ファイル上書き**: 削除前に一時ファイルを上書きして痕跡を残さない
- **例外時処理**: 処理中断時も一時ファイルを確実に削除

### 2. 文書の選択的更新

- **A または** B いずれかの更新: 一方の文書のみを更新可能（両方同時は不可）
- **他文書の保持**: 更新対象でない文書は変更せずに保持
- **メタデータの継承**: 可能な限り元ファイルのメタデータを継承

### 3. 更新プロセスの安全性確保

- **統計的区別不可能性の維持**: 更新後も A/B/未割当のシェアが統計的に区別できないこと
- **タイミング攻撃耐性**: 処理時間が入力に依存しないよう実装
- **ファイル拡散の防止**: 古いファイル、一時ファイルを安全に削除

## 更新プロセスの流れ

```
元ファイルを復号
↓
該当する文書を取得（A or B）
↓
新しい文書で置き換え
↓
元と同じシャミアパラメータで再暗号化
↓
新しいファイルとして出力（UUID更新）
↓
一時ファイルを安全に消去
```

## 主要関数の実装ガイド

### 1. 更新関数のメイン実装

```python
def update(encrypted_file, password, share_ids, new_json_doc, output_file=None):
    """
    暗号化ファイルの特定文書を更新

    Args:
        encrypted_file: 元の暗号化ファイルパス
        password: 更新対象文書のパスワード
        share_ids: 対象文書に対応するシェアIDセット
        new_json_doc: 新しいJSON文書
        output_file: 出力ファイルパス（デフォルトは自動生成）

    Returns:
        str: 新しい暗号化ファイルパス
    """
    # 1. 元ファイルを読み込み
    # 2. パスワードとシェアIDで対象文書を復号
    # 3. 復号できた場合、一時ファイルに安全に保存
    # 4. 元ファイルと同じ暗号化パラメータで再暗号化
    # 5. 新しいUUIDを生成
    # 6. 新しいファイルに書き出し
    # 7. 一時ファイルを安全に削除
```

### 2. 一時ファイル処理関数

```python
def create_secure_temp_file():
    """
    安全な一時ファイルを作成

    Returns:
        tuple: (file_obj, file_path) - ファイルオブジェクトとパス
    """
    # 1. UUIDを生成
    # 2. 安全なディレクトリパスを構築
    # 3. 一時ファイルを作成
    # 4. カスタムクリーンアップをセット

def store_retrieved_document(doc, password, temp_file_path):
    """
    復号された文書を一時ファイルに安全に保存

    Args:
        doc: 保存する文書
        password: 保護用パスワード
        temp_file_path: 一時ファイルパス

    Returns:
        bool: 成功した場合はTrue
    """
    # 1. 文書をシリアライズ
    # 2. シャミア秘密分散法で保護
    # 3. パスワードから鍵を導出
    # 4. AES-GCMで暗号化して保存

def retrieve_document_from_temp(temp_file_path, password):
    """
    一時ファイルから文書を安全に取得

    Args:
        temp_file_path: 一時ファイルパス
        password: 復号用パスワード

    Returns:
        dict: 取得したJSON文書
    """
    # 1. ファイルを読み込み
    # 2. パスワードから鍵を導出
    # 3. AES-GCMで復号
    # 4. シャミア秘密分散法で復元
    # 5. JSONとして解析

def secure_delete_temp_file(temp_file_path):
    """
    一時ファイルを安全に削除

    Args:
        temp_file_path: 削除する一時ファイルパス

    Returns:
        bool: 成功した場合はTrue
    """
    # 1. ファイルをゼロで上書き
    # 2. 続いてランダムデータで上書き
    # 3. ファイルサイズを0に切り詰め
    # 4. ファイルを削除
    # 5. 各ステップでエラー処理
```

### 3. 暗号化パラメータ抽出関数

```python
def extract_encryption_params(encrypted_data, password, share_ids):
    """
    暗号化ファイルからパラメータを抽出

    Args:
        encrypted_data: 暗号化されたバイナリデータ
        password: 復号に使用するパスワード
        share_ids: 使用するシェアIDセット

    Returns:
        dict: 暗号化パラメータ
    """
    # 1. ファイルを復号
    # 2. メタデータからパラメータを抽出
    # 3. 必要なパラメータを辞書にまとめて返却

def encrypt_with_params(json_doc, password, share_ids, unassigned_ids, params):
    """
    既存パラメータを使って再暗号化

    Args:
        json_doc: 暗号化するJSON文書
        password: 暗号化に使用するパスワード
        share_ids: 文書に対応するシェアIDセット
        unassigned_ids: 未割当のシェアIDリスト
        params: 元ファイルから抽出した暗号化パラメータ

    Returns:
        bytes: 暗号化されたデータ
    """
    # 1. パラメータに基づいて暗号化
    # 2. 元ファイルと互換性のある形式で暗号化
    # 3. 新しいUUIDを生成
```

## 実装上の制約とガイドライン

### 1. 一時ファイルの取り扱い

ファイルの更新中に作成する一時ファイルは、情報漏洩のリスクを伴います。以下のガイドラインを厳守してください：

- **保存場所の制限**: 一時ファイルは安全なディレクトリにのみ保存
- **暗号化の義務化**: 一時ファイルも必ず暗号化して保存
- **ダブルシャミア禁止**: 一時ファイルに複数平文機能は使わず、単一のシャミア秘密分散法で保護
- **メモリ上保持**: 可能な限りディスクに書き出さずにメモリ上で処理
- **確実な削除**: finally ブロックを使用して、例外発生時も確実に削除

### 2. エラー処理の方針

- **リカバリーメカニズム**: 更新処理中に失敗した場合、元のファイルを保持
- **アトミック更新**: 更新処理が完全に成功した場合のみ新ファイルを有効化
- **エラー情報の最小化**: エラーメッセージから機密情報が漏れないよう注意

### 3. 再暗号化のセキュリティ要件

- **UUID の更新**: 新しいファイルには新しい UUID を付与
- **ソルトの更新**: 新しいランダムソルトを生成（再利用しない）
- **セキュリティパラメータの継承**: 閾値や素数などのパラメータは継承
- **シェア配置の再シャッフル**: 新しいシェア配置は統計的に独立にシャッフル

### 4. ファイル管理戦略

- **元ファイルの扱い**: デフォルトでは元ファイルを残し、オプションで削除可能
- **バックアップの推奨**: 更新前に元ファイルのバックアップを推奨
- **命名規則**: `encrypted_{timestamp}_{uuid}.henc` の形式で命名
- **一時ファイル命名**: `temp_{timestamp}_{uuid}.tmp` の形式で一意に命名

### 5. 安全な一時ファイル作成のための追加関数

```python
def secure_temporary_file(prefix="temp", suffix=".bin"):
    """
    安全な一時ファイルを作成

    Args:
        prefix: ファイル名の接頭辞
        suffix: ファイル名の接尾辞

    Returns:
        tuple: (file_obj, file_path) - ファイルオブジェクトとパス
    """
    # UUIDを生成
    # 安全なディレクトリパスを構築
    # 一時ファイルを作成
    # カスタムクリーンアップをセット

def secure_overwrite(file_path, passes=3):
    """
    ファイルを安全に上書きして削除

    Args:
        file_path: 削除するファイルのパス
        passes: 上書き回数

    Returns:
        bool: 成功した場合はTrue
    """
    # ファイルサイズを取得
    # 複数回の上書き処理
    # ファイルを切り詰めて削除

def clean_memory_variable(variable):
    """
    メモリ変数を安全にクリア

    Args:
        variable: クリアする変数（バイト列やリスト）
    """
    # 変数タイプに応じてゼロデータで上書き
    # 可能であれば明示的に解放
```

## 更新処理実行フローの詳細

### 1. 元ファイルの検証と読み込み

```
元暗号化ファイルを読み込み
↓
ファイルフォーマットを検証
↓
パスワードとシェアIDで対象文書を復号
↓
復号できた場合、安全な一時ファイルに文書を保存
```

### 2. パラメータ抽出と再暗号化

```
元ファイルから暗号化パラメータを抽出
↓
新しい文書を用意
↓
元のパラメータ（閾値、素数など）を使用
↓
新しいUUIDとソルトを生成
↓
再暗号化を実行
```

### 3. 出力とクリーンアップ

```
新しいファイル名を生成（タイムスタンプ+UUID）
↓
暗号化データを新ファイルに書き出し
↓
一時ファイルを安全に削除
↓
（オプション）元ファイルを安全に削除
↓
新ファイルパスを返却
```

## セキュリティ上の注意点

1. **メモリ内保持時間の最小化**:

   - 復号された平文文書のメモリ内保持時間を最小限に抑える
   - 不要になった時点で即座にメモリ変数をゼロで上書き

2. **一時ファイルの暗号強度**:

   - 一時ファイルも本ファイルと同等の暗号強度で保護
   - シャミア秘密分散法と AES-GCM の二重保護を適用

3. **ファイル命名のセキュリティ**:

   - ファイル名から内容が推測できないようにする
   - UUID + タイムスタンプで一意性を確保

4. **途中経過の分離**:

   - A 文書と B 文書の途中経過が混在しないよう注意
   - それぞれを別々の一時ファイルで処理

5. **エラー時の情報漏洩防止**:
   - エラー発生時も情報漏洩が起きないよう確実に一時ファイル削除
   - エラーメッセージが処理内容を示唆しないよう設計
# CLI インターフェース実装ガイド

## CLI の目的

この CLI インターフェースは、シャミア秘密分散法による複数平文復号システムの 4 つの主要機能（初期化・暗号化・復号・更新）を利用しやすくするためのコマンドラインツールです。セキュリティを確保しつつ、ユーザーフレンドリーな操作性を提供します。

**重要な制約**: 暗号化および更新処理は必ず一つの文書ずつ行い、複数文書の同時処理は行いません。

## コマンド設計

### 1. ヘルプとサブコマンド構造

ツールは以下のサブコマンドを持ちます：

```
shamir-multi-crypt [グローバルオプション] <サブコマンド> [サブコマンドオプション]

サブコマンド:
  - initialize : システムを初期化し、シェアID空間を分割
  - encrypt    : 新規暗号化ファイルを作成し、JSON文書を暗号化
  - decrypt    : 暗号化ファイルから特定のJSON文書を復号
  - update     : 暗号化ファイル内の特定文書を更新
  - generate   : シェアIDセットを生成
  - help       : ヘルプを表示
```

### 2. 主要コマンドの詳細

#### 2.1. 初期化コマンド

```
shamir-multi-crypt initialize --size <シェア数> --ratio <比率> --output-a <Aシェアファイル> --output-b <Bシェアファイル>

オプション:
  --size, -s       : 生成するシェアIDの総数 (デフォルト: 100)
  --ratio, -r      : A:B:未割当の比率 (デフォルト: "35:35:30")
  --output-a       : A用シェアの出力ファイル名 (デフォルト: shares-a-{uuid}.bin)
  --output-b       : B用シェアの出力ファイル名 (デフォルト: shares-b-{uuid}.bin)
  --password-a     : A用シェアファイルのパスワード（指定しない場合はプロンプト）
  --password-b     : B用シェアファイルのパスワード（指定しない場合はプロンプト）
```

このコマンドは以下の処理を行います：

- 指定数のシェア ID を生成
- 比率に基づいて A 用、B 用、未割当に分類
- A 用と B 用のシェアを別々の高度に暗号化されたバイナリファイルに保存
- AB を俯瞰できるマスターデータは出力しない
- 各ファイルに一意の UUID を付与して重複を防止

#### 2.2. シェア ID 生成コマンド

```
shamir-multi-crypt generate --size <シェア数> --output <ファイル名>

オプション:
  --size, -s      : 生成するシェアIDの数 (デフォルト: 100)
  --output, -o    : 出力ファイル名 (デフォルト: shares-{uuid}.bin)
  --ratio, -r     : A:B:未割当の比率 (デフォルト: "35:35:30")
  --password, -p  : 出力ファイルを暗号化するパスワード（指定しない場合はプロンプト）
```

このコマンドは以下の処理を行います：

- 指定数のシェア ID を生成
- 比率に基づいて A 用、B 用、未割当に分類
- 高度に暗号化されたバイナリファイルに保存
- ファイルに一意の UUID を付与

#### 2.3. 暗号化コマンド

```
shamir-multi-crypt encrypt --file <JSONファイル> --shares <シェアIDファイル> --output <暗号化ファイル> --type <タイプ>

オプション:
  --file, -f      : 暗号化するJSON文書ファイルパス
  --shares, -s    : 文書用のシェアIDリストファイル
  --output, -o    : 出力暗号化ファイル名 (デフォルト: encrypted-{uuid}.bin)
  --type, -t      : 文書タイプ（"a"または"b"）
  --threshold     : 閾値（デフォルト: 3）
  --password, -p  : 暗号化に使用するパスワード（指定しない場合はプロンプト）
  --shares-password: シェアファイルのパスワード（指定しない場合はプロンプト）
```

**注意**: このコマンドは一度に一つの文書のみを処理します。両方の文書を同時に暗号化することはできません。

このコマンドは以下の処理を行います：

- 単一の JSON 文書を読み込み
- 暗号化されたシェア ID ファイルを復号して読み込み
- パスワードをプロンプト（指定されていない場合）
- 暗号化処理を実行し、指定された出力パスに高度に暗号化されたバイナリファイルとして保存
- 出力ファイルに一意の UUID を付与

#### 2.4. 復号コマンド

```
shamir-multi-crypt decrypt --input <暗号化ファイル> --shares <シェアIDファイル> --output <出力JSONファイル>

オプション:
  --input, -i     : 暗号化ファイルパス
  --shares, -s    : シェアIDリストファイル
  --output, -o    : 出力JSONファイル名（デフォルト: decrypted-{uuid}.json）
  --password, -p  : 暗号化ファイルのパスワード（指定しない場合はプロンプト）
  --shares-password: シェアファイルのパスワード（指定しない場合はプロンプト）
```

このコマンドは以下の処理を行います：

- 暗号化バイナリファイルとシェア ID ファイルを読み込み
- パスワードをプロンプト（指定されていない場合）
- 復号処理を実行し、指定された出力パスに JSON を保存
- 出力ファイル名に元の暗号化ファイルの UUID を含める

#### 2.5. 更新コマンド

```
shamir-multi-crypt update --input <暗号化ファイル> --file <新JSONファイル> --shares <シェアIDファイル> --output <更新後ファイル>

オプション:
  --input, -i     : 元の暗号化ファイルパス
  --file, -f      : 新しいJSON文書ファイル
  --shares, -s    : シェアIDリストファイル
  --output, -o    : 更新後の暗号化ファイル名（デフォルト: 上書き）
  --password, -p  : 暗号化ファイルのパスワード（指定しない場合はプロンプト）
  --shares-password: シェアファイルのパスワード（指定しない場合はプロンプト）
  --backup, -b    : 元ファイルのバックアップを作成（デフォルト: true）
```

このコマンドは以下の処理を行います：

- 元の暗号化ファイル、新しい JSON 文書、シェア ID ファイルを読み込み
- パスワードをプロンプト（指定されていない場合）
- 必要に応じて元ファイルのバックアップを作成（UUID ＋タイムスタンプ形式）
- 更新処理を実行し、結果を保存
- 元の UUID を維持して更新ファイルを生成

### 3. グローバルオプション

全コマンド共通のオプション：

```
--verbose, -v   : 詳細なログ出力を有効化
--quiet, -q     : 出力を最小限に抑える
--log-file      : ログの出力先ファイル
--help, -h      : ヘルプを表示
--version       : バージョン情報を表示
```

## 実装ガイドライン

### 1. パスワード入力の安全な処理

```python
def prompt_password(prompt_text="パスワードを入力してください: "):
    """
    パスワードを安全にプロンプト

    Args:
        prompt_text: プロンプト表示テキスト

    Returns:
        入力されたパスワード
    """
    # getpassモジュールを使用して画面に表示せずにパスワード入力
    import getpass
    return getpass.getpass(prompt_text)
```

### 2. 暗号化ファイルの処理

```python
def read_encrypted_file(file_path, password=None):
    """
    暗号化バイナリファイルを読み込み

    Args:
        file_path: 暗号化ファイルのパス
        password: パスワード（Noneの場合はプロンプト）

    Returns:
        tuple: (復号されたデータ, ファイルUUID)
    """
    # ファイル読み込み
    # パスワードが必要ならプロンプト
    # ファイルヘッダを解析（UUID含む）
    # 復号と返却
```

### 3. シェア ID リストの処理

```python
def load_share_ids(share_file, password=None):
    """
    暗号化されたシェアIDリストファイルを読み込み

    Args:
        share_file: シェアIDリストの暗号化バイナリファイルパス
        password: パスワード（Noneの場合はプロンプト）

    Returns:
        tuple: (シェアIDのリスト, ファイルUUID)
    """
    # ファイル読み込み
    # パスワードが必要ならプロンプト
    # 復号と解析
    # シェアIDのリストとUUIDを返却
```

### 4. ファイル処理の安全性確保

```python
def safe_write_file(data, output_path, uuid=None, backup=False, binary=True):
    """
    ファイルの安全な書き込み

    Args:
        data: 書き込むデータ
        output_path: 出力先パス
        uuid: ファイルUUID（Noneの場合は新規生成）
        backup: 既存ファイルのバックアップを作成するか
        binary: バイナリモードで書き込むか

    Returns:
        str: 書き込まれたファイルのUUID
    """
    # UUIDが指定されていなければ新規生成
    # バックアップが有効な場合、既存ファイルをUUID+タイムスタンプ形式でバックアップ
    # 一時ファイルに書き込み
    # 書き込み成功後、目的のパスに移動/リネーム
    # 使用したUUIDを返却
```

### 5. 初期化コマンド実装

```python
def initialize_command(args):
    """initialize サブコマンドの実装"""
    # 引数の検証
    # シェアID空間の生成
    # A/B/未割当シェアに分割
    # A用シェアをUUID付きで暗号化して保存
    # B用シェアをUUID付きで暗号化して保存
    # 成功メッセージの表示
```

### 6. メイン CLI 関数

```python
def main():
    """CLI エントリーポイント"""
    # コマンドライン引数のパース
    # サブコマンドに応じた処理の分岐
    # エラーハンドリングと適切なステータスコードでの終了
```

### 7. 暗号化コマンド実装例

```python
def encrypt_command(args):
    """encrypt サブコマンドの実装"""
    # 引数の検証
    # --file が指定されていることを確認
    # --type が "a" または "b" であることを確認
    # JSON文書の読み込み（単一文書のみ処理可能）
    # シェアIDファイルの読み込み
    # パスワードプロンプト（必要な場合）
    # UUIDの生成と保存（ファイル名の一部として使用）
    # 暗号化モジュールの呼び出し（単一文書のみ処理）
    # 結果の保存（UUIDを含むファイル名で）
    # 成功メッセージの表示
```

## セキュリティ上の注意点

### 1. パスワード取り扱い

- **メモリ保持の最小化**: パスワードはメモリ上に保持する時間を最小限に
- **環境変数の禁止**: パスワードを環境変数に保存しない
- **ヒストリー対策**: コマンドラインオプションより対話的入力を優先
- **安全なプロンプト**: `getpass`モジュールなどを使用して画面に表示しない

### 2. バイナリファイルのセキュリティ

- **認証暗号化**: AEAD モード（GCM, ChaCha20-Poly1305 など）を使用
- **鍵導出関数**: パスワードからの鍵導出には Argon2 や PBKDF2 を使用
- **ファイルフォーマット**: バージョン、UUID、ソルト、ノンスなどのメタデータを含むヘッダ形式を採用
- **ファイル完全性**: 認証タグでデータ改ざんを検出

### 3. エラーメッセージと情報漏洩

- **汎用エラーメッセージ**: エラーの詳細が機密情報を漏らさないよう注意
- **常に一定時間実行**: 無効なパスワードなどでも処理時間が変わらないよう考慮
- **同一失敗メッセージ**: 異なる失敗原因でも同じメッセージを表示

### 4. ファイル処理

- **アトミック操作**: ファイル更新は常にアトミックに行う
- **一時ファイルの保護**: 適切なパーミッションでの一時ファイル作成
- **残留データの防止**: 処理完了後に一時ファイルやメモリを適切にクリーンアップ
- **UUID による識別**: 全てのファイルに UUID を付与して一意性を確保

## ユーザービリティ

### 1. プログレス表示

```python
def show_progress(current, total, prefix='', suffix='', bar_length=50):
    """
    プログレスバーを表示

    Args:
        current: 現在の進捗
        total: 全体量
        prefix: プレフィックステキスト
        suffix: サフィックステキスト
        bar_length: バーの長さ
    """
    # プログレスバー表示ロジック
```

### 2. 色付き出力

```python
class Colors:
    """ANSI カラーコード"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def colorize(text, color):
    """テキストに色を付ける"""
    return f"{color}{text}{Colors.ENDC}"
```

### 3. ヘルプメッセージ

明確で詳細なヘルプメッセージを各コマンドに提供します：

```python
# コマンドの説明例
initialize_parser = subparsers.add_parser(
    'initialize',
    help='システムを初期化し、シェアID空間を分割',
    description='システムを初期化し、シェアID空間をA用、B用、未割当に分割します。'
             'A用とB用のシェアIDは別々の暗号化ファイルに保存され、マスターデータは出力されません。'
             '各ファイルにはUUIDが付与され、重複による上書きを防止します。'
)

encrypt_parser = subparsers.add_parser(
    'encrypt',
    help='新規暗号化ファイルを作成し、JSON文書を暗号化',
    description='一つのJSON文書とシェアIDセットを用いて暗号化ファイルを生成します。'
             '生成されたファイルは該当するパスワードとシェアIDセットで復号可能です。'
             '重要: このコマンドは一度に一つの文書のみを処理します。'
)
```

### 4. エラー処理とフィードバック

```python
def handle_error(error, verbose=False):
    """
    エラーを適切に処理して表示

    Args:
        error: 発生したエラー/例外
        verbose: 詳細表示モードか
    """
    # エラータイプに応じた処理
    # verboseモードの場合は詳細表示
    # 適切なエラーコードで終了
```

### 5. UUID 関連のヘルパー関数

```python
def generate_uuid():
    """新しいUUIDを生成"""
    import uuid
    return str(uuid.uuid4())

def make_filename_with_uuid(base_name, extension, uuid_str=None):
    """UUIDを含むファイル名を生成"""
    if uuid_str is None:
        uuid_str = generate_uuid()
    return f"{base_name}-{uuid_str}.{extension}"
```

## リリースとパッケージング

### 1. バージョン管理

```python
__version__ = '1.0.0'

def show_version():
    """バージョン情報を表示"""
    print(f"shamir-multi-crypt version {__version__}")
    print("シャミア秘密分散法による複数平文復号システム")
```

### 2. エントリーポイント定義

`setup.py` または `pyproject.toml` でのエントリーポイント定義：

```python
# setup.py の例
setup(
    # ...その他の設定...
    entry_points={
        'console_scripts': [
            'shamir-multi-crypt=shamir_multi_crypt.cli:main',
        ],
    },
)
```

---

## 実装の追加指示

1. このシステムは情報理論的安全性を持つよう設計されています。すべての実装においてこの原則に忠実であることが最重要です。
2. タイミング攻撃を防ぐため、条件分岐の禁止と定数時間処理は絶対に守ってください。
3. 暗号処理において、設計書にあるアルゴリズムから逸脱しないでください。
4. 「正しいパスワードによる復号」に見せかけたバックドアを仕掛けないでください。
5. 「統計的区別不可能性」を確保するためのA/B/未割当シェア分布を維持してください。
6. シェアデータは必ず高度に暗号化されたバイナリファイルとして出力し、平文のJSONは使用しないでください。
7. 初期化時にはABを俯瞰できるマスターデータは絶対に出力せず、A用、B用のシェアを別々に出力してください。

実装を開始してください。モジュール分割と正しいインポート関係を考慮したファイル構成から検討することをお勧めします。

備考：このシステムの主要な技術的特徴（多段MAP方式とシャミアベースの多重復号）は、研究目的での実装です。

制約条件：すべての原則を守りつつ実現できない場合は、何が達成できて何が難しいかを説明してください。
その際、セキュリティの実現が最優先です。機能を制限してでもセキュリティ原則を守ってください。

実装完了後は、コードの概要と使用方法を簡潔に説明してください。
