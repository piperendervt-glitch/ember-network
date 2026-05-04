# Sprint 1: binary node, discrete time

ember-network シミュレーション開発 Phase の最初の Sprint。AAS の核心ルール「使うと増える、使わないと減る」を最も simple な離散時間 binary input モデルで動作確認する。

## Sprint 1 Objective

AAS の核心ルール (使うと増える、使わないと減る) を最小の概念実装で動作確認する

## 数学モデル

```
weight(t+1) = clip(weight(t) + learning_rate · input(t) - forgetting_rate, 0, 1)
```

- `weight`: 状態変数、初期値 0、値域 [0, 1]
- `input(t)`: 0 または 1
- `learning_rate`: デフォルト 0.1 (加熱強度に相当)
- `forgetting_rate`: デフォルト 0.05 (冷却強度に相当)

物理的解釈は Sprint 2 以降で導入。Sprint 1 は概念モデルとして物理単位を持たない。

## Sprint Key Results 達成状況

| KR | 内容 | 達成判定 | 結果 | 証拠 |
|----|------|----------|------|------|
| **KR-S1** | 一定入力 input=1 を 100 ステップ提示で weight=1.0 到達 | t=20 で weight が 1.0 (誤差 < 1e-10)、t=20-100 で 1.0 安定 | ✅ 達成 | `tests/test_constant_input.py` 5 件 pass、`results/plots/plot_constant_input.png` |
| **KR-S2** | 50 ステップ input=1 + 50 ステップ input=0 で線形減衰 → 0 到達 | t=51-70 で傾き -0.05 線形減衰、t=70 で 0 到達、t=70-100 で 0 安定 | ✅ 達成 | `tests/test_input_cessation.py` 6 件 pass、`results/plots/plot_input_cessation.png` |
| **KR-S3** | 5 シードで bit-perfect に同じ結果 | `random.seed()` + `np.random.seed()` を [0, 1, 2, 3, 42] で固定し `numpy.array_equal` で完全一致 | ✅ 達成 | `tests/test_reproducibility.py` 3 件 pass、`results/plots/plot_reproducibility.png` |

## BinaryNode の設計サマリ

`src/binary_node.py` に `BinaryNode` クラスを実装。

```python
class BinaryNode:
    def __init__(self, learning_rate: float = 0.1,
                 forgetting_rate: float = 0.05) -> None: ...
    def update(self, input_value: int) -> None: ...
    @property
    def weight(self) -> float: ...
    def reset(self) -> None: ...
```

設計判断:

- **状態は `_weight` のみ**: Sprint 1 は最小概念モデルなので、温度や履歴は持たない。
- **clip は in-place で 1.0 / 0.0 にスナップ**: 浮動小数点誤差で 1.0000…001 や -0.0…001 になる場合も、`new_weight > 1.0` / `< 0.0` の比較で厳密に切り詰める。これにより clip 後の値は厳密に 1.0 または 0.0 となり、KR-S1 / KR-S2 の最終 weight 検証で誤差ゼロが保証される。
- **`update()` は戻り値なし**: 仕様書通り `-> None`。weight は property で取得する。
- **入力検証**: `input_value not in (0, 1)` で `ValueError` を raise。`isinstance` ではなく値による比較なので、`0.5` のような型は合うが値が不正な入力も拒否できる。
- **`reset()`**: 学習率パラメータは保持し weight のみ 0 に戻す。

## 結果サマリ

### テスト結果

```
$ pytest tests/ -v --junit-xml=results/logs/pytest_results.xml
============================= 23 passed in 0.34s ==============================
```

- 全 23 テストが pass
- JUnit XML: `results/logs/pytest_results.xml`
- 内訳: `test_basic.py` 9 件、`test_constant_input.py` 5 件、`test_input_cessation.py` 6 件、`test_reproducibility.py` 3 件

### コード品質

```
$ flake8 src/ tests/ visualize.py
(no output, exit 0)
```

### プロット

| ファイル | 内容 |
|---------|------|
| [`results/plots/plot_constant_input.png`](results/plots/plot_constant_input.png) | KR-S1: 一定入力下での weight 軌跡。t=20 で clip 発動、以降 1.0 で安定。実測値 (青) と理論線 (赤点線) が完全に重なる。 |
| [`results/plots/plot_input_cessation.png`](results/plots/plot_input_cessation.png) | KR-S2: 50 ステップ入力後に停止。t=50-70 で線形減衰、t=70 で 0 到達、以降 0 で安定。 |
| [`results/plots/plot_reproducibility.png`](results/plots/plot_reproducibility.png) | KR-S3: 5 シードでの weight 軌跡。決定論モデルなので全 5 線が完全に重なる。 |

## 学んだこと

