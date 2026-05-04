# Claude Code 指示書: ember-network プロジェクト Sprint 1 (binary node) の実装

## プロジェクト概要

`ember-network` は PTC 物理 AAS (Adaptive Artificial Synapse) の deterrence-oriented な参照実装を確立する研究プロジェクトです。熱物理が学習則を直接的に体現する物理基板を、シミュレーション、電子部品仮実装、3D プリント物理基板の段階で開発します。

プロジェクト名の由来: 「ember (燠、おき火)」は、燃え尽きた後も熱を保ち続ける炭火を指します。PTC 経路に残る熱、それが時間とともに自然に冷めていく構造、再び熱が加わることで刻まれる記憶。これらが ember-network の核心です。

このプロジェクトの最初のフェーズとしてシミュレーション開発を行っており、Sprint 1 はその最初のステップです。

詳細はリポジトリルートの `README.md`、`MISSION_OKR.md`、`PROJECT_OKR.md`、`CONSTITUTION.md`、`CLAUDE.md` を参照してください。

## Sprint 1 の位置づけ

Sprint 1 は AAS の核心ルール「使うと増える、使わないと減る」を、最も simple な離散時間 binary input モデルで動作確認します。これは概念レベルの動作確認であり、温度や物理単位は導入しません (これらは Sprint 2 以降)。

## Sprint 1 Objective

AAS の核心ルール (使うと増える、使わないと減る) を最小の概念実装で動作確認する

## Sprint 1 Key Results

### KR-S1

一定入力 input=1 を 100 ステップ提示すると、weight が 1.0 に到達し、その後 1.0 で安定する。具体的には t=20 付近で 1.0 に到達 (clip 発動)、t=20 から t=100 の間 weight は 1.0 で一定 (誤差 < 1e-10)。

### KR-S2

一定入力 input=1 を 50 ステップ後、input=0 を 50 ステップ提示すると、t=50 から線形減衰 (傾き -0.05)、t=70 付近で weight が 0 に到達、t=70 から t=100 で weight は 0 で一定。

### KR-S3

5 つの異なるランダムシードで完全に同じ結果が再現される (現在のモデルは決定論的)。

## 実装する数学モデル

```
weight(t+1) = clip(weight(t) + learning_rate · input(t) - forgetting_rate, 0, 1)
```

- weight: 状態変数、初期値 0、値域 [0, 1]
- input(t): 0 または 1
- learning_rate: デフォルト 0.1
- forgetting_rate: デフォルト 0.05

## 期待される挙動の事前予測

### (1) input=1 を一定で 100 ステップ

- t=0: weight = 0
- t=20: weight が 1.0 に到達 (clip)
- t=20 から t=100: weight = 1.0 (一定)

### (2) input=1 を 50 ステップ、input=0 を 50 ステップ

- t=20: weight = 1.0
- t=50: weight = 1.0 (入力切替直前)
- t=51-70: weight が線形に減衰
- t=70 から t=100: weight = 0 (一定)

### (3) 5 シードでの再現性

全シードで bit-perfect に同じ結果 (このモデルは決定論的)

これらの予測が KR の達成判定基準です。

## ディレクトリ構造

`ember-network/sprint-01-binary-node/` 内に以下を実装:

```
sprint-01-binary-node/
├── README.md
├── SPRINT_OKR.md
├── src/
│   └── binary_node.py
├── tests/
│   ├── test_basic.py
│   ├── test_constant_input.py
│   ├── test_input_cessation.py
│   └── test_reproducibility.py
├── results/
│   ├── plots/
│   └── logs/
└── visualize.py
```

## 実装するクラス

```python
class BinaryNode:
    """
    AAS 核心ルールの最小概念実装。
    
    数学モデル:
        weight(t+1) = clip(weight(t) + learning_rate · input(t) 
                            - forgetting_rate, 0, 1)
    
    物理的解釈:
        - 入力 input=1: 経路を使った状態 (Joule 加熱に相当、ember が燃える)
        - 入力 input=0: 経路を使わない状態 (自然冷却に相当、ember が冷める)
        - learning_rate: 加熱強度に相当
        - forgetting_rate: 冷却強度に相当
        - weight: 経路の重み (PTC の抵抗変化量に相当する量)
    
    注意:
        Sprint 1 では物理単位なしの概念モデル。
        温度、抵抗、Joule 加熱の数式は Sprint 3 以降で導入。
    """
    
    def __init__(self, learning_rate: float = 0.1, 
                 forgetting_rate: float = 0.05):
        # learning_rate と forgetting_rate を保存
        # weight を 0 で初期化
        pass
    
    def update(self, input_value: int) -> None:
        """
        1 ステップの更新。
        
        Args:
            input_value: 0 または 1
        
        Raises:
            ValueError: input_value が 0 または 1 でない場合
        """
        pass
    
    @property
    def weight(self) -> float:
        """現在の weight を返す。"""
        pass
    
    def reset(self) -> None:
        """weight を 0 にリセット。"""
        pass
```

## 実装するテスト

### tests/test_basic.py

- BinaryNode が正しく初期化される (weight=0)
- update() が weight を正しく変更する
- weight が範囲外 (負または 1 超) にならない
- input_value が 0 または 1 以外の場合 ValueError が発生

### tests/test_constant_input.py (KR-S1 検証)

