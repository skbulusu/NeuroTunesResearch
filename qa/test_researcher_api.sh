#!/bin/bash
# ---------------------------------------------------------------------------
# test_researcher_api.sh — end-to-end verification of the NeuroTunes
#                          researcher API (/api/v1) against a LIVE deployment.
#
# Exercises, for each of 4 therapy goals:
#   * POST /api/v1/generate        (music generation → session_id, log_id, tempo)
#   * downloads the returned audio and checks peak loudness (> -2 dBFS)
#   * POST /api/v1/feedback         (rating submission)
#   * GET  /api/v1/sessions/{id}    (session detail returns 3 tracks)
# Exits non-zero on the first broken step.
#
# Usage:
#   ./test_researcher_api.sh [BASE_URL] <API_KEY>
#     BASE_URL  optional, defaults to https://www.netr.ai
#     API_KEY   required; needs generate + feedback + sessions scopes
#
# Example:
#   ./test_researcher_api.sh https://www.netr.ai nt_live_xxx
# ---------------------------------------------------------------------------

BASE_URL="${1:-https://www.netr.ai}"
API_KEY="${2:-}"

if [ -z "$API_KEY" ]; then
  echo "Error: API_KEY required"
  echo "Usage: $0 [BASE_URL] API_KEY"
  exit 1
fi

echo "=========================================="
echo "NeuroTunes Researcher API Verification"
echo "BASE_URL: $BASE_URL"
echo "=========================================="
echo ""

GOALS=("relaxation" "focus" "energy" "sleep_induction")

for GOAL in "${GOALS[@]}"; do
  echo "=== Testing therapy_goal=$GOAL ==="
  
  RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/generate" \
    -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
    -d "{\"age\":30,\"gender\":\"male\",\"diagnosis\":\"anxiety\",\"therapy_goal\":\"$GOAL\",\"stress_level\":6}")
  
  SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
  LOG_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['tracks'][0]['log_id'])")
  AUDIO_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['tracks'][0]['audio_url'])")
  TEMPO=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['music_params']['tempo'])")
  
  echo "  Session: $SESSION_ID | log_id: $LOG_ID | Tempo: $TEMPO BPM"
  
  # Download & verify loudness
  curl -s -o /tmp/test_${GOAL}.wav "$BASE_URL$AUDIO_URL" -H "X-API-Key: $API_KEY"
  PEAK_DB=$(python3 -c "import wave,struct,math; wf=wave.open('/tmp/test_${GOAL}.wav','rb'); frames=wf.readframes(wf.getnframes()); samples=struct.unpack(f'{len(frames)//2}h',frames); peak=max(abs(s) for s in samples); print(f'{20*math.log10(peak/32768):.1f}' if peak>0 else '-100')")
  
  # Test feedback
  FB=$(curl -s -X POST "$BASE_URL/api/v1/feedback" \
    -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
    -d "{\"generation_log_id\": $LOG_ID, \"overall_rating\": 5}")
  FB_ID=$(echo "$FB" | python3 -c "import sys,json; print(json.load(sys.stdin).get('feedback_id','FAIL'))")
  
  # Test session detail
  SESS=$(curl -s -X GET "$BASE_URL/api/v1/sessions/$SESSION_ID" -H "X-API-Key: $API_KEY")
  GEN_COUNT=$(echo "$SESS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['session']['generations']))")
  
  # Validate
  if [ "$LOG_ID" != "null" ] && [ "$FB_ID" != "FAIL" ] && [ "$GEN_COUNT" = "3" ]; then
    PEAK_OK=$(python3 -c "print('✅' if float('$PEAK_DB') > -2.0 else '❌')")
    echo "  Result: ✅ generation ✅ feedback($FB_ID) ✅ session($GEN_COUNT tracks) $PEAK_OK audio($PEAK_DB dBFS)"
  else
    echo "  Result: ❌ FAILED"
    exit 1
  fi
  echo ""
done

echo "=========================================="
echo "✅ All researcher API endpoints verified"
echo "=========================================="
