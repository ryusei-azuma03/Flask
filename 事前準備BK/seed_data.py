from app import db
from app import SurveyItem  # SurveyItemモデルをインポート

# サンプルデータ
sample_data = [
    # 製造業×1000億円～5000億円
    {
        "industry": "製造業",
        "revenue": "1000億~5000億",
        "questions": [
            "基幹システム、業務システム周辺の課題",
            "データ管理と活用の課題",
            "ITインフラ周りの課題",
            "情報セキュリティやITガバナンスの課題",
            "生産現場の省人化業務効率化に向けたIT化の課題",
            "サプライチェーン・外部連携の課題",
            "ITサポート・現場対応の課題",
            "新規事業、製品のソリューション・ソフトウェア化などの課題",
            "DX推進に向けた人材育成の課題",
        ],
    },
    # 小売業×1000億円～5000億円
    {
        "industry": "流通・小売業",
        "revenue": "1000億~5000億",
        "questions": [
            "基幹システム、業務システム周辺の課題",
            "在庫管理と需要予測の精度向上の課題",
            "顧客データの活用とパーソナライゼーションの課題",
            "オムニチャネル対応の課題",
            "情報セキュリティと個人情報保護の課題",
            "物流・配送システムの効率化の課題",
            "ITインフラの拡張性とコスト管理の課題",
            "店舗運営の効率化とデジタル化の課題",
            "エコシステムの構築とサプライチェーンの連携強化の課題",
            "DX推進に向けた人材育成の課題",
        ],
    },
    # 製造業×50億円～100億円
    {
        "industry": "製造業",
        "revenue": "50億~100億",
        "questions": [
            "基幹システム、業務システム周辺の課題",
            "データ管理と活用の課題",
            "ITインフラのコストと運用の課題",
            "情報セキュリティやITガバナンスの課題",
            "生産現場の省人化と業務効率化に向けたIT化の課題",
            "サプライチェーン・外部連携の課題",
            "ITサポート・現場対応の課題",
            "新規事業、製品のソリューション・ソフトウェア化の課題",
            "DX推進に向けた人材育成の課題",
            "IT投資の優先順位設定の課題",
        ],
    },
]

# データベースへの挿入
def seed_data():
    for entry in sample_data:
        industry = entry["industry"]
        revenue = entry["revenue"]
        questions = entry["questions"]

        for question in questions:
            survey_item = SurveyItem(industry=industry, revenue=revenue, question=question)
            db.session.add(survey_item)

    db.session.commit()
    print("サンプルデータを挿入しました！")

if __name__ == "__main__":
    seed_data()
