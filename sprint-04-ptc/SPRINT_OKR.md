# Sprint 4 OKR: realistic PTC effect model

**期間**: 2026-05-04 〜 (推定 17-24 時間)
**位置づけ**: Mission KR-M1 (Substrate-Learning Rule Identity) と KR-M3 (deterrence の物理的特性) への直接的貢献
**Mission との対応**: PTC 効果 R(T) は AAS の物理的本質であり、熱暴走の閾値は deterrence の物理的限界そのもの

---

## Sprint 4 Objective

連続時間温度モデルに PTC 効果 (温度依存の抵抗 R(T)) を導入し、Joule 加熱率が温度に依存する非線形系として実装する。これにより熱暴走と熱平衡の両方の挙動を物理的に正確にモデル化する。

Sprint 3 と異なり、Sprint 4 は Robosheep の判断 (PRL-010, PRL-011 の Sprint 4 での再評価) により 10 項目の新機能を同時に扱う。これは外部 AI の独立提案を Sprint 4 で積極的に活用する方針による。

---

## 数学モデル

### 主方程式

```
dT/dt = (R(T) / R_0) · heating_rate · input(t) - cooling_rate · (T - T_env)
R(T) = R_0 · (1 + α_PTC · (T - T_ref))
w(t)  = (T(t) - T_env) / (T_max - T_env)   ← 派生量
```

### パラメータ (7 つ、Sprint 3 から 3 つ追加)

| 名前 | 値 (default) | Sprint 3 対応 | 物理解釈 |
|------|------|------|------|
| heating_rate | 0.1 | 同 | 基準 (T=T_ref 時) の Joule 加熱率 |
| cooling_rate | 0.05 | 同 | Newton 冷却率 (= 1/τ_cool) |
| T_env | 0.0 | 同 | 周囲温度 (熱力学第二法則による下限) |
| T_max | 1.0 | 同 | 最大温度 (素材損傷リスク) |
| α_PTC | 0.3 | 新規 | PTC の温度係数 (R(T) の T 依存) |
| T_ref | T_env (None) | 新規 | PTC 参照温度 (R(T_ref) = R_0) |
| T_initial | T_env (None) | 新規 | 初期温度 (reset 後の T 値) |

`α_PTC=0` のとき `R(T) = R_0` (定数) となり、Sprint 3 と数学的に同一。

### 解析解 (input=1 一定、T_env=0、T_ref=0、clip なし)

```
dT/dt = heating_rate + (α_PTC · heating_rate - cooling_rate) · T
     = a + b · T
where a = heating_rate, b = α_PTC · heating_rate - cooling_rate

b ≠ 0: T(t) = -(a/b) · (1 - exp(b·t)) + T_initial · exp(b·t)
b = 0: T(t) = a · t + T_initial   (線形成長、臨界条件)
```

### 熱暴走の閾値

```
α_PTC > cooling_rate / heating_rate = 0.5 で熱暴走 (b > 0、指数発散)
```

### 検証で使う α_PTC 値

| α_PTC | b の符号 | 挙動 | 平衡点 T_eq |
|------|------|------|------|
| 0.0 | b < 0 | 線形 (Sprint 3 同一) | 2.0 |
| 0.1 | b < 0 | 弱い PTC | ≈ 2.5 |
| 0.4 | b < 0 | 臨界に近い | 10.0 |
| 0.6 | b > 0 | 熱暴走 (clip なしで発散) | 存在せず |
| 1.0 | b > 0 | 急激な熱暴走 | 存在せず |

---

## Sprint Key Results (8 つ)

### KR-S1: Sprint 3 との連続性 (α_PTC=0 での bit-perfect 一致)

α_PTC=0 のとき、Sprint 4 の TemperatureNode は Sprint 3 の TemperatureNode と数学的に同一であり、数値的に bit-perfect に一致する。

具体的判定:
- パラメータ: α_PTC=0、その他は Sprint 3 と同じ
- シナリオ: input=1 を 100 単位時間
- 全 t で `np.array_equal(T_sprint4, T_sprint3) == True` (literal、bit-perfect)

