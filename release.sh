#!/bin/bash

set -e

# ------------------------------
# 配置服务器信息
# ------------------------------
SERVER_USER="zhshh"
SERVER_HOST="4.241.224.39"
SERVER_PATH="/home/zhshh/bft_release"

VERSION_FILE="VERSION"
NOTES_FILE="RELEASE_NOTES.md"

# ------------------------------
# 0. 生成最新目录结构（覆盖 shuoming.md）
# ------------------------------
echo "📄 正在生成最新目录结构..."

# 覆盖写入 shuoming.md
tree -L 4 > shuoming.md

# 提交更新（如果没有变化则忽略错误）
git add shuoming.md
git commit -m "docs: update directory tree before release" || true

# 推送更新
git push

echo "✅ 已更新 shuoming.md（已覆盖旧内容）"

echo "🚀 开始发布流程..."

# ------------------------------
# 0. 自动同步远程 main（避免 non-fast-forward）
# ------------------------------
echo "🔄 正在同步远程 main..."
git pull --rebase || {
  echo "❌ 自动 rebase 失败，请手动解决冲突"
  exit 1
}
echo "✅ 已同步远程 main"


# ------------------------------
# 1. 自动生成版本号
# ------------------------------
if [ ! -f "$VERSION_FILE" ]; then
  echo "0.1.0" > $VERSION_FILE
fi

VERSION=$(cat $VERSION_FILE)
IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"
PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo $NEW_VERSION > $VERSION_FILE

echo "✅ 新版本号：v$NEW_VERSION"


# ------------------------------
# 2. 自动生成 Release Notes
# ------------------------------
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -z "$LAST_TAG" ]; then
  RANGE=""
  echo "⚠️ 未找到历史 tag，生成所有提交的 Release Notes"
else
  RANGE="$LAST_TAG..HEAD"
fi

{
echo "## Release v$NEW_VERSION"
echo ""
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
} > $NOTES_FILE

echo "✅ Release Notes 已生成：$NOTES_FILE"


# ------------------------------
# 3. 创建 Git Tag
# ------------------------------
git add $VERSION_FILE
git commit -m "chore: bump version to v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo "✅ 已创建 tag：v$NEW_VERSION"


# ------------------------------
# 4. 推送 Tag
# ------------------------------
git push
git push --tags

echo "✅ 已推送 tag 到 GitLab"


# ------------------------------
# 5. 自动创建 GitLab Release（可选）
# ------------------------------
if [ -z "$GITLAB_TOKEN" ] || [ -z "$GITLAB_PROJECT_ID" ]; then
  echo "⚠️ 未设置 GITLAB_TOKEN 或 GITLAB_PROJECT_ID，跳过 GitLab Release 创建"
else
  echo "📦 正在创建 GitLab Release..."
  curl --request POST \
    --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    --data "name=Release v$NEW_VERSION" \
    --data "tag_name=v$NEW_VERSION" \
    --data-urlencode "description=$(cat $NOTES_FILE)" \
    "http://你的GitLab地址/api/v4/projects/$GITLAB_PROJECT_ID/releases"

  echo "✅ GitLab Release 已创建：v$NEW_VERSION"
fi


# ------------------------------
# 6. 拷贝代码到服务器（按版本号）
# ------------------------------
DATE=$(date +%Y%m%d)
TIME=$(date +%H%M)
VERSION_DIR="${SERVER_PATH}/bft_v${NEW_VERSION}_${DATE}_${TIME}"

echo "🚚 正在将代码同步到服务器 ${SERVER_HOST}..."
echo "📁 目标目录：${VERSION_DIR}"

ssh -i "${KEY_PATH}" ${SERVER_USER}@${SERVER_HOST} "mkdir -p ${VERSION_DIR}"

scp -i "${KEY_PATH}" -r \
    BinanceFuturesTestnet \
    mingling \
    VERSION \
    README.md \
    start_conda_bft.sh \
    ${SERVER_USER}@${SERVER_HOST}:${VERSION_DIR}

echo "✅ 代码已同步到服务器：${VERSION_DIR}"


# ------------------------------
# 7. 自动清理旧版本（只保留最近 15 个）
# ------------------------------
echo "🧹 正在清理旧版本..."

ssh ${SERVER_USER}@${SERVER_HOST} "
  cd ${SERVER_PATH} && \
  ls -dt bft_v* | tail -n +16 | xargs -I {} rm -rf {}
"
echo "✅ 已清理旧版本，只保留最近 15 个"

echo "🎉 发布完成！"
