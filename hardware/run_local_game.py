#!/usr/bin/env python3
"""
hardware 폴더 내에서 바로 실행할 수 있는 바로가기 진입점
"""
import os
import sys

# 프로젝트 루트를 sys.path에 추가
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from run_local_game import LocalGameRunner

if __name__ == "__main__":
    runner = LocalGameRunner()
    runner.start()
