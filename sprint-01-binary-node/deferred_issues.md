# Deferred Issues: Sprint 1 で対応しない項目

Self Review で 🟡 中、🟢 軽として指摘した項目のうち、Sprint 1 では
対応せず Sprint 2 以降で扱うか、または永続的に Out of Scope と
すべきものを整理する。

各項目について **対応分類 → 据置きの理由 → Sprint 2 以降での扱い** を記述。

---

## 分類凡例

- **D2 (Defer to Sprint 2+)**: Sprint 2 以降の実装内で自然に再検討される
- **D-future (Defer indefinitely)**: 将来 Sprint で必要になれば対応、現時点では不要
- **OOS (Out of Scope)**: 本プロジェクトの範囲外として永続的に扱わない
- **R1 (Re-evaluate at Retrospective)**: Sprint 1 Retrospective で議論する

---

## `src/binary_node.py` 関連

### 🟡 中: clip ロジックのコード重複

**所在**: L83-86
```python
if new_weight < 0.0:
    new_weight = 0.0
elif new_weight > 1.0:
    new_weight = 1.0
```

**対応分類**: D2

**据置きの理由**:
- Sprint 2 で連続時間モデル化する際、clip の扱いは完全に再設計される
  (例: 物理的には連続的な飽和カーブで表現される可能性)
- 現実装は動作上問題なく、`max(0.0, min(1.0, ...))` への変更は
  「より良い書き方」だが機能的価値はゼロ
- Out of Scope #11「過剰な refactoring」に近い

**Sprint 2 以降での扱い**:
- Sprint 2 でモデル全体を ODE ベースに書き換える際、clip ロジックも
  一緒に再設計する。その時点で `np.clip` または `max/min` のどちらが
  適切か判断する。

---

### 🟡 中: NumPy スタイル docstring の不正確な使用

**所在**: L19, L24
- 「数学モデル」「物理的解釈」セクションは NumPy 標準のセクション名ではない
- セクション underline の長さが不揃い

**対応分類**: D2 (規約として Sprint 2 で確定)

**据置きの理由**:
- 動作には影響なし
- Sphinx + napoleon でドキュメント生成する予定が現時点で確定していない
  (Mission KR-M4 の Open Hardware 公開に必要かは未定)
- 修正方針 (Notes に統合 vs カスタムセクション維持) の判断には
  プロジェクト全体での docstring スタイル方針が必要

**Sprint 2 以降での扱い**:
- Sprint 2 で同等の docstring を書く際、以下のいずれかを統一:
  - **方針 A**: 「数学モデル」「物理的解釈」を `Notes` セクションに統合
    (NumPy 標準準拠)
  - **方針 B**: カスタムセクションを維持し、Sphinx 設定でカスタムセクションを
    認識させる (`napoleon_custom_sections` 設定)
- どちらの方針かを Sprint 2 開始時に決め、Sprint 1 のコードもそれに
  合わせて遡及修正する

---

### 🟢 軽: パラメータ validation がない

**所在**: L54-58 (`__init__`)
- `learning_rate < 0`, `forgetting_rate < 0` 等の異常値を黙って受け入れる

**対応分類**: D-future

**据置きの理由**:
- Sprint 1 の Out of Scope #11「過剰な validation」に該当する判断
- 現実装で異常値を入れるのは意図的な実験 (例: 負の学習率の挙動を見る) で
  あり、validation を入れるとそういう実験が阻害される
- Sprint 7 (物理パラメータ校正) で物理的に意味のある範囲が確定した際、
  validation を入れる必要があれば対応

**Sprint 2 以降での扱い**:
- Sprint 7 で物理パラメータの妥当範囲が確定した時点で再評価
- それまでは validation なしで進める

---

## テストファイル関連

### 🟡 中: `test_update_increments_weight_with_input_one` が定性的すぎる

**所在**: `tests/test_basic.py` L41-46

**対応分類**: D-future (削除候補)

