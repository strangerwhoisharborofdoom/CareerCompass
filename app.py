"""CareerCompass - Course Recommendation Backend
Author: Your Name
Version: 1.0.0
Description: Intelligent course recommendation system using ranking algorithm
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RankingAlgorithm:
    """Scoring and ranking algorithm for course recommendations"""

    @staticmethod
    def calculate_score(program, student_profile):
        """Calculate compatibility score between student and program"""
        score = 0
        breakdown = {}
        
        # Budget fit (max 30 points)
        if program['cost'] <= student_profile['budget']:
            score += 30
            breakdown['budget'] = 30
        else:
            score += max(0, 30 - (program['cost'] - student_profile['budget']) / 100)
            breakdown['budget'] = score - sum(breakdown.values())
        
        # Duration fit (max 25 points)
        if program['duration_months'] <= student_profile['max_duration']:
            score += 25
            breakdown['duration'] = 25
        
        # Placement match (max 20 points)
        if program['placement_rate'] >= 0.75:
            score += 20
            breakdown['placement'] = 20
        elif program['placement_rate'] >= 0.50:
            score += 10
            breakdown['placement'] = 10
        
        # Mode preference (max 15 points)
        if program['mode'] == student_profile['preferred_mode']:
            score += 15
            breakdown['mode'] = 15
        
        # Location preference (max 10 points)
        if program['location'].lower() == student_profile['location'].lower():
            score += 10
            breakdown['location'] = 10
        
        return round(min(score, 100), 2), breakdown


class CourseRecommender:
    """Main recommendation engine"""
    
    def __init__(self):
        self.programs = self.load_programs()
    
    def load_programs(self):
        """Load course programs from data file"""
        try:
            with open('data/programs.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error('Programs data file not found')
            return []
    
    def get_recommendations(self, student_profile, limit=5):
        """Get ranked recommendations for a student"""
        if not self.programs:
            return []
        
        recommendations = []
        for program in self.programs:
            score, breakdown = RankingAlgorithm.calculate_score(
                program, student_profile
            )
            recommendations.append({
                **program,
                'match_score': score,
                'score_breakdown': breakdown
            })
        
        # Sort by score descending
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        return recommendations[:limit]


# Initialize recommender
recommender = CourseRecommender()


# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200


@app.route('/api/recommend', methods=['POST'])
def recommend():
    """Main recommendation endpoint"""
    try:
        data = request.json
        
        # Validate input
        required = ['budget', 'max_duration', 'preferred_mode', 'location']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        student_profile = {
            'budget': int(data.get('budget', 500000)),
            'max_duration': int(data.get('max_duration', 12)),
            'preferred_mode': data.get('preferred_mode', 'online'),
            'location': data.get('location', 'Bengaluru')
        }
        
        recommendations = recommender.get_recommendations(
            student_profile,
            limit=int(data.get('limit', 5))
        )
        
        return jsonify({
            'status': 'success',
            'count': len(recommendations),
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f'Error in recommendation: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/programs', methods=['GET'])
def get_all_programs():
    """Get all available programs"""
    return jsonify({
        'total': len(recommender.programs),
        'programs': recommender.programs
    }), 200


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get platform statistics"""
    programs = recommender.programs
    if not programs:
        return jsonify({'error': 'No programs available'}), 404
    
    avg_cost = sum(p['cost'] for p in programs) / len(programs)
    avg_duration = sum(p['duration_months'] for p in programs) / len(programs)
    avg_placement = sum(p['placement_rate'] for p in programs) / len(programs)
    
    return jsonify({
        'total_programs': len(programs),
        'avg_cost': round(avg_cost, 2),
        'avg_duration_months': round(avg_duration, 2),
        'avg_placement_rate': round(avg_placement * 100, 2),
        'modes': list(set(p['mode'] for p in programs)),
        'locations': list(set(p['location'] for p in programs))
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
