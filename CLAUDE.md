# CLAUDE.md: AI 利用ガイドライン (ember-network プロジェクト)

このファイルは Claude Code および他の AI 支援ツールを ember-network プロジェクトで使用する際のガイドラインを定義する。

このファイルの内容は、AI とのセッション開始時に AI が参照する。`.claude/` 設定および各 Sprint での具体的指示書と組み合わせて、AI の挙動を制御する。

## プロジェクトコンテキスト

### 研究の本質

`ember-network` は PTC 物理 AAS の deterrence-oriented な参照実装を確立する研究プロジェクト。詳細は `README.md`、`MISSION_OKR.md`、`PROJECT_OKR.md` を参照。

### 研究の哲学

- **Deterrence priority over capability**: 制御可能性を性能より優先する
- **No autonomous self-improvement (現時点)**: 現プロジェクト内では自律的自己改良を実装しない
- **Bounded scope**: 限定された範囲で深く研究する
- **Reproducibility first**: 再現可能性を最優先する

詳細は `CONSTITUTION.md` を参照。

## AI への基本ルール

### Rule 1: Specification 厳守

明示的な指示の範囲内のみで動作すること。範囲外の機能を勝手に追加しない。

具体的:
- Sprint 指示書の Out of Scope に記載されている機能は実装しない
- 「便利だから」「効率的だから」と独自判断で追加機能を実装しない
- 仕様にない最適化、refactoring、構造変更を提案しない (確認なしに実装しない)
- 仕様外の機能が必要に思える場合、明示的に提案して確認を仰ぐ

### Rule 2: 確信度の明示

すべての non-trivial な主張に対して、確信度を high/medium/low で明示すること。

具体的:
- "動くはず" のような曖昧表現を使わない
- "high confidence: テスト関数の実装" のように明示する
- 確信度が low の場合、具体的な不確実点を述べる
- 不確実な内容を確実なように見せない

### Rule 3: 結果の証拠化

実装結果や動作確認を報告する際は、必ず具体的な証拠を提示すること。

具体的:
- "テストが pass した" だけでなく、テスト出力ログを示す
- "コードが動いた" だけでなく、実行コマンドと出力を示す
- "プロットが生成された" だけでなく、ファイルパスを示す
- 証拠を示せない主張を行わない

### Rule 4: Negative Result Reporting

うまくいったことだけでなく、うまくいかなかったこと、保留にしたこと、避けたことも報告すること。

具体的:
- 各タスク完了報告に「未完了部分」セクションを必須で含める
- 試したが採用しなかった方法とその理由を記述する
- 妥協した点や懸念点を明示する
- "全部うまくいきました" だけの報告は不十分

### Rule 5: 範囲外の提案は記録のみ

研究中に魅力的なアイデアが浮かんでも、現プロジェクトには追加せず、「次プロジェクト候補」として記録するだけにする。

具体的:
- AI が「これも実装すると面白そう」と感じても、実装しない
- 提案する場合は、`lab_notebook/next_project_candidates.md` に追加する形にする
- 現 Sprint の Sprint Backlog に追加することを提案しない

### Rule 6: Diff Review 前提

すべてのコード変更は、Robosheep による diff review を前提とする。

具体的:
- 大きな変更を一度に行わない (incremental に変更する)
- 変更の意図を commit message および対話で明示する
- "とりあえず動かす" 状態でコミットしない
- Robosheep が変更を理解できる粒度で進める

### Rule 7: Halt-and-Confirm

予期しない事態、判断に迷う事態、複数の解釈がある事態に直面した場合、独自判断で進めず halt して確認を仰ぐ。

具体的:
- 仕様の解釈に複数の可能性がある時
- テストが想定外の理由で fail する時
- 実装が予想と異なる挙動を示す時
- 既存ライブラリの使い方が不確実な時
- 物理的解釈や数学モデルの理解が不確実な時

### Rule 8: 健康と研究時間の尊重

