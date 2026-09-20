# SHINへの参加方法

[English](CONTRIBUTING.md) · [相談・質問](https://github.com/ohayoo37/shin-lang/discussions) · [不具合・改善提案](https://github.com/ohayoo37/shin-lang/issues)

コードの修正だけでなく、不具合報告、翻訳、説明文の改善、サンプル制作、レビューでも参加できます。経験は問いません。フォークに事前許可は不要です。[行動規範](CODE_OF_CONDUCT.md)を守り、相手への敬意を持って参加してください。

## 参加の流れ

1. 質問やアイデアはDiscussionsへ。不具合や具体的な改善は既存Issueを検索してから投稿してください。英語・日本語以外の投稿も歓迎しますが、翻訳の協力が必要になる場合があります。
2. GitHubでリポジトリをForkし、自分のコピーをcloneして、最新のmainから作業ブランチを作ります。
3. 一つの目的に絞って修正します。動作変更には再現例と必要な回帰テストを添え、関係する仕様・サンプルも更新します。文言修正だけなら新しいテストは不要です。
4. 自分のForkへpushし、`ohayoo37/shin-lang:main`宛てにPull Requestを送ります。途中段階はDraftでも構いません。
5. 保守担当者のレビューに応じて修正します。テスト成功だけで自動採用されるわけではありません。

小さな誤字・翻訳修正はIssueなしで提案できます。言語仕様、依存追加、ネイティブ実装、権限や安全性の境界を変える大きな作業は、先に設計を相談してください。`good first issue`や`help wanted`が付いたIssueがあれば参加の入口になります。

## 確認方法

Python 3.9以降とGitで実行できます。テストにクラウドのAPIキーやモデルのダウンロードは不要です。

```sh
python3 -m unittest discover -s tests -v
python3 -m shin check examples/ai.shin
python3 tools/build_site.py --check
python3 tools/build_playground.py --check
```

性能変更では `python3 benchmarks/run.py` も実行し、同じ条件の変更前後の値と環境を示してください。配布関連の変更では `python3 tools/build_release.py` と生成されたzipappを確認します。CIはPython 3.9・3.11・3.13で実行します。

翻訳は `docs/i18n/<locale>.json` を編集し、`python3 tools/build_site.py` でHTMLを再生成して両方をコミットします。英語版と同じキーを揃え、現在の制約を省略せず、スマホ幅やリンクも確認します。新しい言語は生成スクリプトの `LOCALES` にも追加します。生成済みトップページだけを直接編集しないでください。

## レビューと公開の方針

標準ライブラリを優先し、言語の意味とモデル接続を分離します。権限・未検証値・実行予算の変更は境界テストとSECURITY.mdの更新が必要です。AIを使った修正も、提案者自身が内容を理解して検証してください。

認証情報、個人情報、非公開プロンプトなどを投稿しないでください。脆弱性は公開Issueではなく[非公開の報告窓口](https://github.com/ohayoo37/shin-lang/security/advisories/new)へ送ってください。

貢献は既存のMITライセンスで受け入れます。必要な著作権・ライセンス表示を残し、提供する権利がある内容だけを提出してください。別途CLAの提出は求めません。レビューは任意の活動で、回答期限は保証していません。

公式版の採用判断と保守体制は[GOVERNANCE.md](GOVERNANCE.md)に記載しています。現時点の保守担当者は `@ohayoo37` です。
