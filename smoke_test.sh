#!/bin/bash
# -----------------------------------------------------------------------------
# Smoke Test Script for Secure File Sharing VPS Deployment
# Verify that the API and required services are running smoothly.
# -----------------------------------------------------------------------------

set -e

# Configuration
TARGET_URL="${TARGET_URL:-https://localhost}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting smoke tests against ${TARGET_URL}${NC}"

# Helper to print success/failure
check_status() {
    local endpoint=$1
    local expected=$2
    local method=${3:-GET}
    local extra_args=${4:-""}
    
    echo -n "Testing $method $endpoint ... "
    
    # Use curl with -k to allow self-signed certificates during testing
    # Capture HTTP status code
    local status=$(curl -s -k -o /dev/null -w "%{http_code}" -X $method $extra_args "${TARGET_URL}${endpoint}")
    
    if [ "$status" -eq "$expected" ]; then
        echo -e "${GREEN}PASS (Status: $status)${NC}"
    else
        echo -e "${RED}FAIL (Expected: $expected, Got: $status)${NC}"
        exit 1
    fi
}

# 1. Test Swagger UI mapping (checks if FastAPI is responsive)
check_status "/docs" 200

# 2. Test OpenAPI JSON
check_status "/openapi.json" 200

# 3. Test Invalid Route
check_status "/api/does-not-exist" 404

# 4. Test User Registration (Creates a test user for smoke testing)
RANDOM_STR=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 8 || echo "abc123yz")
TEST_USER="smoke_test_${RANDOM_STR}"
TEST_EMAIL="${TEST_USER}@example.com"
TEST_PASS="TestPass123!"

echo -n "Testing account creation... "
REGISTER_DATA="{\"username\": \"$TEST_USER\", \"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASS\"}"
STATUS=$(curl -s -k -o /dev/null -w "%{http_code}" -X POST "${TARGET_URL}/register" -H "Content-Type: application/json" -d "$REGISTER_DATA")

if [ "$STATUS" -eq 201 ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN (Status: $STATUS - user may already exist)${NC}"
fi

# 5. Test Login and Token Generation
echo -n "Testing login flow... "
LOGIN_DATA="username=${TEST_USER}&password=${TEST_PASS}"
LOGIN_RESP=$(curl -s -k -X POST "${TARGET_URL}/auth/login" -H "Content-Type: application/x-www-form-urlencoded" -d "$LOGIN_DATA")

TOKEN=$(echo $LOGIN_RESP | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}PASS (Token retrieved)${NC}"
else
    echo -e "${RED}FAIL (Could not extract token)${NC}"
    exit 1
fi

# 6. Test Authenticated Request (Files list)
check_status "/files/" 200 "GET" "-H \"Authorization: Bearer ${TOKEN}\""

# 7. Test Nginx specific header (if applicable)
# We can check if Nginx is returning its Server header
echo -n "Checking Server header... "
SERVER_HEADER=$(curl -s -k -I "${TARGET_URL}/docs" | grep -i "^server:" | tr -d '\r\n')
if [[ "$SERVER_HEADER" == *"nginx"* ]]; then
    echo -e "${GREEN}PASS ($SERVER_HEADER)${NC}"
else
    echo -e "${YELLOW}WARN (Does not look like Nginx is serving the exact proxy header, got: $SERVER_HEADER)${NC}"
fi

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}All smoke tests completed successfully!${NC}"
echo -e "${GREEN}=====================================${NC}"
