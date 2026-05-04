# Potential Risk Log (潜在リスクログ)

このファイルは ember-network プロジェクトで認識された潜在リスクを追跡する。
Rule 10.6 (検知確率 90% KPI と潜在リスクログ) および Commitment 9 (自己参照
ループの残存リスクの管理) に基づいて運用する。

各 Sprint Retrospective で全エントリーを再評価する。

形式: ハイブリッド形式 (Sprint 2 Retrospective で確定した選択肢 Z)
- ファイル先頭に概要表 (一覧)
- 詳細セクション (各 PRL の完全記述)

---

## 概要表

| ID | カテゴリ | 事象 (要約) | 発見 Sprint | 対処状況 | 関連 Commitment |
|------|------|------|------|------|------|
| PRL-001 | 単純化バイアス | Sprint 1 完了報告で「予期しない挙動: なし」と単純化された | Sprint 1 | 対処済み (Rule 8) | C8 |
| PRL-002 | 仕様の見落とし | Sprint 2 Planning で 6 件の判断項目が未明示 | Sprint 2 | 対処方針確定 | C8 |
| PRL-003 | 数値計算の制約 | RK4 が不連続な右辺で 4 次精度を失う | Sprint 2 | 対処済み (scenarios.py) | C5 |
| PRL-004 | 物理モデルの境界 | 連続時間モデル dw/dt=-β·w は w=0 を漸近境界とする | Sprint 2 | 対処済み (positivity 不変量) | C5 |
| PRL-005 | 自己参照ループ | doctest の期待値が実装結果由来 | Sprint 2 | 対処方針確定 (Rule 10.1) | C8, C9 |
| PRL-006 | 自己参照ループ | Claude Code が認識したケースのみテストされる | Sprint 2 | 対処方針確定 (Rule 10.5) | C9 |
| PRL-007 | 自己参照ループ | Claude Code 自身による Devil's Advocate は外部視点ではない | Sprint 2 | 対処方針確定 (Rule 10.5) | C9 |
| PRL-008 | 自己参照ループ | Halt-and-Confirm の推奨が承認される構造 | Sprint 2 | 監視中 | C9 |

---

## 詳細セクション

### PRL-001: 単純化バイアス

