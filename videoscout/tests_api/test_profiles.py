"""Tests for TikTok profiles API (R7b)."""
import uuid

from videoscout.db.models import TikTokProfileModel


def test_create_and_list_profiles(client, db_session):
    create = client.post(
        "/api/v1/profiles",
        json={"label": "Nurture A", "handle": "@acct_nurture", "stage": "nurture"},
    )
    assert create.status_code == 201
    data = create.json()
    assert data["stage"] == "nurture"
    assert data["handle"] == "acct_nurture"

    listed = client.get("/api/v1/profiles?stage=nurture")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_promote_nurture_to_beta(client, db_session):
    row = TikTokProfileModel(
        label="Grow account",
        handle="grow1",
        stage="nurture",
        beta_eligible=True,
    )
    db_session.add(row)
    db_session.commit()

    resp = client.post(f"/api/v1/profiles/{row.id}/promote")
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage"] == "beta"
    assert body["beta_eligible"] is False
    assert body["promoted_at"] is not None


def test_promote_beta_profile_fails(client, db_session):
    row = TikTokProfileModel(label="Beta", handle="beta1", stage="beta")
    db_session.add(row)
    db_session.commit()

    resp = client.post(f"/api/v1/profiles/{row.id}/promote")
    assert resp.status_code == 409


def test_update_beta_eligible(client, db_session):
    row = TikTokProfileModel(label="Tick", handle="tick1", stage="nurture")
    db_session.add(row)
    db_session.commit()

    resp = client.put(
        f"/api/v1/profiles/{row.id}",
        json={"beta_eligible": True},
    )
    assert resp.status_code == 200
    assert resp.json()["beta_eligible"] is True
