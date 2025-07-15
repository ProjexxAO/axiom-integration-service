from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta
import os
import json
import logging

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///axiom_enterprise.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'axiom-enterprise-secret-key')

db = SQLAlchemy(app)

# Database Models
class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.String(255), primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    complexity_score = db.Column(db.Integer, nullable=False)
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(255), nullable=False)
    mentor_name = db.Column(db.String(100), nullable=False)
    mentor_title = db.Column(db.String(255), nullable=False)
    ai_confidence = db.Column(db.Float, default=99.5)
    processing_time = db.Column(db.String(10), default='2m')
    solutions_count = db.Column(db.Integer, default=3)
    customer_email = db.Column(db.String(255), nullable=False)
    payment_intent_id = db.Column(db.String(255))
    
    # JSON fields for complex data
    business_context = db.Column(db.Text)  # JSON string
    current_challenges = db.Column(db.Text)  # JSON string
    recommended_solutions = db.Column(db.Text)  # JSON string
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_name': self.company_name,
            'industry': self.industry,
            'complexity_score': self.complexity_score,
            'assessment_date': self.assessment_date.isoformat() if self.assessment_date else None,
            'session_id': self.session_id,
            'customer_email': self.customer_email,
            'mentor': {
                'name': self.mentor_name,
                'title': self.mentor_title,
                'avatar': '/api/placeholder/40/40',
                'industry_specialization': self.industry
            },
            'assessment_summary': {
                'complexity_score': self.complexity_score,
                'ai_confidence': f"{self.ai_confidence}%",
                'processing_time': self.processing_time,
                'solutions_count': self.solutions_count
            },
            'business_context': json.loads(self.business_context) if self.business_context else {},
            'current_challenges': json.loads(self.current_challenges) if self.current_challenges else [],
            'recommended_solutions': json.loads(self.recommended_solutions) if self.recommended_solutions else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Reminder(db.Model):
    __tablename__ = 'reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(255), db.ForeignKey('clients.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False)  # high, medium, low
    category = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, dismissed
    ai_generated = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'category': self.category,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'ai_generated': self.ai_generated,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(255), db.ForeignKey('clients.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100), nullable=False)
    file_type = db.Column(db.String(50))
    tags = db.Column(db.Text)  # JSON string
    is_favorite = db.Column(db.Boolean, default=False)
    download_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'file_type': self.file_type,
            'tags': json.loads(self.tags) if self.tags else [],
            'is_favorite': self.is_favorite,
            'download_count': self.download_count,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ProgressMetric(db.Model):
    __tablename__ = 'progress_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(255), db.ForeignKey('clients.id'), nullable=False)
    metric_name = db.Column(db.String(255), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_type': self.metric_type,
            'category': self.category,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }

# Initialize database
with app.app_context():
    db.create_all()

@app.route('/webhook/payment-confirmed', methods=['POST'])
def payment_confirmed():
    """
    Enhanced endpoint for N8N 'Generate Dashboard Access' node
    Creates client record and returns dashboard URL with enterprise features
    """
    try:
        data = request.json
        print(f"Received payment confirmation: {data}")
        
        # Extract client information from N8N/Stripe data
        client_info = extract_client_info_from_n8n(data)
        
        # Create unique client ID
        client_id = f"{client_info['company_name'].lower().replace(' ', '-')}-{client_info['session_id']}"
        
        # Check if client already exists
        existing_client = Client.query.get(client_id)
        if existing_client:
            dashboard_url = f"https://ivfstuba.manus.space/client/{client_id}"
            access_token = generate_access_token(client_id)
            
            return jsonify({
                'dashboard_url': dashboard_url,
                'access_token': access_token,
                'client_id': client_id,
                'customer_email': client_info['customer_email'],
                'client_name': client_info['company_name'],
                'status': 'existing_client',
                'created_at': existing_client.created_at.isoformat()
            })
        
        # Create new client record with enterprise features
        client = create_enterprise_client(client_id, client_info)
        
        # Initialize enterprise dashboard data
        initialize_enterprise_features(client_id, client_info)
        
        # Generate dashboard access
        dashboard_url = f"https://ivfstuba.manus.space/client/{client_id}"
        access_token = generate_access_token(client_id)
        
        response_data = {
            'dashboard_url': dashboard_url,
            'access_token': access_token,
            'client_id': client_id,
            'customer_email': client_info['customer_email'],
            'client_name': client_info['company_name'],
            'payment_intent_id': client_info.get('payment_intent_id'),
            'status': 'success',
            'created_at': datetime.utcnow().isoformat(),
            'enterprise_features': {
                'ai_reminders': True,
                'progress_tracking': True,
                'document_hub': True,
                'team_management': True
            }
        }
        
        print(f"Created enterprise client: {client_id}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in payment_confirmed: {e}")
        logging.error(f"Payment confirmation error: {e}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/api/clients/<client_id>', methods=['GET'])
def get_client(client_id):
    """Get client data by ID"""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'success': False, 'error': 'Client not found'}), 404
        
        return jsonify({
            'success': True,
            'data': client.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clients/<client_id>/reminders', methods=['GET'])
def get_reminders(client_id):
    """Get all reminders for a client"""
    try:
        reminders = Reminder.query.filter_by(client_id=client_id).all()
        return jsonify({
            'success': True,
            'data': [reminder.to_dict() for reminder in reminders]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clients/<client_id>/documents', methods=['GET'])
def get_documents(client_id):
    """Get all documents for a client"""
    try:
        documents = Document.query.filter_by(client_id=client_id).all()
        return jsonify({
            'success': True,
            'data': [doc.to_dict() for doc in documents]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clients/<client_id>/progress', methods=['GET'])
def get_progress(client_id):
    """Get progress metrics for a client"""
    try:
        metrics = ProgressMetric.query.filter_by(client_id=client_id).all()
        return jsonify({
            'success': True,
            'data': [metric.to_dict() for metric in metrics]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/webhook/dashboard-delivered', methods=['POST'])
def dashboard_delivered():
    """
    Enhanced endpoint for N8N 'Confirm Delivery' node
    """
    try:
        data = request.json
        print(f"Dashboard delivery confirmed: {data}")
        
        response_data = {
            'status': 'success',
            'client_id': data.get('client_id'),
            'dashboard_url': data.get('dashboard_url'),
            'email_sent': True,
            'timestamp': datetime.utcnow().isoformat(),
            'enterprise_features_active': True
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in dashboard_delivered: {e}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'AXIOM Enterprise Integration Service',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0',
        'features': ['client_management', 'ai_reminders', 'progress_tracking', 'document_hub']
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with service information"""
    return jsonify({
        'service': 'AXIOM Enterprise Integration Service',
        'status': 'running',
        'version': '2.0.0',
        'endpoints': {
            'payment_confirmed': '/webhook/payment-confirmed',
            'dashboard_delivered': '/webhook/dashboard-delivered',
            'client_data': '/api/clients/<client_id>',
            'health': '/health'
        },
        'description': 'Enterprise service for AXIOM dashboard delivery with full client management'
    })

def extract_client_info_from_n8n(data):
    """Extract client information from N8N data"""
    # Handle both old format and new format
    if 'stripe_data' in data:
        stripe_data = data['stripe_data']
        customer_email = stripe_data.get('customer_email', 'unknown@example.com')
        customer_name = stripe_data.get('customer_details', {}).get('name', 'Unknown Customer')
        metadata = stripe_data.get('metadata', {})
        company_name = metadata.get('company_name', customer_name)
        industry = metadata.get('industry', 'Technology')
        complexity_score = int(metadata.get('complexity_score', 43))
        session_id = stripe_data.get('id', str(uuid.uuid4())[:12])
        payment_intent_id = stripe_data.get('id')
    else:
        # Legacy format support
        customer_email = data.get('customer_email', 'unknown@example.com')
        customer_name = data.get('client_name', 'Unknown Customer')
        company_name = data.get('client_name', customer_name)
        industry = 'Technology'
        complexity_score = 43
        session_id = data.get('project_id', str(uuid.uuid4())[:12])
        payment_intent_id = data.get('payment_intent_id')
    
    return {
        'customer_email': customer_email,
        'customer_name': customer_name,
        'company_name': company_name,
        'industry': industry,
        'complexity_score': complexity_score,
        'session_id': session_id,
        'payment_intent_id': payment_intent_id
    }

def create_enterprise_client(client_id, client_info):
    """Create a new enterprise client record"""
    business_context = generate_business_context(client_info)
    current_challenges = generate_challenges(client_info)
    recommended_solutions = generate_solutions(client_info)
    mentor = assign_mentor(client_info['industry'])
    
    client = Client(
        id=client_id,
        company_name=client_info['company_name'],
        industry=client_info['industry'],
        complexity_score=client_info['complexity_score'],
        session_id=client_info['session_id'],
        customer_email=client_info['customer_email'],
        payment_intent_id=client_info.get('payment_intent_id'),
        mentor_name=mentor['name'],
        mentor_title=mentor['title'],
        ai_confidence=calculate_ai_confidence(client_info['complexity_score']),
        processing_time=calculate_processing_time(client_info['complexity_score']),
        solutions_count=len(recommended_solutions),
        business_context=json.dumps(business_context),
        current_challenges=json.dumps(current_challenges),
        recommended_solutions=json.dumps(recommended_solutions)
    )
    
    db.session.add(client)
    db.session.commit()
    return client

def initialize_enterprise_features(client_id, client_info):
    """Initialize enterprise features for new client"""
    create_ai_reminders(client_id, client_info)
    create_client_documents(client_id, client_info)
    create_progress_baseline(client_id, client_info)

def create_ai_reminders(client_id, client_info):
    """Create AI-powered reminders"""
    complexity = client_info['complexity_score']
    industry = client_info['industry']
    
    reminders_data = [
        {
            'title': 'Strategic Assessment Deep Dive',
            'description': f'Given your complexity score of {complexity}, we recommend a comprehensive strategic assessment within the first week.',
            'priority': 'high',
            'category': 'Strategic Planning',
            'due_date': datetime.now() + timedelta(days=7)
        },
        {
            'title': 'AI Analysis Update',
            'description': 'Review latest AI-generated insights on operational efficiency improvements.',
            'priority': 'medium',
            'category': 'AI Insights',
            'due_date': datetime.now() + timedelta(days=14)
        },
        {
            'title': 'Team Alignment Session',
            'description': 'Schedule cross-functional alignment meeting for strategic initiatives.',
            'priority': 'medium',
            'category': 'Team Management',
            'due_date': datetime.now() + timedelta(days=21)
        }
    ]
    
    for reminder_data in reminders_data:
        reminder = Reminder(client_id=client_id, **reminder_data)
        db.session.add(reminder)
    
    db.session.commit()

def create_client_documents(client_id, client_info):
    """Create initial document set"""
    company_name = client_info['company_name']
    industry = client_info['industry']
    
    documents_data = [
        {
            'title': f'{company_name} Strategic Implementation Roadmap',
            'description': f'Customized strategic roadmap for {company_name}',
            'category': 'Strategic',
            'file_type': 'pdf',
            'tags': json.dumps(['roadmap', 'strategy', company_name.lower()])
        },
        {
            'title': f'{company_name} Complexity Assessment Report',
            'description': f'Detailed complexity analysis for {company_name}',
            'category': 'Analysis',
            'file_type': 'pdf',
            'tags': json.dumps(['analysis', 'complexity', company_name.lower()])
        },
        {
            'title': f'{industry} Industry Best Practices',
            'description': f'Industry-specific best practices for {industry}',
            'category': 'Operational',
            'file_type': 'pdf',
            'tags': json.dumps(['best-practices', industry.lower()])
        }
    ]
    
    for doc_data in documents_data:
        document = Document(client_id=client_id, **doc_data)
        db.session.add(document)
    
    db.session.commit()

def create_progress_baseline(client_id, client_info):
    """Create baseline progress metrics"""
    complexity = client_info['complexity_score']
    initial_progress = max(0, 100 - complexity)
    
    metrics_data = [
        {'metric_name': 'Implementation Progress', 'metric_value': initial_progress, 'metric_type': 'percentage', 'category': 'Overall'},
        {'metric_name': 'Strategic Initiatives', 'metric_value': 0, 'metric_type': 'count', 'category': 'Strategy'},
        {'metric_name': 'Team Engagement', 'metric_value': 95 - (complexity * 0.5), 'metric_type': 'percentage', 'category': 'Team'},
        {'metric_name': 'Risk Mitigation', 'metric_value': 25, 'metric_type': 'percentage', 'category': 'Risk'}
    ]
    
    for metric_data in metrics_data:
        metric = ProgressMetric(client_id=client_id, **metric_data)
        db.session.add(metric)
    
    db.session.commit()

def generate_business_context(client_info):
    """Generate business context"""
    return {
        "company_overview": f"{client_info['company_name']} is a dynamic organization in the {client_info['industry']} sector, committed to strategic excellence.",
        "market_position": f"Established player in the {client_info['industry']} market with growth opportunities.",
        "strategic_focus": "Accelerating organizational effectiveness through strategic implementation."
    }

def generate_challenges(client_info):
    """Generate challenges based on complexity and industry"""
    complexity = client_info['complexity_score']
    industry = client_info['industry']
    
    challenges = []
    
    if complexity > 40:
        challenges.append({
            "id": 1,
            "title": "High Complexity Operations",
            "description": "Managing complex operational processes requiring strategic optimization."
        })
    
    if industry == 'Technology':
        challenges.append({
            "id": 2,
            "title": "Rapid Technology Evolution",
            "description": "Keeping pace with rapidly evolving technology landscape."
        })
    elif industry == 'Manufacturing':
        challenges.append({
            "id": 2,
            "title": "Supply Chain Optimization",
            "description": "Optimizing complex supply chain operations for efficiency."
        })
    
    challenges.append({
        "id": 3,
        "title": "Strategic Implementation Scaling",
        "description": "Scaling strategic initiatives across the organization effectively."
    })
    
    return challenges

def generate_solutions(client_info):
    """Generate solutions based on assessment"""
    complexity = client_info['complexity_score']
    
    return [
        {
            "id": 1,
            "title": "Strategic Excellence Framework",
            "description": "Comprehensive framework for managing strategic initiatives",
            "complexity_reduction": f"{min(40, complexity)}%",
            "implementation_time": "3-4 months",
            "roi_estimate": "250-350%"
        },
        {
            "id": 2,
            "title": "Operational Optimization Platform",
            "description": "Integrated platform for streamlining operations",
            "complexity_reduction": f"{min(30, complexity * 0.7)}%",
            "implementation_time": "2-3 months",
            "roi_estimate": "180-250%"
        },
        {
            "id": 3,
            "title": "AI-Powered Analytics Suite",
            "description": "Advanced analytics for data-driven decision making",
            "complexity_reduction": f"{min(25, complexity * 0.6)}%",
            "implementation_time": "4-6 months",
            "roi_estimate": "200-300%"
        }
    ]

def assign_mentor(industry):
    """Assign mentor based on industry"""
    mentors = {
        'Technology': {'name': 'Alex Chen', 'title': 'Technology Innovation Advisor'},
        'Manufacturing': {'name': 'Sarah Johnson', 'title': 'Manufacturing Excellence Advisor'},
        'Healthcare': {'name': 'Dr. Michael Roberts', 'title': 'Healthcare Strategy Advisor'},
        'Finance': {'name': 'David Williams', 'title': 'Financial Services Advisor'}
    }
    return mentors.get(industry, {'name': 'Alex Thompson', 'title': 'Strategic Implementation Advisor'})

def calculate_ai_confidence(complexity_score):
    """Calculate AI confidence based on complexity"""
    return max(85.0, 100.0 - (complexity_score * 0.3))

def calculate_processing_time(complexity_score):
    """Calculate processing time based on complexity"""
    if complexity_score < 30:
        return "1m"
    elif complexity_score < 50:
        return "2m"
    else:
        return "3m"

def generate_access_token(client_id):
    """Generate secure access token"""
    return f"axiom_{client_id}_{uuid.uuid4().hex[:16]}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)