注意: α_PTC>0 で bit-perfect は崩れる (Sprint 3 から失う資産、Devil's Advocate #1 で予告済み)。

### KR-S2: PTC 効果の検証 (5 つの α_PTC 値)

α_PTC ∈ {0.0, 0.1, 0.4, 0.6, 1.0} の 5 つの値で、解析解との一致を検証する。

具体的判定:
- α_PTC = 0.0: 線形 (Sprint 3 と同一)、誤差 < 1e-15
- α_PTC = 0.1: 平衡点 T_eq ≈ 2.5、誤差 < 1e-6
- α_PTC = 0.4: 平衡点 T_eq = 10.0、誤差 < 1e-6
- α_PTC = 0.6: 熱暴走 (b > 0)、解析解は指数発散、誤差 < 1e-6
- α_PTC = 1.0: 急激な熱暴走、誤差 < 1e-6

### KR-S3: 物理的不変量 (8 つ、preregister 済み)

preregister された 8 つの不変量がすべての時刻で成立する。Hypothesis を 6 不変量すべてに適用 (max_examples=200)。

| # | 不変量 | 内容 |
|---|------|------|
| 1 | monotonicity | input>0 で T < T_eq なら T 単調増加 (clip 適用前) |
| 2 | positivity | T_initial >= T_env なら T >= T_env / T_initial < T_env なら漸近 |
| 3 | bounded | clip 適用時、全時刻で T <= T_max + 1e-15 |
| 4 | equilibrium | input>0 一定継続: b<0 なら T → T_eq、b>=0 なら発散 (clip なし) / T_max (clip あり) |
| 5 | heat-flow direction | input=0 で T と T_env の大小に応じた dT/dt の符号 (対称性) |
| 6 | weight-temperature linearity | 全時刻で w = (T - T_env) / (T_max - T_env) |
| 7 | PTC monotonicity (新規) | α_PTC > 0 で R(T) は T に対し単調増加 (dR/dT = R_0 · α_PTC) |
| 8 | PTC reference (新規) | T = T_ref のとき R(T) = R_0 |

### KR-S4: fractional input サポートの検証

fractional input (input ∈ [0, 1]) で TemperatureNode が正しく動作する。

具体的判定:
- 外部 AI が提案した fractional input テスト 10 件以上を統合 (Sprint 3 で skip した分)
- 解析解との比較 (input が連続値での解析解の導出)
- 物理的不変量が fractional input でも成立
- 範囲外 (input < 0 または input > 1) で ValueError

### KR-S5: T_initial と dt=0 の検証

T_initial パラメータと dt=0 の no-op 処理が正しく動作する。

具体的判定:
- T_initial < T_env からの復帰テスト (ChatGPT II Test 4, 9 後半 を採用)
- dt=0 で状態が変わらないテスト (ChatGPT I Test 8 を採用)
- T_initial > T_max の境界ケースのテスト
- bool 入力の拒絶 (Python bool は int の subclass、`isinstance(x, bool)` で先に reject)

### KR-S6: 熱暴走の検証

α_PTC > 0.5 で熱暴走が発生することを検証。これは ember-network の deterrence の物理的限界の demonstration である。

具体的判定:
- α_PTC = 0.6 (clip なし): T が指数発散、解析解と一致
- α_PTC = 0.6 (clip 付き): T が T_max で止まる
- 熱暴走の閾値 α_PTC = 0.5 で線形成長 (b = 0 の臨界条件)
- 数値計算で NaN や inf が発生しない (発生時は Tripwire #7 発動)

### KR-S7: MMS と Hypothesis の本格運用

MMS で複数の製造解 (多項式・三角関数・指数関数) を非線形 ODE に対して検証。Hypothesis を 6 不変量すべてに適用。

具体的判定:
- MMS: 各製造解で誤差 < 1e-6 (非線形 ODE 対応)
- Hypothesis: 6 不変量すべてで違反なし (max_examples=200)

### KR-S8: 完了報告 (Rule 8/10/11 構造)

Sprint 4 完了報告が Rule 8、Rule 10、Rule 11 の必須要素を満たす。

具体的判定:
- Rule 8 の必須テンプレート構造を遵守 (3 区分、数値的に意外、Devil's Advocate ≥3)
- Rule 10.6 (検知確率 90% KPI) の評価
- Rule 11 (PRL-012 対処の 5 項目チェックリスト) の遵守
- 潜在リスクログ (PRL-001 〜 PRL-012) の再評価
- Mutation Testing の kill rate を記録
- 「失う資産」(α_PTC>0 での bit-perfect 崩壊) と「得る資産」(PTC 効果) のトレードオフ記述

---

## Sprint 1, 2, 3 から Sprint 4 への数学的差異 (Sprint 開始時セルフチェックリスト)

このチェックリストは Sprint 2 で発見された「前 Sprint からの implicit 前提持ち込み」の再発防止策。各実装タスク開始時、Halt-and-Confirm 検討時、完了報告作成時に実質的に確認する (運用上の注意 (1) 形式化のリスク参照)。

### 前提 1: 状態変数の primary/secondary

- [ ] T が primary な状態変数であることを意識しているか?
- [ ] w を primary として扱おうとしていないか?
- [ ] R(T) を状態変数として扱おうとしていないか? (R(T) は T から計算される派生量)
- [ ] reset() は T を T_initial にリセットする実装になっているか? (Sprint 3 では T_env)

### 前提 2: パラメータ数

- [ ] 7 つのパラメータをすべて意識しているか? (heating_rate, cooling_rate, T_env, T_max, α_PTC, T_ref, T_initial)
- [ ] Sprint 3 の 4 つの発想だけを扱おうとしていないか?
- [ ] T_ref と T_initial のデフォルト値が None の処理 (T_env 代入) を実装しているか?

### 前提 3: clip と境界の解釈

- [ ] clip を「数学的境界」ではなく「物理的限界」として扱っているか?
- [ ] T_max は素材損傷リスク、T_env は熱力学第二法則という解釈を docstring に明示しているか?
- [ ] 熱暴走の閾値 α_PTC = 0.5 は parameter space の特異点であり、温度時系列の特異点ではないことを意識しているか?

### 前提 4: 解析解の形式

- [ ] 解析解を「単純な指数関数」と決めつけていないか?
- [ ] b の符号で 3 つの場合分け (b<0、b=0、b>0) を考慮しているか?
- [ ] MMS では複数の製造解 (多項式、三角関数、指数関数) を扱うことを意識しているか?

### 前提 5: Sprint 1, 2, 3 のテスト構造

- [ ] 「Sprint 3 で書いたテストの構造」を Sprint 4 にそのまま持ち込んでいないか?
- [ ] 例: Sprint 3 の lower clip テスト構造 (連続時間 positivity) と同種の前提持ち込みが Sprint 4 で発生していないか?
- [ ] fractional input により Sprint 3 の binary input 前提のテストが破綻する可能性を意識しているか?

### 前提 6: 物理的不変量の preregister

- [ ] Sprint 4 で preregister された 8 つの物理的不変量すべてを実装で検証する意識があるか?
- [ ] 不変量 7 (PTC monotonicity) と不変量 8 (PTC reference) の新規追加を意識しているか?
- [ ] 不変量の検証を「Claude Code が思いついたケース」だけに限定していないか?

### 運用上の注意

(1) **形式化のリスク**: チェックリストが「形式的にチェックして OK」にならないよう、各項目について実質的に判断する。

(2) **チェックリスト自体の限界**: チェックリストは「認識している前提」しか防げない。認識していない盲点はチェックリストに含まれないことを認識する (PRL-006, PRL-007)。

(3) **追加項目の可能性**: Sprint 4 中に新たな implicit 前提を発見したら、本チェックリストに追加し、`lab_notebook/potential_risk_log.md` にも PRL-013 以降として記録する。

---

## Sprint Backlog (22 タスク、推定 17-24 時間)

進行は 5 つの checkpoint commit で区切る:
- **Step A** (タスク 0-4): セットアップ、ガイドライン整備
- **Step B**: Robosheep の外部 AI 3 段階相談 (Robosheep の作業)
- **Step C** (タスク 5-15): 実装と KR 検証
- **Step D** (タスク 16, 18): Mutation Testing、外部 AI 統合
- **Step E** (タスク 19-21): 可視化、README、完了報告

| # | タスク | 推定 | Step |
|---|------|------|------|
| 0 | pytest.ini の継承と修正 | 5-10 分 | A |
| 1 | CLAUDE.md に Rule 11 を追加 | 15-20 分 | A |
| 2 | potential_risk_log.md の更新 | 15-20 分 | A |
| 3 | Sprint 4 ディレクトリ構造作成 | 10-15 分 | A |
| 4 | SPRINT_OKR.md の作成 | 45-60 分 | A |
| 5 | TemperatureNode の Sprint 4 版実装 | 90-120 分 | C |
| 6 | scenarios.py の拡張 | 30-45 分 | C |
| 7 | 解析解の実装 (analytical.py) | 45-60 分 | C |
| 8 | MMS の拡張 (mms.py、非線形 ODE 対応) | 60-90 分 | C |
| 9 | KR-S1 検証 (bit-perfect、α_PTC=0) | 20-30 分 | C |
| 10 | KR-S2 検証 (5 つの α_PTC) | 60-90 分 | C |
| 11 | KR-S3 検証 (8 不変量 + Hypothesis max_examples=200) | 90-120 分 | C |
| 12 | KR-S4 検証 (fractional input) | 45-60 分 | C |
| 13 | KR-S5 検証 (T_initial と dt=0) | 30-45 分 | C |
| 14 | KR-S6 検証 (熱暴走) | 45-60 分 | C |
| 15 | KR-S7 検証 (MMS + Hypothesis 運用) | 60-90 分 | C |
| 16 | Mutation Testing 導入と実施 | 90-120 分 | D |
| 17 | 外部 AI 3 段階相談 (Robosheep 担当) | - | B |
| 18 | 外部 AI テストケース統合 | 90-120 分 | D |
| 19 | 可視化 (6 プロット) | 90-120 分 | E |
| 20 | README.md 作成 | 45-60 分 | E |
| 21 | 完了報告 (Rule 8/10/11 構造) | 45-60 分 | E |

合計推定工数: 17-24 時間 (PROJECT_OKR.md の Sprint 4 time-box 2 営業日は計画上の枠、実際の進行管理は Robosheep の領域)

---

## Out of Scope (Sprint 4 で実装しない項目)

### Sprint 1, 2, 3 から継続する Out of Scope

1. GUI、対話的可視化、ダッシュボード
2. 設定ファイル (YAML, JSON)、コマンドラインオプション
3. ロギングフレームワーク
4. クラスの継承、抽象クラス
5. 並列処理、GPU 加速、Numba 等の最適化
6. 外部データベース、ファイル I/O 以外の永続化
7. 「より良い」実装としての過剰な refactoring 提案
8. soft saturation 関数 (sigmoid 等) の実装
9. scipy.integrate.solve_ivp 等への依存 (テストでは MMS 検証用に sympy を使用可)
10. 適応的時間刻みの実装
11. 数値積分の精度に関する高度な分析
12. ContinuousNode (Sprint 2) と TemperatureNode (Sprint 3, 4) の統合
13. 物理単位 (J、°C、s、Ω、A 等) の導入 → Sprint 7
14. 熱伝達の詳細物理 (放射、対流、伝導の区別)

### Sprint 4 特有の Out of Scope

15. 複数経路 (multi-path) の実装 → Sprint 5
16. R(T) の非線形近似 (指数関数、多項式 2 次以上) → 線形 R(T) のみ扱う
17. 実物 PTC データのテーブル参照 (lookup_table)
18. 連続値入力の高度な制御 (PWM 周波数依存、フィードバック制御)
19. 連立微分方程式の本格的扱い (Sprint 5 以降)
20. 時間反転非対称性の検証
21. 熱暴走の制御理論 (Lyapunov、Bode 等は Sprint 6 で扱う)

### 紛らわしい項目の判断

- **A**: Sprint 3 と Sprint 4 の TemperatureNode は別ファイル (sprint-04-ptc/src/temperature_node.py) として実装。Sprint 3 の実装は変更しない。
- **B**: 熱暴走の挙動の詳細分析 → In Scope (KR-S6)
- **C**: 物理パラメータの値選択 → Out of Scope (Sprint 7)
- **D**: PTC 効果の解析的検証 → In Scope (KR-S2)
- **E**: T_initial の Sprint 5 への影響 → Sprint 4 は単一経路、Sprint 5 で multi-path 拡張は別途
- **F**: Mutation Testing の対象範囲 → 主要モジュール (temperature_node.py、analytical.py、mms.py) のみ。scenarios.py、visualize.py 等は対象外

---

## Tripwires (即座に halt-and-review 発動)

以下のいずれかが発生した場合、進行を止めて Robosheep に判断を仰ぐ:

1. Constitutional Commitments の違反が発見される
2. 主要な KR (S1-S8) のいずれかが達成困難と判明
3. **KR-S1 (α_PTC=0 での bit-perfect 一致) が達成できない** (重大事態、Sprint 4 特有)
4. 物理的不変量のいずれかが違反される
5. 外部 AI のテストケースが Claude Code の実装と矛盾する
6. MMS の数値解と製造解の誤差が予想外に大きい (1e-6 を大幅に超える)
7. **熱暴走の数値計算で発散が制御不能になる (NaN や inf)** (Sprint 4 特有)
8. **Mutation Testing で kill rate が極端に低い (例: < 50%)** (Sprint 4 特有)
9. その他、AI が独自判断で進めるべきでないと感じる事態

---

## Definition of Done (24 項目)

### Sprint 1, 2, 3 から継承する DoD (1-8)

1. `pytest tests/ -v` で全テストが pass
2. `pytest --junit-xml` で JUnit ログが `results/logs/` に保存
3. `python visualize.py` で 6 プロットが `results/plots/` に生成
4. `flake8 src/ tests/ visualize.py scenarios.py` でエラーなし
5. README.md が KR 達成を証拠付きで記述
6. requirements.txt で全依存が pip freeze 形式で完全固定
7. doctest が pytest 実行時に自動実行
8. .python-version ファイルが作成

### Sprint 4 特有の DoD (9-24)

9. KR-S1 達成 (α_PTC=0 での Sprint 3 との bit-perfect 一致)
10. KR-S2 達成 (5 つの α_PTC 値で解析解との一致)
11. KR-S3 達成 (8 つの物理的不変量がすべて成立)
12. KR-S4 達成 (fractional input サポートの検証)
13. KR-S5 達成 (T_initial と dt=0 の検証)
14. KR-S6 達成 (熱暴走の検証)
15. KR-S7 達成 (MMS と Hypothesis 本格運用)
16. KR-S8 達成 (完了報告 Rule 8/10/11 構造)
17. CLAUDE.md に Rule 11 が追加されている (PRL-012 対処のチェックリスト)
18. lab_notebook/potential_risk_log.md が更新されている
19. 外部 AI 3 段階相談の結果が `external_ai_responses/` に保存
20. Hypothesis が 6 不変量すべてに適用 (max_examples=200)
21. Mutation Testing が主要モジュールで実施され、kill rate が記録
22. Sprint 4 完了報告に検知確率 90% KPI の評価が含まれる
23. Sprint 4 完了報告に PRL-001 〜 PRL-012 の再評価が含まれる
24. Sprint 4 完了報告に「失う資産」(α_PTC>0 での bit-perfect 崩壊) と「得る資産」(PTC 効果) のトレードオフが記述

---

## 全体の指針

(1) **北極星優先**: Mission OKR (特に KR-M1 と KR-M3) への貢献が最優先。Project KR-P5 はおまけ。

(2) **失う資産の認識**: Sprint 3 の bit-perfect KR-S1 は α_PTC=0 でのみ維持。α_PTC>0 で崩れる。これは Devil's Advocate #1 (Sprint 3) で指摘済み。

(3) **得る資産**: PTC 効果の物理的リアリティ、熱暴走制御 (deterrence の本質)、非線形 ODE 経験。

(4) **進行管理**: time-box (2 営業日) は計画として保ち、実際の進行は Robosheep が管理。タスク削減判断は Sprint 進行中に Robosheep が行う。

(5) **判断スキップ**: 判断の迷いが少ない問いはスキップ可能 (Sprint 3 Planning で確立)。

外部ベンチマーク (Rule 10, 11、KR-S5/S7) は手段であり目的ではない。手段が目的を圧迫しないよう、北極星 (PTC 効果と熱暴走の物理的正しさ) を中心に据える。

リポジトリルートの `CLAUDE.md` (Rule 1〜11) と `CONSTITUTION.md` (Commitment 1〜9) を厳守する。
