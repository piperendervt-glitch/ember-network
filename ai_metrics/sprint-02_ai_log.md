# Sprint 2 AI 利用メトリクス (進行中の下書き)

**Sprint**: Sprint 2 (continuous time and time constants)
**期間**: 2026-05-04 (1 営業日 — 推定 6-9 時間)
**作成者**: Claude Code (下書き) / Robosheep (Sprint Retrospective での確認・補正)
**目的**: Project KR-P5 (AI 支援開発の方法論的知見の生成) のためのデータ収集

CLAUDE.md (Rule 1〜9) で定義された規範について、Sprint 2 の実際の AI 利用を
記録する。Robosheep が Sprint Retrospective で内容を確認・補正する。

このログは Sprint 2 進行中に随時追記される (Sprint 1 の事後一括記録から
パターン変更)。

---

## Sprint 2 で発見した重要な方法論的観察

Sprint 1 では発見できなかった、Sprint 2 特有の発見が複数得られた。これらは
Project KR-P5 の重要なデータポイント。

### 観察 2-1: RK4 が不連続な input_func で精度を失う

**事象**:
- `test_integrators.py::test_kr_s2_cessation_max_error` で max_err = 1.667e-04
  (KR-S2 閾値 1e-6 を 167 倍超過)
- 原因: RK4 が不連続点 t=50 を跨ぐステップで、k1, k2, k3 (input=1) と
  k4 (input=0) を混在させ、4 次精度が崩れる
- 同じシナリオを ContinuousNode + scenarios.py (1 ステップ内で input 固定)
  で実装すると max_err = 5.33e-15 (KR-S2 厳密達成)

**方法論的観察**:
- RK4 が不連続な右辺で精度を失う数値解析的な制約を、Sprint 2 で実装を
  通じて再発見した
- 「ステップ内で input が固定される設計」が Sprint 3 以降の標準パターン
  となる
- これは Sprint 1 (離散時間、自明に step ごとに固定) では発見できない、
  Sprint 2 特有の発見
- input_func を一般的に扱う integrate_euler/integrate_rk4 と、ステップ内で
  input を固定する ContinuousNode の **役割分担** が明確になった

**Sprint 3 以降への示唆**:
- 物理量 (温度、抵抗) を時系列で扱う場合、ステップ境界での値変化を
  scenarios.py 経由で扱うパターンを継続
- integrators.py は「滑らかな input_func」を仮定し、ステップ関数は
  避ける慣行を確立

### 観察 2-2: 連続時間モデル dw/dt = -β·w は w=0 を漸近境界とする

**事象**:
- `test_clip_enabled_caps_at_zero` で `weight = 6.72e-05` (期待値 0.0)
- 10 ステップ input=1 後、10000 ステップ input=0 で weight が 0 に厳密
  到達せず指数的に近づくのみ
- 解析解: w(t) = w_0·exp(-β·t) → 厳密ゼロにならない

**方法論的観察**:
- 連続時間モデル dw/dt = -β·w は w=0 を **漸近境界** とする (吸収境界
  ではない)
- 離散時間モデル (Sprint 1 の `weight - forgetting_rate`) の lower bound
  挙動 (有限時間で 0 到達) と根本的に異なる
- clip の lower 側は連続時間では「数学的に不要だが、float 誤差への
  safety net として残す」という位置づけ
- 物理的により自然なモデルへの進化を示している (Newton 冷却則と同型)

**Sprint 3 以降への示唆**:
- 温度モデル (Newton 冷却則) でも同じ漸近境界が現れる
- テスト設計で「特定値への厳密到達」を要求するのは離散モデル特有のパターン
- 連続モデルでは「不変量の保存」(例: weight >= 0) を検証する方が物理的
- Sprint 1 のテスト設計を Sprint 2 に持ち込んだ際の盲点として記録

### 観察 2-3: Rule 8 (完了報告必須テンプレート) の効果検証

**事象**:
- Sprint 2 開始時に Rule 8 を追加 (Sprint 1 で発見した単純化バイアス対策)
- KR-S1, S2 検証テスト実装段階で 2 件のテスト失敗を発見
- 「テストが pass する」ことに飛びつかず、本質的原因を特定し halt-and-confirm
  で Robosheep の判断を仰いだ

**方法論的観察**:
- Halt-and-Confirm が適切なタイミングで発動: 独自判断で「修正」せずに
  本質的原因 (RK4 不連続限界、連続 vs 離散の lower bound 差異) を特定
- Rule 7 (Halt-and-Confirm) と Rule 8 (単純化バイアス対策) の **相乗効果**
  で、表面的な解決を回避し方法論的価値を最大化
- もし Rule 8 がなければ、テストの許容誤差を緩めて pass させる
  「テスト書き直しによる隠蔽」が起こり得た
- Sprint 1 で経験したパターン Y (動く=正しい) を、Sprint 2 で同等のリスクが
  あった場面で **発動前に阻止** できた

**Project KR-P5 への貢献**:
- Rule 8 の機能確認 (KR-S5 達成証拠の一つ)
- 単純化バイアス対策が機能している実証データ
- 「テスト失敗 → halt-and-confirm → 本質発見 → 適切な修正」のサイクルが
  記録された

---

## 1〜8 (CLAUDE.md L137-145 の標準項目)

### 1. Specification 違反

**Sprint 2 進行中**: 未確定 (現時点 0 件)

詳細は Sprint 完了時に記載。

### 2. Hallucination

**Sprint 2 進行中**: 未確定 (現時点 0 件)