- **発見日**: Sprint 1 完了時
- **カテゴリ**: 単純化バイアス
- **事象**: Sprint 1 完了報告で「予期しない挙動: なし」と単純化された
- **発見の経緯**: Self Review (Sprint 1 完了後)
- **影響範囲**: プロジェクト全体の方法論
- **対処状況**: 対処済み (Sprint 2 で Rule 8 を導入)
- **残存リスク**: Rule 8 自体が形式化される可能性 (Sprint 2 完了報告
  Devil's Advocate #5 参照)
- **関連 Commitment**: Commitment 8 (Honest Self-Assessment)
- **次回再評価**: 各 Sprint Retrospective

### PRL-002: 仕様の見落とし (Sprint 2 Planning 6 件)

- **発見日**: Sprint 2 Planning ~ Sprint 2 実装中
- **カテゴリ**: 仕様の見落とし
- **事象**: Sprint 2 Planning で 6 件の判断項目を明示せず (doctest 例の不
  整合、dt のデフォルト、scenarios.py の戻り値、t_clip の操作的定義、RK4
  の不連続関数問題、連続時間 lower bound)
- **発見の経緯**: Sprint 2 Halt-and-Confirm
- **影響範囲**: Sprint 2 の実装プロセス
- **対処状況**: 対処方針確定 (Sprint 3 Planning で改善)
- **残存リスク**: Sprint 3 Planning でも見落としが発生する可能性
- **関連 Commitment**: Commitment 8
- **次回再評価**: Sprint 3 Retrospective

### PRL-003: RK4 の不連続点問題

- **発見日**: Sprint 2 実装中
- **カテゴリ**: 数値計算の制約
- **事象**: RK4 が不連続な右辺 (input の切替) で 4 次精度を失う
- **発見の経緯**: Sprint 2 Halt-and-Confirm
- **影響範囲**: 当該 Sprint で対処、Sprint 3 以降の入力切替シナリオ全般
- **対処状況**: 対処済み (scenarios.py 経由で 1 ステップ内 input 固定)
- **残存リスク**: Sprint 3 で温度変数導入時に類似問題が発生する可能性
- **関連 Commitment**: Commitment 5 (Reproducibility First)
- **次回再評価**: Sprint 3 完了時

### PRL-004: 連続時間モデルの lower bound 漸近性

- **発見日**: Sprint 2 実装中
- **カテゴリ**: 物理モデルの境界
- **事象**: 連続時間モデル dw/dt = -β·w は w=0 を漸近境界とする
  (離散時間の Sprint 1 と異なる)
- **発見の経緯**: Sprint 2 Halt-and-Confirm
- **影響範囲**: Sprint 3 の物理モデル設計に直接影響
- **対処状況**: 対処済み (テスト変更、Sprint 3 で物理的不変量 positivity
  として preregister)
- **残存リスク**: 同種の「離散 vs 連続」の混同が他の場面で発生する可能性
- **関連 Commitment**: Commitment 5
- **次回再評価**: Sprint 3 Retrospective

### PRL-005: doctest の自己参照

- **発見日**: Sprint 2 完了報告時
- **カテゴリ**: 自己参照ループ
- **事象**: doctest の期待値が実装結果由来 (Sprint 2 完了報告 Devil's
  Advocate #4)
- **発見の経緯**: Sprint 2 完了報告の Devil's Advocate セクション
- **影響範囲**: プロジェクト全体のテスト方法論
- **対処状況**: 対処方針確定 (Sprint 3 で Rule 10.1 doctest と pytest
  の分離)
- **残存リスク**: Sprint 3 でも完全に分離しきれない可能性
- **関連 Commitment**: Commitment 8, Commitment 9
- **次回再評価**: Sprint 3 Retrospective

### PRL-006: テストカバレッジが Claude Code 認識依存

- **発見日**: Sprint 2 Retrospective
- **カテゴリ**: 自己参照ループ
- **事象**: Claude Code が認識したケースのみテストされる
- **発見の経緯**: Sprint 2 Retrospective での議論
- **影響範囲**: プロジェクト全体のテスト方法論
- **対処状況**: 対処方針確定 (Sprint 3 で外部 AI 3 段階導入、Rule 10.5)
- **残存リスク**: 外部 AI も認識していない盲点が残る
- **関連 Commitment**: Commitment 9
- **次回再評価**: Sprint 3 Retrospective

### PRL-007: Devil's Advocate が自己批判

- **発見日**: Sprint 2 Retrospective
- **カテゴリ**: 自己参照ループ
- **事象**: Claude Code 自身による Devil's Advocate は外部視点ではない
- **発見の経緯**: Sprint 2 Retrospective での議論
- **影響範囲**: プロジェクト全体の自己批判の質
- **対処状況**: 対処方針確定 (Sprint 3 で外部 AI 3 段階導入)
- **残存リスク**: 外部 AI も Claude 系列とは別の偏見を持つ可能性
- **関連 Commitment**: Commitment 9
- **次回再評価**: Sprint 3 Retrospective

### PRL-008: Halt-and-Confirm の推奨が承認される構造

- **発見日**: Sprint 2 Retrospective (Devil's Advocate #5)
- **カテゴリ**: 自己参照ループ
- **事象**: Sprint 2 で 2 つの Halt-and-Confirm で Claude Code、設計支援役
  Claude、Robosheep の判断がすべて一致した。「Claude の推奨を Robosheep
  に承認させる構造」になっている可能性
- **発見の経緯**: Claude Code の Devil's Advocate #5 での自己批判
- **影響範囲**: プロジェクト全体の判断プロセス
- **対処状況**: 監視中
- **残存リスク**: Sprint 3 でも同じ構造が継続する可能性
- **検証方法**: Sprint 3 で「Claude の推奨が Robosheep に却下される事例」が
  発生するかを観察
- **関連 Commitment**: Commitment 9
- **次回再評価**: Sprint 3 Retrospective

---

## 変更履歴

- 2026-05-04 (Sprint 3 開始時、初版作成): PRL-001 から PRL-008 を Sprint 2
  Retrospective の確定版として記載。ハイブリッド形式 (選択肢 Z) を採用。

## 運用ノート

- 各 PRL の対処は Sprint 完了時にステータスを更新する
- 「対処済み」は当該 Sprint で具体的対策が完了した場合
- 「対処方針確定」は方針は決まったが効果検証は次 Sprint 以降
- 「監視中」は能動的対策が困難で、観察によりリスク顕在化を検知する場合
- Sprint 3 中に新規発見された潜在リスクは PRL-009 以降として追加する
- 認識していない盲点は本ログに含まれない (PRL-006, PRL-007 の限界)
