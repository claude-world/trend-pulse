"""
Programmatic representation of Meta's 7 core ranking patents.

Each patent entry includes its key factors, weights, and content strategy implications.
Derived from patent_database.md analysis.
"""

PATENTS = {
    "edgerank": {
        "name": "EdgeRank 三維排序公式",
        "source": "2010 F8 Conference",
        "formula": "Score = Sum(Affinity x Weight x Decay)",
        "factors": {
            "affinity": {"weight": 0.35, "description": "用戶與發布者的互動頻率與深度"},
            "content_weight": {"weight": 0.35, "description": "互動類型價值：分享 > 留言 > 按讚 > 瀏覽"},
            "time_decay": {"weight": 0.30, "description": "內容新鮮度，越新越優先"},
        },
        "strategy": "經營固定受眾、回覆留言、在黃金時段發文",
    },
    "story_viewer_tuple": {
        "name": "基於社交資訊的動態消息排序",
        "patent_id": "US20130031489A1",
        "factors": {
            "social_graph": {"weight": 0.25, "description": "你與誰互動最多"},
            "story_viewer_tuple": {"weight": 0.25, "description": "內容-觀看者-互動行為三元組"},
            "interest_vector": {"weight": 0.25, "description": "用戶歷史行為推導的興趣嵌入"},
            "cross_validation": {"weight": 0.25, "description": "第三方內容源與用戶偏好交叉比對"},
        },
        "strategy": "針對目標受眾興趣向量創作，持續高互動訓練推薦模型",
    },
    "interaction_flywheel": {
        "name": "基於互動的媒體內容推薦",
        "patent_id": "US8171128B2",
        "factors": {
            "interaction_frequency": {"weight": 0.30, "description": "監控用戶與特定用戶/物件的互動頻率"},
            "event_importance": {"weight": 0.30, "description": "根據互動頻率識別事件並按重要性排序"},
            "personalized_feed": {"weight": 0.40, "description": "基於用戶關係生成個人化動態消息流"},
        },
        "strategy": "前30分鐘互動量決定飛輪是否啟動",
    },
    "social_feed": {
        "name": "社交網路動態消息系統",
        "patent_id": "US7669123B2",
        "factors": {
            "connection_strength": {"weight": 0.35, "description": "用戶之間的社交連結強度"},
            "content_relevance": {"weight": 0.35, "description": "內容與用戶興趣的匹配程度"},
            "network_effect": {"weight": 0.30, "description": "內容在社交網路中的傳播路徑"},
        },
        "strategy": "For You feed: 50% 已追蹤 + 50% 演算法推薦",
    },
    "andromeda": {
        "name": "Andromeda 即時信號驅動優化系統",
        "source": "Meta 內部系統",
        "factors": {
            "cross_platform": {"weight": 0.25, "description": "整合三平台行為數據"},
            "deep_engagement": {"weight": 0.30, "description": "轉換概率與深度互動"},
            "realtime_signal": {"weight": 0.25, "description": "即時偵測趨勢與偏好變化"},
            "multimodal_index": {"weight": 0.20, "description": "影片、文字、語音聯合索引"},
        },
        "strategy": "跨平台經營相同主題，蹭熱點要快，圖文並茂",
    },
    "conversation_durability": {
        "name": "Threads 三階段排序管線",
        "source": "Threads AI Ranking System 2024-2026",
        "pipeline": {
            "candidate_generation": 0.20,
            "ranking_scoring": 0.40,
            "diversification": 0.20,
            "conversation_durability": 0.20,
        },
        "durability_signals": {
            "72hr_window": "貼文在 72 小時內是否還有新回覆",
            "3plus_participants": "對話中是否有 3+ 不同用戶",
            "reply_depth": "回覆層數越深分數越高",
        },
        "strategy": "提出有兩面性觀點、開放式問題、互動觸發語",
    },
    "dear_algo": {
        "name": "Dear Algo 用戶主動演算法調校",
        "source": "Meta 2026-02",
        "factors": {
            "natural_language": {"weight": 0.30, "description": "用戶以文字告訴演算法偏好"},
            "trial_period": {"weight": 0.25, "description": "調整後觀察三天效果"},
            "social_propagation": {"weight": 0.20, "description": "可轉發他人的偏好設定"},
            "active_signal": {"weight": 0.25, "description": "疊加在被動信號之上的新層"},
        },
        "strategy": "鼓勵粉絲發 Dear Algo 點名你，創作容易被點名的內容",
    },
}


def get_patent(name: str) -> dict | None:
    """Get a specific patent entry by key name."""
    return PATENTS.get(name)


def get_all_strategies() -> dict[str, str]:
    """Get a mapping of patent name to its content strategy."""
    return {k: v["strategy"] for k, v in PATENTS.items()}


def get_scoring_weights() -> dict[str, float]:
    """Get the dimension-to-patent weight mapping used in score_post."""
    return {
        "hook_power": 0.25,       # EdgeRank Weight + Andromeda
        "engagement_trigger": 0.25,  # Story-Viewer Tuple + Dear Algo
        "conversation_durability": 0.20,  # Threads Conversation Durability
        "velocity_potential": 0.15,  # Andromeda Real-time
        "format_score": 0.15,     # Multi-modal Indexing
    }
