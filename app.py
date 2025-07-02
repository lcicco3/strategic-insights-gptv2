"""
Strategic Insights GPT Backend
Main Flask Application

This is the main entry point for the Strategic Insights GPT Backend API.
It provides endpoints for PubMed and ClinicalTrials.gov data integration,
vector storage with Pinecone, and AI-powered strategic insights generation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.services.pubmed_service import PubMedService
from src.services.clinicaltrials_service import ClinicalTrialsService
from src.services.vector_service import VectorService
from src.services.insights_service import InsightsService

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
pubmed_service = PubMedService()
clinicaltrials_service = ClinicalTrialsService()
vector_service = VectorService()
insights_service = InsightsService()

@app.route('/')
def home():
    """Health check and API information"""
    return jsonify({
        'message': 'Strategic Insights GPT Backend API',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'pubmed_search': '/api/pubmed/search',
            'clinicaltrials_search': '/api/clinicaltrials/search',
            'generate_insights': '/api/insights/generate',
            'vector_search': '/api/vector/search'
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'pubmed': 'available',
            'clinicaltrials': 'available',
            'vector_db': 'available',
            'insights': 'available'
        }
    })

@app.route('/api/pubmed/search', methods=['POST'])
def search_pubmed():
    """Search PubMed articles"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        max_results = data.get('max_results', 10)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        results = pubmed_service.search_articles(query, max_results)
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"PubMed search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clinicaltrials/search', methods=['POST'])
def search_clinicaltrials():
    """Search ClinicalTrials.gov studies"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        max_results = data.get('max_results', 10)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        results = clinicaltrials_service.search_studies(query, max_results)
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"ClinicalTrials search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vector/search', methods=['POST'])
def vector_search():
    """Perform semantic similarity search"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        k = data.get('k', 5)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        results = vector_service.similarity_search(query, k)
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Vector search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/generate', methods=['POST'])
def generate_insights():
    """Generate strategic insights from query"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        context_type = data.get('context_type', 'rwe')
        max_sources = data.get('max_sources', 20)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        insights = insights_service.generate_comprehensive_insights(
            query=query,
            context_type=context_type,
            max_sources=max_sources
        )
        
        return jsonify({
            'success': True,
            'query': query,
            'insights': insights
        })
        
    except Exception as e:
        logger.error(f"Insights generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk/strategic-search', methods=['POST'])
def bulk_strategic_search():
    """Perform bulk strategic search across PubMed and ClinicalTrials"""
    try:
        data = request.get_json()
        topic = data.get('topic', 'real-world evidence')
        max_results_per_source = data.get('max_results_per_source', 10)
        
        # Search PubMed
        pubmed_results = pubmed_service.bulk_strategic_search(topic, max_results_per_source)
        
        # Search ClinicalTrials
        ct_results = clinicaltrials_service.bulk_strategic_search(topic, max_results_per_source)
        
        return jsonify({
            'success': True,
            'topic': topic,
            'pubmed_results': pubmed_results,
            'clinicaltrials_results': ct_results,
            'total_count': len(pubmed_results) + len(ct_results)
        })
        
    except Exception as e:
        logger.error(f"Bulk strategic search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Strategic Insights GPT Backend on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

