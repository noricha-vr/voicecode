# 次にやるべきこと

生成日時: 2026-01-11 18:30
スキャンスコープ: default

## プロジェクト状況サマリー

| 項目 | 状態 |
|------|------|
| プロジェクト名 | voicecode |
| プロジェクトゴール | OSS公開準備完了、Beta段階 |
| 実装進捗 | 100% |
| テストカバレッジ | 高（149テスト、8ファイル） |
| 主要な懸念 | 軽微な改善のみ |

## 推奨アクション（優先度順）

### P0: 緊急（ゴール達成に必須）
- なし（OSS公開準備は完了）

### P1: 高（セキュリティ・品質リスク）
- なし（重大なセキュリティリスクは検出されず）

### P2: 中（品質改善）
- [ ] **未使用依存の整理** - Gemini単段化後に `groq` / `openai` の依存が不要かを再確認して削除
  - ファイル: `pyproject.toml`, `uv.lock`
  - 理由: 互換期間中の暫定依存が残ると保守コストが上がる

- [ ] **Gemini SDK移行** - `google.generativeai` から `google.genai` へ移行
  - ファイル: `transcriber.py`, `scripts/test_gemini_audio.py`, `pyproject.toml`
  - 理由: 現行SDKで FutureWarning（サポート終了）が出るため

- [ ] **pytest収集範囲を固定** - `testpaths = ["tests"]` で `scripts/test_*.py` を誤収集しない
  - ファイル: `pyproject.toml`
  - 理由: 全体テストで実行用スクリプトが収集されるとCI/ローカル検証が不安定になる

- [ ] **Linting設定を追加** - pyproject.toml に ruff/black 設定を追加
  - ファイル: `pyproject.toml`
  - 理由: 自動フォーマット・品質チェック未配置

- [ ] **main.py の分割検討** - 547行で500行超
  - ファイル: `main.py`
  - 理由: UI処理と音声処理ロジックが混在

- [ ] **pytest-cov 導入** - テストカバレッジ測定の自動化
  - ファイル: `pyproject.toml`, `.github/workflows/test.yml`
  - 理由: カバレッジ測定が未設定

### P3: 低（将来的）
- [ ] **postprocessor 互換レイヤの削除** - Gemini単段化が安定したら `main.py` から `PostProcessor` 呼び出しを撤去
  - ファイル: `main.py`, `postprocessor.py`, `tests/test_main.py`
  - 理由: 現在は移行互換のためパススルー実装が残っている

- [ ] **ユーザー辞書のXMLエスケープ追加** - postprocessor.py:280-290
  - 理由: XMLタグを含む辞書で問題が発生する可能性（軽微）

- [ ] **マイク権限エラーメッセージの明確化** - recorder.py
  - 理由: sounddeviceのエラーをユーザーフレンドリーに

- [ ] **プログラミング用語辞書の分離** - postprocessor.py の辞書を別ファイル化
  - 理由: 320行を占める大型辞書を `terminology.py` などに分離

## 並列実行可能グループ

### Group 1（依存関係なし、即座に着手可能）
- Linting設定追加
- pytest-cov導入
- ユーザー辞書のXMLエスケープ追加

### Group 2（将来的）
- main.py分割（アーキテクチャ変更を伴う）
- SaaS化準備（配布戦略ドキュメントに記載）

## 分析詳細

### Goal & Architecture
- アーキテクチャ設計と実装は **高度に整合**
- 単一責務の原則を遵守（recorder/transcriber/postprocessor）
- ドキュメント整備は業界水準を上回る
- 技術的負債はほぼなし

### Implementation Status
- **TODO/FIXME: 0件** - 未解決タスクなし
- **NotImplementedError: 0件** - スタブ実装なし
- 機能は100%実装完了
- テスト: 8ファイル、149テストケース

### Quality & Test
- 型ヒント使用率: 95%+
- Pydantic/Dataclass活用: HistoryEntry, RecordingConfig
- テストの充実度: 高
- 改善余地: Linting設定、main.py分割

### Security & Performance
- APIキー管理: 環境変数で適切に管理
- ハードコード認証情報: なし
- パフォーマンスリスク: なし
- 軽微な改善: ユーザー辞書のXMLエスケープ

## 次のマイルストーン推奨

### 短期（OSS公開後）
- [ ] テストカバレッジ測定自動化
- [ ] Linting設定追加
- [ ] コミュニティからのフィードバック対応

### 中期
- [ ] SaaS化準備（docs/distribution-strategy.md参照）
- [ ] パフォーマンス最適化
- [ ] コミュニティ辞書プラットフォーム

### 長期
- [ ] SaaS提供開始
- [ ] 多言語対応検討
