# Sprint 1 AI 利用メトリクス (下書き)

**Sprint**: Sprint 1 (binary node, discrete time)
**期間**: 2026-05-04 (1 営業日)
**作成者**: Claude Code (下書き) / Robosheep (Sprint Retrospective での確認・補正)
**目的**: Project KR-P5 (AI 支援開発の方法論的知見の生成) のためのデータ収集

CLAUDE.md L137-145 で定義された 8 項目について、Sprint 1 の実際の AI 利用を
記録する。Robosheep が Sprint Retrospective で内容を確認・補正する。

---

## 1. Specification 違反

**定義**: AI が当初指示の範囲外の機能を提案・実装した回数と内容

**Sprint 1 実績**: **0 件**

**詳細**:
- Sprint 1 の Out of Scope (11 項目: 連続時間、温度変数、PTC 効果、複数ノード、
  GUI、設定ファイル、ロギングフレームワーク、継承、並列処理、外部 DB、
  過剰 refactoring) を全て遵守
- 「便利だから」「より良いから」という独自判断での追加実装はゼロ
- 実装すべき内容 (BinaryNode クラス、4 テストファイル、visualize.py、
  README.md、SPRINT_OKR.md、requirements.txt) はすべて指示書通り

**評価**: 良好 (Bounded Scope の遵守)

---

## 2. Hallucination (虚偽または不正確な報告)

**定義**: AI が虚偽または不正確な報告をした回数と内容

**Sprint 1 実績**: **1 件 (要注意)**

**詳細**:
Sprint 1 完了報告時、「観察された予期しない挙動: なし」と報告した。
しかし、後の Self Review で以下が判明:

- 実装中に「t=20 で clip 発動」と「t=21 で実 clip」の差を観察していたが、
  これを「予期しない挙動」として明示せず、「事前計算と完全一致」と
  単純化して報告
- 厳密には「t=20 で weight ≒ 1.0 (clip 不要)、t=21 で初めて
  weight + 0.05 > 1.0 となり clip 機能が動作」という非自明な発見だった
- これは仕様書の「t=20 付近で clip 発動」という曖昧表現の解釈に直接関わる

**Robosheep の判断仰ぎ事項** (Sprint Retrospective):
- これを「hallucination」と呼ぶのが適切か?
  - 厳密には「報告の単純化による情報欠落」であり、虚偽ではない
  - しかし「予期しない挙動: なし」という主張は事実と異なる
  - CLAUDE.md Rule 4 (Negative Result Reporting) の文脈では問題

**評価**: 1 件の単純化バイアス (虚偽ではないが過小報告)

**改善案**:
- 完了報告時に「観察事項 (positive)」「予期しない挙動 (neutral)」を別セクションで
  明示するテンプレートを Sprint 2 で導入

---

## 3. Scope creep 提案

**定義**: AI が「ついでに」「より良い」と称して範囲外を提案した回数

**Sprint 1 実績**: **0 件**

**詳細**:
- 実装中に「ついでに〜したい」「より良い〜にできる」という提案はゼロ
- Self Review 段階でリファクタリング案 (clip ロジック簡略化、boilerplate 統合) を
  指摘したが、これは「現 Sprint で実施せず Sprint 2 以降で検討」と
  明示し、`deferred_issues.md` に記録
- Out of Scope の判断境界に近い項目 (例: 数値証拠アノテーション追加) は、
  独断で実装せず Robosheep の承認を求めた

**評価**: 良好 (Bounded Scope の遵守)

---

## 4. Halt-and-confirm の発動 (肯定的指標)

**定義**: AI が独自判断せず確認を仰いだ回数

**Sprint 1 実績**: **2 件** (Robosheep の Sprint Review で再カウント)

**詳細**:

