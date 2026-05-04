# Critical Review Points: Sprint 1

Self Review で 🔴 重要として指摘した 5 項目について、Robosheep が
diff review・修正可否判断を行うための材料を整理する。

各項目は **問題所在 → 影響 → 修正案 → 据置きの理由 → 推奨判断** の形式で記述。

---

## 項目 1: `update()` で bool が int として通過する

### 問題の正確な所在

- ファイル: `src/binary_node.py`
- 行番号: L74
- 該当コード:
  ```python
  if input_value not in (0, 1):
      raise ValueError(...)
  ```
- 該当テスト: `tests/test_basic.py` L75-80 (`test_invalid_input_raises_value_error`)
  - bool ケース (`True`, `False`) を検証していない

### 問題の本質

Python の `bool` は `int` のサブクラスであり:
- `True == 1` (True)
- `False == 0` (True)
- `True in (0, 1)` (True、`1 in (0, 1)` と等価)
- `False in (0, 1)` (True)

したがって `node.update(True)` は ValueError にならず、`1` として処理される。
仕様書「input_value: int」「0 または 1」に bool を含めるか否かの定義がなく、
**現実装はサイレントに bool を許容している**。

### 影響範囲

**Sprint 1 内:**
- 直接的な機能不全はない (bool が int として扱われるため、計算結果は正しい)
- ただしテストカバレッジに穴があり、KR-S1 / KR-S2 / KR-S3 の達成判定には影響なし

**Sprint 2 以降への影響:**
- Sprint 2 で `input` が連続値 (例: 電流量 [A]) になる場合、型ガードが
  甘いと「真偽値が物理量として誤って渡される」というバグの温床になり得る
- Sprint 6 の AAS 動作シミュレーションで `input` を array に拡張する際、
  `True` 等の混入を検出できないと観測値の sanity check が困難
- Constitutional Commitment 8 (Honest Self-Assessment) の観点から、
  「実装の境界条件が未定義」状態を Sprint 1 で固定化するのは技術的負債

### 修正する場合の具体的変更内容

```python
# src/binary_node.py L73-77
def update(self, input_value: int) -> None:
    if isinstance(input_value, bool) or input_value not in (0, 1):
        raise ValueError(
            f"input_value must be 0 or 1 (not bool), got {input_value!r}"
        )
    ...
```

`tests/test_basic.py` の `test_invalid_input_raises_value_error` に
bool ケースを追加:
```python
for invalid in (-1, 2, 0.5, 100, True, False):
    with pytest.raises(ValueError):
        node.update(invalid)
```

### 修正しない場合の理由

- Sprint 1 の Out of Scope #11「過剰な validation」と解釈する余地がある
- 仕様書には bool 拒否の明示要求がない
- 実害は現時点でゼロ

### 推奨判断

**修正する** (Sprint 1 内)

理由:
- 修正コストは 2 行の変更 + テスト 2 ケース追加のみ (推定 5 分)
- 仕様書の曖昧さを **Sprint 1 の Sprint Review で確定** することで、
  Sprint 2 以降の input 型拡張時の判断基準が固定化される
- Constitutional Commitment 5 (Reproducibility First) は「結果の再現」だけでなく
  「型と境界条件の明示」も含むと解釈できる

---

## 項目 2: `test_clipping_activates_at_t21` の名前と検証内容のミスマッチ

### 問題の正確な所在

- ファイル: `tests/test_constant_input.py`
- 行番号: L51-58
- 該当コード:
  ```python
  def test_clipping_activates_at_t21():
      """t=21 で実際に clip 機能が発動 (1.0 + 0.05 → 1.0 に切り詰め)。

      t=20 では (1.0 - ε) であり厳密には clip 不要、t=21 で初めて
      weight + 0.05 > 1.0 となり clip が発動する。
      """
      trajectory = _run_constant_input(100)
      assert trajectory[21] == 1.0
  ```

### 問題の本質

テスト名と docstring は「**clip 機能が発動した**」ことの検証を主張している。
しかし実際の assertion は「**t=21 で weight が 1.0**」のみ。

これは `weight + 0.05 > 1.0 → clip により 1.0 になった` ことと、
`weight が単に 1.0 だった (clip 不要)` ことを **区別できない**。

つまり:
- 仮に clip 機能を削除しても、t=20 で weight ≒ 1.0 → t=21 で weight = 1.05 になり
  このテストは fail する (検出はできる)
- しかし、もし t=20 で偶然 weight = 1.0 ぴったりになるような実装に変更されたら、
  clip ロジックが壊れていてもテストは pass する

