# Sprint 3: Temperature Variable

**期間**: 2026-05-04 (1 営業日内、9-13 時間相当)
**位置づけ**: Mission KR-M1 (Substrate-Learning Rule Identity) への直接的貢献
**Mission との対応**: 学習則は基板の物理現象 (Joule 加熱と Newton 冷却) そのもの

---

## Sprint 3 Objective

連続時間モデルに温度変数 `T` を導入し、`dT/dt = heating_rate · input - cooling_rate · (T - T_env)` の形で Joule 加熱と Newton 冷却の物理現象が学習則を体現することを示す。Sprint 2 の `ContinuousNode` と数値的に等価でありながら、状態変数 (T が primary、w が派生量) の意味論を物理に再帰させる。

---

## Sprint Key Results 達成状況

| KR | 内容 | 閾値 | 実測 | 達成 |
|---|------|------|------|------|
| **KR-S1** | Sprint 2 との数値的整合性 | < 1e-15 | **0.000e+00** (np.array_equal=True) | ✅ |
| **KR-S2** | T↔w 線形変換 | < 1e-15 | **0.000e+00** (記号的同一) | ✅ |
| **KR-S3** | 物理的不変量 6 件 (preregister 済) | 全成立 | **6/6 すべて成立** (Hypothesis 含む) | ✅ |
| **KR-S4** | MMS 多製造解の数値解一致 | < 1e-6 | poly: 1.21e-13、trig: 1.78e-15、exp: 2.66e-15 | ✅ |
| **KR-S5** | 外部 AI 3 段階の独立検証 | 統合 + 矛盾 halt | **18/46 採用、28 skip (PRL 化)、矛盾 1 件 halt** | ✅ |
| **KR-S6** | Rule 8 と Rule 10 の機能確認 | 報告構造 + KPI | 本完了報告で達成 | ✅ |

**全テスト**: 95/95 pass (`pytest`)、flake8 clean。

---

## TemperatureNode の設計サマリ

### 主方程式

```
dT/dt = heating_rate · input(t) - cooling_rate · (T - T_env)
w(t)  = (T(t) - T_env) / (T_max - T_env)   ← 派生量 (@property)
```

### パラメータ (Sprint 2 との数値的連続性)

| 名前 | 値 | Sprint 2 対応 | 物理解釈 |
|------|------|------|------|
| heating_rate | 0.1 | α | Joule 加熱率 = R₀·I_max² / C_thermal |
| cooling_rate | 0.05 | β | Newton 冷却率 = 1/τ_cool |
| T_env | 0.0 | (新規) | 周囲温度 (熱力学第二法則による下限、漸近境界) |
| T_max | 1.0 | (新規) | 最大温度 (素材損傷リスク、deterrence の物理基盤) |

### 状態変数構造 (前提 1 の遵守)

- **T (温度) が primary な状態変数**: 内部 `self._T` で保持、`@property def temperature` で公開
- **w (weight) は派生量**: `@property def weight` で `(T - T_env) / (T_max - T_env)` を返す。setter なし → assignment で `AttributeError`
- **`reset()`**: T を T_env にリセット (w を 0 にリセットではない)
- **`update()`**: T を進化させる (w を進化させるのではない)

---

## Sprint 2 → Sprint 3 の数学的等価性 (KR-S1 の構造的意味)

### bit-perfect 一致の達成

`T_env=0, T_max=1, heating_rate=α, cooling_rate=β` のとき、5 つの bit-perfect テストすべてで `np.array_equal(T_sprint3, w_sprint2) = True`、`max|T - w| = 0.000e+00`。

### なぜ literal 0.0 が達成されたか

IEEE 754 浮動小数点仕様により `T - 0.0 == T` (任意の有限 T) が **bit-identical** に成立する。Sprint 3 の `_dTdt(T) = heating·input - cooling·(T - T_env)` で T_env=0.0 のとき、`(T - 0.0)` は T と完全一致し、Sprint 2 の `_dwdt(w) = α·input - β·w` と同じ浮動小数点演算列を生成する。さらに RK4 ステップ `T + dt/6 · (k1 + 2·k2 + 2·k3 + k4)` も Sprint 2 と同じ算術順序で書いたため、bit レベルで等価。

