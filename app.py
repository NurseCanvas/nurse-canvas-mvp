import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models import Patient, Device, NurseSession, MockWardGenerator

# [EN] Set ide layout / [JA] 画面を広く使う設定
st.set_page_config(layout="wide", page_title="Nurse Canvas MVP")

# ==========================================
# 💅 【Step 1】Global CSS (Saas-like UI optimization)
# ==========================================

st.markdown("""
<style>
/* [EN] Hide Streamlit default menus / [JA] Streamlitのメニュー等を隠してアプリ感を出す */
#MainMenu {visibility: hiddden;}
footer {visibility: hidden;}
            
/* [EN] Hide Streamlit default menus / [JA] ボタンを「スマホ&手袋」で押しやすい巨大サイズに */
.stButton>button {
    height: 60px;
    font-size: 18px;
    font-weight: hold;
    border-radius: 12px;
    transition: all 0.3s ease 0s;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.stButton>button:active {
    transform: translateY(2px);
    box-shadow: 0 2px 3px rgba(0,0,0,0.1);
}
            
/* [EN] Modern rounded alerts / [JA] アラートパネルの角を丸くしてモダンに */
.stAlert {
    border-radius: 12px;
}
            
/* [EN] Emphasize accordion headers / [JA] アコーディオン(Expander)のタイトルを太字・大きく */
.streamlit-expanderHeader {
    font-size: 16px important;
    font-weight: hold !important;
}
</style>
""", unsafe_allow_html=True)


# --- Helper: Calculate elapsed time / ヘルパー関数:　経過時間の計算 ---
def get_elapsed_string(target_time: datetime) -> str:
    if not target_time:
        return "未実施"
    delta = datetime.now() - target_time
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}時間{minutes}分前"
    return f"{minutes}分前"

# --- Initialize Mock Ward Data / 仮想病棟データ初期化 ---
if "patients" not in st.session_state:
    st.session_state["patients"] = MockWardGenerator.generate_patients()
if "devices" not in st.session_state:
    st.session_state["devices"] = MockWardGenerator.generate_devices(st.session_state["patients"])
if "chart_stock_pool" not in st.session_state:
    st.session_state["chart_stock_pool"] = []
if "current_chart_draft_input" not in st.session_state:
    st.session_state["current_chart_draft_input"] = ""
if "stealth_calls" not in st.session_state:
    st.session_state["stealth_calls"] = MockWardGenerator.generate_stealth_nurse_calls()
if "assistant_logs" not in st.session_state:
    st.session_state.assistant_logs = []
if "temp_activity" not in st.session_state:
    st.session_state.temp_activity = "未選択"

# --- Cgaracter Presets for Demo / デモ用キャラクタープリセット ---
PRESET_NURSES = {
    "Ns.ベテラン(リーダー)": {"role": "リーダー", "phy": 5, "men": 5, "issue": "特になし"},
    "Ns.中堅(メンバー)": {"role": "メンバー", "phy": 3, "men": 3, "issue": "特になし"},
    "Ns.新人(メンタル低下)": {"role": "新人", "phy": 3, "men": 2, "issue": "業務過多・トラフィックJAM"},
    "Ns.突発(易感染アラート)": {"role": "メンバー", "phy": 2, "men": 4, "issue": "プライベート・体調不良"},
    "【デモ用】師長(管理者)": {"role": "管理者", "phy": 5, "men": 5, "issue": "特になし"}
}

# ==========================================
# Page Components / ページコンポーネント群
# ==========================================

def page_login():
    """
    [EN] Authentication page. Collect qualitative fatigue data.
    [JA] ログイン画面。勤務開始時に定性的な疲労データを収集し、管理ダッシュボードへ同期する。
    """
    st.title("🔑 Nurse Canvas : 勤務開始認証")
    st.write("デモ用のプリセットキャラクターを選択してください。")

    selected_preset = st.selectbox("ログイン・キャラクター", list(PRESET_NURSES.keys()))
    preset_data = PRESET_NURSES[selected_preset]

    st.info(f"役割: {preset_data['role']} | 体調: {preset_data['phy']} | メンタル: {preset_data['men']} | 要因: {preset_data['issue']}")

    if st.button("🚀 認証完了 (ログイン)", use_container_width=True):
        st.session_state["nurse_session"] = NurseSession(
            nurse_id=selected_preset.split(" ")[0],
            role=preset_data["role"],
            condition_phy=preset_data["phy"],
            condition_men=preset_data["men"],
            issue_category=preset_data["issue"]
        )
        st.rerun()

