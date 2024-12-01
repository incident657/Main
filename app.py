from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import folium
from geopy.geocoders import Nominatim
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory

app = Flask(__name__)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')  # Use a default fallback
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///mydatabase.db')  # Fallback for local development
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY')

    # Initialize extensions with app
db = SQLAlchemy(app)  # Initialize db with app
migrate = Migrate(app, db)  # Initialize migrate with app and db

class AuditTrail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    performed_by = db.Column(db.String(50))

    report = db.relationship('Report', backref=db.backref('audit_trail', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))  # Link to the report
    is_read = db.Column(db.Boolean, default=False)

    report = db.relationship('Report', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.id}>'

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Primary key column
    username = db.Column(db.String(50), nullable=True)  # Nullable for anonymous feedback
    feedback = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Feedback {self.id}>'

    
# Database model for reports
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    anonymous = db.Column(db.Boolean)
    username = db.Column(db.String(50))
    incident_type = db.Column(db.String(50), nullable=False) 
    severity_type = db.Column(db.String(50))
    urgency_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')

    def __repr__(self):
        return f"<Report {self.title}>"

# Initialize the database
with app.app_context():
    db.create_all()


# Geocoding function
geolocator = Nominatim(user_agent="incident_reporting")

def geocode_location(latitude, longitude):
    """Converts latitude and longitude into a human-readable address."""
    try:
        location = geolocator.reverse((latitude, longitude), language='en', timeout=10)
        if location:
            return location.address  # Return the address
        return "Unknown location"
    except Exception as e:
        print(f"Error during geocoding: {e}")
        return "Unknown location"

# Routes
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/authenticate_user', methods=['POST'])
def authenticate_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    if role == 'admin':
        if username == 'Emily Joy Flores' and password == 'adminpass':
            session['role'] = 'admin'
            session['username'] = username
            return redirect('/admin_reports')
        flash('Invalid admin credentials. Please try again.', 'error')
        return redirect('/')
    elif role == 'resident':
        session['role'] = 'resident'
        session['username'] = username
        return redirect('/resident_report')
    flash('Please select a valid role.', 'error')
    return redirect('/')

@app.route('/resident_report')
def resident_report():
    if session.get('role') != 'resident':
        return redirect('/')
    return render_template('resident_report.html')

@app.route('/submit_report', methods=['POST'])
def submit_report():
    report_title = request.form['report_title']
    report_location = request.form['report_location']
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    report_date = request.form['report_date']
    report_description = request.form['report_description']
    anonymous = request.form.get('anonymous') == 'on'
    incident_type = request.form['incident_type']
    if incident_type == "other":
        custom_incident_type = request.form.get('custom_incident_type', None)
        if custom_incident_type:
            incident_type = custom_incident_type 
    severity_type = request.form['severity_type']
    urgency_type = request.form['urgency_type']
    username = session.get('username') if not anonymous else None

    try:
        timestamp = datetime.strptime(report_date, '%b %d, %YT%I:%M %p')
    except ValueError:
        timestamp = None
            
    report_location = request.form.get('report_location')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')

    if latitude and longitude:  # Auto location detection
        latitude = float(latitude)
        longitude = float(longitude)
        # Get human-readable address
        location = geocode_location(latitude, longitude)
    else:  # Manual input
        location = report_location

    new_report = Report(
        title=report_title,
        location=location,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        timestamp=timestamp,
        description=report_description,
        anonymous=anonymous,
        username=username,
        incident_type=incident_type,
        severity_type=severity_type,
        urgency_type=urgency_type,
    )
    db.session.add(new_report)
    db.session.commit()

     # Flash a success message and redirect to the Thank You page
    flash("Report submitted successfully!", "success")
    return redirect(url_for('thank_you', anonymous='true' if anonymous else 'false'))


@app.route('/thank_you', methods=['GET'])
def thank_you():
    # Retrieve the 'anonymous' query parameter and pass it to the template
    anonymous = request.args.get('anonymous') == 'true'
    return render_template('Thank_you.html', anonymous=anonymous)  # Make sure the template exists in the templates directory

@app.route('/thank_you/<int:report_id>', methods=['GET'])
def thank_you_report(report_id):
    report = Report.query.get_or_404(report_id)
    audit_trail = AuditTrail.query.filter_by(report_id=report.id).all()
    return render_template('Thank_you.html', report=report, audit_trail=audit_trail)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    username = session.get('username', None)
    feedback_text = request.form.get('feedback')
    if feedback_text:
        feedback = Feedback(username=username, feedback=feedback_text)
        db.session.add(feedback)
        db.session.commit()
        flash("Thank you for your feedback!", "success")
    return redirect(url_for('thank_you'))

@app.route('/admin_feedbacks')
def admin_feedbacks():
    if session.get('role') != 'admin':
        return redirect('/')
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    return render_template('admin_feedbacks.html', feedbacks=feedbacks)

@app.route('/notifications')
def get_notifications():
    notifications = Notification.query.filter_by(is_read=False).all()
    return jsonify([{
        "id": n.id,
        "message": n.message,
        "report_id": n.report_id
    } for n in notifications])

# Mark a notification as read
@app.route('/mark_report_old/<int:report_id>', methods=['POST'])
def mark_report_old(report_id):
    report = Report.query.get(report_id)
    if report:
        report.is_new = False
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


