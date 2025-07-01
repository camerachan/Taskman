# Taskman - Streamlitベースのローカルタスク管理ツール

Taskmanは、Streamlitで構築されたローカル動作型のタスク管理アプリです。  
Kanban形式でのタスク管理に加え、データベース切り替え、フィルタリング、ファイル添付、期日ハイライトなどの機能を備えています。

---

## 特徴

- **Kanbanボード**による直感的なタスク管理
- **SQLiteデータベース切り替え機能**（複数プロジェクトに対応）
- **優先度・タグ・キーワードによるフィルター**
- **期日によるソートと色付き表示**
- **ファイル添付**（PDF, 画像, Excel, など）
- **サブタスク管理**（親子関係によるネスト表示）
- **展開・折畳みの保持**（セッションやDBに基づく）

---

## インストール

### 必要なライブラリ

```bash
pip install -r requirements.txt
```

## 起動方法

```bash
streamlit run app.py
```

## ディレクトリ構成

```bash
project/
├── app.py                 # メインのKanbanアプリ
├── uploads/               # 添付ファイル保存先
├── pages/                 # サブページ（例：ガントチャート）
│   └── gantt_chart.py
├── tickets.db             # 初期データベース
└── requirements.txt
```

## データベース仕様（SQLite）

|カラム名	|型	|説明|
|id	|INTEGER|	タスクの一意ID（自動採番）|
|title|	TEXT|	タイトル|
|detail|	TEXT|	詳細内容|
|due|	DATE|	期限|
|priority|	TEXT|	優先度（High, Medium, Low）|
|status|	TEXT|	状態（Todo, Doing, Done）|
|tags|	TEXT|	カンマ区切りのタグ|
|sort|	INTEGER|	カラム内並び順|
|created|	TIMESTAMP|	作成日|
|updated|	TIMESTAMP|	最終更新日|
|parent_id|	INTEGER|	親タスクID（サブタスク用）|
|attachment|	TEXT|	添付ファイルのパス|

## プロジェクトについて

このプロジェクトは、皆様からの機能追加アイデアなどを広く募集しています。
新機能を追加したらぜひPull requestをしてください。
