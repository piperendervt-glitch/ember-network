# Sprint 3 OKR: temperature variable

**期間**: 2026-05-04 〜 (推定 9-13 時間)
**位置づけ**: Mission KR-M1 (Substrate-Learning Rule Identity) への直接的貢献
**Mission との対応**: 学習則は基板の物理現象 (Joule 加熱と Newton 冷却) そのもの

---

## Sprint 3 Objective

連続時間モデルに温度変数 `T` を導入し、`dT/dt = heating_rate · input - cooling_rate · (T - T_env)` の形で Joule 加熱と Newton 冷却の物理現象が学習則を体現することを示す。Sprint 2 の `ContinuousNode` と数値的に等価でありながら、状態変数 (T が primary、w が派生量) の意味論を物理に再帰させる。

---

## 数学モデル

### 主方程式

```
dT/dt = heating_rate · input(t) - cooling_rate · (T - T_env)
w(t)  = (T(t) - T_env) / (T_max - T_env)   ← 派生量
```

### パラメータ (Sprint 2 との数値的連続性)

| 名前 | 値 | Sprint 2 対応 | 物理解釈 |
|------|------|------|------|
| heating_rate | 0.1 | α | Joule 加熱率 |
| cooling_rate | 0.05 | β | Newton 冷却率 (= 1/τ_cool) |
| T_env | 0.0 | (新規) | 周囲温度 (熱力学第二法則による下限) |
| T_max | 1.0 | (新規) | 最大温度 (素材損傷リスク) |

`T_env=0, T_max=1` で `w = T` となり、Sprint 2 と数値的に bit-perfect 一致 (KR-S1)。

### 解析解

```
input=1: T(t) = T_eq + (T_0 - T_eq) · exp(-cooling_rate · t)
         T_eq = heating_rate / cooling_rate = 2.0 (clip なし)
         t_clip = 20 · ln(2) ≈ 13.8629  (T_max=1 に到達する時刻)

input=0: T(t) = T_env + (T_0 - T_env) · exp(-cooling_rate · t)
```

---

## Sprint 3 Key Results

### KR-S1: Sprint 2 との数値的整合性

`TemperatureNode` と Sprint 2 の `ContinuousNode` を同条件で実行し、全 t で `|T_sprint3(t) - w_sprint2(t)| < 1e-15`。

### KR-S2: 温度と weight の変換の正確性

`w = (T - T_env) / (T_max - T_env)` の線形変換が常に正しい (誤差 < 1e-15)。

### KR-S3: 物理的不変量の遵守 (preregister 済み 6 件)

| # | 不変量 | 内容 |
|---|------|------|
| 1 | monotonicity | input=1 継続中、T は単調増加 (clip 適用前) |
| 2 | positivity | 全時刻で T(t) >= T_env |
| 3 | bounded | clip 適用時、全時刻で T(t) <= T_max |
| 4 | equilibrium | 十分長時間で T → T_eq (clip なし) または T_max (clip あり) |
| 5 | heat-flow direction | input=0 かつ T > T_env で dT/dt < 0 |
| 6 | weight-temperature linearity | 全時刻で w = (T - T_env) / (T_max - T_env) |

### KR-S4: MMS による解析解との一致

SymPy で複数の製造解 (多項式・三角関数・指数関数) を導出し、強制項を逆算。RK4 (dt=0.01) で各製造解との最大誤差 < 1e-6。

### KR-S5: 外部 AI 3 段階による独立検証

Grok 3 段階 + ChatGPT 3 段階 = 6 セットのテストケースを統合。矛盾するテストは halt-and-confirm 発動。統合後、すべての外部 AI 由来テストが pass。

### KR-S6: Rule 8 と Rule 10 の機能確認

完了報告で Rule 8 (必須テンプレート)、Rule 10.5 (3 段階結果)、Rule 10.6 (検知確率 90% KPI) が機能。PRL-001〜PRL-008 の再評価記述を含む。

---

## Sprint 1, 2 との数学的差異の事前列挙 (Sprint 3 開始時セルフチェックリスト)

### 運用方針

このチェックリストは Sprint 2 で発見された「前 Sprint からの implicit 前提持ち込み」(例: Sprint 1 の lower clip テストを連続時間モデルに無批判に持ち込んだ誤設計) の再発防止策。各実装タスク開始時、Halt-and-Confirm 検討時、完了報告作成時に確認する。