**据置きの理由**:
- 「input=1 で weight が増加」は他のテスト (test_default_parameters,
  test_constant_input.py 全体) で定量的にカバー済み
- 削除しても KR-S1/S2 達成判定に影響なし
- ただし API レベルの sanity test として残す価値はある

**Sprint 2 以降での扱い**:
- Sprint 2 で BinaryNode を継続使用する場合、削除を検討
- Sprint 2 で別クラス (例: ContinuousNode) になる場合、test_basic.py 全体が
  リプレースされるため自動的に解消

---

### 🟡 中: `test_invalid_input_raises_value_error` のカバレッジ不足

**所在**: `tests/test_basic.py` L75-80

**注**: `review_suggestions.md` の改善案 1 で対応する
(bool, None, "1" を追加する)。
本ドキュメントでは追加の懸念のみ記述:

- `0.0` (float の 0)、`1.0` (float の 1) のケース
  - 現実装では `0.0 in (0, 1) == True` なので **通る**
  - 仕様「int で 0 または 1」を厳格解釈すると拒否すべきだが、実装は許容
  - これは bool 拒否とセットで検討すべきだが、改善案 1 では float 受け入れを
    明示的に拒否しない方針 (0.0 や 1.0 を渡す可能性は低いと判断)

**対応分類**: D2

**Sprint 2 以降での扱い**:
- Sprint 2 で input 型が `int → float` に拡張される時、float の 0/1 の
  扱いが自然に再定義される
- それまでは現状維持

---

### 🟢 軽: `test_constant_input.py` の t=20 重複検証

**所在**: `tests/test_constant_input.py`
- L32-39 (`test_weight_reaches_one_at_t20`) で t=20 検証
- L42-48 (`test_weight_is_stable_at_one_from_t20_to_t100`) でも t=20 を含む

**対応分類**: OOS (修正不要)

**据置きの理由**:
- 重複検証は冗長だが、テストの読みやすさを優先する設計判断として許容範囲
- 1 つの assertion を 2 箇所から呼ぶことのコストは無視できる
- どちらかを削除するとテストの意図 (「到達」と「安定」を区別する) が
  曖昧になる

---

### 🟢 軽: `test_decay_increment_per_step` の境界条件分岐の脆弱性

**所在**: `tests/test_input_cessation.py` L80-88
- `if trajectory[t - 1] > 0.05:` の閾値判断が float 誤差で揺らぐ可能性

**対応分類**: D2

**据置きの理由**:
- 現実装では float 誤差を考慮しても境界値は「明らかに > 0.05」または
  「明らかに ≤ 0.05」のどちらかになり、誤動作しない (実測確認済み)
- ただし可読性は低く、Sprint 2 で連続時間モデルになった際は同じパターンを
  使えない (clip タイミングが Δt に依存するため)

**Sprint 2 以降での扱い**:
- Sprint 2 で同様のテストを書く際、境界条件の分岐ではなく
  「expected = max(0, ...) で計算した理論値との比較」に書き換える

---

## `visualize.py` 関連

### 🟡 中: `"Clipping starts (t=20)"` アノテーションが厳密には不正確

**所在**: `visualize.py` L102-107

**対応分類**: R1 (Sprint 1 Retrospective で議論)

**据置きの理由**:
- 厳密には clip は t=21 で発動するが、視覚的に weight が 1.0 に達するのは
  t=20
- 「視覚的直感性」と「厳密性」のトレードオフ
- Constitutional Commitment 8 (Honest Self-Assessment) との緊張があるが、
  「視覚化の文脈では多少の簡略化が許容される」という解釈もある

**Sprint 1 Retrospective での議論項目**:
- プロットアノテーションの厳密性をどこまで求めるか?
- 案 A: アノテーションを t=21 に修正
- 案 B: 「Clipping starts (t≈20)」のように波線を使う
- 案 C: 現状維持 (視覚的直感性を優先)
- 案 D: 「Saturation reached (t=20)」のように clip 言及を避ける