def page_bedside(current_nurse):
    """
    [EN] Bedside UI. Designed for 1-tap logging to minimize congnitive load.
    [JA] ベッドサイド入力画面。認知負荷を下げるため「1タップ記憶」を徹底した現場UI。
    """
    st.title("🏥 Nurse Canvas : ベッドサイド管理")
    selected_patient_id = st.selectbox("担当患者を選択", options=list(st.session_state["patients"].keys()), format_func=lambda x: f"{st.session_state['patients'][x].bed_no} : {x}")
    current_patient = st.session_state["patients"][selected_patient_id]

    col1, col2 = st.columns([1, 1])

    # 💅 【Step 2】入力画面のレイアウト整理 
    with col1:
        st.info(f"**ベッドNO:** {current_patient.bed_no} | **状態:** {current_patient.status_flag}")
        # [EN] Vitals & Pain scale (NRS) / [JA] バイタル・NRSの独立パネル
        with st.expander("🩺 バイタル・NRS入力", expanded=False):
            vc1, vc2, vc3, vc4, vc5 = st.columns(5)
            bp_h = vc1.number_input("血圧(上)", value=120, step=10)
            bp_l = vc2.number_input("血圧(下)", value=60, step=10)
            pulse = vc3.number_input("脈拍", value=70, step=10)
            spo2 = vc4.number_input("SpO2", value=98, step=1)
            nrs = vc5.number_input("NRS(痛)", value=0, min_value=0, max_value=10, step=1)
            if st.button("📝 バイタルを打刻", use_container_width=True):
                current_patient.add_vital_log(bp_h, bp_l, pulse, spo2, nrs, current_nurse.nurse_id)
                st.rerun()

        st.markdown("#### ▼ 1タップ・ケア記録")
        sc1, sc2 = st.columns(2)
        with sc1:
            pred = current_patient.get_suction_prediction()
            st.markdown(f"**サクション** (前回: {get_elapsed_string(current_patient.last_suction_time)})")

            # [EN] AI Prediction for proactive care / [JA] 事前準備を促すためのAI予測アラート
            if pred["status"] == "予測可能":
                mins = int((pred["next_predicted_time"] - datetime.now()).total_seconds() / 60)
                st.success(f"🤖 **AI予測:** 平均 {pred['avg_interval_mins']}分間隔 (あと {mins}分)")
            
            if st.button("💨 サクション実施", use_container_width=True, type="primary"):
                now = datetime.now()
                current_patient.record_suction(now)     # 今回はMVPなのでサクション間隔の平均とかは取らない。よってサクションidはパージ
                current_patient.add_care_log({"id": f"L_{now.strftime('%H%M%S')}", "time": now.strftime("%H:%M"),  "action": "サクション実施", "nurse": current_nurse.nurse_id})
                st.rerun()
        
        with sc2:
            st.markdown(f"**体位変換** (現在: {current_patient.current_posture})")
            new_pos = st.selectbox("次の体位", ["仰臥位", "左側臥位", "右側臥位"], label_visibility="collapsed")
            if st.button("🔄 体位変換実施", use_container_width=True, type="primary"):
                current_patient.current_posture = new_pos
                current_patient.add_care_log({"id": f"L_{datetime.now().strftime('%H%M%S')}", "time": datetime.now().strftime("%H:%M"), "action": f"体位変換 ({new_pos})", "nurse": current_nurse.nurse_id})
                st.rerun()
    
        st.divider()

        # [EN] Device & Route management (Playlist UI) / [JA] 身体挿入物・デバイス管理(一貫性の高いプレイリストUI)
        st.subheader("🧬 身体挿入物・デバイス管理 (Playlist)")
        patient_devices = [d for d in st.session_state["devices"] if d.patient_id == current_patient.patient_id] 

        if not patient_devices:
            st.write("現在、留置されているルートはありません。")
        else:
            with st.container(border=True):
                for idx, device in enumerate(patient_devices):
                    with st.expander(f"🎵 Track {idx+1} :【{device.route_type}】{device.fluid_name}(位置:{device.location})", expanded=False):
                        st.write("**滴下・輸液管理**")
                        f_name = st.text_input("薬液名", value=device.fluid_name, key=f"fname_{device.device_id}")
                        fc1, fc2 = st.columns(2)
                        f_rate = fc1.number_input("速度(ml/s)", value=device.infusion_rate, step=10, key=f"frate_{device.device_id}")
                        f_vol = fc2.number_input("残量(ml)", value=device.remaining_volume, step=50, key=f"fvol_{device.device_id}")

                        if f_rate > 0 and f_vol > 0:
                            hours_left = f_vol / f_rate
                            st.warning(f"⏳ 更新予測: 約 **{hours_left:.1f} 時間後** に空になります")

                        st.write("**✅ 臨床観察項目 (3タップチェック)**")
                        c1 = st.checkbox("① 接続よし (回路外れなし)", value=device.is_connected, key=f"conn_{device.device_id}")
                        c2 = st.checkbox("② 結露・閉塞なし", value=device.is_clear, key=f"clear_{device.device_id}")
                        c3 = st.checkbox("③ 刺入部良好", value=device.is_site_good, key=f"site_{device.device_id}")

                        new_status = "良好" if (c1 and c2 and c3) else "要観察"

                        if st.button(f"➔ {device.route_type} ログを確定する", key=f"btn_{device.device_id}", use_container_width=True, type="primary"):
                            device.fluid_name = f_name
                            device.infusion_rate = f_rate
                            device.remaining_volume = f_vol
                            device.is_connected = c1
                            device.is_clear = c2
                            device.is_site_good = c3
                            device.device_status = new_status

                            now_str = datetime.now().strftime("%H:%M")
                            log_msg = f"{device.route_type}確認: 【{new_status}】({f_name} 残{f_vol}ml / {f_rate}ml/h)"
                            current_patient.add_care_log({"id": f"L_{datetime.now().strftime('%H%M%S')}", "time": now_str, "action": log_msg, "nurse": current_nurse.nurse_id})
                            st.rerun()

    with col2:
        st.subheader("⏱️ 直近のアセスメント・ログ (最新3件)")
        for log in reversed(current_patient.recent_logs):
            st.markdown(f"**{log['time']}** | {log['action']} *(担当: {log['nurse']})*")
            st.divider()

