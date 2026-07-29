from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

@dataclass
class NurseSession:
    """
    [EN] Session data for the logged-in nurse.Used for workforce orchestration.
    [JA] ログイン中の看護師のセッション情報。病棟の動的平衡(タスク割り当て)の計算に使用する。
    """
    nurse_id: str
    role: str               # "リーダー(Leader)"、"メンバー(Member)"、"新人(Rockie)"
    condition_phy: int      # Physical Condetion / 体調Status (1-5)
    condition_men: int      # Mental Condition / メンタルStatus (1-5)
    issue_category: str = "特なし"  # Factor for low scare / スコア低下時の要因カテゴリ(業務過多など)
    on_call_flag: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """[EN] Serialize for JSON output. / [JA] 看護管理・疲労マネジメント用のデータ構造化"""
        return {
            "nurse_id": self.nurse_id,
            "role": self.role,
            "condition_physical": self.condition_phy,
            "condition_mental": self.condition_men,
            "issue_category": self.issue_category,
            "on_call_flag": self.on_call_flag
        }

@dataclass
class Patient:
    patient_id: str
    bed_no: str
    status_flag: str
    countdown_days: int 
    
    current_posture: str = "仰臥位" # Current Posture / 現在の体位
    last_posture_time: datetime = None

    # [EN] Variables for Suction Prediction AI / [JA] サクション予測モデル用の変数群
    last_suction_time: datetime = None
    suction_history: List[datetime] = field(default_factory=list)

    recent_logs: List[Dict[str, Any]] = field(default_factory=list)
    # [EN]Unfiltered log pool for charting _ [JA] カルテ転記用の全件保存プール (FIFOで消さない)
    all_logs: List[Dict[str, Any]] = field(default_factory=list)

    def record_suction(self, timestamp: datetime):
        """[EN] Record suction time. / [JA]サクション実施時刻を記録し、直近4回分を保持する"""
        self.last_suction_time = timestamp
        self.suction_history.append(timestamp)
        if len(self.suction_history) > 4:
            self.suction_history.pop(0)
    
    def get_suction_prediction(self) -> Dict[str, Any]:
        """[EN] Calculate average interval and predict next suction time. / [JA]サクションの平均間隔と次回予測時刻を計算する"""
        if len(self.suction_history) < 2:
            return {"avg_interval_mins": None, "next_predicted_time": None, "status": "データ不足(学習中)"}
        
        total_seconds = 0
        for i in range(1, len(self.suction_history)):
            diff = self.suction_history[i] - self.suction_history[i-1]
            total_seconds += diff.total_seconds()
        
        avg_seconds = total_seconds / (len(self.suction_history) - 1)
        avg_interval_mins = int(avg_seconds / 60)
        next_predicted_time = self.last_suction_time + timedelta(seconds=avg_seconds)

        return {
            "avg_interval_mins": avg_interval_mins,
            "next_predicted_time": next_predicted_time,
            "status": "予測可能"
        }
    
    def add_vital_log(self, bp_h: int, bp_l: int, pulse: int, spo2: int, nrs: int, nurse_id: str):
        """[EN] Record vital signs and pain scale (NRS). / [JA] バイタルと疼痛(NRS)の記録用メソッド"""
        now = datetime.now()
        log_id = f"V_{now.strftime('%H%M%S')}"
        msg = f"バイタル: 血圧{bp_h}/{bp_l} 脈拍{pulse} SpO2{spo2}% NRS:{nrs}"
        self.add_care_log({"id": log_id, "time": now.strftime("%H:%M"), "action": msg, "nurse": nurse_id})


    def add_care_log(self, log_entry: Dict[str, Any]) -> None:
        """[EN] Add new log (keeps all for charts, last 3 for UI). / [JA] ログ追加。カルテは全件、画面用は最新3件のみ保持(FIFO)"""
        self.all_logs.append(log_entry)
        self.recent_logs.append(log_entry)
        if len(self.recent_logs) > 3:
            self.recent_logs.pop(0)
    
    def to_dict(self) -> Dict[str, Any]:
        """[EN] Serialize for JSON export. / [JA] JSON出力（データ資産化）のための辞書化メソッド"""
        return {
            "patient_id": self.patient_id,
            "bed_no": self.bed_no,
            "status_flag": self.status_flag,
            "countdown_days": self.countdown_days,
            "current_posture": self.current_posture,
            "last_suction_time": self.last_suction_time.strftime("%H:%M") if self.last_suction_time else None,
            "last_posture_time": self.last_posture_time.strftime("%H:%M") if self.last_posture_time else None, 
            "recent_logs": self.recent_logs,
            "all_logs":self.all_logs
        }