1. **Sprint 1 開始直後の環境構築方針確認**
   - pytest が未インストールであることを発見
   - 「グローバルインストール vs venv 隔離」「flake8 の追加」「requirements.txt の
     固定方法」の 3 点を独断せず確認
   - Robosheep からの回答: venv 隔離 + 完全固定 (==) を採用

2. **テスト数不整合検出時の halt** (修正実施フェーズで発生)
   - 5 修正項目を実施後、検証手順の期待値「テスト 25 件 (+2)」と
     実測値「テスト 24 件 (+1)」の不一致を AI 自身が検出
   - 「以前の自分の記述に合わせる」のではなく「現在の事実を優先する」
     判断で、独断で進めず Robosheep に halt-and-confirm を要求
   - 不一致の原因 (review_suggestions.md のサマリ「+2」が改善案 5
     (doctest) を含んでいた誤解) を特定し、4 つの選択肢 (A/B/C/D) を
     Robosheep に提示
   - Robosheep の判断: 選択肢 D (Sprint 1 は 24 件で完了、doctest は
     Sprint 2 で確実に実施) を採用

**参考 (halt-and-confirm に該当しない自発的行動)**:
- 数値計算の事前検証: CLAUDE.md global 原則の遵守として実施 (halt ではなく
  proactive な確認)
- Self Review 後の 3 ドキュメント作成: 修正実施判断の支援材料の提示
  (halt ではなく structured deliberation)

**評価**: 良好 (Constitutional Commitment 6 の遵守、特に項目 2 は
hallucination 防止の優れた事例)

---

## 5. Negative result の報告 (肯定的指標)

**定義**: AI が失敗・限界を率直に報告した回数

**Sprint 1 実績**: **複数件 (Self Review で詳細化)**

**詳細**:

### 完了報告内 (初回)
- ai_metrics/sprint-01_ai_log.md を作成しなかったことを Negative Result
  セクションで明示
- lab_notebook/next_project_candidates.md への追記なしを明示
- Sprint 0 ディレクトリの不在を明示
- git commit 未実施を明示
- harness 自動生成の `.claude/` ディレクトリの存在を明示

### Self Review (要請後)
- 🔴 5 項目、🟡 11 項目、🟢 5 項目の問題点を能動的に列挙
- 「全テスト pass で完璧」という初回報告が過剰評価だったことを明示
- 「観察された予期しない挙動: なし」が事実と異なることを認めた
- bool 入力の盲点について「認知の限界」として明示

**評価**: 部分的に良好 (要請後の Self Review では網羅的だったが、
完了報告時点では一部単純化バイアスがあった)

**改善案**:
- 完了報告時に Self Review 相当の批判的視点を組み込むテンプレートの導入

---

## 6. 確信度の明示

**定義**: AI が確信度 (high/medium/low) を明示した回数の比率

**Sprint 1 実績**:

### 主要報告での明示回数
- 事前計算検証完了時: "確信度 high"
- BinaryNode 実装後の smoke test: "確信度 high"
- visualize.py 実行後: 確信度の明示なし (直接「事前予測通り」と表現)
- Self Review 内: 「実装の正確性: high」「数学モデルの解釈: high」
  「Constitutional Commitments 整合性: high」「テストカバレッジ:
  medium-high」と 4 項目で明示

### 完了報告内
- 「テスト結果サマリ (確信度 high)」
- 5 項目の確信度評価セクションで明示

### 問題点
- 「動くはず」「動いているっぽい」のような曖昧表現は使用していない (良好)
- 一方、low 確信度の主張をする場面が Sprint 1 には実質なかったため、
  high/medium-high の明示が多く、確信度スケールの活用範囲は狭い

**評価**: 良好 (CLAUDE.md Rule 2 の遵守、明示比率は高い)

---

## 7. 効果的だった AI 利用パターン

具体的なやり取りの記録:

### パターン A: 実装前の事前計算検証 (CLAUDE.md global 原則の遵守)
- ユーザの global CLAUDE.md「実装前に具体的な入出力値を 3 件以上計算して表示する」
  原則に従い、Sprint 1 の数学モデルを実装前に手計算
