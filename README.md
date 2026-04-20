# 概要（Overview）
### プレビュー

| トップ画面 | 投稿詳細 |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/3457452c-330f-45b1-b471-9444c1b51f02" width="400"> | <img src="https://github.com/user-attachments/assets/c6857cba-bdba-4508-894f-541d96842b86" width="280"> |


本リポジトリは、Flask で動作するシンプルなポートフォリオ投稿アプリのサンプルです。
学習目的で作成されており、コードの責務分離や構造の理解を重視した構成になっています。

本コードは生成AI（ChatGPT 等）を活用して一部生成されていますが、
「なぜこの設計になっているのか」「どこで何をしているのか」を説明できる状態を
目指していて、本番運用を前提とした設計にはなっていません。

---

## 目的（Purpose）

- Flask アプリの構成と責務分離の考え方を理解する
- ルーティング・認証・DB操作を別ファイルに分割した構造を確認する
- 実装内容を第三者に説明できる状態にする

---

## 想定ユーザー（Target）

- **一般ユーザー** … 新規登録・ログイン、投稿の閲覧・いいね
- **管理者ユーザー** … username が `admin` のユーザーが投稿削除を行える

※ 現時点では学習目的のため、権限設計や UI は簡素に実装されています。

---

## 主な機能

- 新規登録・ログイン・ログアウト
- 投稿一覧（`/`）・投稿詳細（`/post/<id>`）
- 画像アップロード（`image_service.py` で拡張子チェック・Pillow 検証・サムネイル生成）
- いいね（トグル）
- 投稿削除（投稿者本人または管理者のみ）

---

## 技術スタック

- **Python**
- **Flask** … ルーティング・テンプレート
- **Flask-Login** … セッション管理と認証
- **Flask-WTF** … CSRF 保護
- **SQLite** … 学習用途（`database.db` 生成）
- **Pillow** … 画像検証・サムネイル生成

---

## ディレクトリ構成（Structure）

```
.
├── app.py              # エントリーポイント：Flask アプリ生成・ルート登録・DB 初期化
├── auth.py             # 認証処理（登録・ログイン・ログアウト）
├── db.py               # SQLite 接続管理・スキーマ生成・マイグレーション
├── routes.py           # 投稿・いいね・削除などのビジネスロジック
├── search.py           # 検索機能処理
├── image_service.py    # 画像アップロードとサムネイル生成
├── requirements.txt    # 依存パッケージ
├── database.db         # SQLite DB（実行時に生成される場合あり）
├── templates/          # HTML テンプレート（Jinja2）
└── static/             # CSS・アップロード画像（uploads/・thumbs/）
```

---

## 使い方

1. 依存パッケージをインストールする

```bash
pip install -r requirements.txt
```

2. Flask 版アプリを起動する

```bash
python app.py
```

3. ブラウザで `http://localhost:5000/` にアクセスする

---

## FastAPI 版（実務寄り構成）

このリポジトリには、**環境変数で設定を管理**し、**PostgreSQL を前提**にした FastAPI 版（`fastapi_app/`）も同梱しています。
APIキーやパスワード等をコード内に直書きせず、`.env` で注入する前提です。

### 事前準備

- `.env.example` をコピーして `.env` を作成し、値を設定してください（**実値はコミットしない**）

### Docker で起動（おすすめ）

※ Docker がインストールされている環境が必要です。

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- ヘルスチェック: `http://localhost:8000/healthz`
- Swagger UI: `http://localhost:8000/docs`

### ローカル起動（Dockerなし）

```bash
pip install -r requirements.txt
uvicorn fastapi_app.app.main:app --reload --port 8000
```

### マイグレーション（Alembic）

このリポジトリには **初回マイグレーション**（`fastapi_app/migrations/versions/0001_init.py`）を同梱しています。
PostgreSQL を用意して `DATABASE_URL` を設定したうえで、次を実行してください。

```bash
alembic -c fastapi_app/alembic.ini upgrade head
```

（参考）モデルから自動生成したい場合（DBへ接続できる状態が必要）:

```bash
alembic -c fastapi_app/alembic.ini revision --autogenerate -m "init"
alembic -c fastapi_app/alembic.ini upgrade head
```

### 認証API（最低限）

- `POST /auth/register` : ユーザー作成
- `POST /auth/login` : トークン発行（Bearer）

例:

```bash
curl -X POST http://localhost:8000/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"test\",\"password\":\"password123\"}"
```

```bash
curl -X POST http://localhost:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"test\",\"password\":\"password123\"}"
```

---

## テスト（pytest）

FastAPI 版のAPIフロー（登録→ログイン→投稿→いいね→削除）を、SQLiteインメモリDBで自動テストします。

```bash
pip install -r requirements.txt
pytest -q
```

---

## 設計方針（Design Policy）

1. まず動く状態にしてから責務を分離する
2. フレームワークの“魔法”を追いかけすぎず、処理の流れを自分で追えるようにする
3. コメントやドキュメントを充実させ、第三者が理解しやすい状態を保つ

---

## 今後の改善案（TODO）

- 管理者権限の明確化（ロールごとのアクセス制御）
- 本番環境用設定の分離（環境ごとの設定ファイルなど）
- セキュリティ強化（セッション管理、入力バリデーション、CSRF など）
- テスト自動化（ユニットテスト・統合テスト）

---

## 注意事項

本リポジトリは**学習目的**であり、
そのまま本番環境で利用することを想定していません。
