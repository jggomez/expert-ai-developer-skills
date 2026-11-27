"""HTTP endpoint that lists the clients to review."""
from flask import Flask, jsonify, request

from ..services.clients import clients_to_review

app = Flask(__name__)


@app.get("/clients/to-review")
def list_clients():
    owner = request.args.get("owner", "")
    return jsonify(clients_to_review("app.db", owner))