検証の **意図** (clip 機能の動作確認) と **実装** (単一値の比較) が乖離。

### 影響範囲

**Sprint 1 内:**
- 現実装ではテストは pass する (機能的には KR-S1 達成判定に貢献)
- しかしテストの「意味論的妥当性」が低い

**Sprint 2 以降への影響:**
- 連続時間モデルでは clip タイミングが Δt に依存する
- Sprint 2 で同じパターン (テスト名と検証内容の乖離) を繰り返すと、
  「テストが pass しているのに実装が壊れている」状態が発生し得る
- テスト設計の規範として Sprint 1 で正したい

### 修正する場合の具体的変更内容

`test_clipping_activates_at_t21` を、clip 機能を直接検証する形に変更:

```python
def test_clipping_prevents_overflow():
    """weight が 1.0 に到達後、追加の input=1 でも 1.0 を超えない (clip 機能の検証)。

    weight = 1.0 の状態で update(1) を呼ぶと、clip がなければ
    weight = 1.05 になるはず。clip により 1.0 にスナップされることを確認する。
    """
    node = BinaryNode()
    for _ in range(20):
        node.update(1)
    # この時点で weight ≒ 1.0 (誤差 < 1e-10)
    assert abs(node.weight - 1.0) < 1e-10

    node.update(1)  # clip がなければ weight + 0.05 = 1.05 になるはず
    assert node.weight == 1.0  # 厳密に 1.0 (clip により切り詰め)
```

### 修正しない場合の理由

- 実害なし (現実装では pass する)
- 「テスト名は飾り」と割り切れば動く

### 推奨判断

**修正する** (Sprint 1 内)

理由:
- テスト品質の規範を Sprint 1 で固定化する重要性
- 修正コストはテスト 1 件の書き換えのみ (推定 5 分)
- 「テスト名と検証内容の対応」は Constitutional Commitment 8
  (Honest Self-Assessment) の延長線上にある

---

## 項目 3: `test_reproducibility.py` が KR-S3 の本質を検証していない

### 問題の正確な所在

- ファイル: `tests/test_reproducibility.py` 全体
- 該当コード抜粋 (L26-35):
  ```python
  def _run_with_seed(seed: int) -> np.ndarray:
      random.seed(seed)
      np.random.seed(seed)
      node = BinaryNode()
      trajectory = [node.weight]
      for _ in range(100):
          node.update(1)
          trajectory.append(node.weight)
      return np.array(trajectory)
  ```

### 問題の本質

現在のモデルは決定論的で、**シードを設定しても出力に影響しない**
(BinaryNode は random/numpy を使っていない)。

したがって:
- `random.seed(0)` を呼んでも、その後の計算は seed=0 と無関係
- 5 つのシードで同じ結果が出るのは「シードが効いている」ためではなく、
  「**そもそもシードが計算に関与していない**」ため

これは KR-S3「5 つの異なるランダムシードで完全に同じ結果が再現される」の
**文言上は満たす**が、**意図上は何も検証していない**:
- 真の意図は「将来確率的要素を入れても再現性が保たれる枠組みを確立する」
- しかし現テストは「シードを呼んだ後にシード非依存な計算をする」だけで、
  確率的要素が入った時に再現性が保たれることの保証になっていない

### 影響範囲

**Sprint 1 内:**
- KR-S3 の達成判定上は pass する
- しかしテストの **科学的価値** (validity) が低い

**Sprint 2 以降への影響:**
- Sprint 6-7 で個体差 (個体間のパラメータばらつき) を導入する際、
  シード固定が効かないバグが発生しても現テストでは検出できない
- KR-S3 の意図を Sprint 2 以降で正しく継承できない

### 修正する場合の具体的変更内容

KR-S3 の意図を 2 段階に分解してテスト:

1. **シード非依存性の明示確認** (現モデル決定論性の証拠):
   ```python
   def test_model_is_seed_independent():
       """現モデルは決定論的でシードに依存しないことを明示確認。

       シードを設定しない場合と設定した場合で結果が完全一致することで、
       BinaryNode が random/numpy のグローバル状態を消費していないことを示す。
       """
       # シード設定なし
       node1 = BinaryNode()
       traj1 = [node1.weight]
       for _ in range(100):
           node1.update(1)
           traj1.append(node1.weight)

       # シード設定あり
       random.seed(42)
       np.random.seed(42)
       node2 = BinaryNode()
       traj2 = [node2.weight]
       for _ in range(100):
           node2.update(1)
           traj2.append(node2.weight)

       assert np.array_equal(np.array(traj1), np.array(traj2))
   ```