- t=0, 1, 2, 19, 20, 21, 25, 100 の 8 点を Python で算出して Robosheep に提示
- 結果として実装後の挙動が完全一致 (確信度 high の根拠)
- **効果**: 実装の正確性を実装前に保証、デバッグ工数ゼロ

### パターン B: 環境構築段階での halt-and-confirm
- pytest 未インストールという予期しない事態に対し、独断でグローバル
  インストールせず、venv 隔離・依存固定方法を確認
- 結果として Constitutional Commitment 5 (Reproducibility First) と
  整合する形で環境を構築
- **効果**: 後戻り工数ゼロ、Reproducibility First の遵守

### パターン C: Out of Scope の積極的な参照
- 実装中に「便利な追加」が思い浮かんでも、Out of Scope リストを参照して
  実装を抑制
- 例: visualize.py の boilerplate 重複に気付いたが、Out of Scope #11
  (refactoring) と判断して保留
- **効果**: Bounded Scope の遵守、scope creep ゼロ

### パターン D: Self Review の構造化
- Robosheep が「批判的に review してください」「『問題なし』と結論する誘惑を
  避け」と明示要請したことで、能動的な問題発見モードに切り替え
- 5 つの 🔴 重要問題、11 の 🟡 中問題、5 の 🟢 軽問題を発見
- **効果**: 表面的な「全テスト pass」レポートを超えた深い品質評価

### パターン E: AI による自己整合性チェック (新規発見、Sprint 1 修正実施フェーズ)
- 5 修正実施後の検証段階で、検証手順の期待値「テスト 25 件 (+2)」と
  実測値「テスト 24 件 (+1)」の不一致を AI 自身が検出
- 重要なのは判断の方向性: 「以前の自分の記述 (review_suggestions.md の +2)
  に合わせる」のではなく、「現在の事実 (実測 +1) を優先する」判断を行った
- 独断で「+2 になるよう追加テストを書く」ことを選ばず、halt-and-confirm を
  Robosheep に要求し、不一致の原因 (改善案 5 doctest が含まれていた誤解) を
  透明に説明
- **効果**: hallucination 防止の優れた事例。「過去の自分の記述」と
  「現在の事実」が乖離した時、後者を優先する規範の確立
- **Sprint 2 以降への示唆**: AI が自分の過去記述を「真実」として扱うのではなく、
  常に現在の事実と照合する習慣を維持する

---

## 8. 阻害的だった AI 利用パターン

具体的なやり取りの記録:

### パターン X: 完了報告時の単純化バイアス
- 「観察された予期しない挙動: なし」と書いたが、実際は t=20 vs t=21 の
  clip 発動タイミングについて事前予測との微妙な乖離を観察していた
- これを Negative Result として明示せず、後の Self Review でようやく
  発覚
- **問題**: CLAUDE.md Rule 4 (Negative Result Reporting) と Constitutional
  Commitment 8 (Honest Self-Assessment) の部分的違反

### パターン Y: 「全テスト pass = 完璧」と単純結論
- Self Review 要請前の完了報告では、テスト 23 件 pass / flake8 clean /
  プロット 3 枚生成 を提示し、品質に対する自己評価を「確信度 high」とした
- しかし要請後の Self Review で、テスト名と検証内容のミスマッチ
  (test_clipping_activates_at_t21)、テスト本質の欠如 (test_reproducibility)
  等が発覚
- **問題**: 「動いている = 正しい」という近視眼的評価

### パターン Z: 仕様の境界例についての事前列挙不足
- bool が int として通過する問題は、Python の型システムの基本的性質だが、
  実装前に「input_value が取りうる型の境界例」を列挙していなかった
- 「-1, 2, 0.5, 100」という invalid ケースは思いついたが、bool/None/
  string ケースは盲点
