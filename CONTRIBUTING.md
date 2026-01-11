# Contributing to voicecode

voicecode への貢献をご検討いただきありがとうございます。

## Issue の報告

バグ報告や機能リクエストは GitHub Issues で受け付けています。

### バグ報告

バグを報告する際は、以下の情報を含めてください:

- macOS のバージョン
- Python のバージョン
- 再現手順
- 期待される動作
- 実際の動作
- エラーメッセージ（ある場合）

### 機能リクエスト

新機能を提案する際は、以下を記載してください:

- 解決したい課題
- 提案する解決策
- 代替案（検討した場合）

## Pull Request

### プロセス

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'feat: Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. Pull Request を作成

### 開発環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/noricha-vr/voicecode.git
cd voicecode

# 依存関係をインストール
uv sync

# テストを実行
uv run pytest tests/
```

### コードスタイル

- **型ヒント**: 関数の引数と戻り値には型ヒントを付けてください
- **Ruff**: コードフォーマットとリンティングには Ruff の使用を推奨します
- **ドキュメント**: 公開関数には docstring を記述してください

### コミットメッセージ

[Conventional Commits](https://www.conventionalcommits.org/) に従ってください:

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメントのみの変更
- `style:` コードの意味に影響しない変更（フォーマット等）
- `refactor:` バグ修正でも機能追加でもないコード変更
- `test:` テストの追加・修正
- `chore:` ビルドプロセスやツールの変更

### テスト

- 新機能には対応するテストを追加してください
- 既存のテストが全てパスすることを確認してください

```bash
# 全テスト実行
uv run pytest tests/

# 特定のテストファイル
uv run pytest tests/test_postprocessor.py

# 詳細出力
uv run pytest tests/ -v
```

## 質問

質問がある場合は、GitHub Issues で気軽にお問い合わせください。
