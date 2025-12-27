#!/bin/bash
set -e

######################################
# 基础配置
######################################
MODE=${1:-github}

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
echo "🚀 启动【发布流程】"
echo "👉 发布模式：$MODE"
echo "👉 当前分支：$BRANCH"
echo "👉 当前提交：$COMMIT"
echo "======================================"
echo

######################################
# [0/6] 工作区检查 + 自动提交（UTF-8 安全）
######################################
echo "🔍 [0/6] 检查工作区状态（支持中文 / 自动提交文档）..."

AUTO_FILES=()
BLOCKING_FILES=()

# 允许自动提交的文件规则
AUTO_COMMIT_REGEX='(\.gitignore$|\.md$|git-release\.sh$|release\.sh$)'

# 使用 git porcelain -z，100% 兼容中文 / 空格
while IFS= read -r -d '' entry; do
  status="${entry:0:2}"
  file="${entry:3}"

  if [[ "$file" =~ $AUTO_COMMIT_REGEX ]]; then
    AUTO_FILES+=("$file")
  else
    BLOCKING_FILES+=("$file")
  fi
done < <(git status --porcelain -z)

# 阻断核心文件
if [[ ${#BLOCKING_FILES[@]} -gt 0 ]]; then
  echo "❌ 检测到【核心文件】未提交，发布已终止："
  for f in "${BLOCKING_FILES[@]}"; do
    echo " - $f"
  done
  echo
  echo "👉 请先提交或恢复以上文件后再发布"
  exit 1
fi

# 自动提交文档 / 脚本
if [[ ${#AUTO_FILES[@]} -gt 0 ]]; then
  echo "📝 检测到可自动提交的文件："
  for f in "${AUTO_FILES[@]}"; do
    echo " - $f"
  done

  echo
  echo "📦 正在自动提交文档 / 脚本更新..."
  git add "${AUTO_FILES[@]}"
  git commit -m "docs(chore): auto commit before release"
  echo "✅ 自动提交完成"
else
  echo "✅ 工作区干净，无需自动提交"
fi

echo

######################################
# [1/6] 同步远程仓库
######################################
echo "🔄 [1/6] 同步远程仓库（git pull --rebase）..."
git pull --rebase
echo "✅ 远程仓库同步完成"
echo

######################################
# [2/6] 生成版本号
######################################
echo "🔢 [2/6] 生成新版本号..."

[ ! -f "$VERSION_FILE" ] && echo "0.1.0" > "$VERSION_FILE"

OLD_VERSION=$(cat "$VERSION_FILE")
IFS='.' read -r M m p <<< "$OLD_VERSION"
NEW_VERSION="$M.$m.$((p+1))"

echo "$NEW_VERSION" > "$VERSION_FILE"

echo "📌 旧版本号：v$OLD_VERSION"
echo "📌 新版本号：v$NEW_VERSION"
echo

######################################
# [3/6] 生成 Release Notes
######################################
echo "📝 [3/6] 生成 Release Notes..."

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
RANGE=${LAST_TAG:+$LAST_TAG..HEAD}

cat > "$NOTES_FILE" <<EOF
## Release v$NEW_VERSION

$(git log $RANGE --pretty=format:"- %s")
EOF

echo "📎 上一个版本 Tag：${LAST_TAG:-无}"
echo "✅ Release Notes 已生成：$NOTES_FILE"
echo

######################################
# [4/6] 提交 / Tag / 推送 GitHub
######################################
echo "📦 [4/6] 提交版本信息并推送 GitHub..."

git add "$VERSION_FILE" "$NOTES_FILE"
git commit -m "chore: release v$NEW_VERSION"

git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo "⬆️ 推送代码到 GitHub..."
git push origin "$BRANCH"

echo "⬆️ 推送 Tag 到 GitHub..."
git push origin "v$NEW_VERSION"

echo "✅ GitHub 发布完成（v$NEW_VERSION）"
echo

######################################
# [5/6] 服务器发布（可选）
######################################
if [[ "$MODE" == "server" || "$MODE" == "force-server" ]]; then
  echo "🖥️ [5/6] 开始服务器发布..."

  DATE=$(date +%Y%m%d_%H%M%S)
  TARGET="$SERVER_PATH/bft_v${NEW_VERSION}_$DATE"

  echo "📂 创建服务器目录：$TARGET"
  ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_HOST" "mkdir -p $TARGET"

  echo "📤 上传项目文件到服务器..."
  scp -i "$KEY_PATH" -r \
    core services utils config scripts \
    main.py run.sh requirements.txt \
    start_conda_bft.sh VERSION \
    "$SERVER_USER@$SERVER_HOST:$TARGET"

  echo "🔗 更新 CURRENT 软链接..."
  ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_HOST" \
    "ln -sfn $TARGET $SERVER_PATH/CURRENT"

  echo "✅ 服务器发布完成"
else
  echo "ℹ️ 当前为 github 模式，跳过服务器发布"
fi

echo

######################################
# [6/6] 完成
######################################
echo "======================================"
echo "🎉 发布流程全部完成"
echo "👉 当前版本：v$NEW_VERSION"
echo "======================================"