1. **浮動小数点誤差は許容範囲内に収まる**: `0.05` を 20 回加算しても、累積誤差は ~4.4e-16 程度で、KR の許容誤差 1e-10 を 6 桁下回る。clip 機能が「丁度 1.0」「丁度 0.0」を保証することで、長期的な数値安定性も担保される。
2. **clip 発動タイミングの解釈**: 「t=20 付近で 1.0 に到達 (clip 発動)」という仕様は、t=20 で weight ≒ 1.0 (clip 不要) → t=21 で初めて weight + 0.05 > 1.0 となり実際に clip が動くという段階的挙動として実装される。テストでは `test_clipping_activates_at_t21` で明示的に確認した。
3. **決定論的モデルでも再現性テストの意義はある**: 現在のモデルはシードに依存しないが、`random.seed()` と `np.random.seed()` を固定する習慣を Sprint 1 から確立しておくことで、Sprint 2 以降で確率的要素 (例: 個体差、ノイズ) を導入した時に再現性インフラがそのまま使える。
4. **venv + pip freeze で環境固定**: `requirements.txt` を pip freeze 形式 (==) でコミットすることで、Constitutional Commitment 5 (Reproducibility First) を最も厳格な形で満たす。numpy 2.4.4, matplotlib 3.10.9, pytest 9.0.3, flake8 7.3.0 など全 20 パッケージのバージョンが完全固定される。
5. **可視化は理論線との重ね合わせが効果的**: 理論値 (`theory_constant_input` 関数等) を実測値と同じプロットに重ねることで、「数学モデルの予測通りに動いている」ことが視覚的に一目で確認できる。後続 Sprint で物理現象を入れた時の予測 vs 実測の比較インフラとしても流用可能。

## Sprint 2 への引き継ぎ事項

### Sprint 2 (連続時間モデル) で扱う予定の項目

- 離散時間 `t+1 = t + 1` を、連続時間 `dw/dt = ...` に置き換える
- 時定数 (heating time constant, cooling time constant) の導入
- ODE ソルバ (`scipy.integrate.solve_ivp` 等) の選定
- 時間ステップ Δt のサンプリング方針

### Sprint 1 から流用できるインフラ

- `BinaryNode` クラスの構造 (init / update / weight / reset の 4 メソッド) は Sprint 2 以降のクラス設計のテンプレートになる
- `tests/` の sys.path 操作パターン (各テストファイル冒頭で `sys.path.insert`) はそのまま使える
- `visualize.py` の実測値 vs 理論線の重ね合わせパターンは Sprint 2 以降の検証プロットでも有効
- `results/logs/pytest_results.xml` 出力の習慣は、各 Sprint で同様に運用する

### 確認事項 / 未解決の疑問

- 仕様書の「t=20 付近で clip 発動」という表現は、本実装では「t=20 で weight ≒ 1.0、t=21 で実 clip」と解釈した。Sprint Review で問題なければ、Sprint 2 以降の同種の表現も同じ解釈で進める。
- KR-S3 の「5 シードで bit-perfect」は決定論モデルでは自明だが、Sprint 6-7 で個体差を入れた際にこの KR は「同一シードでの再現性」に再定義する必要がある。

### Out of Scope だが lab_notebook 候補として記録すべき項目

(本 Sprint では特に発見なし)

## 動作確認環境

- **Python**: 3.12.10
- **OS**: Windows 11 Home (10.0.26200)
- **依存パッケージ**: `requirements.txt` 参照 (pip freeze 形式で完全固定)
- **シェル**: PowerShell 5.1 / bash (両方で動作確認)

## 再現手順

```powershell
# venv の作成と依存インストール
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# テスト実行
pytest tests/ -v --junit-xml=results/logs/pytest_results.xml

# プロット生成
python visualize.py

# コード品質チェック
flake8 src/ tests/ visualize.py
```

## ディレクトリ構造

```
sprint-01-binary-node/
├── README.md                       # 本ファイル
├── SPRINT_OKR.md                   # Sprint 1 OKR と Backlog
├── SPRINT_01_INSTRUCTIONS.md       # 実装指示書 (Robosheep からの input)
├── requirements.txt                # 依存固定 (pip freeze)
├── .gitignore                      # .venv 等を除外
├── visualize.py                    # 3 プロット生成スクリプト
├── src/
│   └── binary_node.py              # BinaryNode クラス
├── tests/
│   ├── test_basic.py               # 基本動作 (9 件)
│   ├── test_constant_input.py      # KR-S1 検証 (5 件)
│   ├── test_input_cessation.py     # KR-S2 検証 (6 件)
│   └── test_reproducibility.py     # KR-S3 検証 (3 件)
└── results/
    ├── plots/                      # 生成プロット (3 枚)
    └── logs/
        └── pytest_results.xml      # JUnit 形式テストログ
```

## OKR との関係

詳細は `SPRINT_OKR.md` を参照。

- **Project KR-P1 (7 段階シミュレーションの完了)**: Sprint 1 の Definition of Done を満たし、進捗 1/7 を達成。
- **Project KR-P5 (AI 支援開発の方法論的知見)**: 本 Sprint の AI 関連メトリクスは `ai_metrics/sprint-01_ai_log.md` に別途記録予定 (本 Sprint の Sprint Review 時に Robosheep が記録)。
- **Mission KR-M2 (単極性更新の十分性)**: `input ∈ {0, 1}` の単極性更新で weight が増減する基礎的 demonstration を達成。