# ▼【完全復活】カルテ自動生成・追記機能 ＆ 先輩Wチェック
def page_chart_pool(current_nurse):
    st.title("📝 カルテ送信待ち ＆ Wチェックプール")

    # 対象患者を選択
    selected_patient_id = st.selectbox("担当患者を選択",options=list(st.session_state["patients"].keys()),format_func=lambda x: f"{st.session_state['patients'][x].bed_no} : {x}")
    current_patient = st.session_state["patients"][selected_patient_id]

    cc1, cc2 = st.columns([1, 1])

    with cc1:
        st.markdown("**1. カルテに含めるアクションを選択**")

        if not current_patient.all_logs:
            st.info("本日のケア記録がまだありません。")
        else:
            log_options = {log["id"]: f"[{log['time']}] {log['action']}" for log in current_patient.all_logs}

            selected_log_ids = st.multiselect(
                "カルテ記事に組み込むログを選択",
                options=list(log_options.keys()),
                default=list(log_options.keys()),   # 初期状態は全選択
                format_func=lambda x: log_options[x]
            )

            if st.button("⬇️ 選択したログから下書きを生成", use_container_width=True):
                selected_logs = [log for log in current_patient.all_logs if log["id"] in selected_log_ids]
                lines = [f"{log['time']} {log['action']} (担当:{log['nurse']})" for log in selected_logs]
                generated_str = "\n".join(lines)

                existing_text = st.session_state.get("current_chart_draft_input", "")
                if existing_text:
                    st.session_state["current_chart_draft_input"] = generated_str + "\n\n" + existing_text
                else:
                    st.session_state["current_chart_draft_input"] = generated_str
                st.rerun()
        
        st.markdown("**2. 自動生成されたドラフト (追記可能) **")

        # 🚨【バグ修正】テキストエリアを描画する「前」にクリア処理を挟む
        if st.session_state.get("force_clear_draft"):
            st.session_state["current_chart_draft_input"] = ""
            st.session_state["force_clear_draft"] = False

        # セッションに保持されたテキストを初期値として表示
        edited_text = st.text_area(
            "カルテ貼付用テキストエリア (自由記述・補足対応)",
            height=150,
            key="current_chart_draft_input"
        )

        if st.button("🌟 この記事をカルテ送信待ちプールにストックする", use_container_width=True, type="primary"):
            # 修正 : テキストエリアの入力値を確実に取得
            text_to_stock = st.session_state.get("current_chart_draft_input", "")
            if text_to_stock.strip():   # 空白や改行だけの場合は弾く
                stock_entry = {
                    "time": datetime.now().strftime("%H:%M"),
                    "bed_no": current_patient.bed_no,
                    "patient_id": current_patient.patient_id,
                    "text": text_to_stock,
                    "w_check_by": None  # 【2つの新設】初期状態はWチェック未実装
                }
                st.session_state["chart_stock_pool"].append(stock_entry)
                st.session_state["force_clear_draft"] = True     # 下書きをクリア
                st.success("カルテ待ちプールにストックしました！")
                st.rerun()
            else:
                st.error("テキストが空欄です。")
    
    with cc2:
        st.markdown("**📺 カルテ送信待ちプール(YouTube Playlist風) **")

        with st.container(border=True):
            if not st.session_state["chart_stock_pool"]:
                st.write("ストックされている記事はありません。")
            else:
                for idx, stock in enumerate(st.session_state["chart_stock_pool"]):
                    st.markdown(f"🎵 **Track #{idx+1}** | {stock['time']}打刻 [ベッド {stock['bed_no']} : {stock['patient_id']}]")

                    # Wチェックのステータス表示
                    if stock["w_check_by"]:
                        st.success(f"✅ 先輩Wチェック済 (承認者: {stock['w_check_by']}")
                    else:
                        st.warning("⚠️ Wチェック未実施")
                    
                    st.code(stock["text"], language="text")

                    # -----------------------------------------------------
                    # 🤝 【新設：機能2】先輩Wチェック（デバイス物理受け渡し）
                    # -----------------------------------------------------
                    with st.expander(f"🤝 先輩ナースにWチェックを受ける", expanded=False):
                        st.write("※この画面のまま、端末を一緒に確認する先輩ナースに手渡してください。")
                        senior_name = st.text_input("確認先輩ナース名 / ID", key=f"senior_{idx}")
                        senior_pwd = st.text_input("認証用簡易パスコード (例: 1234)", type="password", key=f"senior_pwd_{idx}")

                        if st.button("🌟 相互チェックを承認する", key=f"approve_{idx}", type="primary"):
                            if senior_name and senior_pwd == "1234":
                                stock["w_check_by"] = senior_name
                                target_p = st.session_state["patients"].get(stock["patient_id"])
                                if target_p:
                                    now_str = datetime.now().strftime("%H:%M")
                                    target_p.add_care_log({
                                        "id": f"W_{datetime.now().strftime('%H%M%S')}",
                                        "time": now_str,
                                        "action": f"【カルテWチェック承認】承認者: {senior_name}",
                                        "nurse": current_nurse.nurse_id            
                                    })
                                st.success(f"{senior_name} さんのWチェックを記録しました!")
                                st.rerun()
                            else:
                                st.error("先輩のID、またはパスコード(1234)が正しくありません。")
                    
                    if st.button("🗑️ 削除", key=f"del_{idx}"):
                        st.session_state["chart_stock_pool"].pop(idx)
                        st.rerun()
                    st.divider()
                    
                if st.button("🗑️ プールを一括クリア", use_container_width=True):
                    st.session_state["chart_stock_pool"] = []
                    st.rerun()