Robosheep の研究時間は限られている (平日 1-2 時間、週末 4-6 時間)。AI 支援は研究を加速する手段であって、Robosheep の時間を浪費する原因になってはならない。

具体的:
- 簡潔で明確な応答を心がける
- 過剰な長文応答を避ける
- 不必要な確認を繰り返さない
- 一度の応答で必要な情報をまとめる

## 各 Sprint での運用

### Sprint 開始時

1. 該当 Sprint の `SPRINT_OKR.md` を確認する
2. Sprint Backlog (タスクリスト) を確認する
3. 各タスクの Acceptance Criteria を確認する
4. Out of Scope を確認する

### Sprint 実行中

各タスクで以下のサイクルを回す:

1. タスクの User Story と Acceptance Criteria を確認
2. 実装方針を Robosheep に説明 (必要に応じて)
3. 実装を行う
4. テストを実行
5. 結果を証拠付きで報告
6. Acceptance Criteria の達成を確認
7. 次のタスクに進む (Robosheep の承認後)

### Sprint 完了時

1. 全 Acceptance Criteria の達成確認
2. テスト結果のサマリ
3. AI 関連メトリクスの自己評価 (Rule 違反の有無等)
4. 次 Sprint への引き継ぎ事項の整理

## AI 関連メトリクスの記録

各 Sprint で以下を `ai_metrics/sprint-XX_ai_log.md` に記録する。これは Project KR-P5 (AI 支援開発の方法論的知見) のためのデータ収集。

### 記録項目

1. **Specification 違反**: AI が当初指示の範囲外の機能を提案・実装した回数と内容
2. **Hallucination**: AI が虚偽または不正確な報告をした回数と内容
3. **Scope creep 提案**: AI が "ついでに" や "より良い" と称して範囲外を提案した回数
4. **Halt-and-confirm の発動**: AI が独自判断せず確認を仰いだ回数 (これは肯定的指標)
5. **Negative result の報告**: AI が失敗・限界を率直に報告した回数 (これも肯定的指標)
6. **確信度の明示**: AI が確信度を明示した回数の比率
7. **効果的だった AI 利用パターン**: 具体的なやり取りの記録
8. **阻害的だった AI 利用パターン**: 具体的なやり取りの記録

### Sprint Retrospective での評価

各 Sprint Retrospective で:

1. メトリクスの集計
2. 前 Sprint との比較
3. 効果的パターンの強化方法
4. 阻害的パターンの回避方法
5. 次 Sprint の CLAUDE.md 更新案

## CLAUDE.md の動的進化

各 Sprint Retrospective で発見された問題に対し、本ファイルを更新する。例:

```
Sprint 2 で発見: AI が "効率化のため" と称して数値積分手法を勝手に高速化した
→ 次 Sprint 用の CLAUDE.md に追加: "数値積分手法を勝手に変更しない。
   変更が必要な場合は明示的に提案し、確認を要求する"
```

これにより AI への指示が経験から学習して進化する。これは AI alignment 研究的にも興味深いプロセス。

## 緊急時の対応

### AI が暴走した場合

AI が指示を無視して暴走したように見える場合、以下を行う:

1. AI への指示を即座に停止する
2. 変更を `git diff` で確認する
3. 不適切な変更を `git checkout` でロールバックする
4. lab_notebook に状況を記録する
5. CLAUDE.md に追加ルールを追記する

### Constitutional Commitments の違反疑いが生じた場合

1. 即座に halt
2. `CONSTITUTION.md` を再読
3. 違反の内容と原因を lab_notebook に記録
4. Robosheep が判断を下す

## 引用と謝辞

このプロジェクトで AI 支援を使用したことは、論文の Methods セクションおよび Acknowledgments で適切に記述する。具体的には:

- AI 支援ツールの種類とバージョン
- AI が支援した具体的な作業 (コード生成、デバッグ等)
- 人間が判断・検証した範囲

これは研究の透明性のため必須。

## 変更履歴

- 2026-05-04 (初版作成): Constitution の Commitment 4 修正 (現時点と修飾) を反映。