特筆事項: Sprint 1 で発見した単純化バイアスが Rule 8 によって
構造的に予防されているか観察中。

### 3. Scope creep 提案

**Sprint 2 進行中**: 未確定 (現時点 0 件)

### 4. Halt-and-confirm の発動

**Sprint 2 進行中**:

1. **Sprint 2 開始直後の仕様確認 (5 質問)**
   - ContinuousNode のデフォルト integrator と doctest 例の不整合
   - dt のデフォルト値
   - scenarios.py の戻り値仕様
   - KR-S3 の t_clip 検出方法
   - R1 項目の確認
   - Robosheep の回答後、明確な仕様で実装に進めた

2. **テスト失敗時の halt (KR-S1, S2 検証段階)**
   - test_kr_s2_cessation_max_error と test_clip_enabled_caps_at_zero の 2 件失敗
   - 「テスト書き直しで pass にする」ことを選ばず、本質的原因を分析して
     Robosheep に halt-and-confirm を要求
   - 4 つの選択肢 (A/B/C/D) を各失敗について提示
   - Robosheep の判断: 両方とも Claude Code の推奨選択肢を採用

### 5. Negative result の報告

**Sprint 2 進行中**:

- KR-S2 テストが当初の設計で失敗したことを発見・報告 (隠さず)
- lower clip テストの設計ミスを認め、Sprint 1 の発想を Sprint 2 に
  誤って持ち込んでいた認知の偏りを明示
- RK4 の数値解析的制約を「Sprint 2 で再発見した」と Document に記録

### 6. 確信度の明示

**Sprint 2 進行中**:

- 事前計算検証 (w_eq=2.0, τ=20, t_clip=13.86294, 各時点の解析値): 確信度 high
- ContinuousNode 実装の数値検証: 確信度 high (smoke test で事前計算値と
  完全一致)
- RK4 4 次収束性の理論的予測: 確信度 high (古典的数値解析)
- KR-S3 dt=0.01 での t_clip 検出値 13.87: 確信度 high (解析的予測 13.863
  と誤差 0.007、dt 解像度に律速)

### 7. 効果的だった AI 利用パターン

**Sprint 2 進行中**:

#### パターン A (継続): 実装前の事前計算検証
- Sprint 1 で確立したパターン。Sprint 2 でも `w_eq=2.0`, `τ=20`,
  `t_clip=13.8629...`, 各時点の解析値を実装前に手計算
- 結果として ContinuousNode の smoke test が事前予測と完全一致
- **効果**: 実装の正確性を実装前に保証

#### パターン B (新規、Sprint 2 で確立): scenarios.py による役割分担の明確化
- Sprint 1 では visualize/test で重複実装していたシナリオを scenarios.py に
  一元化
- 「ステップ内で input が固定される」物理的に正しいパターンが scenarios.py
  に集約された
- 結果として KR-S2 の不連続点問題が「scenarios.py 経由なら解決」という
  形で構造的に対処された
- **効果**: 設計の正しさが numerical issue を未然に予防

#### パターン F (新規): Halt-and-Confirm + Rule 8 の相乗効果
- テスト失敗を「修正で pass させる」のではなく「本質を理解する」方向に
  導く構造
- Rule 8 (単純化バイアス禁止) が「テストの許容誤差を緩める」誘惑を抑制
- Rule 7 (Halt-and-Confirm) が「独断で修正」を抑制
- 両者の組み合わせで、Robosheep の判断を仰いで方法論的価値を最大化

### 8. 阻害的だった AI 利用パターン

**Sprint 2 進行中**:

#### パターン Z (継続、Sprint 1 から): 仕様の境界例についての事前列挙不足
- Sprint 2 では type 境界 (bool 拒否) を Sprint 1 から継承して対処済み
- しかし「不連続点での RK4 精度低下」は事前に列挙できなかった
- 「数値積分手法の境界条件」という新しい列挙カテゴリが必要

#### パターン W (新規発見): 前 Sprint の発想の過剰持ち込み
- Sprint 1 の lower clip テスト (「いずれ weight=0 になる」) を Sprint 2 の
  連続時間モデルに無批判に持ち込んだ
- 連続 vs 離散の本質的差異を考慮していなかった
- **対策**: Sprint 開始時に「前 Sprint との数学的差異」を意識的に列挙する

---

## Robosheep が判断した修正方針 (Sprint 2 中盤)

| 失敗 | 採用された選択肢 | 理由 |
|------|--------------------|------|
| 1 (KR-S2 cessation) | A: scenarios.py 経由で test_continuous_node.py に移動 | 物理的に正しいパターン、KR-S2 厳密達成、Sprint 3 以降との整合 |
| 2 (lower clip) | B: 「全ステップで weight >= 0」に変更 | 連続時間モデルの数学的性質と整合、安全網としての検証 |

修正後の状況: 29 テスト全 pass、KR-S1, S2 達成 (max error 5.33e-15)。

---

## Sprint Retrospective での評価項目 (Robosheep が記入予定)

Sprint 完了後に Robosheep が記入する。形式は Sprint 1 の log と同様。

---

## 注記

このログは Sprint 2 進行中に随時追記される下書き。
Sprint 完了時に最終版として整理し、Sprint Retrospective で Robosheep が
内容確認・補正する。

---

## 変更履歴

- 2026-05-04 初版 (Sprint 2 中盤、KR-S1/S2 検証完了時点で記録)
  - 観察 2-1, 2-2, 2-3 を記録
  - Robosheep の指示に従い、Project KR-P5 への重要データポイントとして
    位置づけ
