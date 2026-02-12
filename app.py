"""
Flask ポートフォリオアプリのエントリポイント。

担当: ルーティング・認証・セッション・DB 接続・投稿・検索・いいね・削除の
      一連の Web リクエスト処理を束ねる。
"""

import os
import re
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFProtect
from image_service import process_uploaded_image
from werkzeug.security import check_password_hash, generate_password_hash


# -----------------------------------------------------------------------------
# アプリ・拡張の初期化
# -----------------------------------------------------------------------------

app = Flask(__name__)
"""担当: Flask アプリ本体。設定・ルート・コンテキストの起点。"""

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # アップロード上限 5MB

csrf = CSRFProtect(app)
"""担当: 全 POST フォームへの CSRF トークン検証。"""

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)
"""担当: ログイン状態の管理。未認証時のリダイレクト先指定。"""


# -----------------------------------------------------------------------------
# 認証用モデル・ローダー
# -----------------------------------------------------------------------------


class User(UserMixin):
    """担当: ログイン中ユーザーの id / username / password_hash を保持。Flask-Login が要求するインターフェースを満たす。"""

    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash


@login_manager.user_loader
def load_user(user_id):
    """担当: セッションの user_id から User を復元。リクエストごとにログイン状態を復元するために呼ばれる。"""
    try:
        database = get_db()
        row = database.execute(
            "SELECT id, username, password FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if row:
            return User(row["id"], row["username"], row["password"])
    except Exception:
        app.logger.exception("load_user failed")
    return None


# -----------------------------------------------------------------------------
# DB 接続（リクエストスコープ）
# -----------------------------------------------------------------------------


def get_db():
    """担当: リクエストごとに一つの SQLite 接続を g に保持し、Row で返す。"""
    if "db" not in g:
        g.db = sqlite3.connect("database.db")
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """担当: リクエスト終了時に g に保持した DB 接続を閉じる。"""
    database = g.pop("db", None)
    if database is not None:
        database.close()


# -----------------------------------------------------------------------------
# DB スキーマ初期化・マイグレーション
# -----------------------------------------------------------------------------


def init_db():
    """担当: users / posts / likes テーブルを未作成の場合のみ作成する。"""
    database_connection = sqlite3.connect("database.db")
    cursor = database_connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            filename TEXT,
            body TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            post_id INTEGER
        )
    """)

    database_connection.commit()
    database_connection.close()


def ensure_likes_index():
    """担当: likes の (user_id, post_id) 重複防止用ユニークインデックスを存在する場合のみ作成。"""
    database_connection = sqlite3.connect("database.db")
    cursor = database_connection.cursor()
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS index_likes_user_post ON likes(user_id, post_id)",
    )
    database_connection.commit()
    database_connection.close()


def ensure_posts_has_body():
    """担当: 既存 DB の posts に body カラムがなければ追加する（マイグレーション）。"""
    database_connection = sqlite3.connect("database.db")
    cursor = database_connection.cursor()
    cursor.execute("PRAGMA table_info(posts)")
    columns = cursor.fetchall()
    column_names = [column_info[1] for column_info in columns]
    if "body" not in column_names:
        cursor.execute("ALTER TABLE posts ADD COLUMN body TEXT")
        database_connection.commit()
    database_connection.close()


# 起動時: DB ファイルが無ければ作成し、スキーマ・インデックス・マイグレーションを適用
if not os.path.exists("database.db"):
    os.makedirs("static/uploads", exist_ok=True)
    init_db()

ensure_likes_index()
ensure_posts_has_body()


# -----------------------------------------------------------------------------
# ルーティング: 認証（登録・ログイン・ログアウト）
# -----------------------------------------------------------------------------


@app.route("/register", methods=["GET", "POST"])
def register():
    """担当: 新規登録画面の表示と、ユーザー名・パスワードの検証・ハッシュ化・DB 登録。"""
    if request.method == "POST":
        username = request.form["username"]
        raw_password = request.form["password"]

        if not raw_password:
            flash("パスワードを入力してください。")
            return render_template("register.html", title="新規登録")
        if len(raw_password) < 8:
            flash("パスワードは8文字以上にしてください。")
            return render_template("register.html", title="新規登録")
        if len(raw_password) > 128:
            flash("パスワードは128文字以下にしてください。")
            return render_template("register.html", title="新規登録")
        if not re.match(r"^[\x21-\x7E]+$", raw_password):
            flash(
                "パスワードは英数字および記号（半角）で入力してください。日本語や全角文字は使えません。",
            )
            return render_template("register.html", title="新規登録")

        password_hash = generate_password_hash(raw_password)
        try:
            database = get_db()
            database.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password_hash),
            )
            database.commit()
        except sqlite3.IntegrityError:
            flash("ユーザー名は既に使われています。")
            return render_template("register.html", title="新規登録")
        except Exception:
            app.logger.exception("failed to register")
            flash("登録に失敗しました。")
            return render_template("register.html", title="新規登録")

        return redirect("/login")
    return render_template("register.html", title="新規登録")


@app.route("/login", methods=["GET", "POST"])
def login():
    """担当: ログイン画面の表示と、ユーザー名・パスワード照合・セッション開始。"""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            database = get_db()
            row = database.execute(
                "SELECT id, username, password FROM users WHERE username=?",
                (username,),
            ).fetchone()
            if row and check_password_hash(row["password"], password):
                login_user(User(row["id"], row["username"], row["password"]))
                return redirect("/")
        except Exception:
            app.logger.exception("login error")
        return "ログイン失敗"

    return render_template("login.html", title="ログイン")


@app.route("/logout")
def logout():
    """担当: セッションを破棄しトップへリダイレクト。"""
    logout_user()
    return redirect("/")


# -----------------------------------------------------------------------------
# ルーティング: 投稿（アップロード・一覧・詳細）
# -----------------------------------------------------------------------------


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """担当: 投稿フォームの表示と、タイトル・本文・画像の受付・検証・保存（画像は image_service に委譲）。"""
    if request.method == "POST":
        if not current_user.is_authenticated:
            abort(401)
        title = request.form["title"]
        body = request.form.get("body", "")
        image = request.files.get("image")

        if not title or title.strip() == "":
            flash("タイトルが入力されていません")
            return render_template("upload.html", title="投稿")

        filename, error = process_uploaded_image(
            image,
            upload_base_dir="static/uploads",
        )
        if error:
            flash(error)
            return render_template("upload.html", title="投稿")

        try:
            database = get_db()
            database.execute(
                "INSERT INTO posts (user_id, title, filename, body) VALUES (?, ?, ?, ?)",
                (int(current_user.id), title, filename, body),
            )
            database.commit()
        except Exception:
            app.logger.exception("failed to insert post")
            flash("投稿の保存に失敗しました")
            return render_template("upload.html", title="投稿")

        return redirect("/")

    return render_template("upload.html", title="投稿")


@app.route("/")
def home():
    """担当: 投稿一覧の取得（created_at 降順）と index テンプレートの表示。"""
    try:
        database = get_db()
        rows = database.execute(
            "SELECT id, user_id, title, filename, body, created_at FROM posts ORDER BY created_at DESC",
        ).fetchall()
        posts = [dict(row) for row in rows]
        return render_template("index.html", posts=posts, title="投稿一覧")
    except Exception:
        app.logger.exception("failed to fetch posts")
        abort(500)


@app.route("/post/<int:id>")
def post(id):
    """担当: 指定 ID の投稿取得・いいね数取得・詳細テンプレート表示。存在しなければ 404。"""
    try:
        database = get_db()
        row = database.execute(
            "SELECT id, user_id, title, filename, body, created_at FROM posts WHERE id=?",
            (id,),
        ).fetchone()
        if not row:
            abort(404)
        post_data = dict(row)
        like_count = database.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id=?",
            (id,),
        ).fetchone()[0]
        return render_template(
            "post.html",
            post=post_data,
            like_count=like_count,
        )
    except Exception:
        app.logger.exception("failed to fetch post")
        abort(500)


# -----------------------------------------------------------------------------
# ルーティング: 検索
# -----------------------------------------------------------------------------


@app.route("/search", methods=["GET"])
def search():
    """担当: クエリパラメータ search_query でタイトル部分一致検索し、検索結果テンプレートを返す。"""
    search_keyword = request.args.get("search_query", "").strip()

    try:
        database = get_db()
        rows = database.execute(
            """
            SELECT id, user_id, title, filename, body, created_at
            FROM posts
            WHERE title LIKE ?
            ORDER BY created_at DESC
            """,
            (f"%{search_keyword}%",),
        ).fetchall()
        posts = [dict(row) for row in rows]
        return render_template(
            "search_results.html",
            posts=posts,
            search_keyword=search_keyword,
            title="検索結果",
        )
    except Exception:
        app.logger.exception("search failed")
        abort(500)


# -----------------------------------------------------------------------------
# ルーティング: いいね・削除
# -----------------------------------------------------------------------------


@app.route("/like/<int:id>", methods=["POST"])
@login_required
def like(id):
    """担当: 対象投稿へのいいねのトグル（既にいいね済みなら削除、未なら追加）。投稿詳細へリダイレクト。"""
    if not current_user.is_authenticated:
        abort(401)
    try:
        database = get_db()
        existing = database.execute(
            "SELECT id FROM likes WHERE user_id=? AND post_id=?",
            (int(current_user.id), id),
        ).fetchone()

        if existing:
            database.execute(
                "DELETE FROM likes WHERE user_id=? AND post_id=?",
                (int(current_user.id), id),
            )
        else:
            database.execute(
                "INSERT INTO likes (user_id, post_id) VALUES (?, ?)",
                (int(current_user.id), id),
            )
        database.commit()
        return redirect(url_for("post", id=id))
    except Exception:
        app.logger.exception("like/unlike failed")
        abort(500)


@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    """担当: 投稿者本人または admin のみ削除可能。DB レコード削除とアップロードファイル・サムネイルの削除。"""
    if not current_user.is_authenticated:
        abort(401)
    try:
        database = get_db()
        row = database.execute(
            "SELECT user_id, filename FROM posts WHERE id=?",
            (id,),
        ).fetchone()
        if not row:
            return redirect(url_for("home"))

        owner_id = row["user_id"]
        filename = row["filename"]

        if int(current_user.id) != int(owner_id) and current_user.username != "admin":
            abort(403)

        for path in (
            os.path.join("static", "uploads", filename),
            os.path.join("static", "uploads", "thumbs", filename),
        ):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    app.logger.exception("failed to remove file: %s", path)

        database.execute("DELETE FROM posts WHERE id=?", (id,))
        database.commit()
        return redirect(url_for("home"))
    except Exception:
        app.logger.exception("failed to delete post")
        abort(500)


# -----------------------------------------------------------------------------
# 起動
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
