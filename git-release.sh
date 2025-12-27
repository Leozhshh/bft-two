#!/bin/bash
set -e

######################################
# 固定配置
######################################
SERVER_USER="zhshh"
SERVER_HOST="4.241.224.39"
SERVER_PATH="/home/zhshh/bft_release"
KEY_PATH="$HOME/.ssh/id_ed25519.pub"

VERSION_FILE="VERSION"
NOTES_FILE="RELEASE_NOTES.md"
KEEP_COUNT=9

######################################
# 基础信息
######################################
BRANCH=$(git branch --show-current)
COMMIT=$(git rev-parse --short HEAD)

echo "======================================"
echo "🚀 启动【全自动发布流程】"
echo "👉 当前分支：$BRANCH"
echo "👉 当前提交：$COMMIT"
echo "======================================"
echo

######################################
# [0/8] 自动提交文档 / 脚本
######################################
echo "🔍 [0/8] 检测并自动提交文档 / 脚本..."

AUTO_FILES=$(git status --porcelain | \
grep -E '\.md$|\.sh$|\.gitignore$' || true)

if [[ -n "$AUTO_FILES" ]]; then
  echo "📄 发现以下文件将被自动提交："
  echo "$AUTO_FILES"
  git add .
  git commit -m "docs(chore): auto update docs and scripts"
  git push
  echo "✅ 文档 / 脚本已提交"
else
  echo "✅ 无需提交文档 / 脚本"
fi
echo

######################################
# [1/8] 同步远程
######################################
echo "🔄 [1/8] 同步远程 main..."
git pull --rebase
echo "✅ 同步完成"
echo

######################################
# [2/8] 生成新版本号
######################################
echo "🔢 [2/8] 生成新版本号..."

[ ! -f "$VERSION_FILE" ] && echo "0.1.0" > "$VERSION_FILE"

IFS='.' read -r M m p < "$VERSION_FILE"
OLD_VERSION="$M.$m.$p"
NEW_VERSION="$M.$m.$((p+1))"

echo "📌 旧版本：v$OLD_VERSION"
echo "📌 新版本：v$NEW_VERSION"

echo "$NEW_VERSION" > "$VERSION_FILE"
echo

######################################
# [3/8] 生成 Release Notes
######################################
echo "📝 [3/8] 生成 Release Notes..."

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
RANGE=${LAST_TAG:+$LAST_TAG..HEAD}

cat > "$NOTES_FILE" <<EOF
## Release v$NEW_VERSION

$(git log $RANGE --pretty=format:"- %s")
EOF

echo "✅ Release Notes 生成完成"
echo

######################################
# [4/8] 提交版本并创建 Tag
######################################
echo "📦 [4/8] 提交版本并创建 Tag..."

git add "$VERSION_FILE" "$NOTES_FILE"
git commit -m "chore: release v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

git push
git push --tags

echo "✅ GitHub 发布完成（v$NEW_VERSION）"
echo

######################################
# [5/8] 服务器部署
######################################
echo "🚀 [5/8] 开始服务器部署..."

DATE=$(date +%Y%m%d_%H%M%S)
TARGET="$SERVER_PATH/bft_v${NEW_VERSION}_$DATE"

ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_HOST" "mkdir -p $TARGET"

scp -i "$KEY_PATH" -r \
  core services utils config main.py run.sh requirements.txt \
  start_conda_bft.sh VERSION \
  "$SERVER_USER@$SERVER_HOST:$TARGET"

ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_HOST" <<EOF
cd "$SERVER_PATH"
ln -sfn "$TARGET" CURRENT
EOF

echo "✅ 服务器已切换至新版本：$TARGET"
echo

######################################
# [6/8] 清理服务器旧版本
######################################
echo "🧹 [6/8] 清理服务器旧版本（保留最近 $KEEP_COUNT 个）..."

ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_HOST" <<EOF
cd "$SERVER_PATH"

CURRENT_DIR=\$(readlink CURRENT | xargs basename)
VERSIONS=\$(ls -dt bft_v* 2>/dev/null || true)

COUNT=0
for dir in \$VERSIONS; do
  [ "\$dir" = "\$CURRENT_DIR" ] && continue
  COUNT=\$((COUNT + 1))
  if [ "\$COUNT" -gt "$KEEP_COUNT" ]; then
    echo "🗑️ 删除旧版本：\$dir"
    rm -rf "\$dir"
  else
    echo "📦 保留版本：\$dir"
  fi
done
EOF

echo "✅ 旧版本清理完成"
echo

######################################
# [7/8] 完成
######################################
echo "======================================"
echo "🎉 全自动发布完成"
echo "👉 当前版本：v$NEW_VERSION"
echo "======================================"