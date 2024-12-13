from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid
import os
import openai
from flask_cors import CORS
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__)
CORS(app)

# データベース設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# GPTのAPIキー設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# データベースモデル
class MeetingCandidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.String(36), nullable=False)
    date_time_start = db.Column(db.String(16), nullable=False)
    duration = db.Column(db.Integer, nullable=False)

# データベースモデルの修正
class CustomerLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.String(36), nullable=False, unique=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    sales_rep_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=True)  # 部署名を追加
    role_name = db.Column(db.String(100), nullable=True)    # 役職を追加
    industry = db.Column(db.String(50), nullable=False)
    revenue = db.Column(db.String(50), nullable=False)
    meeting_type = db.Column(db.String(50), nullable=False)
    link = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

# マイグレーションを適用
def upgrade_database():
    with app.app_context():
        # 部署名と役職を追加
        if not hasattr(CustomerLink, 'department'):
            db.session.execute('ALTER TABLE customer_link ADD COLUMN department TEXT;')
        if not hasattr(CustomerLink, 'position'):
            db.session.execute('ALTER TABLE customer_link ADD COLUMN position TEXT;')
        db.session.commit()

class SurveyItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    industry = db.Column(db.String(50), nullable=False)
    revenue = db.Column(db.String(50), nullable=False)
    question = db.Column(db.String(255), nullable=False)
    related_item_id = db.Column(db.Integer, nullable=True)

class CustomerResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.String(36), nullable=False)
    selected_date_time = db.Column(db.String(16), nullable=False)
    survey1_selected_items = db.Column(db.Text, nullable=True)
    survey1_priority_item = db.Column(db.String(255), nullable=True)
    survey2_selected_items = db.Column(db.Text, nullable=True)
    survey_completed = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

# データベース初期化
@app.before_first_request
def create_tables():
    db.create_all()

# リンクの有効期限チェック
def is_link_expired(link):
    return datetime.utcnow() > link.expires_at

# 営業画面エンドポイント
@app.route('/sales/register_deal', methods=['POST'])
def register_deal():
    data = request.json
    deal_id = str(uuid.uuid4())  # UUIDで一意のdeal_idを生成

    # 入力データを取得
    company_name = data.get('company_name')
    contact_name = data.get('contact_name')
    sales_rep_name = data.get('sales_rep_name')
    department = data.get('department')
    role_name = data.get('role_name')
    industry = data.get('industry')
    revenue = data.get('revenue')
    meeting_type = data.get('meeting_type')
    duration = data.get('duration')
    dates = data.get('dates')

    # 必須フィールドのチェック
    if not all([company_name, contact_name, sales_rep_name, industry, revenue, meeting_type, duration, dates]):
        return jsonify({'error': 'Missing required fields'}), 400

    if len(dates) > 5:
        return jsonify({'error': 'You can only provide up to 5 candidate dates.'}), 400

    # 商談候補日時を保存
    for date in dates:
        candidate = MeetingCandidate(deal_id=deal_id, date_time_start=date, duration=duration)
        db.session.add(candidate)

    # URLリンクを生成
    unique_link = f"http://localhost:3000/customer/select_date/{deal_id}"  # Next.jsのURLに変更
    expires_at = datetime.utcnow() + timedelta(days=30)

    # データベースにリンク情報を保存
    customer_link = CustomerLink(
        deal_id=deal_id,
        company_name=company_name,
        contact_name=contact_name,
        sales_rep_name=sales_rep_name,
        industry=industry,
        revenue=revenue,
        meeting_type=meeting_type,
        link=unique_link,
        expires_at=expires_at
    )
    db.session.add(customer_link)
    db.session.commit()

    # 正しいレスポンスを返す
    return jsonify({
        'message': 'Deal registered successfully',
        'link': unique_link,
        'data':data
    })

# お客様画面エンドポイント
@app.route('/customer/select_date/<deal_id>', methods=['GET'])
def select_date(deal_id):
    customer_link = CustomerLink.query.filter_by(deal_id=deal_id).first()
    if not customer_link:
        return jsonify({'error': 'Invalid deal_id'}), 404

    if is_link_expired(customer_link):
        return jsonify({'error': 'This link has expired'}), 403

    candidates = MeetingCandidate.query.filter_by(deal_id=deal_id).all()
    candidate_list = [{'id': c.id, 'start': c.date_time_start, 'duration': c.duration} for c in candidates]

    return jsonify({
        'meeting_method': customer_link.meeting_type,
        'duration': f"{candidates[0].duration}分" if candidates else "不明",
        'candidates': candidate_list,
        'industry':customer_link.industry,
        'revenue':customer_link.revenue
    })


