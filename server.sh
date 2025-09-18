#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    echo "📁 Loading configuration from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  No .env file found, using defaults..."
fi

# Configuration with defaults
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-testpass123}"
TEST_NAME="${TEST_NAME:-TestUser}"

echo "🚀 Testing FitPro Backend API routes"
echo "📍 Base URL: $BASE_URL"
echo "📧 Test Email: $TEST_EMAIL"
echo "================================"

# Test server health
echo "🔍 Testing server connectivity..."
curl -s "$BASE_URL/" | jq . || echo "❌ Server not responding"

echo -e "\n📝 Testing user registration..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/app/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\"
  }")

echo "$REGISTER_RESPONSE" | jq . 2>/dev/null || echo "$REGISTER_RESPONSE"

echo -e "\n🔐 Testing user login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/app/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\"
  }")

echo "$LOGIN_RESPONSE" | jq . 2>/dev/null || echo "$LOGIN_RESPONSE"

# Extract JWT token if login successful
JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty' 2>/dev/null)

if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
    echo -e "\n🎯 JWT Token acquired! Testing protected endpoints..."
    
    echo -e "\n🎧 Testing Spotify OAuth..."
    curl -s -X GET "$BASE_URL/spotify/auth/login" \
      -H "Authorization: Bearer $JWT_TOKEN" | jq . 2>/dev/null || echo "❌ Spotify endpoint failed"
    
    echo -e "\n🏃 Testing Whoop OAuth..."
    curl -s -X GET "$BASE_URL/whoop/auth/login" \
      -H "Authorization: Bearer $JWT_TOKEN" | jq . 2>/dev/null || echo "❌ Whoop endpoint failed"

    echo -e "\n🏃 Testing Whoop Status..."
    curl -s -X GET "$BASE_URL/whoop/status" \
      -H "Authorization: Bearer $JWT_TOKEN" | jq . 2>/dev/null || echo "❌ Whoop endpoint failed"

    echo -e "\n🏃 Testing Whoop User Profile..."
    curl -s -X GET "$BASE_URL/whoop/profile" \
      -H "Authorization: Bearer $JWT_TOKEN" | jq . 2>/dev/null || echo "❌ Whoop endpoint failed"

    echo -e "\n🎧 Testing Spotify User Status..."
    curl -s -X GET "$BASE_URL/spotify/status" \
      -H "Authorization: Bearer $JWT_TOKEN" | jq . 2>/dev/null || echo "❌ Spotify status endpoint failed"

    echo -e "\n🎧 Testing Spotify User Profile..."
    curl -s -X GET "$BASE_URL/spotify/profile" \
      -H "Authorization: Bearer $JWT_TOKEN" | jq . 2>/dev/null || echo "❌ Spotify profile endpoint failed"
else
    echo "⚠️  No JWT token received - skipping protected endpoint tests"
fi

echo -e "\n✅ Test suite completed!"