#!/bin/bash

# 历史记录导入导出插件构建脚本

echo "开始构建历史记录导入导出插件..."

# 进入web目录
cd "$(dirname "$0")/web"

# 检查是否存在node_modules
if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    npm install
fi

# 构建项目
echo "构建Vue联邦模块..."
npm run build

# 复制构建文件到dist目录
echo "复制构建文件..."
cp -r dist/* ../dist/

echo "构建完成！"
echo "联邦模块入口: /assets/remoteEntry.js"