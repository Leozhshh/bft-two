#!/bin/bash

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null)
if [ -z "$LAST_TAG" ]; then
  echo "No previous tag found. Generating notes for all commits."
  RANGE=""
else
  RANGE="$LAST_TAG..HEAD"
fi

echo "### ✨ Features"
git log $RANGE --pretty=format:"- %s" | grep "^feat" || echo "(none)"

echo ""
echo "### 🐞 Fixes"
git log $RANGE --pretty=format:"- %s" | grep "^fix" || echo "(none)"

echo ""
echo "### 🔧 Refactors"
git log $RANGE --pretty=format:"- %s" | grep "^refactor" || echo "(none)"

echo ""
echo "### 📚 Docs"
git log $RANGE --pretty=format:"- %s" | grep "^docs" || echo "(none)"

echo ""
echo "### 🧹 Chores"
git log $RANGE --pretty=format:"- %s" | grep "^chore" || echo "(none)"