---

### 前提 1: 状態変数の primary/secondary

- [ ] T が primary な状態変数であることを意識しているか?
- [ ] w を primary として扱おうとしていないか?
- [ ] `reset()` は T を T_env にリセットする実装になっているか?
- [ ] `update()` は T を進化させる実装になっているか?

### 前提 2: パラメータ数

- [ ] 4 つのパラメータ (heating_rate, cooling_rate, T_env, T_max) をすべて意識しているか?
- [ ] Sprint 2 の α, β の発想で 2 つのパラメータだけを扱おうとしていないか?

### 前提 3: clip の解釈

- [ ] clip を「数学的境界」ではなく「物理的限界」として扱っているか?
- [ ] T_max は素材損傷リスク、T_env は熱力学第二法則という解釈を docstring に明示しているか?

### 前提 4: 解析解の形式

- [ ] 解析解を「指数関数」と決めつけていないか?
- [ ] MMS では複数の製造解 (多項式、三角関数、指数関数) を扱う必要を意識しているか?

### 前提 5: Sprint 1, 2 のテスト構造

- [ ] 「Sprint 1, 2 で書いたテストの構造」を Sprint 3 にそのまま持ち込んでいないか?
- [ ] 例: Sprint 2 の lower clip テストの誤設計 (連続時間で w=0 到達を期待) と同種の前提持ち込みが Sprint 3 で発生していないか?

### 前提 6: 物理的不変量の preregister

- [ ] preregister された 6 つの不変量 (monotonicity, positivity, bounded, equilibrium, heat-flow direction, weight-temperature linearity) すべてを実装で検証する意識があるか?
- [ ] 不変量の検証を「Claude Code が思いついたケース」だけに限定していないか?

---

### 運用上の注意

(1) **形式化のリスク**: チェックリストが「形式的にチェックして OK」にならないよう、各項目について実質的に判断する。

(2) **チェックリスト自体の限界**: チェックリストは「認識している前提」しか防げない。認識していない盲点はチェックリストに含まれないことを認識する (PRL-006, PRL-007 の自己参照ループの限界と同じ)。

(3) **追加項目の可能性**: Sprint 3 中に新たな implicit 前提を発見したら、本チェックリストに追加し、`lab_notebook/potential_risk_log.md` にも PRL-009 以降として記録する。

---

## Sprint Backlog (19 タスク、推定 9-13 時間)

進行は 4 つの checkpoint commit で区切る:
- **Step A** (タスク 0-5): セットアップ、ガイドライン整備
- **Step C** (タスク 6-13): 実装と基本テスト (Robosheep の外部 AI 相談と並行可)
- **Step D** (タスク 15): 外部 AI テスト統合
- **Step E** (タスク 16-18): 可視化、README、完了報告

| # | タスク | 推定 | Step |
|---|------|------|------|
| 0 | pytest.ini の継承 | 5 分 | A |
| 1 | CLAUDE.md に Rule 10 追加 | 15-20 分 | A |
| 2 | CONSTITUTION.md に Commitment 9 追加 | 10-15 分 | A |
| 3 | potential_risk_log.md 作成 (PRL-001〜008) | 30-45 分 | A |
| 4 | Sprint 3 ディレクトリ構造作成 | 10-15 分 | A |
| 5 | SPRINT_OKR.md 作成 | 30-45 分 | A |
| 6 | TemperatureNode クラス実装 | 45-60 分 | C |
| 7 | scenarios.py 拡張 | 20-30 分 | C |
| 8 | analytical.py 実装 | 20-30 分 | C |
| 9 | MMS 実装 (mms.py) | 60-90 分 | C |
| 10 | KR-S1 検証 (Sprint 2 整合性) | 20-30 分 | C |
| 11 | KR-S2 検証 (T↔w 変換) | 15-20 分 | C |
| 12 | KR-S3 検証 (6 不変量 + Hypothesis) | 60-90 分 | C |
| 13 | KR-S4 検証 (MMS 多製造解) | 45-60 分 | C |
| 14 | 外部 AI 3 段階相談 (Robosheep 担当) | - | (parallel) |
| 15 | 外部 AI テストケース統合 | 60-90 分 | D |
| 16 | 可視化 (4 プロット) | 60-90 分 | E |
| 17 | README.md 作成 | 30-45 分 | E |
| 18 | 完了報告 (Rule 8 構造) | 30-45 分 | E |