判断基準の確定が Sprint 2 以降のプロット品質基準になる。

---

### 🟡 中: `run_with_seed` のグローバル状態副作用

**所在**: `visualize.py` L58-62

**対応分類**: D2

**据置きの理由**:
- visualize.py 内では問題が顕在化しない
- Sprint 1 のテスト構造ではテスト間のシード状態漏れが問題になっていない
- 厳密な隔離 (context manager 化) は Sprint 6-7 で確率要素を入れた時に
  必要になる

**Sprint 2 以降での扱い**:
- Sprint 6 (AAS 動作シミュレーション) で確率的個体差を入れる時、以下の
  パターンに統一:
  ```python
  from contextlib import contextmanager

  @contextmanager
  def seeded_state(seed):
      py_state = random.getstate()
      np_state = np.random.get_state()
      random.seed(seed)
      np.random.seed(seed)
      try:
          yield
      finally:
          random.setstate(py_state)
          np.random.set_state(np_state)
  ```
- Sprint 6 でこのパターンが確立したら、Sprint 1 のコードに遡及適用するかを
  判断

---

### 🟡 中: visualize と test の間のロジック重複

**所在**:
- `tests/test_constant_input.py::_run_constant_input`
- `tests/test_input_cessation.py::_run_cessation_scenario`
- `visualize.py::run_constant_input`
- `visualize.py::run_input_cessation`

**対応分類**: D2

**据置きの理由**:
- 共有モジュール (`src/scenarios.py` 等) への抽出は「便利な refactoring」で
  Sprint 1 Out of Scope #11 に該当
- 4 箇所の実装が「同じシナリオを表現している」ことが明示されていれば、
  重複自体は許容範囲

**Sprint 2 以降での扱い**:
- Sprint 2 で連続時間モデル化により、シナリオ実行ロジックが大きく変わる
- Sprint 2 で `src/scenarios.py` を新設し、シナリオ定義を一元化する
  ことを検討 (Sprint 2 の Sprint OKR で明示的に決める)

---

### 🟢 軽: `set_ylim(-0.05, 1.1)` の説明なし

**所在**: `visualize.py` L112, L159, L198

**対応分類**: OOS (修正不要)

**据置きの理由**:
- プロット見やすさのための慣用的な値設定
- コメントを追加すると逆にノイズになる

---

### 🟢 軽: 3 plot 関数の boilerplate 重複

**所在**: `visualize.py` の 3 つの `plot_*` 関数

**対応分類**: D2

**据置きの理由**:
- ヘルパー関数化は Out of Scope #11 (refactoring) に近い
- 重複量は小さく、各関数の独立性が高い (個別に修正しやすい)

**Sprint 2 以降での扱い**:
- Sprint 2-3 でプロット数が 5 個以上に増えた時点で、`_setup_axes` 等の
  ヘルパー抽出を検討

---

## 全体関連

### 🟡 中: Python バージョンが固定されていない

**所在**: なし (`.python-version` や `pyproject.toml::requires-python` 不在)

**対応分類**: R1 (Sprint 1 Retrospective で議論)

**据置きの理由**:
- `requirements.txt` で全パッケージ固定済み
- README.md に「Python 3.12.10」を明記済み (人間が読める形での記録)
- ただし機械的強制 (例: `python -m venv` 時の version check) はない

**Sprint 1 Retrospective での議論項目**:
- どの強制方法を採用するか:
  - 案 A: `.python-version` (pyenv 用)
  - 案 B: `pyproject.toml` の `requires-python = ">=3.12,<3.13"`
  - 案 C: README.md の記載のみ (現状)
- Sprint 2 開始時に決定

---

### 🟡 中: harness 自動生成 `.claude/` ディレクトリ

**所在**: `sprint-01-binary-node/.claude/`

**対応分類**: R1

**据置きの理由**:
- Claude Code が自動生成したディレクトリで、私 (Claude Code) が
  操作したわけではない
