# SHIN

**自由な発想。明示された権限。**

AIの判断と、プログラムが持つ権限を分ける実験的プログラミング言語です。独自の構文を専用バイトコードへ変換し、小さなVMで実行します。**v0.2.0a2は動く初期実装です。「世界最速」「完全に安全」を達成した言語ではありません。**

[English](README.md) · [公式ページ](https://ohayoo37.github.io/shin-lang/) · [言語仕様](docs/language.md) · [セキュリティの範囲](SECURITY.md)

## まず動かす

Python 3.9以降があれば、追加の実行時ライブラリは不要です。

```sh
git clone https://github.com/ohayoo37/shin-lang.git
cd shin-lang
python3 -m shin run examples/hello.shin
python3 -m shin run examples/ai.shin --allow-model demo
```

```text
permit model "demo";
budget steps = 1000;

fn answer(prompt) {
    let draft = infer("demo", prompt);
    return check_text(draft, 200);
}

print(answer("AIの出力は、検証してから使う。"));
```

`demo`は入力をそのまま返すテスト用モデルで、実際のAI推論ではありません。コードの`permit`と実行者の`--allow-model`が揃わなければ実行を拒否します。

## Webサイト・アプリ・CMSを作る

```sh
python3 -m shin init my-site --template website
python3 -m shin serve my-site --port 8000
```

`http://127.0.0.1:8000`を開くとサイトが動きます。`--template app`でブラウザアプリ、`api`でJSON API、`cms`で記事サイトを生成できます。

v0.2ではルーティング、安全なHTML生成、静的サイト出力、SQLite保存、トークン認証付きCMS編集画面、下書き／公開切替、編集競合の検出を追加しました。

[Web・CMS開発ガイド](docs/web.md) · [SHINで生成した公開デモ](https://ohayoo37.github.io/shin-lang/demo/) · [サンプル](examples/)

対象はWebサイト・ブラウザアプリ・APIです。iOS／Android／デスクトップのネイティブアプリ生成は未実装です。付属サーバーは開発用で、本番運用には別のホスティングと認証・運用設計が必要です。

## 今回実装したこと

| 項目 | v0.2の内容 |
|---|---|
| 柔軟な記述 | 関数・再帰・分岐・ループ・配列・辞書・ブロックスコープ |
| AI接続 | テスト用モデル、ホストが明示したローカルOllamaへの接続 |
| 権限 | モデル名は文字列リテラル。コンパイル時に必要権限を収集し、実行者の許可と照合 |
| 検証 | AI出力と入力JSONは未検証値。文字数・型・JSONキーなどを検証して利用 |
| 制限 | 命令数・呼び出し深さ・値サイズ・累計論理割当量・出力量・協調的な経過時間チェック |
| 開発支援 | 構文／権限チェック、バイトコード表示、実行統計、テスト、ベンチマーク |

外部ファイル操作・任意通信・シェル実行・動的コード実行は言語機能として提供していません。ファイルからのソース・設定・入力読み込みはCLIを操作するホストの役割です。

## 設計上の限界

文字列やJSONの検証は、AI回答の真実性や業務上の正しさを保証しません。メモリ制限は値の論理サイズを数える方式で、OS全体のメモリ使用量を制限するものではありません。時間制限もプロセスを強制終了するものではなく、信頼済みホスト処理から戻った時点のチェックを含みます。

現状のPython製VMは、付属の単純計算ベンチマークでPythonより遅い結果です。小さい配布ソース・外部依存不要という特徴と、演算速度は別の評価です。測定結果を公開し、将来のネイティブ／Wasm実装と比較する基準にします。

静的型検査、並列実行、GPU最適化、クラウドAI接続、OSサンドボックスは未実装です。Ollama接続はローカルHTTP試験サーバーで通信形式を検証済みですが、実モデルによる推論品質は今回未検証です。

## 検証する

```sh
python3 -m unittest discover -s tests -v
python3 benchmarks/run.py
python3 -m shin check examples/ai.shin
python3 -m shin disasm examples/functions.shin
```

開発方針は[ロードマップ](docs/roadmap.md)に記載しています。MITライセンスで公開しています。PyPIへの登録はまだ行っていません。

## Website languages

[English](https://ohayoo37.github.io/shin-lang/en/) · [日本語](https://ohayoo37.github.io/shin-lang/ja/) · [Español](https://ohayoo37.github.io/shin-lang/es/) · [Français](https://ohayoo37.github.io/shin-lang/fr/) · [Deutsch](https://ohayoo37.github.io/shin-lang/de/) · [Português](https://ohayoo37.github.io/shin-lang/pt-BR/) · [简体中文](https://ohayoo37.github.io/shin-lang/zh-CN/) · [한국어](https://ohayoo37.github.io/shin-lang/ko/)

公開紹介サイトは8言語対応です。技術文書は英語中心で、日本語READMEも用意しています。Webサイトのテンプレートと公開デモは英語、アプリとCMS編集画面は現在日本語です。翻訳の更新は `docs/i18n/*.json` を編集して `python3 tools/build_site.py` を実行します。

## オープンソース開発への参加

SHINは[MITライセンス](LICENSE)のオープンソースです。コード修正、翻訳、ドキュメント、サンプル、不具合報告、レビューなどで参加できます。初めての貢献も歓迎します。

- [日本語の参加ガイド](CONTRIBUTING.ja.md) · [English guide](CONTRIBUTING.md)
- [質問・アイデアの相談](https://github.com/ohayoo37/shin-lang/discussions)
- [不具合報告・改善提案](https://github.com/ohayoo37/shin-lang/issues/new/choose)
- [運営・レビュー方針](GOVERNANCE.md) · [行動規範](CODE_OF_CONDUCT.md)

Forkして修正を提案でき、公式版には保守担当者のレビューを経て取り込みます。脆弱性は[非公開の報告窓口](https://github.com/ohayoo37/shin-lang/security/advisories/new)へ送ってください。