# Add a new report (for testing purposes)
@app.route('/add_report', methods=['POST'])
def add_report():
    report_title = request.form.get('report_title')
    report_location = request.form.get('report_location')
    # Other form processing logic...
    new_report = Report(title=report_title, location=report_location)
    db.session.add(new_report)
    db.session.commit()

    # Create a notification for the new report
    notification_message = f"New incident reported: {report_title}"
    new_notification = Notification(message=notification_message, report_id=new_report.id)
    db.session.add(new_notification)
    db.session.commit()

    return redirect(url_for('admin_reports'))

# Database setup
@app.before_request
def setup_db():
    with app.app_context():
        db.create_all()

@app.route('/notification.html')
def notification_page():
    return render_template('notification.html')

@app.route('/admin_reports')
def admin_reports():
    if session.get('role') != 'admin':
        return redirect('/')
    try:
        reports = Report.query.all()

        # Handle the case where there are no reports
        if not reports:
            flash("No reports are available.", "info")
            return render_template('admin_reports.html', reports=[], warning_sign=False)

        # Process reports if available
        for report in reports:
            if report.timestamp:
                report.date = report.timestamp.strftime('%b %d, %Y')
                report.time = report.timestamp.strftime('%I:%M %p')

        # Check if any report is critical and urgent
        warning_sign = any(
            report.severity_type.lower() == 'critical' and report.urgency_type.lower() == 'immediate'
            for report in reports
        )

        # Retrieve highlighted report from query parameters
        highlight_report_id = request.args.get('highlight')

        return render_template(
            'admin_reports.html',
            reports=reports,
            warning_sign=warning_sign,
            highlight_report_id=highlight_report_id
        )
    except Exception as e:
        app.logger.error(f"Error in admin_reports: {e}")
        flash("An error occurred while fetching admin reports.", "error")
        return render_template('error.html')
 # Render an error page for graceful handling

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/delete_report/<int:id>', methods=['POST'])
def delete_report(id):
    report = Report.query.get(id)
    if report:
        db.session.delete(report)
        db.session.commit()
        flash("Report deleted successfully!", 'success')
    else:
        flash("Report not found!", 'error')
    return redirect('/admin_reports')

    # Apply search filter
@app.route('/search_filter_reports')
def search_filter_reports():
    search_query = request.args.get('search')
    date_filter = request.args.get('date')
    category_filter = request.args.get('category')
    status_filter = request.args.get('status')

    query = Report.query

    if search_query:
        query = query.filter(
            Report.title.ilike(f'%{search_query}%') |
            Report.location.ilike(f'%{search_query}%') |
            Report.username.ilike(f'%{search_query}%') |
            Report.incident_type.ilike(f'%{search_query}%')
        )

    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%b %d, %Y')
            query = query.filter(Report.timestamp >= date_obj)  # Replace 'timestamp' with your correct field.
        except ValueError:
            pass

    if category_filter:
        query = query.filter(Report.incident_type.ilike(f'%{category_filter}%'))

    if status_filter:
        query = query.filter(Report.status.ilike(f'%{status_filter}%'))

    reports = query.all()
    return render_template('admin_reports.html', reports=reports)

@app.route('/mark_as_done/<int:id>', methods=['POST'])
def mark_as_done(id):
    report = Report.query.get_or_404(id)
    report.status = 'Resolved'

    # Create an audit trail entry
    audit = AuditTrail(
        report_id=report.id,
        action="Report marked as resolved",
        performed_by="Admin",  # You can adjust this based on the logged-in user
    )
    db.session.add(audit)
    db.session.commit()

    return redirect(url_for('admin_reports'))

@app.route('/update_incident_type/<int:id>', methods=['POST'])
def update_incident_type(id):
    custom_incident = request.form.get('custom_incident')
    if custom_incident:
        # Update the report in the database
        report = Report.query.get_or_404(id)
        report.incident_type = custom_incident
        db.session.commit()
        flash('Incident type updated successfully.', 'success')
    else:
        flash('Custom incident type cannot be empty.', 'danger')
    return redirect(url_for('admin_reports'))

@app.route('/locate/<int:report_id>')
def locate_report(report_id):
    report = Report.query.get_or_404(report_id)
    if report.latitude and report.longitude:
        # Use Google Maps to show the report location
        return redirect(f'https://www.google.com/maps?q={report.latitude},{report.longitude}')
    else:
        flash("No location data available for this report.", "error")
        return redirect('/admin_reports')

@app.route('/fetch_new_reports', methods=['GET'])
def fetch_new_reports():
    # Get the last seen timestamp from the frontend
    last_timestamp = request.args.get('last_timestamp')
    last_seen_time = datetime.fromisoformat(last_timestamp) if last_timestamp else datetime.min

    # Fetch reports added after the last seen timestamp
    new_reports = Report.query.filter(Report.timestamp > last_seen_time).order_by(Report.timestamp).all()

    return jsonify([{
        "id": r.id,
        "title": r.title,
        "location": r.location,
        "timestamp": r.timestamp.isoformat()
    } for r in new_reports])
        
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    # Use the environment variable `PORT` or a default port (e.g., 5000)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
