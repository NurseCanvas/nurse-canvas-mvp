import streamlit as st
import datetime

# --- セッションステート(仮想データベース)の初期化 ---
if "assistant_logs" not in st.session_state:
    st.session_state.assistant_logs = []
if "temp_activity" not in st.session_state:
    st.session_state.temp_activity = "未選択"

st.set_page_config(page_title="Nurse Canvas - 患者変遷トラッカー", layout="wide")

# ==========================================
# 1. 医療補助者（入力センサー）UI
# ==========================================
def assistant_ui():
    st.header("👤 医療補助者 (タスクシフト) 入力画面")
    st.write("食事介助などの「余白の時間」に、患者の様子を直感的に記録します。")

    st.subheader("1. 何のケア中ですか？ (3×3 直感アイコン)")
    cols = st.columns(3)
    activities = ["食事介助", "入浴・清拭", "リハビリ", "面会・電話", "排泄介助", "雑談・傾聴", "読書・テレビ", "睡眠・休息", "その他"]

    # 3×3グリッドの生成
    for i in range(3):
        with cols[i]:
            for j in range(3):
                act = activities[i*3 + j]
                if st.button(act, use_container_width=True):
                    st.session_state.temp_activity = act

    st.info(f"📍 現在の選択: **{st.session_state.temp_activity}**")

    st.subheader("2. 基幹プロンプトに対する反応")
    prompt = st.selectbox("投下した質問", [
        "Q1. 退院したら何が楽しみですか？",
        "Q2. 今回の病気で何か生活を変えようと考えましたか？",
        "Q3. ご家族やご友人とはどんなお話をされましたか？"
    ])

    reaction = st.radio("患者の反応(評価せず、事実のみ選択)", [
        "笑顔・前向きに話した",
        "無言・視線を逸らした",
        "不安やネガティブな発言をした"        
    ])

    if st.button("📝 記録を送信する", type="primary", use_container_width=True):
        log = {
            "time": datetime.datetime.now().strftime("%H:%M"),
            "activity": st.session_state.temp_activity,
            "prompt": prompt,
            "reaction": reaction
        }
        st.session_state.assistant_logs.append(log)
        st.success("システムにログを送信しました。ナースへ共有されます。")

# ==========================================
# 2. 看護師（マトリックス評価・オーケストレーション）UI
# ==========================================
def nurse_ui():
    st.header("🩺 看護師 (マトリックス評価) 画面")
    st.write("補助者のログを元に、精神状態の変遷を 5×5 の座標で確定(キャリブレーション)します。")

    st.subheader("🔔 システムからの神託 (アラート)")
    if not st.session_state.asistant_logs:
        st.info("現在、補助者からの新規ログはありません。")
    else:
        latest = st.session_state.assistant_logs[-1]
        st.warning(f"""
        ⚠️ **【AI検知】**{latest['time']} の「{latest['activity']}」 中、
        『{latest['prompt']}』に対し **【{latest['reaction']}】** という反応がありました。

        ➡ 学習性無力感(第4象限)への移動リスクを検知。専門的なアセスメントを推奨します。
        """)
    
    st.divider()

    st.subheader("🧠 精神状態の座標化 (キャリブレーション)")
    col1, col2 = st.columns(2)
    with col1:
        acceptance = st.slider("病気の受容度 (X軸)", 1, 5, 3)
        motivation = st.slider("療養・退院後の意欲(Y軸)", 1, 5, 3)
    
    with col2:
        st.markdown("#### 📍 現在の座標・象限")
        quadrant = ""
        if acceptance >= 3 and motivation >= 3:
            quadrant = "第1象限：適応（健全な受容）"
        elif acceptance < 3 and motivation >= 3:
            quadrant = "第2象限：過剰適応（焦り・無理な頑張り）"
        elif acceptance < 3 and motivation < 3:
            quadrant = "第3象限：フリーズ（拒絶・抵抗）"
        else:
            quadrant = "第4象限：諦観（学習性無力感）"
        
        st.success(f"**判定：** {quadrant}")

        st.markdown("💡 **システム提案 (ネクストアクション):**")
        if "第4象限" in quadrant:
            st.write("まずは「ここにいても安全である」というホスピタリティ傾聴を維持し、無理に未来の話をしないワークフローへタスクシフトします。")
        elif "第2象限" in quadrant:
            st.write("空回りのリスク大。MSW（ソーシャルワーカー）を早期介入させ、現実的なハードルを提示するパスを起動します。")
        else:
            st.write("現在のトーンを維持。次回の食事解除時にもQ1[cite: 2] のプロンプトを継続投下するよう補助者へ指示を出します。")  

# ==========================================
# ルーティング（サイドバー）
# ==========================================
st.sidebar.title("ログイン権限モック")
role = st.sidebar.radio("UI切り替え", ["医療補助者(センサー)", "看護師(評価者)"])

if role == "医療補助者(センサー)":
    assistant_ui()
else:
    nurse_ui()