- 中身が project local の Claude Code 設定か、ephemeral state かが
  Robosheep 側で確認が必要
- `.gitignore` への追加可否は Robosheep の判断

**Sprint 1 Retrospective での議論項目**:
- `.claude/` を `.gitignore` に追加するか
- それとも commit して全 Sprint で共有するか

---

### 🟢 軽: `SPRINT_OKR.md` の Backlog と DoD の重複

**所在**: `SPRINT_OKR.md` の Sprint Backlog テーブルと Definition of Done

**対応分類**: OOS (修正不要)

**据置きの理由**:
- 重複は意図的: Backlog は「何をするか」のリスト、DoD は「完了の判断基準」
- 視点が異なるため重複していてもよい

---

### 🟢 軽: `README.md` の「学んだこと」が長文

**所在**: `README.md` の「学んだこと」セクション

**対応分類**: OOS (修正不要)

**据置きの理由**:
- Sprint 完了時のドキュメントは、CLAUDE.md Rule 8 の「簡潔さ」が
  そのまま適用される対象ではない (会話応答ではなく documentation)
- Sprint 2 以降の参照価値を考慮すると詳細な記述が望ましい
- ただし冗長な箇条書きを統合する余地はある

---

## まとめ表

| 対応分類 | 件数 | 内訳 |
|---------|------|------|
| D2 (Sprint 2 で対応) | 7 | clip 冗長、docstring スタイル、test 弱体 ×2、 cessation 境界、global state、ロジック重複 |
| D-future (将来必要時) | 2 | パラメータ validation、定性テスト削除 |
| R1 (Retrospective) | 3 | clipping アノテーション、Python バージョン、`.claude/` |
| OOS (永続的に対応せず) | 4 | t=20 重複、ylim 説明、boilerplate、DoD 重複、長文 README |

**合計 16 項目**

---

## Sprint 2 で最初に対応する項目 (Sprint 2 Sprint Backlog の予約)

### doctest 実行の有効化

- **出典**: `review_suggestions.md` 改善案 5
- **推定工数**: 5 分
- **実施タイミング**: Sprint 2 の本格実装 (連続時間モデル) 開始前
- **実施方法**: `pytest.ini` に `--doctest-modules` を追加 (推奨)
  または `tests/test_doctest.py` を作成
- **効果**: Sprint 2 以降のコードでも doctest 検証が自動化される
- **根拠**: docstring の Examples セクションが「動かないテスト」として
  残ることを防ぐ。Constitutional Commitment 5 (Reproducibility First)
  および Mission KR-M4 (Open Hardware) との整合。

これは Sprint 1 終了後、Sprint 2 Planning 時に再判断する性質ではなく、
**Sprint 2 で確実に実施する予約** として位置づける。

経緯:
- Self Review で 🔴 として指摘された 5 項目のうち 4 項目 (bool, clip テスト,
  reproducibility テスト, plot 数値証拠) は Sprint 1 内で修正実施
- 5 項目目 (ai_metrics 作成) も Sprint 1 で実施
- doctest 改善は当初 `review_suggestions.md` のトップ 5 改善案には含まれて
  いたが、`critical_review_points.md` の 5 項目 (= Robosheep が修正実施を
  指示した範囲) には含まれず、Sprint 1 の境界外
- Sprint 1 の境界を明確に保つため、本予約として Sprint 2 に持ち越し

---

## Sprint 2 開始時に再評価が必要な項目

以下は Sprint 2 開始時の Sprint OKR レビューで明示的に意思決定する:

1. **Python バージョン固定方法** (案 A/B/C)
2. **docstring スタイル** (NumPy 標準 vs カスタムセクション維持)
3. **共有モジュール `src/scenarios.py` の新設可否**
4. **`.claude/` ディレクトリの commit/ignore 方針**
5. **プロットアノテーションの厳密性ポリシー**

これらは Sprint 1 Retrospective で議論し、Sprint 2 Sprint OKR の
冒頭で確定させる。
