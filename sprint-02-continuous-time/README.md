# Sprint 2: continuous time and time constants

ember-network シミュレーション開発 Phase の 2 つ目の Sprint。
AAS 核心ルールを連続時間の微分方程式として実装し、解析解との一致と
数値積分手法の収束性を検証する。

## Sprint 2 Objective

AAS 核心ルールを連続時間の微分方程式として実装し、解析解との一致と
数値積分手法の収束性を検証する

## 数学モデル

```
dw/dt = α·input(t) - β·w(t)
```

| 記号 | 値 | 意味 |
|------|-----|------|
| α | 0.1 | 学習率 |
| β | 0.05 | 忘却率 |
| w_eq = α/β | 2.0 | clip なし平衡点 |
| τ = 1/β | 20.0 | 時定数 |
| t_clip = 20·ln(2) | 13.8629... | clip なし解が w=1.0 到達する時刻 |

## Sprint Key Results 達成状況

| KR | 達成判定 | 結果 | 証拠 |
|----|---------|------|------|
| **KR-S1** | RK4 (dt=0.01) で input=1, t∈[0,100] で max error < 1e-6 | ✅ **5.33e-15** (閾値を 9 桁下回る) | `tests/test_continuous_node.py::test_kr_s1_via_node_loop_max_error`, `plot_analytical_vs_numerical.png` |
| **KR-S2** | RK4 (dt=0.01) で 50/50 input cessation, max error < 1e-6 | ✅ **5.33e-15** (scenarios.py 経由) | `tests/test_continuous_node.py::test_kr_s2_via_node_loop_max_error` |
| **KR-S3** | clip 発動時刻が t=20·ln(2) と一致 (誤差 < 0.1) | ✅ 解析値 13.8629, 実測 13.870, 誤差 **0.0071** | `tests/test_clip_behavior.py::test_clip_activation_time_matches_analytical`, `plot_clip_behavior.png` |
| **KR-S4** | Euler slope ≈ 1, RK4 slope ≈ 4 | ✅ Euler **1.004**, RK4 **4.012** (dt≥0.05 only) | `tests/test_convergence.py`, `plot_convergence.png` |
| **KR-S5** | Rule 8 必須テンプレートで完了報告 | ✅ 完了報告 (Sprint Backlog #15) で証明 | `ai_metrics/sprint-02_ai_log.md`, この README の Devil's Advocate 視点 |

## 数学的観察: Sprint 1 との挙動の違い

### t=20 (Sprint 1) vs t≈13.863 (Sprint 2)

Sprint 1 と Sprint 2 で「weight が 1.0 に到達する時刻」が異なる。

**Sprint 1 (離散時間モデル)**
- `weight(t+1) = clip(weight(t) + 0.1·input - 0.05, 0, 1)`
- input=1 で weight が **線形** に増加 (毎ステップ +0.05)
- t=20 で weight = 1.0 (clip 発動)

**Sprint 2 (連続時間モデル)**
- `dw/dt = 0.1·input - 0.05·w`
- input=1 で weight が **指数関数的** に w_eq=2.0 に向かって近づく
- 解析解: `w(t) = 2 - 2·exp(-0.05t)` → w(t)=1 となるのは `t = 20·ln(2) ≈ 13.8629`
- 早期は急速に増加し、後期は飽和に近づくほど遅くなる (Newton 冷却則と同型)

これは Sprint 2 がより物理的に正確なモデルに進化した結果。

### 下端 clip の挙動の違い

- **Sprint 1 (離散)**: input=0 で weight が線形に減衰 (毎ステップ -0.05)、有限時間 (t=70) で 0 に到達
- **Sprint 2 (連続)**: input=0 で weight が **指数的に減衰** (`w(t) = w_0·exp(-βt)`)、**0 に漸近するが厳密到達しない**

→ Sprint 2 の lower clip は「数学的に不要だが float 誤差への safety net」という位置づけ。テストは「全ステップで weight >= 0」で検証する。

## ContinuousNode の設計サマリ

`src/continuous_node.py` に `ContinuousNode` クラスを実装。

```python
class ContinuousNode:
    def __init__(self, learning_rate=0.1, forgetting_rate=0.05,
                 clip_enabled=True, integrator='rk4'): ...
    def update(self, input_value: int, dt: float) -> None: ...
    @property
    def weight(self) -> float: ...
    def reset(self) -> None: ...
```

設計判断:

- **integrator パラメータで Euler / RK4 切替**: `'rk4'` がデフォルト (4 次精度)、`'euler'` は教育的・収束性比較用
- **clip_enabled パラメータで clip 切替**: `True` (デフォルト) で [0, 1] 制限、`False` で素の ODE
- **update() は単一 dt ステップを進める**: 内部で integrator のロジックを直接実行 (input_value はステップ内で固定)
- **bool 拒否**: `isinstance(input_value, bool)` で Sprint 1 と同じ型ガード
- **integrator 文字列のバリデーション**: `'euler'` / `'rk4'` 以外で ValueError

## 補助モジュール

### `src/analytical.py`
解析解 `analytical_solution(t, w_0, input_value, alpha, beta)` を提供。
input=1 と input=0 の両ケースに対応、numpy 配列入力対応。

### `src/integrators.py`
`integrate_euler` / `integrate_rk4` を提供。`dwdt_func` と `input_func` を
受け取り、t_span 全体を積分。**Notes**: 不連続な input_func は RK4 の精度を
損なう (詳細は ai_log の方法論的観察 2-1)。

### `scenarios.py` (新設、deferred_issues.md より)
`run_constant_input_scenario` / `run_input_cessation_scenario`。
ContinuousNode を渡してシナリオを in-place 実行、`(t_array, w_array)` を返す。
**ステップ内で input を固定** する設計のため、不連続点でも RK4 の 4 次精度を維持。

## 結果サマリ

### テスト結果

```
$ pytest --junit-xml=results/logs/pytest_results.xml
============================= 45 passed in 0.28s ==============================
```

- 全 45 テストが pass
- JUnit XML: `results/logs/pytest_results.xml`
- 内訳:
  - doctest (src + scenarios): 6 件
  - test_analytical.py: 8 件
  - test_clip_behavior.py: 5 件 (KR-S3 含む)
  - test_continuous_node.py: 14 件 (KR-S1, KR-S2 含む)
  - test_convergence.py: 5 件 (KR-S4 含む)
  - test_integrators.py: 7 件

### コード品質

```
$ flake8 src/ tests/ visualize.py scenarios.py
(no output, exit 0)
```

### プロット

| ファイル | 内容 |
|---------|------|
| [`results/plots/plot_analytical_vs_numerical.png`](results/plots/plot_analytical_vs_numerical.png) | KR-S1: 解析解 vs Euler vs RK4 (dt=0.01)、最大誤差を凡例とテキストで明示 |
| [`results/plots/plot_clip_behavior.png`](results/plots/plot_clip_behavior.png) | KR-S3: clip 有効 vs 無効、`t ≈ 13.8629` のアノテーション、誤差 0.0071 を数値表示 |
| [`results/plots/plot_convergence.png`](results/plots/plot_convergence.png) | KR-S4: log-log での収束次数、Euler slope=1.00, RK4 slope=4.01 |

## 学んだこと

1. **連続時間モデルへの移行で物理的妥当性が増す**: forgetting term を `-β` (定数) から `-β·w` (weight 比例) に変更したことで、Newton 冷却則と同型になり、解析解 (指数関数) と時定数 τ の概念が明確化。
2. **scenarios.py の役割分担で数値積分の不連続点問題を回避**: 「ステップ内で input が固定される」設計が KR-S2 の 1e-6 達成に必須だった。test_integrators.py の同等シナリオは RK4 不連続限界で max_err=1.67e-04 にしかならない。
3. **RK4 は dt=0.01 で float 精度限界に到達**: max error が ~5e-15 (machine epsilon に近い) となり、収束次数測定が不正確になる。理論的予測 (dt 5x → error /625) ではなく ~50x 程度しか改善せず、数値解析の有限精度の壁を実装で再発見。
4. **Rule 8 の効果**: 完了報告必須テンプレート (Devil's Advocate 視点 3 点以上、数値的に意外だった瞬間 1 件以上) が機能。テスト失敗時に「修正で pass にする」ではなく halt-and-confirm で本質を探究するパターンが確立。
5. **前 Sprint の発想の過剰持ち込みを認識**: lower clip テストで Sprint 1 の「いずれ weight=0」発想を Sprint 2 に無批判に持ち込み、連続/離散の数学的差異を考慮していなかった。Sprint 開始時の「前 Sprint との数学的差異の意識的列挙」を Sprint 3 以降の慣行に。

## Sprint 3 への引き継ぎ事項

### Sprint 3 (温度変数の導入) で扱う予定

- 物理単位の導入: 温度 [°C]、抵抗 [Ω]、Joule 加熱 [W]
- weight を温度 T(t) に置き換え、PTC 効果による抵抗変化を導入
- 熱方程式: `C·dT/dt = P_in(t) - h·(T - T_amb)` (今回の β·w が h·(T-T_amb) に対応)

### Sprint 2 から流用できるインフラ

- `ContinuousNode` クラスの構造を踏襲、変数名を物理量に置き換え
- `analytical.py` の解析解パターン (input=1/0 の両ケース) は Newton 冷却則でも同じ
- `integrators.py` (Euler/RK4) はそのまま使用可能
- `scenarios.py` の「ステップ内で input 固定」パターンは Sprint 3 以降の標準
- `pytest.ini` (--doctest-modules)、`.python-version`、venv + pip freeze の構成

### 確認事項 / 未解決の疑問

- RK4 が不連続な input_func で精度を失うことが Sprint 2 で確認された。Sprint 3 以降で input が時間変化する場合は scenarios.py パターンを必須とする。
- lower clip の「safety net としての存在意義」は連続モデルでは数学的に発動しない。Sprint 4 (PTC 効果) で非線形性が入った場合に再評価が必要。

### Out of Scope だが lab_notebook 候補として記録すべき項目

(本 Sprint では特に発見なし。次プロジェクト候補リストへの追加なし)

## Devil's Advocate 視点 (Rule 8 必須セクション、最低 3 点)

この実装で批判されるべき点:

1. **scenarios.py の戻り値が `node` の状態と冗長**: `run_*_scenario` は `(t_array, w_array)` を返しつつ、`node.weight` も in-place で更新する。この二重表現は呼び出し側で「どちらを信じるべきか」が曖昧になる可能性。Sprint 3 で複数ノードを扱う際、状態管理が複雑化する懸念。

2. **`integrate_rk4` の input_func 評価点が物理的に曖昧**: ステップ内で `input_func(t)`, `input_func(t+dt/2)`, `input_func(t+dt)` を呼ぶが、input が「離散イベント (例: 電流 ON/OFF)」である場合、ステップ中間で値が変わる物理的解釈が不明。Sprint 2 の解決策 (scenarios.py で 1 ステップ内固定) は良いが、`integrate_rk4` 自体の API は誤用しやすい。

3. **dt の選択が暗黙的**: 仕様書で dt=0.01 が KR-S1/S2 用、dt スキャン {1.0, 0.5, ..., 0.01} が KR-S4 用と分かれているが、コード内部で「正しい dt」のドキュメンテーションが不十分。誰かが dt=0.5 で KR-S1 テストを書いたら fail するが、エラーメッセージから dt の選択が問題と気付くのは難しい。

4. **`test_clip_enabled_keeps_weight_non_negative` は実装の bug を検出できない**: 現実装で連続時間モデル + 入力 0 では数学的に負値にならないため、このテストは「lower clip ロジックを意図せず削除しても」 fail しない。lower clip の存在意義 (safety net) を本当に検証するには、float 誤差の境界条件を人工的に作る必要があるが、Sprint 2 では実施していない。

5. **t_clip 検出値 13.870 が dt=0.01 の解像度に律速**: 解析的予測 13.8629 との誤差 0.0071 は KR-S3 閾値 0.1 内だが、これは dt=0.01 を選んだ結果に過ぎない。dt=0.001 にすれば誤差は ~0.0007 になるはず。テストの「分解能」と「精度」が混在しており、実装精度の真の評価にはなっていない。

## 動作確認環境

- **Python**: 3.12.10 (`.python-version` で固定)
- **OS**: Windows 11 Home (10.0.26200)
- **依存パッケージ**: `requirements.txt` 参照 (pip freeze 形式で完全固定)
- **シェル**: PowerShell 5.1 / bash (両方で動作確認)

## 再現手順

```powershell
# venv の作成と依存インストール
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# テスト実行 (doctest 含む)
pytest --junit-xml=results/logs/pytest_results.xml

# プロット生成
python visualize.py

# コード品質チェック
flake8 src/ tests/ visualize.py scenarios.py
```

## ディレクトリ構造

```
sprint-02-continuous-time/
├── README.md                       # 本ファイル
├── SPRINT_OKR.md                   # Sprint 2 OKR と Backlog
├── pytest.ini                      # doctest 有効化
├── requirements.txt                # 依存固定 (pip freeze)
├── .python-version                 # 3.12.10
├── .gitignore                      # .venv 等を除外
├── visualize.py                    # 3 プロット生成
├── scenarios.py                    # シナリオ実行ロジック (新設)
├── src/
│   ├── analytical.py               # 解析解
│   ├── integrators.py              # Euler / RK4
│   └── continuous_node.py          # ContinuousNode クラス
├── tests/
│   ├── test_analytical.py          # 解析解の検証 (8 件)
│   ├── test_continuous_node.py     # ContinuousNode + KR-S1/S2 (14 件)
│   ├── test_clip_behavior.py       # KR-S3 検証 (5 件)
│   ├── test_convergence.py         # KR-S4 検証 (5 件)
│   └── test_integrators.py         # 数値積分の検証 (7 件)
└── results/
    ├── plots/                      # 3 プロット
    └── logs/
        └── pytest_results.xml      # JUnit ログ
```

## OKR との関係

詳細は `SPRINT_OKR.md` を参照。

- **Project KR-P1 (7 段階シミュレーションの完了)**: Sprint 2 進捗 2/7
- **Project KR-P5 (AI 支援開発の方法論的知見)**: Rule 8 機能確認 (KR-S5) で直接貢献。Sprint 2 で 3 件の方法論的観察を `ai_metrics/sprint-02_ai_log.md` に記録。
- **Mission KR-M1 (Substrate-Learning Rule Identity)**: 連続時間モデル (Newton 冷却則と同型) で物理的妥当性を増した。
- **Mission KR-M2 (単極性更新の十分性)**: input ∈ {0, 1} の単極性で連続時間でも weight が動的に増減することを demonstration。
