"""
MIT-WPU Vyas Smart-Room Maintenance Tracker
Run script to start the Flask development server.
"""
import os
# FixLink-V1 - Entry Point
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Import socketio here to get the initialized instance from app module
    from app import socketio
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    print("=" * 60)
    print("MIT-WPU Vyas Smart-Room Maintenance Tracker")
    print("=" * 60)
    print(f"Server: http://localhost:{port}")
    print(f"Student Portal: http://localhost:{port}/report")
    print(f"Admin Dashboard: http://localhost:{port}/admin")
    print("=" * 60)
    
    if socketio:
        socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
    else:
        print("Error: SocketIO instance not found. Starting without SocketIO...")
        app.run(host='0.0.0.0', port=port, debug=debug)