- 100 ステップ input=1 で最終 weight が 1.0 (誤差 < 1e-10)
- t=25 以降は weight が 1.0 で一定
- t=20 付近で clip が発動

### tests/test_input_cessation.py (KR-S2 検証)

- 50 ステップ input=1 後、50 ステップ input=0 で最終 weight が 0
- 入力停止後の減衰が線形 (傾き -0.05)
- t=70 付近で 0 に到達

### tests/test_reproducibility.py (KR-S3 検証)

- 5 つの異なるシードで bit-perfect に同じ結果

## 実装する可視化 (visualize.py)

### plot_constant_input.png

- 横軸: time step (0-100)
- 縦軸: weight (0-1)
- 実測値 (青線): 一定入力での weight
- 理論線 (赤点線): 0.05·t (clip 前)、1.0 (clip 後)
- アノテーション: t=20 で「Clipping starts」

### plot_input_cessation.png

- 横軸: time step (0-100)
- 縦軸: weight (0-1)
- 実測値 (青線): 50 ステップ入力 + 50 ステップ非入力
- 理論線 (赤点線): 同じシナリオの理論予測
- アノテーション: t=50 「Input ceases」、t=70 「Decay completes」

### plot_reproducibility.png

- 横軸: time step
- 縦軸: weight
- 5 つのシードでの weight 時系列を 5 本の線で表示
- 全線が完全に重なる (決定論性の確認)

## README.md の必須内容

1. Sprint 1 Objective
2. Sprint Key Results と達成状況の表
3. BinaryNode の設計サマリ
4. 結果サマリ (テスト結果、プロットへのリンク)
5. 学んだこと (3-5 項目の bullet)
6. Sprint 2 への引き継ぎ事項

## SPRINT_OKR.md の必須内容

1. Sprint Objective
2. Sprint Key Results (KR-S1, KR-S2, KR-S3)
3. Sprint Backlog (タスクリスト)
4. Definition of Done
5. Out of Scope
6. Mission OKR / Project OKR との関係

## 重要な制約 (Out of Scope)

以下は Sprint 1 では実装しないこと。実装が必要と感じても、Sprint 2 以降で扱うため、現時点では追加しない:

1. 連続時間モデル (Sprint 2 で扱う)
2. 温度変数や物理単位 (Sprint 3 以降)
3. PTC 効果の非線形数式 (Sprint 4 以降)
4. 複数ノード間の相互作用 (Sprint 5 以降)
5. GUI、対話的可視化、ダッシュボード
6. 設定ファイル (YAML, JSON)、コマンドラインオプション
7. ロギングフレームワーク (logging モジュール)
8. クラスの継承、抽象クラス
9. 並列処理、GPU 加速、Numba 等の最適化
10. 外部データベース、ファイル I/O 以外の永続化
11. 「より良い」実装としての過剰な refactoring 提案

## 依存ライブラリ

- numpy >= 1.24
- matplotlib >= 3.7
- pytest >= 7.0

これら以外のライブラリは使用しないこと。requirements.txt または pyproject.toml に依存を固定すること。

## コーディング規約

1. Python 3.11 以上
2. PEP 8 準拠 (flake8 でエラーなし)
3. Type hints を使用
4. docstring を関数・クラスに記述 (Google スタイルまたは NumPy スタイル)
5. 関数は単一責務

## 完了確認の手順

実装後、以下をすべて確認:

1. `pytest tests/ -v` で全テストが pass する
2. `python visualize.py` で 3 つのプロットが results/plots/ に生成される
3. README.md が Sprint 1 の OKR 達成を記述している
4. `flake8 src/ tests/ visualize.py` でエラーなし
5. 全ファイルが正しい場所に配置されている

## 確信度の表明 (重要)

実装中、以下のいずれかに該当する場合は、独自判断で進めず、明示的に報告して判断を仰ぐこと:

1. 仕様の解釈に複数の可能性があり、判断が必要
2. 実装が予想と異なる挙動を示し、原因が不明
3. テストが想定外の理由で fail する
4. Out of Scope に該当しない範囲でも、仕様外の機能の追加が必要に思える
5. 既存ライブラリの使い方が不確実
6. 物理的解釈や数学モデルの理解が不確実

確信度は high/medium/low で明示すること。"動くはず" のような曖昧表現は使わず、確信度が low の場合は具体的な不確実点を明示する。

## 進捗報告の形式

各タスク完了時に以下を報告:

1. 完了したタスク名
2. 実装したファイルとその目的
3. テスト結果 (pass/fail の数)
4. 観察された予期しない挙動 (あれば)
5. 確信度の評価
6. 次のタスクへの提案

## 全体の指針

このプロジェクトは AI 支援開発における OKR の有効性を検証する実験的側面も持ちます。指示書の範囲を厳密に守り、scope creep を避け、不確実な点は明示的に報告することが、研究全体の方法論的価値に貢献します。完璧な実装よりも、明確で検証可能な実装を優先してください。

リポジトリルートの `CLAUDE.md` に記載された AI 利用ガイドライン (Specification 厳守、確信度の明示、結果の証拠化、Negative Result Reporting、範囲外の提案は記録のみ、Diff Review 前提、Halt-and-Confirm、健康と研究時間の尊重) を厳守してください。
