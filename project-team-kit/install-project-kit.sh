#!/bin/bash

# Project Team Kit Installer / 项目团队套件安装器

KIT_SOURCE="$HOME/.openclaw/templates/project-team-kit"
PROJECT_DIR="$1"

if [ -z "$PROJECT_DIR" ]; then
  echo "Usage: ./install-project-kit.sh /path/to/project"
  exit 1
fi

echo "Installing Project Team Kit to: $PROJECT_DIR"
echo "---"

# Create project directory if it doesn't exist
mkdir -p "$PROJECT_DIR"

# Copy all files
cp -r "$KIT_SOURCE"/* "$PROJECT_DIR/"

echo "✓ Copied kit files to $PROJECT_DIR"
echo ""
echo "Next steps:"
echo "1. cd $PROJECT_DIR"
echo "2. Edit PROJECT-IDENTITY.md with your project details"
echo "3. Update project type: [New Project - Ongoing Project - Completed Project]"
echo "4. Have OpenClaw read context to initialize"
echo ""
echo "Files installed:"
ls -1 "$PROJECT_DIR"/*.md | grep -v "^$"
echo ""
echo "Ready to use! Read README.md for details."