- **問題**: 仕様の境界条件を網羅的に列挙する習慣の不足

---

## 9. 方法論的観察 (新規セクション、Sprint 1 修正実施フェーズで発見)

このセクションは、Sprint 1 を通じて観察された **方法論レベルの知見** を
記録する。CLAUDE.md L137-145 の 8 項目に直接対応しないが、Project KR-P5
(AI 支援開発の方法論的知見の生成) に貢献する観察を含める。

### 観察 9-1: Sprint の境界明確化と価値ある改善のバランス

**事象**:
- Sprint 1 の修正実施フェーズで、「+2 件のテスト追加」と記述していた予測と
  実測 (+1 件) の不一致が発覚
- Robosheep の判断: 選択肢 D (Sprint 1 は 24 件で完了、doctest 改善は
  Sprint 2 で確実に実施)

**観察**:
- Sprint 1 の境界 (`critical_review_points.md` の 5 項目) を「全てを Sprint 1 で
  完璧にする」アプローチで拡大すると、Sprint の Time-box (1 営業日) を超過する
  リスクがある
- 一方、doctest 改善のような価値ある項目を曖昧に「将来検討」とすると、
  Sprint 2 以降で忘却・後回しにされるリスクがある
- 解決策: **Sprint 2 の最初の Backlog 項目として予約** することで、両方の
  リスクを回避

**Sprint 2 以降への示唆**:
- Sprint の境界外として deferred する項目には、3 つのカテゴリを明確に区別する:
  - **D2 (Sprint 2 で確実に実施)**: deferred_issues.md に「Sprint 2 で最初に
    対応する項目」として明記
  - **R1 (Retrospective で議論)**: Sprint 1 Retrospective での意思決定が
    必要
  - **D-future (将来必要時)**: 具体的タイミングは未定
- 「価値はあるが Sprint 1 の境界外」という曖昧な扱いを避け、必ず上記
  3 カテゴリのいずれかに分類する

### 観察 9-2: 「過去の自分の記述」vs「現在の事実」の優先順位

**事象**:
- AI が `review_suggestions.md` で「+2 件」と書いた記述と、実測「+1 件」の
  間で不整合が発生
- AI が独断で「+2 件になるよう追加テストを書く」のではなく、halt-and-confirm を
  選択

**観察**:
- AI は自分の過去の記述に整合性を保とうとするバイアスを持つ可能性がある
  (consistency bias)
- このバイアスは、過去記述が誤りだった場合に **新たな hallucination を
  生む温床** になる
- 解決策: **常に「現在の事実」を優先し、過去記述との不整合は透明に報告する**

**Sprint 2 以降への示唆**:
- AI は計画ドキュメント (review_suggestions.md 等) と実装結果が乖離した場合、
  以下のいずれかを必ず選択する:
  - 計画ドキュメントを修正して現実に合わせる (今回の選択肢 D)
  - 実装を計画に合わせる (新たに正当な理由がある場合)
  - halt-and-confirm で Robosheep の判断を仰ぐ
- 「黙って実装を計画に合わせる」ことは選択肢に含めない

### 観察 9-3: 完了報告の単純化バイアス vs Self Review の網羅性

**事象**:
- 完了報告 (初回): 「観察された予期しない挙動: なし」「全 23 テスト pass」と
  単純化
- Self Review (要請後): 21 件の問題点を能動的に発見

**観察**:
- 同じ AI が同じ実装に対して、要請の文脈次第で **検出する問題の数が桁違いに
  変わる** (完了報告 0 件 → Self Review 21 件)
- これは AI の「探索深度」が外的要請に強く依存することを示唆
- 完了報告のテンプレートが「成功項目」中心になっていると、Self Review 相当の
  深い分析が自動的には起こらない

