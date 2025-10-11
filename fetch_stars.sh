#!/bin/bash
# This script fetches your starred repositories from GitHub and saves them to stars.json

echo "Fetching starred repositories from GitHub..."
gh api --paginate /user/starred > stars.json
echo "Successfully fetched stars and saved to stars.json"