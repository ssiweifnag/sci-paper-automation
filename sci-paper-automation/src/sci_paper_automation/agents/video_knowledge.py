"""
Knowledge Distiller 整合模組
將 YouTube/Bilibili 影片轉為結構化知識
"""

import subprocess
import json
import os
from typing import List, Dict, Optional


class VideoKnowledgeExtractor:
    """從影片中提取知識"""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "google"):
        """
        初始化
        
        Args:
            api_key: AI API key（用於摘要生成）
            provider: AI provider (google/openai/anthropic)
        """
        self.api_key = api_key
        self.provider = provider
    
    def process_video(
        self, 
        url: str, 
        style: str = "academic",
        language: str = "zh",
        summary: bool = True
    ) -> Dict:
        """
        處理影片 URL
        
        Args:
            url: YouTube 或 Bilibili URL
            style: 摘要風格 (standard/academic/actions/news/investment/podcast/eli5/bullets)
            language: 語言代碼 (zh/yue/en)
            summary: 是否生成摘要
        
        Returns:
            包含 transcript 和 summary 的字典
        """
        cmd = ["kd", "process", url, "--style", style, "--language", language]
        
        if not summary:
            cmd.append("--no-summary")
        
        if self.api_key:
            # 設定 API key
            subprocess.run(
                ["kd", "config", "set", "provider", self.provider],
                capture_output=True
            )
            subprocess.run(
                ["kd", "config", "set", "api-key", self.api_key],
                capture_output=True
            )
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "url": url,
            "style": style,
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    def transcribe_only(self, url: str) -> Dict:
        """
        只做轉錄，不做摘要（不需要 API key）
        
        Args:
            url: 影片 URL
        
        Returns:
            轉錄結果
        """
        cmd = ["kd", "transcribe", url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "url": url,
            "success": result.returncode == 0,
            "transcript": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    def get_styles(self) -> List[Dict]:
        """取得所有可用的摘要風格"""
        result = subprocess.run(["kd", "styles"], capture_output=True, text=True)
        
        styles = []
        lines = result.stdout.split("\n")
        current_style = None
        
        for line in lines:
            if line.strip().startswith("-"):
                key = line.strip().replace("-", "").strip()
                current_style = key
                styles.append({"key": key, "name": "", "description": ""})
            elif current_style and "Name:" in line:
                styles[-1]["name"] = line.split("Name:")[1].strip()
            elif current_style and "Description:" in line:
                styles[-1]["description"] = line.split("Description:")[1].strip()
        
        return styles
    
    def configure(self, provider: str, api_key: str) -> bool:
        """設定 AI provider 和 API key"""
        try:
            subprocess.run(
                ["kd", "config", "set", "provider", provider],
                capture_output=True, check=True
            )
            subprocess.run(
                ["kd", "config", "set", "api-key", api_key],
                capture_output=True, check=True
            )
            self.provider = provider
            self.api_key = api_key
            return True
        except Exception as e:
            return False


def extract_video_knowledge(
    url: str,
    style: str = "academic",
    api_key: Optional[str] = None,
    provider: str = "google"
) -> Dict:
    """
    便捷函數：快速提取影片知識
    
    Args:
        url: 影片 URL
        style: 摘要風格
        api_key: AI API key
        provider: AI provider
    
    Returns:
        知識提取結果
    """
    extractor = VideoKnowledgeExtractor(api_key=api_key, provider=provider)
    return extractor.process_video(url, style=style)
