# 2段階優先順位を持つエンジニア用語辞書の実装計画

## 概要

音声認識の精度向上のため、2段階の優先順位を持つ辞書機能を実装する。

| 優先順位 | 名称 | 機能 | 例 |
|----------|------|------|-----|
| 強 | 変換 | 日本語読み → 英語表記に変換 | 「イシュー」→「Issue」 |
| 弱 | ヒント | 単語リストとしてLLMに提示 | haiku, sonnet, Opus |

## 設計

### ファイル形式（後方互換性あり）

`~/.voicecode/dictionary.txt`:
```
# === 変換（強い優先順位） ===
# 形式: 読み<TAB>英語
クロードコード	Claude Code
イシュー	Issue

# === ヒント（弱い優先順位） ===
# 形式: 単語のみ（タブなし）
haiku
sonnet
Opus
```

**判定ロジック**: タブを含む → 変換、タブなし → ヒント

### システムプロンプトへの反映

```xml
<terminology>
  <!-- 既存カテゴリ -->

  <category name="ユーザー辞書（変換）">
    <term japanese="イシュー" english="Issue" context="always"/>
  </category>

  <category name="ユーザー辞書（ヒント）" type="hint">
    <hint>haiku, sonnet, Opus, Claude, Cursor</hint>
    <note>これらの単語はプログラミング文脈で頻繁に使用されます。音声認識結果にこれらの単語が含まれる可能性が高い場合、優先的に採用してください。</note>
  </category>
</terminology>
```

## 変更対象ファイル

| ファイル | 変更内容 |
|----------|----------|
| `postprocessor.py` | `_load_user_dictionary()` を拡張して2種類のエントリを返す |
| `tests/test_postprocessor.py` | ヒントエントリのパーステストを追加 |
| `~/.voicecode/dictionary.txt` | 初期ヒント単語を追加 |

## 実装手順

### 1. `_load_user_dictionary()` の変更

**現在**: `str` を返す（変換エントリのXML）
**変更後**: `tuple[str, str]` を返す（変換XML, ヒントXML）

```python
def _load_user_dictionary() -> tuple[str, str]:
    """ユーザー辞書を読み込んで変換用とヒント用のXML文字列を返す。"""
    # タブあり → conversion_terms
    # タブなし → hint_words
    ...
    return conversion_xml, hint_xml
```

### 2. `PostProcessor.__init__()` の変更

```python
conversion_xml, hint_xml = _load_user_dictionary()
user_dict = conversion_xml + hint_xml
if user_dict:
    self._system_prompt = SYSTEM_PROMPT.replace(
        "</terminology>", user_dict + "\n</terminology>"
    )
```

### 3. テスト追加

- ヒントエントリのパース
- 変換とヒントの混在
- ヒントのみのファイル

### 4. 初期ヒント単語の追加

```
# AI モデル名
haiku
sonnet
Opus
Claude
GPT
Gemini
Qwen
DeepSeek
Llama

# 開発ツール
Cursor
Windsurf
Copilot
Codex

# その他
CLI
MCP
LSP
Svelte
Prisma
Vercel
Supabase
```

## 完了条件

### ユーザー価値
- ユーザーは辞書に単語を追加するだけで、その単語の認識率が向上する
- ユーザーは日本語読みからの変換と、ヒント登録を1ファイルで管理できる

### 受け入れ確認の手順
- [ ] `dictionary.txt` にタブなしで「haiku」を追加し、「ハイク」と発話した際に「haiku」と認識されやすくなることを確認
- [ ] 既存の変換エントリ（例：イシュー→Issue）が引き続き動作することを確認
- [ ] テストがすべてパスすることを確認

### 技術的完了条件
- [ ] `uv run pytest tests/test_postprocessor.py` がパス
- [ ] 後方互換性：既存の辞書形式がそのまま動作
