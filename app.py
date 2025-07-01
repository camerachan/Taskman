# ----- streamlit exe化 script------
# venv\Scripts\Activate
# streamlit-desktop-app build app.py --name Taskman --pyinstaller-options --windowed --onefile --icon=taskman.ico

import streamlit as st
import sqlite3, pathlib
from streamlit_sortables import sort_items
from datetime import datetime, timedelta
import os

# -------------------- DB 設定 --------------------
DB = pathlib.Path("tickets.db") # Default DB File name
conn = sqlite3.connect(DB, check_same_thread=False)
conn.row_factory = sqlite3.Row

conn.execute(
    """CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        detail TEXT,
        due   DATE,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Todo',
        tags  TEXT,
        sort  INTEGER DEFAULT 0,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        parent_id INTEGER DEFAULT NULL,
        attachment TEXT DEFAULT NULL,
        is_extended INTEGER DEFAULT 0
    )"""
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS subtasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        sort INTEGER DEFAULT 0,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
    );
    """
)
conn.commit()


STATUSES = ["Todo", "Doing", "Done"]
PRIORITIES = ["High", "Medium", "Low"]
TODAY = datetime.today().date()
DATABASE_NAME = 'taskman.db'

# -------------------- UTIL --------------------

def save_uploaded_file(uploaded_file):
    os.makedirs("uploads", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"uploads/{timestamp}_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def save_file(uploaded):
    if not uploaded:
        return None
    folder = pathlib.Path("uploads"); folder.mkdir(exist_ok=True)
    name = datetime.now().strftime("%Y%m%d_%H%M%S_") + uploaded.name
    path = folder / name
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    return str(path)

def fetch_board():
    rows = conn.execute("SELECT * FROM tickets ORDER BY status, sort, id").fetchall()
    board = {s: [] for s in STATUSES}
    for r in rows:
        board[r["status"].strip()].append(dict(r))
    return board

# -------------------- Sub task CRUD --------------------
def fetch_subtasks(ticket_id):
    rows = conn.execute("SELECT * FROM subtasks WHERE ticket_id=? ORDER BY sort, id", (ticket_id,)).fetchall()
    return [dict(r) for r in rows]

def add_subtask(ticket_id, title):
    conn.execute("INSERT INTO subtasks (ticket_id, title) VALUES (?,?)", (ticket_id, title))
    conn.commit()

def toggle_subtask(sub_id, new):
    conn.execute("UPDATE subtasks SET done=?, updated=CURRENT_TIMESTAMP WHERE id=?", (1 if new else 0, sub_id))
    conn.commit()

def delete_subtask(sub_id):
    conn.execute("DELETE FROM subtasks WHERE id=?", (sub_id,))
    conn.commit()

# -------------------- Tiecket CRUD --------------------

def insert_ticket(title, detail, due, priority, tags, parent_id=None, attachment=None, is_extended=1):
    conn.execute(
        "INSERT INTO tickets (title, detail, due, priority, tags, status, parent_id, attachment, is_extended) VALUES (?,?,?,?,?,?,?,?,?)",
        (title, detail, due, priority, tags, "Todo", parent_id, save_path, is_extended),
    )
    conn.commit()


def update_ticket(ticket_id, title, detail, due, priority, tags, attachment=None):
    conn.execute(
        "UPDATE tickets SET title=?, detail=?, due=?, priority=?, tags=?, attachment=?, updated=CURRENT_TIMESTAMP WHERE id=?",
        (title, detail, due, priority, tags, attachment, ticket_id),
    )
    conn.commit()

def move_ticket(ticket_id, new_status):
    conn.execute(
        "UPDATE tickets SET status=?, updated=CURRENT_TIMESTAMP WHERE id=?",
        (new_status, ticket_id),
    )
    conn.commit()

def delete_ticket(ticket_id):
    conn.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
    conn.commit()

def set_expand_state(ticket_id, state):
    print("expand state:", ticket_id, state)
    conn.execute(
        "UPDATE tickets SET is_extended=? WHERE id=?",
        (1 if state else 0, ticket_id)
    )
    conn.commit()
    st.session_state.expand_card[str(ticket_id)] = state

def get_expander_state(expander_id):
    """データベースからエキスパンダーの状態を取得する"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_expanded FROM expander_states WHERE expander_id = ?", (expander_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return bool(result[0])
    return False # デフォルトは閉じた状態

def save_expander_state(expander_id, is_expanded):
    """エキスパンダーの状態をデータベースに保存する"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO expander_states (expander_id, is_expanded) VALUES (?, ?)",
        (expander_id, int(is_expanded))
    )
    conn.commit()
    conn.close()

# -------------------- Streamlit --------------------
st.set_page_config(layout="wide", page_title="My Kanban")

# ---- Global font-size CSS ----
FONT_SIZE = 13 
st.markdown(
    f"""
    <style>
    html, body, [class*='st-'] {{
        font-size: {FONT_SIZE}px;
    }}
    h1 {{font-size: {FONT_SIZE + 8}px;}}
    h2, h3 {{font-size: {FONT_SIZE + 4}px;}}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Session init ---
if "expand_card" not in st.session_state:
    st.session_state.expand_card = {}
if "expand_all" not in st.session_state:
    st.session_state.expand_all = False
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None
if "prev_expand_card" not in st.session_state:
    st.session_state.prev_expand_card ={}
if "is_expanded" not in st.session_state:
    st.session_state.is_expanded = {}


# --- sidebar ---
with st.sidebar.expander("Utilities", expanded=True):
    if st.button("展開/折畳み"):
        st.session_state.expand_all = not st.session_state.expand_all

    hide_done  = st.checkbox("✅完了タスクを非表示", value=False)
    overdue_only = st.checkbox("⏰本日期限のみ")
    search_term = st.text_input("🔍検索")
    sort_by_due = st.checkbox("📅期日で並べ替え", value=True)
    sort_by_priority = st.checkbox("⚡優先度で並べ替え", value=False)


    # --- DB File Select ---
    db_files = list(pathlib.Path(".").glob("*.db"))
    db_names = [f.name for f in db_files]
    defalt_db = "tickets.db"

    selected_db = st.selectbox("📂使用するDB", db_names, index=db_names.index(defalt_db) if defalt_db in db_names else 0)

    # --- DB Change ---
    DB = pathlib.Path(selected_db)
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row

# --- Create New DB ---
with st.sidebar.expander("新しいDBを作成", expanded=False):
    new_db_name = st.text_input("新しいDBファイル名", value="new_tasks.db", placeholder="例: mytask.db")
    if st.button("新規作成"):
        if not new_db_name.endswith(".db"):
            new_db_name += ".db"
        elif pathlib.Path(new_db_name).exists():
            st.error("すでに同名のファイルがあります。")
        else:
            conn_new = sqlite3.connect(new_db_name)
            conn_new.execute("""
                            CREATE TABLE IF NOT EXISTS tickets (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                title TEXT NOT NULL,
                                detail TEXT,
                                due   DATE,
                                priority TEXT DEFAULT 'Medium',
                                status TEXT DEFAULT 'Todo',
                                tags  TEXT,
                                sort  INTEGER DEFAULT 0,
                                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                parent_id INTEGER DEFAULT NULL,
                                attachment TEXT DEFAULT NULL,
                                is_extended INTEGER DEFAULT 0
                            )
            """)
            conn_new.commit()
            conn_new.close()
            st.success(f"{new_db_name} を作成しました")
            st.rerun()
# --- End of Create New DB ---
# --- End of Sidebar ---
           

# --- Ticket submission form ---
with st.form("add", border=True, clear_on_submit=True):
    title = st.text_input("タイトル")
    detail = st.text_area("詳細")
    c1, c2, c3 = st.columns(3)
    due = c1.date_input("期日", value=None)
    priority = c2.selectbox("優先度", PRIORITIES)
    tags = c3.text_input("タグ", placeholder="bug,urgent")

    uploaded_file = st.file_uploader("添付ファイル", key="file", type=["pdf", "png", "jpg", "xlsx", "csv", "txt", "docx", "msg"])

    if st.form_submit_button("追加") and title:
        if uploaded_file:
            save_path = save_uploaded_file(uploaded_file)
        else:
            save_path = None
        insert_ticket(title, detail, due.isoformat() if due else None, priority, tags, None, save_path or None, 1)
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        st.session_state.expand_card[new_id] = True
        st.success("登録しました！")
        st.rerun()
# --- end of Ticket submission form ---


# ------- Callback for subtask --------
def add_subtask_cb(ticket_id, key):
    txt = st.session_state.get(key, "").strip()
    if txt:
        add_subtask(ticket_id, txt)
        st.session_state[key] = ""

# --- board ---
board = fetch_board()

# --- チケット要素の抽出 ---
all_cards = [card for col in board.values() for card in col]
# --- Tag要素の抽出 ---
tag_set = sorted(set(tag.strip()  for c in all_cards if c.get("tags") for tag in c["tags"].split(",")))

# --- Filtering section ---
st.subheader("Filter")

# --- Priority Filter ---
st.markdown("Filter by Priority")
priority_cols = st.columns(10) # 3列に設定してたらHigh/Middle/Priorityの幅が広かったので、10列に変更
priority_filter = []
with priority_cols[0]:
    if st.checkbox("High", value=True):
        priority_filter.append("High")
with priority_cols[1]:
    if st.checkbox("Medium", value=True):
        priority_filter.append("Medium")
with priority_cols[2]:
    if st.checkbox("Low", value=True):
        priority_filter.append("Low")
# --- End of Priority Filter ---

# --- Tag Filter ---
selected_tags = st.multiselect("Filter by Tags", tag_set, default=tag_set)
# --- End of Tag Filter ---
# --- End of Filtering section ---

# --- 区切り線 ---
st.divider()

current_ids = [card["id"] for col in board.values() for card in col]
cols = st.columns(len(STATUSES))

# --- 各ステータスのチケットに対して、展開状態を初期化 ---
for c in all_cards:
    cid = str(c["id"])
    if cid not in st.session_state.expand_card:
        st.session_state.expand_card[cid] = bool(c.get("is_extended", False)) #初期値


for idx, status in enumerate(STATUSES):
    if hide_done and status == "Done":
        continue
    with cols[idx]:
        st.markdown(f"### {status}")
        # --- チケットの並び替えとフィルタリング ---
        cards = board[status]
        # --- 期限でのフィルタと優先度フィルタ ---
        if sort_by_due and sort_by_priority:
            priority_map = {"High": 0, "Medium": 1, "Low": 2}
            cards.sort(key=lambda x: (
                x["due"] or "9999-12-31",
                priority_map.get(x["priority"], 3),
                x["id"]
            ))
        # --- 期限での並び替えと優先度での並び替えの条件分岐 ---
        elif sort_by_due:
            cards.sort(key=lambda x: (x["due"] or "9999-12-31", x["id"]))
        elif sort_by_priority:
            priority_map = {"High": 0, "Medium": 1, "Low": 2}
            cards.sort(key=lambda x: (priority_map.get(x["priority"], 3), x["id"]))
        # 期限フィルタ（今日以前のみ表示）
        if overdue_only:
            cards = [
                c for c in cards
                if c["due"] and datetime.strptime(c["due"], "%Y-%m-%d").date() <= TODAY
            ]
        # 検索条件フィルタ(検索ボックスに入力された文字列がタイトルまたはタグに含まれるか)
        if search_term:
            cards = [c for c in cards if search_term.lower() in c["title"].lower() or search_term.lower() in (c["tags"] or "")] 

        # 優先度とタグフィルタ
        cards = [c for c in cards if c["priority"] in priority_filter and (not c["tags"] or any(t in selected_tags for t in c["tags"].split(",")))]
        
        # --- チケット単位の表示処理 ---
        for card in cards:
            # 期日までの日数を計算
            if card["due"]:
                try:
                    due_date = datetime.strptime(card["due"], "%Y-%m-%d").date()
                    days_left = (due_date - datetime.today().date()).days
                except:
                    days_left = None
            else:
                days_left = None

            # 日数に応じた色の■マーク
            if days_left is None:
                highlight = ""  # 期日なし
            elif days_left < 0:
                highlight = "⚫"  # 期限切れ
            elif days_left < 1:
                highlight = "🔴"  # 今日
            elif days_left <= 2:
                highlight = "🟠"  # 2日以内
            elif days_left <= 5:
                highlight = "🟡"  # 5日以内
            else:
                highlight = "🟢"  # それ以降
            #is_editing = st.session_state.edit_id == card["id"]
            #card_id = str(card["id"])

            cid = card["id"]
            is_editing = st.session_state.edit_id == cid
            card_id = str(cid)
            
            #is_expanded = st.session_state.expand_card == card["id"]
            is_expanded = st.session_state.expand_card.get(card_id, False)

            with st.expander(f"{highlight}{card['title']}", expanded=is_expanded):
                if is_editing:
                    # --- edit mode ---
                    etitle = st.text_input("タイトル", value=card["title"], key=f"et_{card['id']}")
                    edetail = st.text_area("詳細", value=card["detail"], key=f"ed_{card['id']}")
                    c1, c2, c3 = st.columns(3)
                    edue = c1.date_input("期日", value=datetime.strptime(card["due"], "%Y-%m-%d") if card["due"] else None, key=f"edu_{card['id']}")
                    eprio = c2.selectbox("優先度", ["High", "Medium", "Low"], index=["High","Medium","Low"].index(card["priority"]), key=f"epr_{card['id']}")
                    etags = c3.text_input("タグ", value=card["tags"] or "", key=f"etag_{card['id']}")
                    if st.button("💾 保存", key=f"save_{card['id']}"):
                        update_ticket(card["id"], etitle, edetail, edue.isoformat() if edue else None, eprio, etags)
                        st.session_state.edit_id = None
                        st.rerun()
                    if st.button("✖ キャンセル", key=f"cxl_{card['id']}"):
                        st.session_state.edit_id = None
                        st.rerun()
                else:
                    st.markdown(card["detail"].replace("\n", "<br>"), unsafe_allow_html=True)
                    st.markdown("""
                    <style>
                    css-1n76uvr, .stMultiSelect [data-baseweb="tag"] {
                        background-color: #A0AECB !important;
                        color: white !important;
                        border-radius: 8px !important;
                        padding: 2px 8px !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    # ===== 小タスク一覧 =====
                    for sub in fetch_subtasks(card_id):
                        c_chk, c_lbl, c_del = st.columns([0.08, 0.78, 0.14])
                        with c_chk:
                            st.checkbox("", value=bool(sub["done"]), key=f"chk_{sub['id']}", on_change=toggle_subtask, args=(sub["id"], not sub["done"]))
                        with c_lbl:
                            label = f"~~{sub['title']}~~" if sub["done"] else sub["title"]
                            st.markdown(label, unsafe_allow_html=True)
                        with c_del:
                            if st.button("🗑️", key=f"del_{card_id}_{sub['id']}"):
                                delete_subtask(sub["id"])
                                st.rerun()

                    # -- 追加行 (コンパクト) --
                    c_inp, c_add = st.columns([0.8, 0.2])
                    new_key = f"new_sub_{cid}"
                    with c_inp:
                        st.text_input("小タスクを追加", key=new_key, placeholder="小タスクを追加", label_visibility="collapsed",on_change=add_subtask_cb,args=(cid,new_key))
                    with c_add:
                        st.button("＋", key=f"add_{cid}", on_click=add_subtask_cb, args=(cid, new_key))


                    st.caption(f"Due: {card['due']} | Priority: {card['priority']} | Tags🏷: {card['tags']}")
                    if card.get("attachment") and os.path.exists(card["attachment"]):
                        file_name = os.path.basename(card["attachment"])
                        with open(card["attachment"], "rb") as f:
                            st.download_button(
                                label= f"📎 {file_name}",
                                data=f,
                                file_name=os.path.basename(card["attachment"]),
                                mime="application/octet-stream"
                            )
                    #c1, c2, c3, c4, = st.columns([1,1,1,1])
                    c1, c3 = st.columns([1,1])
                    with c1:
                        if st.button("編集", key=f"edit_{card['id']}"):
                            st.session_state.edit_id = card["id"]
                            st.rerun()
                    #with c2:
                    #    if st.button("戻", key=f"prev_{card['id']}"):
                    #        move_ticket(card['id'], STATUSES[max(idx-1,0)])
                    #        st.rerun()
                    with c3:
                    #    if st.button("進", key=f"next_{card['id']}"):
                    #        move_ticket(card['id'], STATUSES[min(idx+1,len(STATUSES)-1)])
                    #        st.rerun()
                    #with c4:
                        if st.button("削除", key=f"del_{card['id']}"):
                            delete_ticket(card['id'])
                            st.rerun()