def page_dashboard():
    st.title("📊 病棟オーケストレーション・ダッシュボード")
    st.write("現在の病棟全体の負荷(動的平衡)を可視化します。")

    # 労務アラートのモックアップ
    st.error("🚨 **【易感染アラート】** Ns.突発 が『体調2 (風邪症状)』で出勤しています。白血病患者・ICUベッドの担当から外すよう調整してください。")
    st.warning("⚠️ **【メンタル低下】** Ns.新人 が『メンタル2 (業務過多)』です。今日のリーダーはフォローを手厚くしてください。")

    st.subheader("📈 過去1週間の疲労度ヒートマップ (ダミーデータ)")
    # グラフ用ダミーデータ作成
    dates = pd.date_range(end=datetime.today(), periods=7)
    df = pd.DataFrame({
        "Ns.新人 (夜勤連続で低下)": [4, 4, 3, 3, 2, 2, 2],
        "Ns.ベテラン (安定)": [5, 5, 5, 5, 5, 5, 5],
        "Ns.中堅": [3, 4, 3, 4, 3, 3, 3]
    }, index=dates)
    st.line_chart(df)

def page_incident_canvas():
    st.title("🔍 インシデント相関分析 Canvas")
    st.write("発生日時と患者IDから、トラフィックJAMと疲労の重なり（動的平衡の崩れ）を暴き出します。")

    col1, col2 = st.columns([1, 2])
    with col1:
        target_p = st.selectbox("対象患者", list(st.session_state["patients"].keys()))
        target_time = st.time_input("インシデント発生時刻(目安)")
        analyze_btn = st.button("🚨 相関Canvasを展開する", type="primary", use_container_width=True)
    
    if analyze_btn:
        st.divider()
        st.subheader("⚠️ RCA (Root Cause Analysis) レポート")
        st.markdown(f"対象: **{target_p}** | 発生時刻付近のトラフィック分析")

        c1, c2 = st.columns(2)
        with c1:
            st.error(f"**【環境要因】ステルス・ナースコール多発**\n\n設定時刻の直前2時間で、病棟全体でナースコールが **{len(st.session_state['stealth_calls'])}回** 頻発し、トラフィックJAMが発生。")
            with st.expander("コール履歴詳細を見る"):
                for call in st.session_state['stealth_calls']:
                    st.write(f"- {call['time'].strftime('%H:%M')} : ベッド {call['patient_bed']}")
        with c2:
            st.warning("**【人的要因】担当ナースの疲労**\n\n当時の担当 Ns.新人のメンタルスコアは **2 (業務過多)** であり、認知リソースが極度に低下していた相関が認められます。")
        
        st.success("💡 **結論:** 個人のミスではなく、病棟の動的平衡が崩れたことによるシステムエラーです。")

