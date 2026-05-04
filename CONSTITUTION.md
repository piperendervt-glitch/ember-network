# Constitutional Commitments: ember-network

研究プログラム全体を通じて守る原則。各判断時に整合性を確認する。

## 原則の位置づけ

これらの原則は「変更可能な計画」ではなく「守るべき制約」である。Sprint OKR や Project OKR の調整は柔軟に行うが、Constitutional Commitments の改訂は研究方針の根本的変更を意味し、深い熟慮を経て Robosheep 本人が決定する。

これは TRUSS framework における constitution.md と同じ位置づけであり、研究の長期的健全性を保証する役割を持つ。

## Commitment 1: Deterrence Priority over Capability

いかなる段階でも、capability の向上が deterrence の弱化につながる場合、deterrence を優先する。

具体的判断基準:
- 性能向上のための提案が、deterrence 性質を損なう場合は却下する
- 「より良い」「より効率的」「より速い」という改善提案が、deterrence と緊張する場合は控える
- ベンチマーク勝負を意図的に避ける論文構成を採用する

この原則は ember-network の存在意義そのもの。capability 競争に参加する研究は、別の研究プロジェクトとして分離する。

## Commitment 2: Human-in-the-Loop

自律的な決定機構を物理 AAS およびシミュレーションに実装しない。すべての段階遷移、scope 変更、新ステップ追加は Robosheep 本人の明示的決定を要する。

具体的判断基準:
- AI が自律的に次のタスクを開始することを許可しない
- AI による自己改良ループを実装しない
- 「気を利かせて追加実装」を AI が行うことを許可しない
- すべての Sprint 遷移は人間による Sprint Review を経る

この原則は ember-network が「制御不能 AI への抑止」を研究テーマとすることと整合する。

## Commitment 3: Bounded Scope

研究プログラム全体のスコープを「PTC 物理 AAS の最小実装の検証」に限定する。

範囲内:
- Sprint 0-7 (Sprint 8 は任意)
- 1 入力 → 3 並列 PTC の AAS
- シミュレーション、電子部品仮実装、3D プリント物理基板の 3 段階
- preregistration の定量的基盤

範囲外 (別プロジェクトとして分離):
- 世代間転写 (Paper B 系列)
- モジュラー結合 (Paper C 系列)
- embodied 統合 (Paper D 系列)
- 人工生命的拡張 (Paper E 系列)
- 異種素材統合
- 個体間転写
- スイッチ出力応用

魅力的に見える拡張案が浮かんでも、本プロジェクトには追加せず、「次プロジェクト候補」として lab_notebook に記録するのみ。

## Commitment 4: No Autonomous Self-Improvement (現時点)

現時点のシミュレーションコードおよび物理基板に、自己改良・自己複製機構を実装しない。AI 支援 (Claude Code 等) を使う場合も、コード変更の最終決定は人間が行う。

具体的判断基準:
- AI が「コードを改善した」と勝手に refactoring することを許可しない
- AI が specification 外の機能を「便利だから」と追加することを許可しない
- すべてのコード変更は Robosheep が diff review を経て承認する
- AI による「気の利いた」最適化を信頼せず、明示的指示の範囲内のみで動作させる

将来的な研究方向としての保留:

将来的に「人間レビューを必須経由する複製」「物理的に制限された複製」など、deterrence と整合する形での自己複製・自己改良の研究の可能性は残す。これは現プロジェクト (ember-network の最小実装研究) の範囲外であり、別研究プロジェクトとして明示的に分離した上で扱う。

現時点での原則 (現プロジェクト内で自己改良を実装しない) と、将来の可能性の保留 (別プロジェクトでの探究を否定しない) は両立する。

## Commitment 5: Reproducibility First

各段階の結果は、ランダムシード固定で完全に再現可能であること。この再現可能性は、性能・速度より優先される。

具体的判断基準:
- すべてのランダム要素にシード固定を実装する
- 環境 (Python バージョン、ライブラリバージョン) を requirements.txt または pyproject.toml で固定する
- 結果生成のすべてのコマンドを文書化する
- 「再現に必要な情報」が完備されていない結果は信頼しない

## Commitment 6: Halt-and-Review Default

不確実性や予期しない結果に直面したら、進行を止めて再評価することを default とする。「とりあえず進める」は禁止。

具体的判断基準:
- Sprint 中の tripwire 発動時は即座に halt
- AI が予期しない実装をした時は即座に halt して確認
- 仕様の解釈に複数の可能性がある時は判断を仰いでから進める
- 「動いているっぽい」状態を「動いている」と扱わない

## Commitment 7: Health and Life Balance

研究は Robosheep の本業 (契約社員業務)、健康、人間関係を犠牲にしてはならない。

具体的判断基準:
- 平日の研究時間は 1-2 時間を上限とする
- 週末の研究時間は 4-6 時間を上限とする
- 睡眠時間を削って研究しない
- 看護師の友人との連絡を含む生活リズムを優先する
- 本業の業務時間中は研究のことを考えない

研究は手段であり、Robosheep の人生が目的である。この優先順位を逆転させない。

## Commitment 8: Honest Self-Assessment

研究の進捗、成果、限界を、自分自身に対しても誇張・隠蔽せず正確に評価する。

具体的判断基準:
- 「うまくいっている」と「うまくいっているように見える」を区別する
- 失敗を成功の一部として隠さず、失敗として記録する
- 確信度の低い主張を「動いているはず」のような曖昧表現で隠さない
- 研究の限界 (規模が小さい、特定条件でのみ動作等) を論文・公開時に明示する

## 原則の運用

### 各 Sprint 完了時のチェック

各 Sprint Review で以下を問う:

1. Sprint 中の判断は、Constitutional Commitments と整合していたか?
2. 違反や境界での緊張は発生していなかったか?
3. 違反があった場合、なぜ発生し、どう対処したか?

### 違反時の対応

Constitutional Commitments の違反を発見した場合:

1. 即座に halt
2. 違反の内容と原因を lab_notebook に記録
3. 対応策を検討:
   - 単純な見落とし: 修正して継続
   - 構造的な問題: Sprint OKR や Project OKR の見直し
   - 根本的な問題: Mission OKR や Constitution の改訂検討

### 原則の改訂条件

Constitutional Commitments の改訂は研究の根本方針の変更を意味する。以下のいずれかに該当する場合のみ改訂を検討:

- 当初の研究方針 (deterrence-oriented) 自体を見直す必要がある
- 原則同士の根本的矛盾が発見された
- 研究の社会的・技術的環境が大きく変化した

軽い変更や Sprint レベルの困難は改訂理由にならない。改訂時は熟慮の期間 (1 週間以上) を取り、変更履歴を文書化する。

## 関連原則

これらの原則は以下の研究方針・哲学と整合する:

- **deterrence-oriented AI 開発**: capability ではなく制御可能性を追求
- **TRUSS framework**: Architect/Implementer/Reviewer 三層構造
- **Tsukumogami Framework**: 分散知能、小さく機能限定された単位
- **PHNN passivity 観点**: 物理散逸が安定性を保証
- **fiberfeel-rig の preregistration 流儀**: 厳密な方法論

## 変更履歴

- 2026-05-04 (初版作成): Commitment 4 を「現時点」と修飾し、将来の研究方向 (deterrence と整合する形での自己複製・自己改良の探究) としての保留を明記。