@dataclass
class Device:
    """
    [EN] Attached devices(e.g., CV, IV lines). Monitored for safety and fluid volume.
    [JA] 身体挿入物 (CV、抹消点滴など)。医療安全と輸液残量の管理用クラス。
    """
    device_id: str
    patient_id: str     # [EN]Foreign Key to Patient / [JA]どの患者に刺さっているか
    route_type: str     # "CV", "PICC", "末梢点滴"
    location: str       # "右鎖骨下", "左前腕"        
    device_status: str  # "良好", "要観察", "交換申請"
    exchange_timer: int # [EN] Days until replacement / [JA]交換日までのカウントダウン日数

    # [EN] 3-Tap Safety Check (Crucial for preventing incidents) / [JA]現場での3タップチェック項目（インシデント防止の要）
    is_connected: bool = True   # Connection OK / 接続よし
    is_clear: bool = True       # No occlusion / 閉塞・結露なし
    is_site_good: bool = True   # Insertion site OK / 刺入部良好

    fluid_name: str = ""        # Fluid Name / 薬剤名
    infusion_rate: int = 0      # Rate(ml/h) / 投与速度
    remaining_volume: int = 0   # Remaining(ml) / 残量

    def to_dict(self) -> Dict[str, Any]:
        """
        デバイス状態を構造化データ(JSON用)に変換
        """
        return {
            "device_id": self.device_id,
            "patient_id": self.patient_id,
            "route_type": self.route_type,
            "location": self.location,
            "device_status": self.device_status,
            "exchange_timer": self.exchange_timer,
            "infusion_data": {
                "name": self.fluid_name,
                "rate": self.infusion_rate,
                "remaining": self.remaining_volume
            },
            "checks": {
                "connection_ok": self.is_connected,
                "no_condensation": self.is_clear,
                "site_condition_ok": self.is_site_good
            }
        }
    
# ==========================================
# ▼【新設】仮想病棟（12床）モックデータジェネレーター
# ==========================================
class MockWardGenerator:
    """
    [EN] Generates mock ICU/Ward data to demonstrate macro-level orchestration.
    [JA] 仮想病棟(12床)モックデータ生成。マクロ視点でのトラフィック可視化デモ用。
    """
    @staticmethod
    def generate_patients() -> Dict[str, Patient]:
        patients = {}
        statuses = ["全介助", "一部介助", "自立", "重症(ICU転倒予定)"]
        for i in range(1, 13):
            p_id = f"P-{100+i}"
            b_no = f"No.{i}"
            status = random.choice(statuses)
            p = Patient(patient_id=p_id, bed_no=b_no, status_flag=status, countdown_days=random.randint(1, 14))

            # [EN] Add dummy historical logs / [JA] ダミーの初期ログ(サクション等)
            now = datetime.now()
            if status in ["全介助", "重症(ICU転棟予定)"]:
                p.record_suction(now - timedelta(hours=1, minutes=random.randint(5, 50)))
                p.add_care_log({"id": f"L_{p_id}_1", "time": (now - timedelta(hours=1)).strftime("%H:%M"), "action":"サクション実施", "nurse": "Ns.ベテラン"})
            patients[p_id] = p
        return patients

    @staticmethod
    def generate_devices(patients: Dict[str, Patient]) -> List[Device]:
        devices = []
        d_id_counter = 901
        for p_id, p in patients.items():
            if p.status_flag in ["全介助", "重症(ICU転棟予定)"]:
                devices.append(Device(device_id=f"D-{d_id_counter}", patient_id=p_id, route_type="CV", location="右鎖骨下", device_status="良好", exchange_timer=4, fluid_name="ビーフリード", infusion_rate=40, remaining_volume=200))
                d_id_counter += 1
            if random.random() > 0.5:
                devices.append(Device(device_id=f"D-{d_id_counter}", patient_id=p_id, route_type="末梢点滴", location="前腕", device_status="良好", exchange_timer=2, fluid_name="アセリオ", infusion_rate=100, remaining_volume=100))
                d_id_counter += 1
        return devices
    
    @staticmethod
    def generate_stealth_nurse_calls() -> List[Dict[str, Any]]:
        """
        [EN] Generates background nurse call data for Root Cause Analysis (RCA).
        [JA] インシデント相関デモ用 : 裏でナースコールが頻発していたというステルスデータ
        """
        calls = []
        base_time = datetime.now() - timedelta(hours=2, minutes=30)
        for _ in range(20):
            call_time = base_time + timedelta(minutes=random.randint(1, 45))
            calls.append({"time": call_time, "patient_bed": f"No.{random.randint(1, 12)}", "type": "ナースコール(呼出)"})
        return sorted(calls, key=lambda x: x["time"])    