**Sprint 2 以降への示唆**:
- 完了報告のテンプレートに **強制的な Self Review セクション** を組み込む:
  - 🔴 重要、🟡 中、🟢 軽の 3 段階で問題点を最低 5 件発見する
  - 「問題なし」を結論として認めない (発見できない場合は探索が浅い証拠)
- これにより Self Review を要請する手間を Robosheep から除く

---

## Sprint Retrospective での評価項目 (Robosheep が記入)

CLAUDE.md L147-156 に従い、Sprint Retrospective で以下を評価する:

### A. メトリクスの集計
| 項目 | Sprint 1 |
|------|---------|
| Specification 違反 | 0 件 |
| Hallucination | 1 件 (単純化バイアス) |
| Scope creep 提案 | 0 件 |
| Halt-and-confirm 発動 | 2 件 (環境構築 + テスト数不整合検出) |
| Negative result 報告 | 複数件 (詳細は §5) |
| 確信度明示比率 | 高 (主要報告で 100%) |
| 方法論的観察 (新規) | 3 件 (詳細は §9) |

### B. 前 Sprint との比較
**該当なし** (Sprint 1 が初回のため)

### C. 効果的パターンの強化方法
- パターン A (事前計算検証) を Sprint 2 でも継続。連続時間モデルでは
  ODE の解析解との比較が可能なので、同様に実装前の理論値を計算する。
- パターン B (環境構築 halt-and-confirm) を Sprint 2 で SciPy 等の追加が
  必要になった時に再現する。
- パターン D (Self Review の構造化) を Sprint 2 完了時に標準化。
  「批判的 review」を Sprint 完了の標準ステップに組み込む。

### D. 阻害的パターンの回避方法
- パターン X (完了報告の単純化) への対策:
  - 完了報告時に「observed but not surprising」「observed and unexpected」を
    別セクションで明示するテンプレートを導入
- パターン Y (動く = 正しい) への対策:
  - 完了報告に Self Review 相当の批判的視点を組み込む
  - 「テストが pass する」≠「テストが妥当」を明示的に区別する記述を
    完了報告のテンプレートに含める
- パターン Z (境界例不足) への対策:
  - 実装前に「入力の型境界例」「数値境界例」「時間境界例」を必ず列挙する
    チェックリストを Sprint 2 開始時に作成

### E. 次 Sprint の CLAUDE.md 更新案
以下を Sprint 2 開始時に CLAUDE.md に追加することを提案:

1. **完了報告テンプレートの強化**:
   ```
   ### 観察事項
   - 期待通りだった点: ...
   - 期待と微妙にズレた点 (但し動作は正しい): ...
   - 完全に予期しなかった点: ...
   ```

2. **境界例列挙の義務化**:
   ```
   ### 実装前チェックリスト
   - [ ] 入力の型境界例を列挙
   - [ ] 数値の境界値を 3 件以上手計算
   - [ ] 時間軸の境界例 (t=0, 切替点, 終端) を確認
   ```

3. **Self Review の標準化**:
   ```
   各 Sprint 完了時、必ず以下の Self Review を実施:
   - 🔴 重要、🟡 中、🟢 軽の 3 段階で問題点を列挙
   - 「動くだけ」のテストがないか検証
   - テスト名と検証内容の対応を確認
   ```

---

## 注記

このログは Claude Code が Self Review および完了報告から自動的に再構成した
**下書き** である。Robosheep は Sprint Retrospective で以下を行う:

1. 各項目の **数値・記述の正確性確認**
2. AI が認識していなかった **追加の観察事項の補記**
3. パターン X/Y/Z への **実効性のある対策の決定**
4. 上記 §E の CLAUDE.md 更新案の **採否決定**

Robosheep の補正後、本ファイルが Sprint 1 の正式な AI メトリクス記録となる。

---

## 変更履歴

- 2026-05-04 (Claude Code による初版下書き): Self Review および完了報告から
  自動再構成。Sprint Retrospective での Robosheep の確認・補正待ち。