2. **既存テストはそのまま残す** (KR-S3 文言の達成証拠として):
   - `test_constant_input_bit_perfect_across_seeds`
   - `test_cessation_bit_perfect_across_seeds`
   - `test_same_seed_produces_same_result`

   ただし docstring に「現モデルでは自明だが、Sprint 6 以降で確率要素を
   入れた際の再現性インフラとして残す」旨を明記。

### 修正しない場合の理由

- KR-S3 の文言は満たしている
- 「決定論モデルでシード依存性を真にテストするのは原理的に不可能」と割り切る

### 推奨判断

**Sprint 1 内で修正する** (テスト追加 + docstring 更新)

理由:
- 新規テストの追加コストは小さい (推定 10 分)
- Sprint 6-7 で個体差を入れた時、既存の test_reproducibility.py の
  パターンをそのまま流用すると同じ問題が再発する
- 「決定論モデルではシードが効かないことを **明示的に検証する**」ことで、
  Sprint 2 以降で確率要素を入れた時に **このテストが fail するように**
  なる (意図した変化の検出器として機能する)

---

## 項目 4: `plot_reproducibility.png` に重なりの数値証拠がない

### 問題の正確な所在

- ファイル: `visualize.py`
- 行番号: L170-206 (`plot_reproducibility`)
- 該当コード抜粋:
  ```python
  ax.set_title(
      "KR-S3: Reproducibility across 5 seeds "
      "(deterministic model: lines overlap)"
  )
  ```

### 問題の本質

5 本の線を `alpha=0.7` で半透明描画しているが:
- 完全に重なる場合、視覚的には最後に描かれた線 (purple) のみが目立つ
- 「他の線が下に隠れている」のか「実際に一致している」のか判別困難
- Title の `"lines overlap"` という主張は **テキストのみで数値証拠がない**

CLAUDE.md Rule 3 (結果の証拠化)「証拠を示せない主張を行わない」に
形式的に違反する可能性。プロット内に「max(|diff|) = 0.0」のような
数値表示があれば、視覚と数値の両方で重なりを証明できる。

### 影響範囲

**Sprint 1 内:**
- KR-S3 の達成証拠としては test_reproducibility.py の pass で代替可能
- プロット単体で見た時の説得力が低い

**Sprint 2 以降への影響:**
- Sprint 6-7 で個体差プロット (100 個体の挙動分布) を作る際、
  「ばらつきの数値表示」をプロット内に含める習慣を Sprint 1 で確立すべき
- 論文公開時 (Mission KR-M1) のプロット品質基準

### 修正する場合の具体的変更内容

`plot_reproducibility` 関数内に、5 シード間の最大差分を計算して
プロット内テキストとして表示:

```python
def plot_reproducibility() -> Path:
    trajectories = {seed: run_with_seed(seed) for seed in SEEDS}
    t = np.arange(TOTAL_STEPS + 1)

    # 数値証拠の計算
    reference = trajectories[SEEDS[0]]
    max_diff = max(
        np.max(np.abs(traj - reference))
        for traj in trajectories.values()
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    # ... (既存の描画ロジック)

    # 数値証拠をプロット内に表示
    ax.text(
        0.05, 0.95,
        f"max(|diff|) across 5 seeds = {max_diff:.2e}",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white",
                  edgecolor="gray", alpha=0.9),
    )
    # ...
```

### 修正しない場合の理由

- KR-S3 の達成証拠は test 結果で十分
- プロットは「視覚的補助」と割り切る

### 推奨判断

**修正する** (Sprint 1 内)

理由:
- 修正コストは 10 行未満の追加 (推定 5 分)
- 「数値証拠をプロットに埋め込む」習慣を Sprint 1 で確立する価値
- Mission KR-M4 (Open Hardware としての公開) における
  プロット単体の自己完結性

---

## 項目 5: `ai_metrics/sprint-01_ai_log.md` を作成していない

### 問題の正確な所在

- 不在ファイル: `ai_metrics/sprint-01_ai_log.md`
- 関連仕様: `CLAUDE.md` L132-145
  > 各 Sprint で以下を `ai_metrics/sprint-XX_ai_log.md` に記録する。
  > これは Project KR-P5 (AI 支援開発の方法論的知見) のためのデータ収集。

### 問題の本質

CLAUDE.md は「各 Sprint で AI 関連メトリクスが記録される」と明記しており、
これは Project KR-P5 (AI 支援開発の方法論的知見の生成) の達成判定に
直接関わる。

私は **Sprint 1 完了報告で「Robosheep が手動で記録する」と判断した**が、
これには 2 つの問題:

