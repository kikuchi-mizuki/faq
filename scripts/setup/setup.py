#!/usr/bin/env python3
"""
LINE Q&A自動応答システム セットアップスクリプト
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def run_command(command, description):
    """コマンドを実行"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✅ {description}完了")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失敗: {e}")
        print(f"エラー出力: {e.stderr}")
        return False


def check_python_version():
    """Pythonバージョンの確認"""
    print("🐍 Pythonバージョンを確認中...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9以上が必要です。現在のバージョン: {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_poetry():
    """Poetryの確認・インストール"""
    print("📦 Poetryの確認中...")
    try:
        result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
        print(f"✅ Poetry {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("❌ Poetryがインストールされていません")
        print("Poetryのインストール方法:")
        print("curl -sSL https://install.python-poetry.org | python3 -")
        return False


def install_dependencies():
    """依存関係のインストール"""
    print("📚 依存関係をインストール中...")
    if not run_command("poetry install", "依存関係のインストール"):
        return False

    # 開発用依存関係もインストール
    if not run_command("poetry install --with dev", "開発用依存関係のインストール"):
        return False

    return True


def create_env_file():
    """環境変数ファイルの作成"""
    print("🔧 環境変数ファイルの作成中...")
    env_file = Path(".env")
    env_example = Path("env.example")

    if env_file.exists():
        print("✅ .envファイルは既に存在します")
        return True

    if env_example.exists():
        # env.exampleをコピーして.envを作成
        with open(env_example, "r", encoding="utf-8") as f:
            content = f.read()

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ .envファイルを作成しました")
        print("⚠️  必ず環境変数を実際の値に設定してください")
        return True
    else:
        print("❌ env.exampleファイルが見つかりません")
        return False


def run_tests():
    """テストの実行"""
    print("🧪 テストを実行中...")
    if not run_command("poetry run pytest tests/ -v", "テストの実行"):
        print("⚠️  テストに失敗しましたが、セットアップは続行します")
        return True
    return True


def check_code_quality():
    """コード品質チェック"""
    print("🔍 コード品質をチェック中...")

    # Blackによるフォーマットチェック
    if not run_command("poetry run black --check .", "コードフォーマットチェック"):
        print("⚠️  コードフォーマットに問題があります")
        print("poetry run black . を実行してフォーマットを修正してください")

    # Flake8によるリントチェック
    if not run_command("poetry run flake8 .", "リントチェック"):
        print("⚠️  リントに問題があります")

    return True


def create_directories():
    """必要なディレクトリの作成"""
    print("📁 ディレクトリを作成中...")
    directories = ["logs", "data", "temp"]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ {directory}/ ディレクトリを作成しました")

    return True


def main():
    """メイン処理"""
    print("🚀 LINE Q&A自動応答システム セットアップを開始します")
    print("=" * 50)

    # 基本的なチェック
    if not check_python_version():
        sys.exit(1)

    if not check_poetry():
        sys.exit(1)

    # 依存関係のインストール
    if not install_dependencies():
        print("❌ 依存関係のインストールに失敗しました")
        sys.exit(1)

    # 環境変数ファイルの作成
    if not create_env_file():
        print("❌ 環境変数ファイルの作成に失敗しました")
        sys.exit(1)

    # ディレクトリの作成
    if not create_directories():
        print("❌ ディレクトリの作成に失敗しました")
        sys.exit(1)

    # テストの実行
    run_tests()

    # コード品質チェック
    check_code_quality()

    print("\n" + "=" * 50)
    print("🎉 セットアップが完了しました！")
    print("\n次のステップ:")
    print("1. .envファイルの環境変数を設定してください")
    print("2. Google Sheets APIの設定を行ってください")
    print("3. LINE Messaging APIの設定を行ってください")
    print("4. poetry run dev でアプリケーションを起動してください")
    print("\n詳細はREADME.mdを参照してください")


if __name__ == "__main__":
    main()