def page_discharge_tracker():
    st.title("🔄 退院支援トラッカー (Imigi モジュール)")
    st.write("※デモ用 : タブを切り替えることで「補助者用のスマホからの入力」と「看護師側へのリアルタイム連携」を実演できます。")

    tab1, tab2 = st.tabs(["📱 医療補助者 (入力センサー)", "💻 看護師 (マトリックス評価)"])

    # ==========================================
    # タブ1: 医療補助者（入力センサー）UI
    # ==========================================
    with tab1:
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
                    # バグ修正: ボタンが押されたら状態を更新する
                    if st.button(act, use_container_width=True, key=f"act_{act}"):
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
                "time": datetime.now().strftime("%H:%M"),
                "activity": st.session_state.temp_activity,
                "prompt": prompt,
                "reaction": reaction
            }
            st.session_state.assistant_logs.append(log)
            st.success("システムにログを送信しました。ナースのダッシュボード (隣のタブ) へ共有されます。")
    
    # ==========================================
    # タブ2: 看護師（マトリックス評価）UI
    # ==========================================
    with tab2:
        st.header("🩺 看護師 (マトリックス評価) 画面")
        st.write("補助者のログを元に、精神状態の変遷を 5×5 の座標で確定(キャリブレーション)します。")

        st.subheader("🔔 システムからの神託 (アラート)")
        if not st.session_state.assistant_logs:
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
        cc1, cc2 = st.columns(2)
        with cc1:
            acceptance = st.slider("病気の受容度 (X軸)", 1, 5, 3)
            motivation = st.slider("療養・退院後の意欲(Y軸)", 1, 5, 3)
        
        with cc2:
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
                st.write("現在のトーンを維持。次回の食事解除時にもQ1のプロンプトを継続投下するよう補助者へ指示を出します。")  
    




# ==========================================
# ルーティング（Sidebar Navigation）
# ==========================================

if "nurse_session" not in st.session_state:
    page_login()
else:
    current_nurse = st.session_state["nurse_session"]

    # サイドバーのプロフィール表示
    st.sidebar.markdown(f"### 👤{current_nurse.nurse_id}")
    st.sidebar.markdown(f"権限: {current_nurse.role} | 体調: {current_nurse.condition_phy}")
    if st.sidebar.button("🔓 ログアウト"):
        del st.session_state["nurse_session"]
        st.rerun()
    
    st.sidebar.divider()

    # 役割(role)によるメニューの出し分け
    if current_nurse.role == "管理者":
        st.sidebar.markdown("### 管理メニュー")
        page = st.sidebar.radio("遷移先を選択", ["📊 ダッシュボード", "🔍 インシデント分析"])
        if page == "📊 ダッシュボード": page_dashboard()
        elif page == "🔍 インシデント分析": page_incident_canvas()
    else:
        st.sidebar.markdown("### 臨床メニュー")
        # メニューに「退院支援トラッカー」を追加
        page = st.sidebar.radio("遷移先を選択", ["🏥 ベッドサイド入力", "📝 カルテ＆Wチェック", "🔄 退院支援トラッカー"])

        if page == "🏥 ベッドサイド入力": page_bedside(current_nurse)
        elif page == "📝 カルテ＆Wチェック": page_chart_pool(current_nurse)
        elif page == "🔄 退院支援トラッカー": page_discharge_tracker()
    
    # 資産出力(デモ確認用)
    st.sidebar.divider()
    with st.sidebar.expander("💾 JSONデータ確認", expanded=False):
        output_json = current_nurse.to_dict()
        output_json["stock_charts_with_w_check"] = st.session_state["chart_stock_pool"]
        st.json(output_json)