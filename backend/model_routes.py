"""
model_routes.py — Model management API routes for SCIP Guardian Orchestrator

Add these routes to orchestrator.py:

    from model_routes import register_model_routes
    register_model_routes(app, supabase)

Exposes:
    GET  /api/model/stats        — current model stats
    POST /api/model/train        — retrain on existing data
    POST /api/model/seed         — seed training data via OpenRouter + train
"""

from flask import Blueprint, jsonify, request


def register_model_routes(app, supabase):
    """Register model management routes on the Flask app."""

    def _auth(req):
        """Returns user_id or None."""
        auth = req.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return None
        token = auth.split(' ')[1]
        try:
            resp = supabase.auth.get_user(token)
            return resp.user.id if resp.user else None
        except Exception:
            return None

    @app.route('/api/model/stats', methods=['GET'])
    def model_stats():
        """Return current custom model stats."""
        user_id = _auth(request)
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from custom_model import CustomSecurityModel
            model = CustomSecurityModel()
            return jsonify(model.get_stats()), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/model/train', methods=['POST'])
    def model_train():
        """Retrain the custom model on all existing data."""
        user_id = _auth(request)
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from model_trainer import ModelTrainer
            trainer = ModelTrainer()
            result  = trainer.retrain()
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/model/seed', methods=['POST'])
    def model_seed():
        """
        Generate synthetic training data via OpenRouter and train the model.
        This is the "teach" endpoint — run once after setup to bootstrap the model.
        Optional body: { "delay": 0.3 }
        """
        user_id = _auth(request)
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            from model_trainer import ModelTrainer
            data    = request.json or {}
            delay   = float(data.get('delay', 0.5))
            trainer = ModelTrainer()
            result  = trainer.seed(delay=delay)
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500