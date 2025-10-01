from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
# Allow cross-origin requests so the static HTML can POST from localhost or file://
CORS(app, resources={r"/v1/*": {"origins": "*"}})

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    if not submission.submission_id:
        email_norm = submission.email.lower().strip()
        hour_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        raw = f"{email_norm}{hour_stamp}"
        submission_id = sha256(raw.encode()).hexdigest()
        submission.submission_id = submission_id
    else:
        submission_id = submission.submission_id

    record = StoredSurveyRecord(
        **submission.dict(),
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )

    record.email = compute_sha256(record.email)
    record.age = compute_sha256(record.age)

    #Computed the hash of the connactination of email 
    # in the format of email + YYYYMMDDHH and set record.submission_id
    record.submission_id = compute_sha256(record.email + datetime.now().strftime("%Y%m%d%H"))

    # 
    # do the same for the age and calculating the age in the record

    append_json_line(record.dict())
    return jsonify({"status": "ok"}), 201

#this function computes the sha256 of the value that is passed in and return a string
def compute_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

if __name__ == "__main__":
    app.run(port=0, debug=True)
