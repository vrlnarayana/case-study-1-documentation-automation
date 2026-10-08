"""
LLM Client for Documentation Automation System.
Supports multiple models with fallback chain:
1. Primary: Qwen 3.8-27b
2. Secondary: kimi-k2.5-aws (or other)
3. Fallback: Template-based generation
"""

import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: Dict[str, int]
    success: bool
    error: Optional[str] = None


class LLMClient:
    """Client for LLM API calls with fallback support."""
    
    def __init__(self):
        """Initialize LLM client with fallback configuration."""
        # Primary model (Qwen)
        self.provider = os.getenv("LLM_PROVIDER", "qwen").lower()
        self.base_url = os.getenv("LLM_BASE_URL", "http://52.140.126.42:4000/v1")
        self.api_key = os.getenv("LLM_API_KEY", "sk-XMb7UMpAAHOuPIxKMH7OiQ")
        self.model = os.getenv("LLM_MODEL", "qwen3.8-27b")
        
        # Fallback model (kimi-k2.5-aws)
        self.fallback_provider = os.getenv("FALLBACK_LLM_PROVIDER", "kimi").lower()
        self.fallback_base_url = os.getenv("FALLBACK_LLM_BASE_URL", self.base_url)  # Same endpoint
        self.fallback_api_key = os.getenv("FALLBACK_LLM_API_KEY", self.api_key)  # Same key
        self.fallback_model = os.getenv("FALLBACK_LLM_MODEL", "kimi-k2.5-aws")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        print(f"[LLMClient] Primary: {self.provider}/{self.model}")
        print(f"[LLMClient] Fallback: {self.fallback_provider}/{self.fallback_model}")
        print(f"[LLMClient] Base URL: {self.base_url}")
    
    def _try_generate(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> Optional[LLMResponse]:
        """Try generation with specific configuration.
        
        Returns:
            LLMResponse on success, None on failure
        """
        try:
            # Update headers for this request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "choices" not in data or not data["choices"]:
                return None
            
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            
            return LLMResponse(
                content=content,
                model=data.get("model", model),
                usage=usage,
                success=True
            )
            
        except Exception as e:
            print(f"[LLMClient] Model {model} failed: {str(e)[:100]}")
            return None
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        use_fallback: bool = True
    ) -> LLMResponse:
        """Generate text from LLM with fallback support.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            use_fallback: Whether to try fallback model
            
        Returns:
            LLMResponse with content and metadata
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Try primary model
        print(f"[LLMClient] Trying primary model: {self.model}")
        response = self._try_generate(
            self.base_url,
            self.api_key,
            self.model,
            messages,
            temperature,
            max_tokens
        )
        
        if response and response.success:
            print(f"[LLMClient] Primary model succeeded: {self.model}")
            return response
        
        # Try fallback model if enabled
        if use_fallback and self.fallback_model != self.model:
            print(f"[LLMClient] Trying fallback model: {self.fallback_model}")
            response = self._try_generate(
                self.fallback_base_url,
                self.fallback_api_key,
                self.fallback_model,
                messages,
                temperature,
                max_tokens
            )
            
            if response and response.success:
                print(f"[LLMClient] Fallback model succeeded: {self.fallback_model}")
                return response
        
        # Both failed
        error_msg = f"All models failed. Primary: {self.model}"
        if use_fallback and self.fallback_model != self.model:
            error_msg += f", Fallback: {self.fallback_model}"
        
        return LLMResponse(
            content="",
            model="none",
            usage={},
            success=False,
            error=error_msg
        )
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Generate and parse JSON from LLM.
        
        Args:
            prompt: User prompt (should ask for JSON)
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Parsed JSON dict or error dict
        """
        response = self.generate(prompt, system_prompt, temperature, max_tokens)
        
        if not response.success:
            return {"error": response.error, "success": False}
        
        try:
            # Try to extract JSON from markdown code blocks
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            result["success"] = True
            return result
            
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse JSON: {str(e)}",
                "raw_content": response.content,
                "success": False
            }


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
