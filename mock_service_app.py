from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

@app.route('/webhook/payment-confirmed', methods=['POST'])
def payment_confirmed():
    """
    Mock endpoint for N8N 'Generate Dashboard Access' node
    Returns dashboard URL and client data for email delivery
    """
    try:
        data = request.json
        print(f"Received payment confirmation: {data}")
        
        # Extract data from N8N/Stripe
        project_id = data.get('project_id', f'project-{uuid.uuid4().hex[:8]}')
        client_name = data.get('client_name', 'Test Company')
        customer_email = data.get('customer_email', 'test@example.com')
        payment_intent_id = data.get('payment_intent_id', f'pi_{uuid.uuid4().hex[:16]}')
        
        # Generate unique client identifier
        client_id = f"client-{project_id}-{uuid.uuid4().hex[:8]}"
        
        # Create dashboard URL pointing to your deployed dashboard
        dashboard_url = f"https://kfexlqqg.manussite.space/client/{client_id}"
        
        # Generate mock access token
        access_token = f"mock-token-{uuid.uuid4().hex[:16]}"
        
        # Response data for N8N email node
        response_data = {
            'dashboard_url': dashboard_url,
            'access_token': access_token,
            'project_id': project_id,
            'client_id': client_id,
            'customer_email': customer_email,
            'client_name': client_name,
            'payment_intent_id': payment_intent_id,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'success'
        }
        
        print(f"Generated dashboard access: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in payment_confirmed: {e}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/webhook/dashboard-delivered', methods=['POST'])
def dashboard_delivered():
    """
    Mock endpoint for N8N 'Confirm Delivery' node
    Confirms email was sent successfully
    """
    try:
        data = request.json
        print(f"Dashboard delivery confirmed: {data}")
        
        response_data = {
            'status': 'success',
            'project_id': data.get('project_id'),
            'dashboard_url': data.get('dashboard_url'),
            'email_sent': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in dashboard_delivered: {e}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify service is running
    """
    return jsonify({
        'status': 'healthy',
        'service': 'AXIOM Mock Integration Service',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.route('/', methods=['GET'])
def root():
    """
    Root endpoint with service information
    """
    return jsonify({
        'service': 'AXIOM Integration Service (Mock)',
        'status': 'running',
        'endpoints': {
            'payment_confirmed': '/webhook/payment-confirmed',
            'dashboard_delivered': '/webhook/dashboard-delivered',
            'health': '/health'
        },
        'description': 'Mock service for testing AXIOM dashboard delivery workflow'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