1. **CLAUDE.md には「Robosheep が記録する」とは書かれていない**
   - 主体が誰かは未明示
   - AI が下書きを作るべきか、Robosheep が一から書くべきかは未定

2. **Sprint Retrospective で評価される項目** (CLAUDE.md L147-156)
   - 「メトリクスの集計」「前 Sprint との比較」「効果的パターンの強化方法」等
   - これらは Sprint 1 完了時点で AI が観察したデータがないと書けない

### 影響範囲

**Sprint 1 内:**
- Project KR-P5 の Sprint 1 分のデータが未記録 → 後で再構成困難
  (会話ログ、コミット履歴等から復元することは可能だが工数大)
- Sprint Retrospective が情報不足で実施しにくい

**Sprint 2 以降への影響:**
- Sprint 1 のメトリクス基準値がない状態で Sprint 2 以降の比較ができない
- 「前 Sprint との比較」が Sprint 2 で初めて意味を持つが、Sprint 1 の
  データがないと Sprint 2 のメトリクス記録も同様にスキップされやすい
  (悪循環)
- Project 完了時の「AI 支援開発の OKR 有効性評価」(KR-P5) が成立しない

### 修正する場合の具体的変更内容

`ai_metrics/sprint-01_ai_log.md` を作成。Claude Code が観察データを
**下書き** として記入し、Robosheep が Sprint Retrospective で確認・補正する形。

下書きに含める項目 (CLAUDE.md L137-145 の 8 項目):

1. **Specification 違反**: AI が指示範囲外の機能を提案・実装した回数と内容
   - Sprint 1 観察: **0 件** (Out of Scope 11 項目を全て遵守)
2. **Hallucination**: AI が虚偽または不正確な報告をした回数と内容
   - Sprint 1 観察: **1 件** (完了報告で「予期しない挙動: なし」と書いたが、
     実際は t=20 vs t=21 の clip 発動タイミングについて事前予測との乖離あり)
3. **Scope creep 提案**: AI が「ついでに」「より良い」と称して範囲外を提案した回数
   - Sprint 1 観察: **0 件**
4. **Halt-and-confirm の発動**: AI が独自判断せず確認を仰いだ回数 (肯定的指標)
   - Sprint 1 観察: **2 件** (環境構築方針、依存固定方針)
5. **Negative result の報告**: AI が失敗・限界を率直に報告した回数 (肯定的指標)
   - Sprint 1 観察: **6 件** (完了報告内の Negative Result セクション)
6. **確信度の明示**: AI が確信度を明示した回数の比率
   - Sprint 1 観察: 主要報告で **5 回明示** (high/medium-high)、
     全 non-trivial 主張中の比率は要算出
7. **効果的だった AI 利用パターン**:
   - 実装前の事前計算検証 (CLAUDE.md global 原則の遵守) → 実装後の挙動と完全一致
   - 環境構築段階での halt-and-confirm
8. **阻害的だった AI 利用パターン**:
   - 完了報告で「予期しない挙動: なし」と単純化したことが、後のレビューで
     より深刻な問題 (bool 通過、テスト名ミスマッチ) の発見を遅らせた可能性

### 修正しない場合の理由

- Robosheep が手動で全記録を書く方針なら不要
- ただし CLAUDE.md の文言を厳格に守ると不在は方針違反

### 推奨判断

**修正する** (Sprint 1 内、Claude Code が下書き作成)

理由:
- Project KR-P5 の達成判定に直接影響
- 下書き作成コストは小さい (推定 15 分)
- Sprint 2 以降の継続性のため、Sprint 1 で形式を確立すべき
- Robosheep の手動記録工数を削減

---

## まとめ表

| # | 項目 | 推奨判断 | 推定工数 | KR/Commitment 関連 |
|---|------|---------|---------|--------------------|
| 1 | bool 通過 | 修正する | 5 分 | Commitment 8 |
| 2 | clip テスト名ミスマッチ | 修正する | 5 分 | Commitment 8 |
| 3 | reproducibility テストの本質欠如 | 修正する (テスト追加) | 10 分 | KR-S3, Commitment 5 |
| 4 | plot 数値証拠なし | 修正する | 5 分 | Rule 3, KR-M4 |
| 5 | ai_metrics 未作成 | 修正する (下書き) | 15 分 | KR-P5 |

**合計推定工数: 40 分**

全 5 項目を修正することで、Sprint 1 の品質を Constitutional Commitments と
整合する形で確定でき、Sprint 2 以降の負債を残さない。

ただし、最終判断は Robosheep が `review_suggestions.md` の具体的な diff を
確認した上で行う。