#選択日時の保存
@app.route('/customer/confirm_date', methods=['POST'])
def confirm_date():
    data = request.json
    deal_id = data.get('deal_id')
    selected_date_time = data.get('selected_date_time')

    if not deal_id or not selected_date_time:
        return jsonify({'error': 'Missing deal_id or selected_date_time'}), 400

    response = CustomerResponse.query.filter_by(deal_id=deal_id).first()
    if not response:
        response = CustomerResponse(deal_id=deal_id)

    response.selected_date_time = selected_date_time
    db.session.add(response)
    db.session.commit()

    return jsonify({'message': 'Date confirmed successfully'})

#アンケート１の表示
@app.route('/api/survey_items', methods=['GET'])
def get_survey_items():
    industry = request.args.get('industry')
    revenue = request.args.get('revenue')
    print(industry,revenue)

    if not industry or not revenue:
        return jsonify({'error': 'Industry and revenue are required'}), 400
    columns = SurveyItem.__table__.columns
    print(columns)

# デバッグ: データベース内の全レコードを表示
    print("\nAll records in database:") 
    all_items = SurveyItem.query.all() 
    for item in all_items: 
        print(f"Industry: '{item.industry}', Revenue: '{item.revenue}'")
    
    # データベースから業種と売上に基づく設問を取得
    survey_items = SurveyItem.query.filter_by(industry=industry,revenue=revenue).all()
    if not survey_items:
        return jsonify({'error': 'No survey items found for the given criteria'}), 404

    # 設問をリスト形式で返す
    items = [{'id': item.id, 'question': item.question} for item in survey_items]
    print(items)
    return jsonify(items)


@app.route('/admin/manage_deals', methods=['GET'])
def manage_deals():
    customer_links = CustomerLink.query.all()
    deals = []
    for link in customer_links:
        response = CustomerResponse.query.filter_by(deal_id=link.deal_id).first()
        confirmed_date = response.selected_date_time if response and response.selected_date_time else "未定"
        survey1_selected = response.survey1_selected_items if response and response.survey1_selected_items else "未回答"
        survey2_selected = response.survey2_selected_items if response and response.survey2_selected_items else "未回答"

        deals.append({
            "deal_id": link.deal_id,
            "company_name": link.company_name,
            "department": link.department or "未設定",
            "position": link.position or "未設定",
            "contact_name": link.contact_name,
            "sales_rep_name": link.sales_rep_name,
            "industry": link.industry,
            "revenue": link.revenue,
            "confirmed_date": confirmed_date,
            "survey1_selected_items": survey1_selected,
            "survey2_selected_items": survey2_selected,
        })

    return jsonify(deals)


# 商談サジェスト生成エンドポイント
@app.route('/admin/generate_suggestion', methods=['POST'])
def generate_suggestion():
    data = request.json
    deal_id = data.get("deal_id")

    if not deal_id:
        return jsonify({"error": "deal_id is required"}), 400

    customer_link = CustomerLink.query.filter_by(deal_id=deal_id).first()
    if not customer_link:
        return jsonify({"error": "Invalid deal_id"}), 404

    response = CustomerResponse.query.filter_by(deal_id=deal_id).first()
    if not response:
        return jsonify({"error": "No customer response found for this deal_id"}), 404

    gpt_prompt = f"""
    あなたは営業戦略の専門家です。以下の情報を基に、次の商談に向けた考察と提案シナリオを作成してください。
    【企業情報】
    - 企業名: {customer_link.company_name}
    - 業種: {customer_link.industry}
    - 売上: {customer_link.revenue}

    【アンケート回答】
    - 優先課題: {response.survey1_priority_item}
    - 他の課題: {response.survey1_selected_items}
    - 詳細課題: {response.survey2_selected_items}

    出力形式:
    1. 考察:
    (ここに考察を記載)

    2. 提案シナリオ:
    (ここに具体的な提案シナリオを記載)
    """

    try:
        gpt_response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=gpt_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        gpt_output = gpt_response.choices[0].text.strip()

    except Exception:
        print("エラーが発生しました")

if __name__ == "__main__":
    app.run(debug=True)