---

## Out of Scope

### Sprint 1, 2 から継続

1. GUI、対話的可視化、ダッシュボード
2. 設定ファイル (YAML, JSON)、コマンドラインオプション
3. ロギングフレームワーク
4. クラスの継承、抽象クラス
5. 並列処理、GPU 加速、Numba 等の最適化
6. 外部データベース、ファイル I/O 以外の永続化
7. 「より良い」実装としての過剰な refactoring 提案
8. soft saturation 関数 (sigmoid 等) の実装
9. scipy.integrate.solve_ivp 等への依存 (テストでは MMS の検証用途で scipy.integrate を使用可)
10. 適応的時間刻みの実装
11. 複数の入力パターンへの一般化
12. 数値積分の精度に関する高度な分析
13. ContinuousNode と TemperatureNode の統合

### Sprint 3 特有

14. 物理単位 (J、°C、s、Ω、A 等) の導入 → Sprint 7
15. 温度依存の抵抗 R(T) (PTC 効果) → Sprint 4
16. 複数経路 (multi-path) の実装 → Sprint 5
17. 連続値の入力 (PWM 制御等)
18. 時間反転非対称性の検証
19. Mutation Testing (mutmut)
20. AI Debate / Maker-Checker の継続的運用パターン化
21. 熱伝達の詳細物理 (放射、対流、伝導の区別)
22. 連立微分方程式の本格的扱い (Sprint 3 では実質単一変数)

---

## Tripwires (即座に halt-and-review 発動)

1. Constitutional Commitments の違反が発見される
2. 主要な KR (S1-S6) のいずれかが達成困難と判明
3. Sprint 2 との数値的整合性が崩れる (KR-S1 が失敗)
4. 物理的不変量のいずれかが違反される
5. 外部 AI のテストケースが Claude Code の実装と矛盾する
6. MMS の数値解と製造解の誤差が予想外に大きい (1e-6 を大幅に超える)
7. その他、AI が独自判断で進めるべきでないと感じる事態

---

## Definition of Done

20 項目すべて達成:

1. `pytest tests/ -v` で全テストが pass
2. `pytest --junit-xml` で JUnit ログが `results/logs/` に保存
3. `python visualize.py` で 4 プロットが `results/plots/` に生成
4. `flake8 src/ tests/ visualize.py scenarios.py` でエラーなし
5. README.md が KR 達成を証拠付きで記述
6. requirements.txt で全依存が pip freeze 形式で完全固定
7. doctest が pytest 実行時に自動実行
8. .python-version ファイルが作成
9. KR-S1 達成 (Sprint 2 との数値的整合性、誤差 < 1e-15)
10. KR-S2 達成 (T↔w 変換、誤差 < 1e-15)
11. KR-S3 達成 (preregister 6 不変量がすべて成立)
12. KR-S4 達成 (MMS による解析解との一致、誤差 < 1e-6)
13. KR-S5 達成 (外部 AI 3 段階のテストが pass)
14. KR-S6 達成 (Rule 8 と Rule 10 の機能確認)
15. CLAUDE.md に Rule 10 が追加
16. CONSTITUTION.md に Commitment 9 が追加
17. lab_notebook/potential_risk_log.md が作成、PRL-001〜008 の初期エントリー
18. 外部 AI 3 段階相談の結果が `external_ai_responses/` に保存
19. Property-Based Testing (Hypothesis) が 1-2 件試行的に導入
20. Sprint 3 完了報告が Rule 8 の必須テンプレートに従う

---

## 全体の指針

このプロジェクトの北極星は **Mission OKR (PTC 物理 AAS の deterrence-oriented な参照実装)** への貢献。Sprint 3 は KR-M1 (Substrate-Learning Rule Identity) への直接的貢献として、温度変数の導入により「学習則は基板の物理現象そのもの」という主張を実装的に明示する。

外部ベンチマーク (Rule 10、KR-S5) は手段であり目的ではない。手段が目的を圧迫しないよう、北極星 (温度モデルの正しさ) を中心に据える。

リポジトリルートの `CLAUDE.md` (Rule 1〜10) と `CONSTITUTION.md` (Commitment 1〜9) を厳守する。
