"""Tests for experiments API endpoints."""
import uuid


def test_create_experiment(client):
    resp = client.post(
        "/api/v1/experiments",
        json={
            "keyword": "aespa winter fancam",
            "suggestion_source": "agent_suggested",
            "agent_suggested_score": 78,
            "channel_id": "UC_test",
            "channel_subscribers": 23000,
            "creator_avg_views": 2000,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["keyword"] == "aespa winter fancam"
    assert data["test_status"] == "in_progress"
    assert data["agent_suggested_score"] == 78
    assert data["views_vs_baseline"] is None
    assert data["suggestion_id"] is None
    assert data["prediction_signals"] is None


def test_create_experiment_with_suggestion_snapshots_prediction_signals(
    client, db_session, sample_suggestion
):
    sample_suggestion.platform_signals = {
        "agent": {
            "risk_flags": ["single_viral_source", "search_sample_bias"],
            "validation": {
                "validation_status": "weakened",
                "pattern_assessment": "mixed",
                "adjustments": {
                    "generalizability": 0.0,
                    "video_performance": -0.12,
                    "confidence": -0.12,
                    "saturation": 0.05,
                },
                "risk_flags": ["single_viral_source"],
                "validation_rationale": "Sample-shape saturation undo (+0.05) applied (n=5).",
            },
            "confidence": 0.6,
            "component_reasons": {"relevance": "should not be snapshotted"},
        }
    }
    db_session.commit()

    resp = client.post(
        "/api/v1/experiments",
        json={
            "keyword": sample_suggestion.keyword,
            "suggestion_source": "agent_suggested",
            "agent_suggested_score": 80,
            "predicted_score": 80,
            "suggestion_id": str(sample_suggestion.id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["suggestion_id"] == str(sample_suggestion.id)
    assert data["prediction_signals"]["risk_flags"] == [
        "single_viral_source",
        "search_sample_bias",
    ]
    assert data["prediction_signals"]["validation"]["validation_status"] == "weakened"
    assert data["prediction_signals"]["validation"]["adjustments"]["saturation"] == 0.05
    assert "component_reasons" not in data["prediction_signals"]


def test_create_experiment_unknown_suggestion_id_returns_400(client):
    resp = client.post(
        "/api/v1/experiments",
        json={
            "keyword": "orphan experiment keyword",
            "suggestion_source": "agent_suggested",
            "suggestion_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 400
    assert "not found" in resp.json()["error"]["message"].lower()


def test_list_experiments(client):
    client.post(
        "/api/v1/experiments",
        json={
            "keyword": "kpop dance trend",
            "suggestion_source": "user_manual",
            "channel_id": "UC_test_list",
        },
    )
    client.post(
        "/api/v1/experiments",
        json={
            "keyword": "kdrama ost shorts",
            "suggestion_source": "agent_suggested",
            "agent_suggested_score": 81,
        },
    )

    resp = client.get("/api/v1/experiments?status=in_progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    keywords = [item["keyword"] for item in data["items"]]
    assert "kpop dance trend" in keywords
    assert "kdrama ost shorts" in keywords


def test_report_experiment(client):
    create_resp = client.post(
        "/api/v1/experiments",
        json={
            "keyword": "tiktok choreography idea",
            "suggestion_source": "agent_suggested",
            "agent_suggested_score": 75,
            "creator_avg_views": 10000,
            "predicted_score": 75,
        },
    )
    experiment_id = create_resp.json()["id"]

    report_resp = client.post(
        f"/api/v1/experiments/{experiment_id}/report",
        json={
            "actual_views": 12000,
            "actual_engagement": 13.0,
            "actual_retention": 0.42,
            "user_rating": 4,
            "test_status": "success",
        },
    )
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert report_data["actual_views"] == 12000
    assert report_data["actual_engagement"] == 13.0
    assert report_data["actual_retention"] == 0.42
    assert report_data["test_status"] == "success"
    assert 1.19 <= report_data["views_vs_baseline"] <= 1.21
    assert 0.82 <= report_data["accuracy"] <= 0.83
    assert report_data["outcome_type"] == "true_positive"


def test_analyze_experiments(client):
    payloads = [
        {
            "keyword": "viral dance challenge",
            "predicted_score": 80,
            "actual_views": 300,
            "actual_engagement": 3.5,
            "test_status": "failed",
        },
        {
            "keyword": "viral shorts trend",
            "predicted_score": 78,
            "actual_views": 250,
            "actual_engagement": 3.0,
            "test_status": "failed",
        },
        {
            "keyword": "viral dance move",
            "predicted_score": 82,
            "actual_views": 350,
            "actual_engagement": 4.0,
            "test_status": "failed",
        },
    ]

    for payload in payloads:
        created = client.post(
            "/api/v1/experiments",
            json={
                "keyword": payload["keyword"],
                "suggestion_source": "agent_suggested",
                "agent_suggested_score": payload["predicted_score"],
                "predicted_score": payload["predicted_score"],
                "creator_avg_views": 1000,
            },
        )
        experiment_id = created.json()["id"]
        report = client.post(
            f"/api/v1/experiments/{experiment_id}/report",
            json={
                "actual_views": payload["actual_views"],
                "actual_engagement": payload["actual_engagement"],
                "test_status": payload["test_status"],
            },
        )
        assert report.status_code == 200

    analyze_resp = client.post("/api/v1/experiments/analyze")
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["total_experiments"] == 3
    assert len(data["patterns"]) >= 1
    assert len(data["weight_suggestions"]) >= 1
