import pytest
from fastapi.testclient import TestClient

import api.main as api
import core.llm


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setenv("LLM_PROVIDER", "mock")
    mp.setenv("LLM_MODEL", "mock-1")
    mp.setenv("Q2D_RETRIEVAL", "tfidf")
    mp.setattr(core.llm, "CACHE_DIR", tmp_path_factory.mktemp("llm"))
    api.resources.cache_clear()
    yield TestClient(api.app)
    api.resources.cache_clear()
    mp.undo()


def run_dialogue(client, system, message):
    r = client.post("/api/session", json={"message": message, "system": system})
    assert r.status_code == 200, r.text
    body = r.json()
    sid, turn = body["session_id"], body["turn"]
    steps = 0
    while turn["action"] == "ask":
        assert turn["question"]["text"]
        options = turn["question"].get("options") or []
        payload = {"text": "not sure", "value": options[0]["value"]} if options else {"text": "not sure"}
        turn = client.post(f"/api/session/{sid}/answer", json=payload).json()["turn"]
        steps += 1
        assert steps <= 7
    assert turn["result"]["predicted"]
    return sid, body


def test_demo_uses_the_saved_clarity_estimate(client):
    # A(q) belongs to the mock-user model in configs/experiment.yaml, not to the system LLM.
    from core.clarity import load_clarity
    saved = load_clarity("groq/openai/gpt-oss-120b")
    assert saved and api.resources()["clarity"] == saved


def test_systems_and_stats(client):
    systems = client.get("/api/systems").json()
    assert systems["default"] == "q2d" and len(systems["systems"]) == 8
    stats = client.get("/api/benchmark/stats").json()
    assert stats["n_cases"] == 300 and len(stats["example"]["variants"]) == 7


def test_q2d_session_and_trace(client):
    sid, body = run_dialogue(client, "q2d", "fridge cooling agalla compressor sound ide")
    first = body["turn"]
    assert "understanding" in first and {"H_L", "H_D", "H"} <= set(first["belief"])
    assert all("status" in s for s in first["fault_state"].values())
    trace = client.get(f"/api/session/{sid}/trace").json()
    assert trace["turns"][0]["t"] == 0 and trace["turns"][-1]["result"]
    assert client.post(f"/api/session/{sid}/answer", json={"text": "yes"}).status_code == 409


@pytest.mark.parametrize("system", ["b1_direct", "b2_llm_questions", "b3_infogain_dx"])
def test_baseline_sessions(client, system):
    run_dialogue(client, system, "my fridge is not cooling")


def test_unknown_session_and_system(client):
    assert client.post("/api/session/nope/answer", json={"text": "x"}).status_code == 404
    assert client.post("/api/session", json={"message": "x", "system": "gpt"}).status_code == 400


def test_results_side_endpoints_follow_the_saved_runs(client):
    if not (api.RESULTS / "latest.json").exists():
        assert client.get("/api/results/example").status_code == 404
        return
    ex = client.get("/api/results/example")
    assert ex.status_code == 200 and ex.json()["message"] and ex.json()["turns"]
    for row in client.get("/api/results/sensitivity").json():
        assert row["weights"] and "q2d" in row["systems"]


def test_conversation_survives_a_server_restart(client):
    message = "fridge not cooling, compressor sound ide"
    first = client.post("/api/session", json={"message": message, "system": "q2d"}).json()
    sid, turn = first["session_id"], first["turn"]
    if turn["action"] != "ask":
        pytest.skip("the mock run answered at once")
    option = turn["question"]["options"][0]
    reply = {"text": option["label"], "value": option["value"]}
    expected = client.post(f"/api/session/{sid}/answer", json=reply).json()["turn"]

    api.SESSIONS.clear()   # what a restart does to the in-memory sessions
    assert client.post(f"/api/session/{sid}/answer", json=reply).status_code == 404
    rebuilt = client.post(f"/api/session/{sid}/answer",
                          json={**reply, "message": message, "system": "q2d", "history": []})
    assert rebuilt.status_code == 200, rebuilt.text
    assert rebuilt.json()["turn"]["belief"] == expected["belief"]
    assert rebuilt.json()["turn"]["question"] == expected["question"]


def test_errors_are_readable_json(client):
    r = client.post("/api/session/nope/answer", json={"text": "yes"})
    assert r.status_code == 404 and "expired" in r.json()["detail"]
    assert client.get("/api/health").json()["ok"] is True