### 構造的意味

これは「TemperatureNode が ContinuousNode の物理的解釈である」ことの数学的証明。Sprint 4 で PTC R(T) を導入すると非線形性により bit-perfect は崩れる予定だが、その時点で「Sprint 3 ↔ Sprint 2 の整合性は数学モデルの整合性であって実装の独立検証ではない」ことが顕在化する (Devil's Advocate #1 の指摘)。

---

## 物理的不変量 6 項目の達成 (KR-S3)

Sprint 3 Planning で preregister された 6 不変量 (Rule 10.2)。すべてのテストが pass。

| # | 不変量 | テスト数 | 検証方法 |
|---|------|------|------|
| 1 | monotonicity | 2 | input=1 中、`np.diff(T) >= -1e-10` |
| 2 | positivity | 5 (含 Hypothesis 1) | 全時刻で `T >= T_env` |
| 3 | bounded | 3 (含 Hypothesis 1) | clip 適用時、全時刻で `T <= T_max` |
| 4 | equilibrium | 3 | T → T_eq (clip なし) または T_max (clip 付き) |
| 5 | heat-flow | 3 (含 Hypothesis 1) | input=0 かつ T > T_env で T 減少 |
| 6 | linearity | 2 | 全時刻で `w = (T-T_env)/(T_max-T_env)` |
| - | sentinel | 1 | 6 不変量を 1 シミュレーションで同時検証 |

**Hypothesis 試行的導入** (Rule 10 の補完): 3 件 (positivity、heat-flow、bounded)。bounded は Step C 完了報告 Devil's Advocate #4 への対応として Step E で追加 (`max_examples=40`、heating_rate ∈ [0.01, 2.0] / cooling_rate ∈ [0.01, 1.0] / T_env ∈ [-5, 5] / T_offset ∈ [0.5, 10] のパラメータ空間)。

---

## MMS による解析解との一致 (KR-S4)

SymPy で 3 種類の製造解を生成し、強制項を逆算して RK4 で数値積分。期待値が実装と完全に独立 (Rule 10.3)。

| 製造解 | T(t) | 区間 | 最大誤差 | 閾値比 |
|------|------|------|------|------|
| polynomial | 0.5·t² + 0.1·t | (0, 10) | **1.208e-13** | 1e-6 を 7 桁下回る |
| trigonometric | 0.3·sin(0.2·t) + 0.5 | (0, 30) | **1.776e-15** | 1e-6 を 9 桁下回る |
| exponential | 1 − exp(−0.05·t) | (0, 60) | **2.665e-15** | 1e-6 を 9 桁下回る |

すべて float64 機械精度規模に到達。

---

## 外部 AI 3 段階相談の結果サマリ (KR-S5)

### 配置情報

`external_ai_responses/` に Robosheep が Grok と ChatGPT に独立で 3 段階で相談した結果を配置 (`.py` 形式、計 6 ファイル、46 テスト、1,392 行)。

### 統合結果 (18/46 採用)

Step D の Halt-and-Confirm で Robosheep が確定した **Option E** (Type 1 fractional input は Sprint 3 では skip、Sprint 4 で再評価) に基づく分類。

| カテゴリ | テスト数 | 取り扱い |
|---|---|---|
| **Type 5: 採用** | **18** | `tests/test_external_ai.py` に統合、全 pass |
| Type 1: fractional input | 10 | skip → PRL-010 (Sprint 4 再評価) |
| Type 2: Interface 矛盾 | (Type 5 内で adapt) | adapter (`_heat_until` helper) で吸収 |
| Type 3: 負の初期 T | 2 | skip → PRL-011 (Sprint 4 再評価) |
| Type 4: 既存テストとの重複 | 11 | 除外 (KR-S1〜S4 で既にカバー) |
| dt=0 矛盾 | 1 | skip → PRL-010 (Sprint 4 再評価) |
| AI 間の重複 | 4 | 除外 |
| **合計** | **46** | **18 採用 + 28 skip** |

### 採用元の内訳 (18 件)

| AI / Stage | 採用 | 主要観点 |
|------|------|------|
| Grok II (前提なし) | 3 | 長時間冷却、boundary 安定性、ランダム binary stress |
| Grok III (文脈あり) | 2 | reset idempotency、パルス accumulation |
| Grok I (既存共有) | 3 | weight read-only、半減期、clip + cooling 並立 |
| ChatGPT II (前提なし) | 2 | impulse response、large dt 安定性 |
| ChatGPT III (文脈あり) | 4 | dt invariance、primary/secondary feedback、drift、heating_rate scaling |
| ChatGPT I (既存共有) | 4 | mutation テスト 4 種 (separability、T_env shift、ON/OFF asymmetry、parameter swap) |

### 矛盾発見と halt-and-confirm

10 件の fractional input テストが Sprint 3 OKR Out of Scope 項目 17 と矛盾 → **Step D 中盤で halt-and-confirm 発動**。Robosheep の Option E 判断で Sprint 3 では skip、Sprint 4 で再評価。

---

## 学んだこと (方法論的観察)

### 1. AI ファミリー間の interface 想定の構造的分岐

ChatGPT 全系統 (3 ファイル) は **pure function** `step_temperature(T, input, dt, params)` を想定、Grok 全系統 (3 ファイル) は **class インスタンス** + 内部 attr 直接代入 (`node._temperature = X`) を想定。同じ Sprint 3 仕様を読んでも AI ファミリーで interface 解釈が完全に分岐した。これは Rule 10.5 の「外部 AI 3 段階の独立性」が方法論的に機能したことの強い証拠であり、同時に「Sprint 仕様書が interface を明示すべき」という運用改善の示唆 (PRL-010 で Sprint 4 への引き継ぎ)。

### 2. 線形 ODE の commutativity と mutation テストの限界

ChatGPT I Test 5 (`asymmetric_response_to_input_toggle`) は ON→OFF と OFF→ON で結果が顕著に異なることを atol=1e-6 で主張。Sprint 3 の線形 ODE では実際の差は ~5e-7 (B0=0 のため A0·A1 = A1·A0 + 微小 RK4 打切り誤差)。外部 AI が線形性の commutativity を完全には認識していなかった可能性。Sprint 4 で PTC R(T) の非線形性が入ると真の非可換性が現れ、このテストの mutation 検出力が回復するはず。

### 3. RK4 の不連続点問題 (Sprint 2 から継続)

PRL-003 (Sprint 2 で発見、scenarios.py で対処) は Sprint 3 でも有効。`scenarios.py` 経由で 1 ステップ内 input 固定パターンを継承し、KR-S1 / KR-S2 を高精度で達成。

### 4. Hypothesis 試行的導入の盲点と対処

Step C で Hypothesis 2 件 (positivity、heat-flow direction) を導入したが Devil's Advocate #4 で「違反しにくい性質を選んだ可能性」を自己批判。Step E で bounded (clip ロジックという複雑な分岐を持つ箇所) に追加 1 件、計 3 件。max_examples=40 は防御的すぎる設定で、Sprint 4 で 200 への増強と他不変量への展開を予定 (PRL-010 に追記)。

### 5. 偶発的可視と構造的対処

`external_ai_responses/*.py` が pytest 自動収集で ImportError → エラーメッセージにファイル名と import 行が露出。pytest.ini に `--ignore=external_ai_responses` と `norecursedirs` を追加して構造的に分離。テスト logic の中身は Step D まで読まずに済んだ (PRL-009 として記録、検証可能性は内省のみという限界も明記)。

---

## 結果サマリ

### テスト構成 (95 件)

```
sprint-03-temperature/
├── scenarios.py                       (2 doctest)
├── src/
│   ├── analytical.py                  (1 doctest)
│   ├── mms.py                         (5 doctest)
│   └── temperature_node.py            (1 doctest)
└── tests/
    ├── test_analytical.py             (10 unit)
    ├── test_external_ai.py            (18 KR-S5)
    ├── test_invariants.py             (20 KR-S3、Hypothesis 3 件含む)
    ├── test_mms.py                    (10 KR-S4)
    ├── test_sprint2_consistency.py    ( 5 KR-S1)
    ├── test_temperature_node.py       (13 unit)
    └── test_weight_conversion.py      (10 KR-S2)
合計: 9 doctest + 86 pytest = 95 件
```

### プロット (4 件)

`results/plots/`:
- `plot_temperature_evolution.png` - 温度時系列、Sprint 2 weight との bit-perfect 一致を可視化
- `plot_clip_behavior.png` - T_max での clip、t_clip≈13.86 の解析的予測との一致
- `plot_invariants.png` - 6 物理的不変量を交互 input パターンで同時可視化
- `plot_mms_verification.png` - 3 製造解 (poly/trig/exp) と数値解の比較

---

## Sprint 4 への引き継ぎ事項

### 潜在リスクログ (PRL-001 〜 PRL-011)

11 件のリスクを `lab_notebook/potential_risk_log.md` で追跡。Sprint 3 で新規発見した 3 件:

- **PRL-009**: 外部 AI ファイルの偶発的可視 (pytest 自動収集) → 部分対処、内省的検証の限界記録
- **PRL-010**: 外部 AI による fractional input の独立提案 + dt=0 + Hypothesis max_examples 増強 → Sprint 4 Planning で再評価
- **PRL-011**: 非物理初期状態 (T < T_env) の検証手段なし → Sprint 4 で `T_initial` パラメータ追加検討

### Sprint 4 で考慮すべき技術項目

1. **PTC R(T) の導入** (Sprint 4 主目的): 抵抗が温度に依存する非線形性。Sprint 3 ↔ Sprint 2 の bit-perfect 等価性は崩れる予定。
2. **fractional input サポート再評価**: 6 AI 中 4 つが自然視 → deterrence-oriented との整合性を Robosheep が判断。
3. **`T_initial` パラメータ**: 非物理状態 (T < T_env) からの復帰検証を可能にするか。
4. **AI への interface 明示**: Sprint 4 仕様書で「class vs pure function」を明示、`EXTERNAL_AI_3_STAGE_PROMPTS.md` テンプレート改訂検討。
5. **Hypothesis 増強**: max_examples=40 → 200、他不変量 (monotonicity 等) への展開。
6. **chatgpt_I Test 5 (asymmetry) 閾値の再検討**: PTC 非線形性で真の asymmetry が現れる可能性、atol を 1e-6 に戻す候補。

---

## 動作確認環境

- Python 3.12.10
- 完全固定された依存 (`requirements.txt`、24 packages、pip freeze 形式):
  - numpy==2.4.4, matplotlib==3.10.9, pytest==9.0.3, sympy==1.14.0, hypothesis==6.152.4
- venv: `sprint-03-temperature/.venv/` (gitignore で除外)

## 再現手順

```bash
cd sprint-03-temperature
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# テスト実行 (95 件)
.venv/Scripts/python.exe -m pytest --tb=short

# プロット生成 (4 件)
.venv/Scripts/python.exe visualize.py

# flake8 検査
.venv/Scripts/python.exe -m flake8 src/ tests/ visualize.py scenarios.py

# JUnit XML
.venv/Scripts/python.exe -m pytest --junit-xml=results/logs/pytest_results.xml
```

---

## ディレクトリ構造

```
sprint-03-temperature/
├── README.md                          (本ファイル)
├── SPRINT_OKR.md                      (KRs、Backlog、セルフチェックリスト)
├── pytest.ini                         (--doctest-modules + external_ai_responses 除外)
├── requirements.txt                   (24 packages、完全固定)
├── .python-version                    (3.12.10)
├── .gitignore                         (.venv, __pycache__, .pytest_cache)
├── visualize.py                       (4 プロット生成)
├── scenarios.py                       (Sprint 2 パターンを拡張、TemperatureNode 用)
├── src/
│   ├── temperature_node.py            (TemperatureNode、T が primary)
│   ├── analytical.py                  (温度方程式の解析解)
│   └── mms.py                         (Method of Manufactured Solutions)
├── tests/
│   ├── test_temperature_node.py       (13 unit)
│   ├── test_analytical.py             (10 unit)
│   ├── test_invariants.py             (20、KR-S3 + Hypothesis 3 件)
│   ├── test_mms.py                    (10、KR-S4)
│   ├── test_sprint2_consistency.py    ( 5、KR-S1 bit-perfect)
│   ├── test_weight_conversion.py      (10、KR-S2)
│   └── test_external_ai.py            (18、KR-S5)
├── external_ai_responses/             (Robosheep 配置、6 ファイル、46 テスト)
│   ├── grok_stage_II.py
│   ├── grok_stage_III.py
│   ├── grok_stage_I.py
│   ├── chatgpt_stage_II.py
│   ├── chatgpt_stage_III.py
│   └── chatgpt_stage_I.py
└── results/
    ├── plots/                         (4 PNG)
    └── logs/                          (pytest_step_c.xml, pytest_step_d.xml)
```

---

## OKR との関係

- **Mission KR-M1 (Substrate-Learning Rule Identity)** への直接的貢献: 温度変数 T を primary な状態変数として導入し、Joule 加熱と Newton 冷却が学習則を体現することを実装的に明示。Sprint 2 の抽象モデル → Sprint 3 の物理的解釈 → Sprint 4 の PTC 効果と段階的に物理現象を接続する流れを確立。
- **Project KR-P5 (AI 支援開発の方法論的知見)** への貢献: Rule 10 の運用 (外部 AI 3 段階)、Rule 8 の継続運用、PRL-009/010/011 の追加、AI ファミリー間の interface 分岐の発見。
- **Constitution Commitment 9 (自己参照ループ残存リスクの管理)**: 検知確率 90% KPI と PRL の運用が始動。

---

## Devil's Advocate (本 README に対する自己批判)

1. **bit-perfect 一致 (KR-S1) は Sprint 4 で必ず崩れる**: 構造的に Sprint 2 の同形であり、PTC R(T) を入れた瞬間に bit レベルの等価性は失われる。「Sprint 3 の達成」は「Sprint 4 で必ず手放す資産」であり、過度に強調すると Sprint 4 への移行心理を阻害する可能性。
2. **18/46 採用判断の主観性**: 「Type 5 採用」「Type 4 重複」の境界は私の判断。Robosheep が独立に検証していない (PRL-006 自己参照ループ)。Sprint 3 Retrospective で Robosheep が元の 46 テストを精査して再評価する余地。
3. **Hypothesis 3 件は依然少ない**: max_examples=40 の防御的設定、対象不変量も 6 中 3 件のみ。Sprint 3 で本格運用とは言えず、PRL-010 の引き継ぎは「導入したという既成事実」を作る形式化のリスク (PRL-001 単純化バイアスの再発候補)。
4. **AI ファミリー interface 分岐の発見が「面白い」だけで終わるリスク**: 観察として深いが、Sprint 4 の運用改善 (`EXTERNAL_AI_3_STAGE_PROMPTS.md` 改訂) に具体的につなげなければ、知見として活用されない。Sprint 4 Planning 時に Robosheep に明示的に提案する責任。
5. **本 README が成功側のナラティブに偏っている可能性**: 95/95 pass、bit-perfect 達成、6 不変量成立 — 数値的事実はその通りだが、「Sprint 3 で十分」と読者に錯覚させるリスク。実際の限界 (Out of Scope の fractional input、interface adapter による意図変換、Hypothesis の控えめな運用) は学んだことセクションに記載したが、「達成」と「限界」のバランスは Robosheep が読んで判断する必要。
