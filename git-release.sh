#!/bin/bash
set -e

######################################
# 基础配置
######################################
SERVER_USER="zhshh"
SERVER_HOST="4.241.224.39"
SERVER_PATH="/home/zhshh/bft_release"
KEY_PATH="$HOME/.ssh/id_rsa"

VERSION_FILE="VERSION"
NOTES_FILE="RELEASE_NOTES.md"

######################################
# 基础信息
######################################
BRANCH=$(git branch --show-current)
COMMIT=$(git log -1 --oneline)

echo "======================================"
echo "🚀 启动【GitHub + 服务器发布流程】"
echo "👉 当前分支：$BRANCH"
echo "👉 当前提交：$COMMIT"
echo "======================================"
echo

######################################
# [0/7] 工作区检查 + 自动提交（UTF-8 安全）
######################################
echo "🔍 [0/7] 检查工作区状态（自动提交文档 / 脚本）..."

AUTO_FILES=()
BLOCKING_FILES=()

AUTO_COMMIT_REGEX='(\.gitignore$|\.md$|git-release\.sh$|release\.sh$)'

while IFS= read -r -d '' entry; do
  file="${entry:3}"

  if [[ "$file" =~ $AUTO_COMMIT_REGEX ]]; then
    AUTO_FILES+=("$file")
  else
    BLOCKING_FILES+=("$file")
  fi
done < <(git status --porcelain -z)

if [[ ${#BLOCKING_FILES[@]} -gt 0 ]]; then
  echo "❌ 检测到【核心文件】未提交，发布已终止："
  for f in "${BLOCKING_FILES[@]}"; do
    echo " - $f"
  done
  exit 1
fi

if [[ ${#AUTO_FILES[@]} -gt 0 ]]; then
  echo "📝 自动提交以下文件："
  for f in "${AUTO_FILES[@]}"; do echo " - $f"; done
  git add "${AUTO_FILES[@]}"
  git commit -m "docs(chore): auto commit before release"
  echo "✅ 文档提交完成"
else
  echo "✅ 工作区干净"
fi

echo

######################################
# [1/7] 同步远程
######################################
echo "🔄 [1/7] 同步远程仓库..."
git pull --rebase
echo "✅ 同步完成"
echo

######################################
# [2/7] 版本号
######################################
echo "🔢 [2/7] 生成新版本号..."

[ ! -f "$VERSION_FILE" ] && echo "0.1.0" > "$VERSION_FILE"

OLD_VERSION=$(cat "$VERSION_FILE")
IFS='.' read -r M m p <<< "$OLD_VERSION"
NEW_VERSION="$M.$m.$((p+1))"

echo "$NEW_VERSION" > "$VERSION_FILE"

echo "📌 旧版本号：v$OLD_VERSION"
echo "📌 新版本号：v$NEW_VERSION"
echo

######################################
# [3/7] Release Notes
######################################
echo "📝 [3/7] 生成 Release Notes..."

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
RANGE=${LAST_TAG:+$LAST_TAG..HEAD}

cat > "$NOTES_FILE" <<EOF
## Release v$NEW_VERSION

$(git log $RANGE --pretty=format:"- %s")
EOF

echo "✅ Release Notes 已生成"
echo

######################################
# [4/7] GitHub 提交 / Tag / Push
######################################
echo "📦 [4/7] 发布到 GitHub..."

git add "$VERSION_FILE" "$NOTES_FILE"
git commit -m "chore: release v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

git push origin "$BRANCH"
git push origin "v$NEW_VERSION"

echo "✅ GitHub 发布完成（v$NEW_VERSION）"
echo

######################################
# [5/7] 服务器发布（必然执行）
######################################
echo "🖥️ [5/7] 开始服务器发布..."

DATE=$(date +%Y%m%d_%H%M%S)
TARGET="$SERVER_PATH/bft_v${NEW_VERSION}_$DATE"

echo "📂 创建服务器目录：$TARGET"
ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_HOST" "mkdir -p $TARGET"

echo "📤 拷贝代码到服务器..."
scp -i "$KEY_PATH" -r \
  core services utils config scripts \
  main.py run.sh requirements.txt \
  start_conda_bft.sh VERSION \
  "$SERVER_USER@$SERVER_HOST:$TARGET"

echo "🔗 更新 CURRENT 软链接..."
ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_HOST" \
  "ln -sfn $TARGET $SERVER_PATH/CURRENT"

echo "✅ 服务器发布完成"
echo

######################################
# [6/7] 结束
######################################
echo "======================================"
echo "🎉 发布完成"
echo "👉 GitHub Tag：v$NEW_VERSION"
echo "👉 服务器目录：$TARGET"
echo "======================================"